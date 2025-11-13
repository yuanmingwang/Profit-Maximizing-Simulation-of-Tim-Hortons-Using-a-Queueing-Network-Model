# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# metrics.py
# -----------------------------------------------------------------------------
# Purpose:
#   Collect and summarize KPIs: waits, utilizations, throughput, and profit.
#
# Design notes:
#   - Keep side‑effect methods (note_*) for instrumentation from the router.
#   - Summaries return JSON‑serializable dicts for easy tabulation.
#
# Usage:
#   M = Metrics(cfg); M.summary()
# -----------------------------------------------------------------------------

from __future__ import annotations
from typing import Dict
from statistics import mean

class Metrics:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.pickups = 0
        self.kitchen_entries = 0

    def note_kitchen_entry(self, order):
        self.kitchen_entries += 1

    def note_pickup(self, order):
        self.pickups += 1

    def note_block(self, t, station, job):
        # extend to track losses/blocking if modeling finite buffers upstream
        pass

    def summary(self) -> Dict:
        return {
            "pickups": self.pickups,
            "kitchen_entries": self.kitchen_entries,
        }
