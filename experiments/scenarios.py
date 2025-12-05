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

BASELINE_OPTIMIZED = {
    "name": "baseline_optimized",
    "overrides": {
        "service_rates": {
            "cashier": 0.45,
            "window": 0.5,
            "beverage": 0.29700000000000004,
            "beverage_refill": 2.0,
            "espresso": 0.2,
            "espresso_maintenance": 2.0,
            "hotfood": 0.33,
            "pack": 0.2,
            "shelf": 0.05,
            "dine_in": 6.0,
            "table_cleaning": 0.33,
        },
        "capacities": {
            "shelf_N": 20,
            "beverage_urn_size": 25,
            "espresso_c": 1,
            "espresso_batch_size": 40,
            "hotfood_c": 1,
            "beverage_c": 1,
            "dine_in_tables": 11,
            "table_cleaners": 1,
        },
        "penalties": {
            "mobile_late": 0.4,
            "drivethru_p90_breach": 0.2,
            "pickup_renege": 0.0,
            "balk_loss_pct": 0.2,
        },
        "costs": {
            "price_coffee": 3.75,
            "price_espresso": 5.5,
            "price_hotfood": 5.0,
            "cogs_pct": 0.35,
            "wages_per_hour": {
                "cashier": 16.0,
                "window": 16.0,
                "beverage": 16.0,
                "espresso": 16.0,
                "hotfood": 16.0,
                "pack": 16.0,
                "shelf": 0.0,
                "dine_in": 0.0,
                "dine_in_clean": 16.0,
                "_default_": 17.0,
            },
        },
    },
}

HIGH_LOAD = {
    "name": "high_load",
    "overrides": {
        "service_rates": {
            "cashier": 0.8,
            "window": 1,
            "drive_thru_pickup": 0.5,
            "beverage": 1,
            "beverage_refill": 2.0,
            "espresso": 1,
            "espresso_maintenance": 5.0,
            "hotfood": 1,
            "pack": 0.5,
            "shelf": 0.5,
            "dine_in": 10,
            "table_cleaning": 1.5,
        },
        "capacities": {
            "shelf_N": 20,
            "drive_thru_lane_order": 5,
            "drive_thru_lane_pickup": 3,
            "beverage_urn_size": 25,
            "espresso_c": 1,
            "espresso_batch_size": 40,
            "hotfood_c": 1,
            "beverage_c": 2,
            "dine_in_tables": 12,
            "table_cleaners": 1,
        },
        "sim": {
            "day_minutes": 960,
            "warmup_minutes": 30,
            "seed": 3,
        },
    },
}

HIGH_LOAD_OPTIMIZED = {
    "name": "high_load_optimized",
    "overrides": {
        "service_rates": {
            "cashier": 0.8,
            "window": 0.8,
            "beverage": 1,
            "espresso": 1,
            "hotfood": 1,
            "pack": 0.55,
            "shelf": 0.4,
            "dine_in": 8.0,
            "table_cleaning": 1.2000000000000002,
        },
        "capacities": {
            "shelf_N": 20,
            "espresso_c": 1,
            "hotfood_c": 1,
            "beverage_c": 2,
            "dine_in_tables": 13,
            "table_cleaners": 1,
        },
        "penalties": {
            "mobile_late": 0.4,
            "drivethru_p90_breach": 0.2,
            "pickup_renege": 0.0,
            "balk_loss_pct": 0.2,
        },
        "costs": {
            "price_coffee": 3.75,
            "price_espresso": 5.5,
            "price_hotfood": 5.0,
            "cogs_pct": 0.35,
            "wages_per_hour": {
                "cashier": 16.0,
                "window": 16.0,
                "beverage": 16.0,
                "espresso": 16.0,
                "hotfood": 16.0,
                "pack": 16.0,
                "shelf": 0.0,
                "dine_in": 0.0,
                "dine_in_clean": 16.0,
                "_default_": 17.0,
            },
        },
        "sim": {
            "day_minutes": 960,
            "warmup_minutes": 30,
            "seed": 3,
        },
    },
}

SCENARIOS = [BASELINE, BASELINE_OPTIMIZED, HIGH_LOAD, HIGH_LOAD_OPTIMIZED]