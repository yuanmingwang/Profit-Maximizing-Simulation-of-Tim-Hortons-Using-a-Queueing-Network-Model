"""
experiments/scenarios.py

Holds scenario definitions (decision variables) to sweep during experiments.
Add staffing levels, device counts, and policy flags here.
"""

from __future__ import annotations

BASELINE = {
    "name": "baseline",
    "overrides": {},  # override config keys here per scenario
}

SCENARIOS = [BASELINE]
