# Project Description

This project models the daily operations of a typical Tim Hortons outlet, focusing on its three
primary customer channels: walk-in counter service, drive-thru, and mobile orders. The goal is
to maximize daily profit by optimizing staﬃng, equipment use, and prioritization policies while
maintaining acceptable customer service levels. The restaurant operates under stochastic customer
demand, with peak loads during breakfast and lunch hours.

# Tim Hortons Queueing‑Network Simulation

This repository build a discrete‑event simulation (DES) for a Tim Hortons
store using a queueing‑network model. It is structured for repeatable
experiments, confidence intervals, and policy/staffing comparisons.

## Prerequisites
- Python 3.9+ recommended
- Install deps using the provided requirements file:
```bash
python3 -m pip install --user -r requirements.txt
```
- If you prefer manual installs, at minimum you need PyYAML (matplotlib for plots; SciPy for t-critical values). If matplotlib/SciPy are absent, the code still runs (plots/CI fallback).
```bash
python3 -m pip install --user pyyaml matplotlib scipy
```

## How to run experiments
```bash
python -m experiments.run_experiments
```
Key experiment parameters in `config/baseline.yaml` under `experiments`:
- `replications`: iid daily runs per scenario.
- `confidence_level`: CI level (e.g., 0.95).
- `time_series_interval_minutes`: bin width for profit/revenue interval plot.
- `crn_compare`: list of scenario-name pairs for CRN paired comparisons, e.g.:
  ```yaml
  crn_compare:
    - [baseline, profit_focus]
    - [baseline, high_load]
  ```

## How to run the optimizer
Grid/coordinate search for profitable configs:
```bash
python -m experiments.optimize_profit
```
Tunable constants at the top of `experiments/optimize_profit.py`:
- `SERVICE_STEP`, `CAPACITY_STEP`, `COORDINATE_PASSES`: grid resolution/passes.
- `USE_ABSOLUTE_SERVICE_TIMES` + `SERVICE_TIME_RANGES/STEP`: scan absolute means.
- `USE_WAGE_SEARCH`, `USE_PENALTY_SEARCH`, `USE_PRICE_SEARCH`: sweep wages/penalties/prices with ranges and steps.
- `USE_PACK_PRIORITY_SEARCH`, `PACK_PRIORITY_OPTIONS`: scan pack-queue priority orders.
- `SEARCH_ITERATIONS`, `SEARCH_START_SEED`: replications and starting seed per candidate.
- `SELECTED_SCENARIOS`: scenario names to optimize (must match `experiments/scenarios.py`).

## Project Layout
- `sim/` — simulation engine, primitives, routing, and metrics.
- `experiments/` — scenarios, replication loops, and result aggregation.
- `config/` — YAML configuration for baseline rates, costs, and capacities.

## Config cheat sheet (config/baseline.yaml)
- `arrival_rates`: NHPP dayparts per channel; `mobile_promises` for promised pickup cadence.
- `service_rates`: mean minutes per station (includes refill/maintenance times).
- `capacities`: servers/buffers, drive-thru lane limits, urn/espresso batch sizes.
- `costs`: menu prices, COGS %, wages per station.
- `penalties`: mobile late, drive-thru p90 breach target/penalty, pickup reneges, balk loss fraction.
- `customers`: pickup patience by channel (minutes).
- `order_mix`: per-channel item inclusion probabilities.
- `policies`: `pack_priority` (channel priority at pack; empty list = FIFO).
- `experiments`: replication count, CI level, plot bin width, optional `crn_compare` pairs.
- `sim`: day length, warmup minutes, base seed.

## Notes
- Simulation engine (Env) runs in seconds.
- The code favors clarity over performance.
