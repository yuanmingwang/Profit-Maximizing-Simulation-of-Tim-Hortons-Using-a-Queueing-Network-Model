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
                [0, 150, 0.75],
                [150, 300, 0.5],
                [300, 420, 0.65],
                [420, 450, 0.0],
                [450, 660, 0.45],
                [660, 840, 0.5],
                [840, 960, 0.25],
            ],
            "drive_thru": [
                [0, 150, 1.0],
                [150, 300, 0.7],
                [300, 420, 1.0],
                [420, 450, 0.0],
                [450, 660, 0.55],
                [660, 840, 0.6],
                [840, 960, 0.25],
            ],
            "mobile": [
                [0, 150, 0.4],
                [150, 300, 0.35],
                [300, 420, 0.5],
                [420, 450, 0.0],
                [450, 660, 0.25],
                [660, 840, 0.3],
                [840, 960, 0.15],
            ],
            "mobile_promises": {
                "start": 0,
                "end": 960,
                "interval": 5,
                "promise_offset": 7,
            },
        },
        "service_rates": {
            "cashier": 0.55,
            "window": 0.60,
            "beverage": 0.40,
            "espresso": 0.30,
            "hotfood": 0.40,
            "pack": 0.25,
            "shelf": 0.03,
            "dine_in": 6.5,
            "table_cleaning": 0.45,
        },
        "capacities": {
            "shelf_N": 18,
            "espresso_c": 1,
            "hotfood_c": 2,
            "beverage_c": 2,
            "dine_in_tables": 18,
            "table_cleaners": 2,
        },
        "costs": {
            "price_coffee": 2.00,
            "price_espresso": 4.00,
            "price_hotfood": 3.50,
            "cogs_pct": 0.38,
            "wages_per_hour": {
                "cashier": 16.5,
                "window": 16.5,
                "beverage": 17.5,
                "espresso": 17.5,
                "hotfood": 17.5,
                "pack": 16.5,
                "shelf": 16.5,
                "dine_in": 0.0,
                "dine_in_clean": 15.5,
                "_default_": 16.5,
            },
        },
        "penalties": {
            "mobile_late": 0.75,
            "drivethru_p90_breach": 0.3,
            "pickup_renege": 0.5,
            "balk_loss_pct": 0.3,
        },
        "customers": {
            "pickup_patience_minutes": {
                "dine_in": 7,
                "mobile": 4,
            }
        },
        "sim": {
            "day_minutes": 960,
            "warmup_minutes": 0,
            "seed": 3,
        },
    },
}

HIGH_CLEANING_LOAD = {
    "name": "dine_in_stress",
    "overrides": {
        "service_rates": {
            "dine_in": 7.0,
            "table_cleaning": 0.6,
        },
        "capacities": {
            "dine_in_tables": 12,
            "table_cleaners": 1,
        },
        "sim": {
            "day_minutes": 960,
            "warmup_minutes": 0,
            "seed": 3,
        },
    },
}

PROFIT_FOCUS = {
    "name": "profit_focus",
    "overrides": {
        "capacities": {
            "espresso_c": 2,
            "hotfood_c": 2,
            "beverage_c": 2,
            "dine_in_tables": 12,
            "table_cleaners": 1,
        },
        "service_rates": {
            "cashier": 0.45,
            "window": 0.45,
            "hotfood": 0.30,
            "pack": 0.18,
            "shelf": 0.02,
            "dine_in": 5.5,
            "table_cleaning": 0.28,
        },
        "penalties": {
            "mobile_late": 0.5,
            "drivethru_p90_breach": 0.2,
            "pickup_renege": 0.0,
            "balk_loss_pct": 0.4,
        },
        "customers": {
            "pickup_patience_minutes": {
                "dine_in": 8,
                "mobile": 5,
            }
        },
        "sim": {
            "day_minutes": 960,
            "warmup_minutes": 0,
            "seed": 3,
        },
    },
}

SCENARIOS = [BASELINE, LEGACY_BASELINE, HIGH_CLEANING_LOAD, PROFIT_FOCUS]
