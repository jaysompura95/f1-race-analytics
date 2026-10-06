# F1 Race Analytics

> Data-driven insights from Formula 1 racing — an interactive analytics dashboard built with Python, Pandas, Plotly and Streamlit.

## Overview
F1 Race Analytics turns historical Formula 1 race data into an interactive dashboard covering championships, qualifying-vs-race conversion, driver and constructor performance, circuit history and a dedicated **Data Science Insights** section. Every number is calculated from the data at runtime — nothing is hard-coded.

## Problem Statement
Raw race results are easy to find but hard to interpret. Questions such as *"Does starting on the front row really matter?"*, *"Who is the most consistent driver?"* or *"Which team's drivers carry the points load?"* require cleaning, feature engineering and careful metric design.

## Objectives
- Build a reproducible pipeline from a public API to an analysis-ready dataset.
- Define transparent, documented metrics (no black-box "AI score").
- Present the results in a fast, filterable, professional dashboard.

## Features
- Sidebar filters: **season range, driver, constructor, circuit, race** + one-click **Reset Filters**.
- 8 KPI cards that react to every filter: wins, podiums, points, poles, average finish, DNFs, average grid, positions gained.
- **Championship** – points progression, driver/constructor standings, wins and podiums.
- **Qualifying vs Race** – grid-vs-finish scatter, positions gained/lost, auto-generated insight.
- **Drivers** – multi-driver comparison table + radar chart.
- **Constructors** – team table, driver contribution, driver-vs-team-mate comparison.
- **Circuits** – best drivers, DNF reasons, fastest-lap history per circuit.
- **Race Explorer** – full grid → finish table for any race.
- **Data Science Insights** – correlation, podium probability (with logistic regression), positions gained by grid range, consistency scores, DNF rate, points per race, performance trend.
- Friendly handling of API failures, empty selections, invalid seasons, missing qualifying data and renamed teams/drivers.

## Dataset / API
| | |
|---|---|
| **Source** | [Jolpica F1 API](https://github.com/jolpica/jolpica-f1) — community-run, open-source, Ergast-compatible |
| **Docs** | https://github.com/jolpica/jolpica-f1/tree/main/docs |
| **Coverage** | Seasons 1950 → present (as available from the API) |
| **Endpoints used** | `seasons`, `{season}/results`, `{season}/qualifying`, `{season}/sprint` |

**This is not official Formula 1 data** and the project is not affiliated with or endorsed by Formula 1. Please respect the API's rate limits and terms of use.

## Tech Stack
Python · Pandas · NumPy · Plotly · Streamlit · scikit-learn (logistic regression) · Requests · pytest

> SQL: the pipeline uses pandas for all transformations, so no database is required. (An optional SQLite export is listed under *Future Improvements*.)

## Data Pipeline
```
Jolpica API ─► data_loader.py ─► data_cleaning.py ─► feature_engineering.py ─► analytics.py ─► visualizations.py ─► app.py
 (paginated)    ingest + cache    types, names, DNF     derived columns          pure metric        Plotly figures      Streamlit UI
                (CSV on disk)     classification        (grid, gains, poles)     functions
```
- **Caching:** finished seasons are stored in `data/cache/` forever; the in-progress season refreshes after 6 h; Streamlit also caches loaded datasets in memory.
- **Robustness:** retries with back-off, request pacing, partial-failure handling (a failing season is skipped with a warning), stale season-list fallback.

## Key Metrics
| Metric | Definition |
|---|---|
| Wins / Podiums | Classified finish = P1 / P1–P3 |
| Points | Race points + sprint points |
| Pole positions | Qualifying P1 (falls back to grid P1 when a race has no qualifying data) |
| Average finish | Mean finishing position of cars that **did not retire** |
| DNF | Status that is not "Finished" or "+N Lap(s)" (includes disqualifications and non-starters) |
| Average grid | Mean starting slot; pit-lane starters (grid 0) count as starting at the back |
| Positions gained | Grid slot − finishing position, non-retirements only |
| Points per race | Total points ÷ race entries |

## Data Science Methodology
1. **Grid ↔ finish correlation** – Pearson and Spearman (rank) correlation on classified finishers.
2. **Podium probability** – observed share of podiums per grid slot, plus a one-feature logistic regression to smooth small samples.
3. **Positions gained by grid range** – mean/median gains for P1–3, P4–6, P7–10, P11–15, P16+.
4. **Consistency scores** – see below.
5. **Performance trend** – slope of a least-squares line through finishing position over the selected races (negative = improving).
6. **DNF rate** and **points per race** – simple rates with sample sizes shown.

### Driver Consistency Score
A transparent 0–100 score (higher = steadier). Requires at least 5 races.

```
score = 0.40 × finish_stability + 0.30 × reliability + 0.30 × points_stability

finish_stability = 100 × (1 − min( σ(finish position, non-retired races) / 8 , 1))
reliability      = 100 × (1 − DNF rate)
points_stability = 100 × (1 − min( CV(points per race) / 1.5 , 1))      # 0 if no points scored
                   where CV = standard deviation / mean
```
The caps (8 places, CV 1.5) and weights are constants in `src/analytics.py`. The score measures **steadiness, not speed**: a slow but reliable car can score well. The **constructor** score applies the same formula to each team's car entries.

## Screenshots
Add screenshots to `assets/screenshots/` and link them here:

```md
![Dashboard overview](assets/screenshots/overview.png)
![Qualifying vs race](assets/screenshots/qualifying.png)
![Data science insights](assets/screenshots/insights.png)
```

## Installation
```bash
git clone https://github.com/<your-username>/f1-race-analytics.git
cd f1-race-analytics
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running Locally
```bash
streamlit run app.py
```
The first load of each season downloads ~10–15 API requests (roughly 10–20 s); later loads are instant from the cache.

Run the tests:
```bash
pytest
```

## Project Structure
```
f1-race-analytics/
├── app.py                    # Streamlit UI only
├── requirements.txt
├── .streamlit/config.toml    # dark theme
├── data/                     # README + git-ignored cache
├── src/
│   ├── data_loader.py        # API ingestion, pagination, caching
│   ├── data_cleaning.py      # types, names, DNF classification, merges
│   ├── feature_engineering.py
│   ├── analytics.py          # pure, testable metric functions
│   ├── visualizations.py     # Plotly figures
│   └── pipeline.py           # loader → cleaning → features
├── notebooks/exploratory_analysis.ipynb
├── assets/screenshots/
└── tests/                    # hand-checked unit tests + app smoke tests
```

## Results / Insights
_Run the app for your chosen seasons and paste 3–4 findings here, e.g. the top-3 grid → podium conversion rate, the grid/finish correlation, and the most consistent driver. These values are calculated live, so quote the seasons you analysed._

## Limitations
- Third-party, community-maintained data — it may contain errors and is not official.
- Qualifying data is mostly available from 1994 onwards; earlier seasons have no qualifying metrics.
- Points use the race results as recorded (plus sprint points); historical points systems differ by era, so cross-era points comparisons are not like-for-like.
- "Race pace" is approximated by the fastest race lap, which is affected by tyres, fuel and track evolution; lap-by-lap data is not used.
- Grid positions include penalties; "positions gained" therefore mixes on-track overtakes and penalty effects.
- Constructor data follows the API's team identifiers, so team lineage (e.g. renamed teams) is unified only by identifier.
- Downloads are limited to 10 seasons at a time to respect API rate limits.

## Future Improvements
- Lap-by-lap pace, tyre and pit-stop analysis (basis for an **F1 Race Strategy Simulator**).
- Era-adjusted points and Elo-style driver ratings.
- Optional SQLite/DuckDB layer for ad-hoc SQL queries.
- Team-mate qualifying head-to-head and weather/circuit-type features.
- CI (GitHub Actions) running `pytest`.

## Author
**Your Name** — [GitHub](https://github.com/your-username) · [LinkedIn](https://www.linkedin.com/in/your-profile)

---
*F1 Race Analytics — Data Science Portfolio Project.*
