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
Installed pyyaml via 
```bash
python3 -m pip install --user pyyaml
```
So the runner can load YAML configs; ensure this package is available in any environment that runs the experiments.


## How to run
```bash
python -m experiments.run_experiments
```
Extend `experiments/scenarios.py` and the simulation/primitives 
(queues/servers) to create more simulations.

## Project Layout
- `sim/` — simulation engine, primitives, routing, and metrics.
- `experiments/` — scenarios, replication loops, and result aggregation.
- `config/` — YAML configuration for baseline rates, costs, and capacities.

## Notes
- Simulation engine (Env) runs in seconds.
- The code favors clarity over performance.
