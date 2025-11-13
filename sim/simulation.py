# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# simulation.py
# -----------------------------------------------------------------------------
# Purpose:
#   Simulate a single replication ("one day"): build stations, router,
#   schedule arrivals, run the event loop, and return metrics.
#
# Design notes:
#   - Warm‑up handling lives outside, in experiments/.
#
# Usage:
#   from sim.simulation import run_one_day
#   results = run_one_day(cfg)
# -----------------------------------------------------------------------------

from __future__ import annotations
import random, yaml, os
from typing import Dict
from .queues import Env
from .stations import make_stations
from .network import Router
from .metrics import Metrics
from .arrivals import schedule_arrivals

def run_one_day(cfg: Dict) -> Dict:
    random.seed(cfg["sim"].get("seed", 0))

    stations = make_stations(cfg)
    M = Metrics(cfg)
    router = Router(cfg, stations, M)
    env = Env(router)

    # Schedule exogenous arrivals then run
    schedule_arrivals(env, router, cfg)
    T_end = cfg["sim"]["day_minutes"] * 60.0
    env.run_until(T_end)

    return M.summary()
