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

LEGACY_BASELINE = {
    "name": "legacy_baseline",
    "overrides": {
        "arrival_rates": {
            "walkin": [
                [0, 60, 0.6],
                [60, 180, 1.0],
                [180, 300, 0.8],
                [300, 480, 0.5],
            ],
            "drive_thru": [
                [0, 60, 0.5],
                [60, 180, 0.9],
                [180, 300, 0.7],
                [300, 480, 0.4],
            ],
            "mobile_promises": {
                "start": 0,
                "end": 480,
                "interval": 5,
                "promise_offset": 5,
            },
        },
        "service_rates": {
            "cashier": 0.75,
            "espresso": 0.50,
            "hotfood": 0.67,
            "beverage": 0.42,
        },
        "capacities": {
            "shelf_N": 20,
            "espresso_c": 1,
            "hotfood_c": 2,
            "beverage_c": 2,
        },
        "costs": {
            "price_coffee": 2.5,
            "price_espresso": 4.0,
            "price_hotfood": 5.0,
            "cogs_pct": 0.35,
            "wage_per_min": 0.5,
        },
        "penalties": {
            "mobile_late": 1.0,
            "drivethru_p90_breach": 1.0,
            "pickup_renege": 2.5,
        },
        "customers": {
            "pickup_patience_minutes": {
                "dine_in": 8,
                "mobile": 5,
            }
        },
        "sim": {
            "day_minutes": 480,
            "warmup_minutes": 0,
            # "seed": 3,
        },
    },
}

SCENARIOS = [BASELINE, LEGACY_BASELINE]
