"""F1 Race Analytics — Streamlit dashboard entrypoint.

All business logic lives in ``src/``; this file only wires filters, layout and charts together.
Run with:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import itertools

import numpy as np
import pandas as pd
import streamlit as st

from src import analytics as an
from src import visualizations as viz
from src.data_loader import F1DataError, get_available_seasons
from src.pipeline import build_dataset

st.set_page_config(page_title="F1 Race Analytics", page_icon="🏎️", layout="wide")

MAX_SEASONS = 10          # keeps first-time downloads within the API's rate limits
ALL_RACES = "All races"
DATA_SOURCE_NOTE = (
    "Data: [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) (community-run, Ergast-compatible; "
    "**not official Formula 1 data**). Coverage 1950–present; qualifying data mostly from 1994; "
    "sprint points included from 2021."
)

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1400px;}
h1.f1-title {font-size: 2.6rem; font-weight: 800; letter-spacing: -0.5px; margin: 0;}
h1.f1-title span {color: #E10600;}
p.f1-sub {color: #9AA0AB; margin: 0 0 1.2rem 0; font-size: 1.05rem;}
.kpi {background: #161A23; border: 1px solid #2A2F3A; border-left: 4px solid #E10600;
      border-radius: 6px; padding: 14px 16px; margin-bottom: 12px;}
.kpi-label {color: #9AA0AB; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;}
.kpi-value {font-size: 1.9rem; font-weight: 700; line-height: 1.2;}
.insight {background: #161A23; border: 1px solid #2A2F3A; border-left: 4px solid #00D2BE;
          border-radius: 6px; padding: 12px 16px; margin: 6px 0 14px 0;}
.footer {text-align: center; color: #9AA0AB; font-size: .85rem; margin-top: 2.5rem;
         padding-top: 1rem; border-top: 1px solid #2A2F3A;}
</style>
""", unsafe_allow_html=True)

_keys = itertools.count()


def show_fig(fig) -> None:
    st.plotly_chart(fig, theme=None, key=f"fig{next(_keys)}")


def show_df(df: pd.DataFrame, **kwargs) -> None:
    try:
        st.dataframe(df, hide_index=True, width="stretch", **kwargs)
    except TypeError:                       # older Streamlit versions
        st.dataframe(df, hide_index=True, use_container_width=True, **kwargs)


def kpi_card(label: str, value: str) -> None:
    st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)


def fmt(value, spec: str = ",.0f", signed: bool = False) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    return format(value, ("+" if signed else "") + spec)


# --------------------------------------------------------------------------- header
st.markdown('<h1 class="f1-title">F1 <span>Race</span> Analytics</h1>', unsafe_allow_html=True)
st.markdown('<p class="f1-sub">Data-driven insights from Formula 1 racing</p>', unsafe_allow_html=True)


# --------------------------------------------------------------------- cached loaders
@st.cache_data(ttl=3600, show_spinner=False)
def cached_seasons() -> list[int]:
    return get_available_seasons()


@st.cache_data(ttl=1800, show_spinner=False)
def cached_dataset(seasons: tuple[int, ...]):
    return build_dataset(list(seasons))


# ------------------------------------------------------------------------- sidebar
st.sidebar.markdown("## 🏁 Filters")
reset_slot = st.sidebar.container()

try:
    all_seasons = cached_seasons()
except F1DataError as exc:
    st.error(f"**Could not load the season list.** {exc}")
    st.stop()

this_year = dt.date.today().year
completed = [s for s in all_seasons if s < this_year]
default_season = max(completed) if completed else max(all_seasons)
DEFAULT_RANGE = (default_season, default_season)

saved = st.session_state.get("flt_seasons")
if not (isinstance(saved, (tuple, list)) and len(saved) == 2
        and all(s in all_seasons for s in saved)):
    st.session_state["flt_seasons"] = DEFAULT_RANGE
for key, default in (("flt_drivers", []), ("flt_constructors", []), ("flt_circuits", []),
                     ("flt_race", ALL_RACES)):
    st.session_state.setdefault(key, default)


def reset_filters() -> None:
    st.session_state.update(flt_seasons=DEFAULT_RANGE, flt_drivers=[], flt_constructors=[],
                            flt_circuits=[], flt_race=ALL_RACES)


s_from, s_to = st.sidebar.slider("Season", min_value=min(all_seasons), max_value=max(all_seasons),
                                  key="flt_seasons")
selected_seasons = [s for s in all_seasons if s_from <= s <= s_to]
if len(selected_seasons) > MAX_SEASONS:
    selected_seasons = selected_seasons[-MAX_SEASONS:]
    st.sidebar.warning(f"Showing the latest {MAX_SEASONS} seasons of your range "
                       "(keeps downloads within the API rate limits).")

try:
    with st.spinner("Loading race data… the first download of a season can take ~10–20 seconds."):
        df, notes = cached_dataset(tuple(selected_seasons))
except F1DataError as exc:
    st.error(f"**Could not load F1 data.** {exc}")
    st.stop()
except Exception as exc:                    # noqa: BLE001 - last-resort guard for the UI
    st.error("Something unexpected went wrong while loading data.")
    with st.expander("Technical details"):
        st.exception(exc)
    st.stop()

for note in notes:
    st.warning(note)
if df.empty:
    st.warning("No usable race data for the selected seasons. Try a different range.")
    st.stop()


def sanitize(key: str, options: list) -> None:
    st.session_state[key] = [v for v in st.session_state[key] if v in options]


driver_opts = sorted(df["driver_name"].dropna().unique())
constructor_opts = sorted(df["constructor_name"].dropna().unique())
circuit_opts = sorted(df["circuit_name"].dropna().unique())
for k, opts in (("flt_drivers", driver_opts), ("flt_constructors", constructor_opts),
                ("flt_circuits", circuit_opts)):
    sanitize(k, opts)

st.sidebar.multiselect("Driver", driver_opts, key="flt_drivers", placeholder="All drivers")
st.sidebar.multiselect("Constructor / team", constructor_opts, key="flt_constructors",
                       placeholder="All constructors")
st.sidebar.multiselect("Circuit", circuit_opts, key="flt_circuits", placeholder="All circuits")

# `scope` = everything except the driver filter (used where we need whole teams / whole grids)
scope = df
if st.session_state["flt_constructors"]:
    scope = scope[scope["constructor_name"].isin(st.session_state["flt_constructors"])]
if st.session_state["flt_circuits"]:
    scope = scope[scope["circuit_name"].isin(st.session_state["flt_circuits"])]

race_opts = [ALL_RACES] + list(scope.sort_values("race_index")["race_label"].drop_duplicates())
if st.session_state["flt_race"] not in race_opts:
    st.session_state["flt_race"] = ALL_RACES
st.sidebar.selectbox("Race", race_opts, key="flt_race")
if st.session_state["flt_race"] != ALL_RACES:
    scope = scope[scope["race_label"] == st.session_state["flt_race"]]

f = scope[scope["driver_name"].isin(st.session_state["flt_drivers"])] if st.session_state["flt_drivers"] else scope

reset_slot.button("↺ Reset Filters", on_click=reset_filters)
st.sidebar.caption(DATA_SOURCE_NOTE)

if f.empty:
    st.warning("No races match the current filters (for example, a driver who did not race for the "
               "selected team). Adjust the filters or press **Reset Filters**.")
    st.stop()

# ------------------------------------------------------------------------ KPI cards
k = an.kpis(f)
st.caption(f"{len(f):,} race entries · {f['race_index'].nunique()} races · "
           f"seasons {s_from}–{s_to}")
row1, row2 = st.columns(4), st.columns(4)
cards = [("Wins", fmt(k["wins"])), ("Podiums", fmt(k["podiums"])), ("Points", fmt(k["points"], ",.1f")),
         ("Pole positions", fmt(k["poles"])), ("Average finish", fmt(k["avg_finish"], ".2f")),
         ("DNFs", fmt(k["dnfs"])), ("Average grid", fmt(k["avg_grid"], ".2f")),
         ("Positions gained", fmt(k["positions_gained"], ",.0f", signed=True))]
for col, (label, value) in zip(row1 + row2, cards):
    with col:
        kpi_card(label, value)

tabs = st.tabs(["🏆 Championship", "⏱️ Qualifying vs Race", "🧑‍✈️ Drivers", "🏭 Constructors",
                "🛣️ Circuits", "🔎 Race Explorer", "🧪 Data Science Insights"])

# ===================================================================== 1. Championship
with tabs[0]:
    show_fig(viz.points_progression(an.cumulative_points(f, top_n=10)))
    drv_sum, con_sum = an.group_summary(f, "driver_name"), an.group_summary(f, "constructor_name")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Driver standings")
        show_df(an.standings(f, "driver_name").rename(columns={"driver_name": "Driver"}))
    with c2:
        st.subheader("Constructor standings")
        show_df(an.standings(f, "constructor_name").rename(columns={"constructor_name": "Constructor"}))
    c3, c4 = st.columns(2)
    with c3:
        show_fig(viz.hbar(drv_sum, "driver_name", "wins", "Wins by driver"))
    with c4:
        show_fig(viz.hbar(drv_sum, "driver_name", "podiums", "Podiums by driver", color="#00D2BE"))
    st.caption("Points = race points + sprint points, aggregated over the selected seasons. "
               "Fastest-lap bonus points (2019–2024) are included in race points as reported by the API.")

# ============================================================ 2. Qualifying vs race
with tabs[1]:
    st.markdown(f'<div class="insight">💡 {an.grid_insight_text(f)}</div>', unsafe_allow_html=True)
    show_fig(viz.grid_vs_finish(f))
    c1, c2 = st.columns(2)
    with c1:
        d = an.group_summary(f, "driver_name")
        if not d.empty:
            d = d[d["races"] >= min(3, int(d["races"].max()))]
        show_fig(viz.hbar(d, "driver_name", "avg_gain", "Average positions gained by driver (top 15)", fmt="+.2f"))
    with c2:
        show_fig(viz.gains_distribution(f))
    st.caption("Positions gained = grid slot − finishing position, for cars that did not retire. "
               "Pit-lane starters are treated as starting at the back of the grid.")

# ===================================================================== 3. Drivers
with tabs[2]:
    summary = an.group_summary(f, "driver_name")
    default_cmp = list(summary["driver_name"].head(3))
    chosen = st.multiselect("Compare drivers", list(summary["driver_name"]), default=default_cmp,
                            key="cmp_drivers")
    cmp_df = summary[summary["driver_name"].isin(chosen)]
    if cmp_df.empty:
        st.info("Pick at least one driver to compare.")
    else:
        c1, c2 = st.columns([3, 2])
        with c1:
            show_df(cmp_df[["driver_name", "races", "points", "wins", "podiums", "avg_finish", "avg_quali",
                            "dnfs", "positions_gained", "points_per_race"]]
                    .rename(columns={"driver_name": "Driver", "races": "Races", "points": "Points",
                                     "wins": "Wins", "podiums": "Podiums", "avg_finish": "Avg finish",
                                     "avg_quali": "Avg quali", "dnfs": "DNFs",
                                     "positions_gained": "+/- Pos", "points_per_race": "Pts / race"}),
                    column_config={"Avg finish": st.column_config.NumberColumn(format="%.2f"),
                                   "Avg quali": st.column_config.NumberColumn(format="%.2f"),
                                   "Pts / race": st.column_config.NumberColumn(format="%.2f"),
                                   "Points": st.column_config.NumberColumn(format="%.1f")})
            show_fig(viz.hbar(cmp_df, "driver_name", "points_per_race", "Points per race", fmt=".2f"))
        with c2:
            show_fig(viz.radar(an.radar_metrics(cmp_df)))
    st.caption("Avg finish counts only cars that did not retire. Avg quali is blank where no qualifying data exists.")

# ================================================================= 4. Constructors
with tabs[3]:
    team_df = scope           # ignore the driver filter so whole teams are shown
    con = an.group_summary(team_df, "constructor_name")
    show_df(con[["constructor_name", "races", "points", "wins", "podiums", "avg_finish", "dnf_rate"]]
            .rename(columns={"constructor_name": "Constructor", "races": "Entries", "points": "Points",
                             "wins": "Wins", "podiums": "Podiums", "avg_finish": "Avg finish",
                             "dnf_rate": "DNF %"}),
            column_config={"Avg finish": st.column_config.NumberColumn(format="%.2f"),
                           "DNF %": st.column_config.NumberColumn(format="%.1f"),
                           "Points": st.column_config.NumberColumn(format="%.1f")})
    c1, c2 = st.columns(2)
    with c1:
        show_fig(viz.hbar(con, "constructor_name", "points", "Constructor points"))
    with c2:
        team = st.selectbox("Driver vs team comparison", list(con["constructor_name"]), key="team_pick")
        contrib = an.constructor_driver_contribution(team_df)
        show_fig(viz.contribution_bar(contrib, team))
        show_df(contrib[contrib["constructor_name"] == team][["driver_name", "points", "share_pct", "races"]]
                .rename(columns={"driver_name": "Driver", "points": "Points", "share_pct": "Share of team %",
                                 "races": "Races"}),
                column_config={"Share of team %": st.column_config.NumberColumn(format="%.1f")})
    st.subheader("Driver vs team-mate")
    show_fig(viz.teammate_bar(an.teammate_comparison(team_df[team_df["constructor_name"] == team])))
    st.caption("Compares each driver's points per race with the average of their team-mates in the same races.")

# ===================================================================== 5. Circuits
with tabs[4]:
    circuits_here = sorted(f["circuit_name"].unique())
    circuit = st.selectbox("Circuit", circuits_here, key="circuit_pick")
    cdf = f[f["circuit_name"] == circuit]
    ck = an.kpis(cdf)
    a, b, c, d_, e = st.columns(5)
    for col, (label, val) in zip((a, b, c, d_, e), [
            ("Races", fmt(cdf["race_index"].nunique())), ("Wins", fmt(ck["wins"])),
            ("Podiums", fmt(ck["podiums"])), ("DNFs", fmt(ck["dnfs"])),
            ("Avg finish", fmt(ck["avg_finish"], ".2f"))]):
        with col:
            kpi_card(label, val)
    table = an.circuit_driver_table(cdf).drop(columns="circuit_name").sort_values(
        ["wins", "podiums", "avg_finish"], ascending=[False, False, True])
    c1, c2 = st.columns(2)
    with c1:
        show_fig(viz.hbar(table, "driver_name", "wins", f"Wins at {circuit}"))
        show_fig(viz.status_bar(an.status_breakdown(cdf)))
    with c2:
        show_fig(viz.circuit_pace_fig(an.circuit_pace(cdf)))
        show_df(table.rename(columns={"driver_name": "Driver", "races": "Races", "wins": "Wins",
                                      "podiums": "Podiums", "dnfs": "DNFs", "avg_finish": "Avg finish",
                                      "points": "Points"}),
                column_config={"Avg finish": st.column_config.NumberColumn(format="%.2f")})
    st.subheader("Best driver at every circuit in the current selection")
    best = an.best_driver_per_circuit(f)
    show_df(best.rename(columns={"circuit_name": "Circuit", "driver_name": "Driver", "races": "Races",
                                 "wins": "Wins", "podiums": "Podiums", "dnfs": "DNFs",
                                 "avg_finish": "Avg finish", "points": "Points"}),
            column_config={"Avg finish": st.column_config.NumberColumn(format="%.2f")})
    st.caption("'Race pace' is approximated by the fastest race lap of each Grand Prix; it is only comparable "
               "across seasons when the circuit layout is unchanged.")

# ================================================================= 6. Race explorer
with tabs[5]:
    explorer_pool = df if not st.session_state["flt_circuits"] else df[df["circuit_name"].isin(
        st.session_state["flt_circuits"])]
    labels = list(explorer_pool.sort_values("race_index")["race_label"].drop_duplicates())
    sidebar_race = st.session_state["flt_race"]
    if sidebar_race != ALL_RACES and sidebar_race in labels:
        race_label = sidebar_race
        st.caption("Using the race chosen in the sidebar.")
    else:
        race_label = st.selectbox("Race", labels, index=len(labels) - 1, key="explorer_race")
    rt = an.race_table(df, race_label)
    if rt.empty:
        st.info("No data for this race.")
    else:
        show_df(rt, column_config={
            "Pos": st.column_config.NumberColumn(format="%d"),
            "Grid": st.column_config.NumberColumn(format="%d", help="0 = pit-lane start"),
            "Quali": st.column_config.NumberColumn(format="%d"),
            "Points": st.column_config.NumberColumn(format="%.1f"),
            "+/- Positions": st.column_config.NumberColumn(format="%+d", help="Grid − finish (blank for retirements)")})
        st.caption("Full classification for the race (not narrowed by the driver filter).")

# ============================================================ 7. Data science insights
with tabs[6]:
    st.markdown("Each metric below is computed live from the currently filtered data, with a plain-language explanation.")
    corr = an.grid_finish_correlation(f)
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Grid ↔ finish (Spearman)", fmt(corr["spearman"], ".2f"))
    with c2:
        kpi_card("Grid ↔ finish (Pearson)", fmt(corr["pearson"], ".2f"))
    with c3:
        kpi_card("Samples", fmt(corr["n"]))
    st.caption("**1. Correlation** — how strongly starting position predicts finishing position. +1 means the grid "
               "order is perfectly preserved; 0 means no relationship. Spearman compares rankings (robust to "
               "outliers); Pearson compares raw positions.")

    c1, c2 = st.columns(2)
    with c1:
        show_fig(viz.podium_probability(an.podium_probability_by_grid(f), an.podium_probability_model(f)))
        st.caption("**2. Podium probability** — the share of starts from each grid slot that ended in the top 3. "
                   "The teal line is a logistic regression (scikit-learn) that smooths noisy small samples.")
    with c2:
        show_fig(viz.gains_by_bucket(an.gains_by_grid_bucket(f)))
        st.caption("**3. Positions gained by grid range** — cars at the back have more places to gain; "
                   "front-runners can only hold or lose positions.")

    st.markdown("---")
    st.subheader("Consistency")
    with st.expander("How is the consistency score calculated?"):
        st.markdown(
            "`score = 0.40 × finish stability + 0.30 × reliability + 0.30 × points stability`\n\n"
            f"- **Finish stability** = 100 × (1 − min(σ of finishing positions ÷ {an.FINISH_STD_CAP:g}, 1)), using "
            "races the car finished.\n"
            "- **Reliability** = 100 × (1 − DNF rate).\n"
            f"- **Points stability** = 100 × (1 − min(CV of points per race ÷ {an.POINTS_CV_CAP:g}, 1)); 0 if "
            "no points were scored.\n\nMinimum 5 races. It measures *steadiness*, not speed — a slow but "
            "reliable car can score well.")
    c1, c2 = st.columns(2)
    drv_cons = an.consistency_score(f, "driver_name")
    con_cons = an.consistency_score(scope, "constructor_name")
    with c1:
        show_fig(viz.consistency_bar(drv_cons, "driver_name", "Driver consistency score"))
        st.caption("**4. Driver consistency score** (0–100, higher = steadier).")
    with c2:
        show_fig(viz.consistency_bar(con_cons, "constructor_name", "Constructor consistency score"))
        st.caption("**5. Constructor consistency score** — same formula applied to each team's car entries.")
    with st.expander("Consistency components (drivers)"):
        show_df(drv_cons, column_config={c: st.column_config.NumberColumn(format="%.2f")
                                         for c in drv_cons.columns if c not in ("driver_name", "races")})

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("DNF rate & points per race")
        ds = an.group_summary(f, "driver_name")
        show_df(ds[["driver_name", "races", "dnfs", "dnf_rate", "points_per_race"]].rename(columns={
            "driver_name": "Driver", "races": "Races", "dnfs": "DNFs", "dnf_rate": "DNF %",
            "points_per_race": "Pts / race"}),
            column_config={"DNF %": st.column_config.NumberColumn(format="%.1f"),
                           "Pts / race": st.column_config.NumberColumn(format="%.2f")})
        st.caption("**6. DNF rate** = retirements ÷ race entries. **7. Points per race** = total points ÷ race entries.")
    with c2:
        st.subheader("Performance trend")
        trend = an.performance_trend(f)
        top_drivers = list(an.group_summary(f, "driver_name")["driver_name"].head(5))
        show_fig(viz.rolling_finish_fig(an.rolling_finish(f, top_drivers)))
        if not trend.empty:
            show_df(trend.rename(columns={"driver_name": "Driver", "races": "Races",
                                          "slope_per_race": "Slope (places / race)", "trend": "Trend"}),
                    column_config={"Slope (places / race)": st.column_config.NumberColumn(format="%+.3f")})
        st.caption("**8. Performance trend** — slope of a straight line fitted to finishing position across the "
                   "selected races. Negative = finishing higher up as the season goes on.")

st.markdown('<div class="footer">F1 Race Analytics — Data Science Portfolio Project<br>'
            'Data from the Jolpica F1 API (community project, not affiliated with or endorsed by Formula 1).</div>',
            unsafe_allow_html=True)
