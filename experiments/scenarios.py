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
    "name": "baseline_optimized_scenario_2",
    "overrides": {
        "service_rates": {
            "cashier": 0.4,
            "window": 0.45,
            "drive_thru_pickup": 0.15030000000000002,
            "beverage": 0.33,
            "beverage_refill": 1.6,
            "espresso": 0.3,
            "espresso_maintenance": 1.6,
            "hotfood": 0.36300000000000004,
            "pack": 0.2,
            "shelf": 0.02,
            "dine_in": 6.0,
            "table_cleaning": 0.264,
        },
        "capacities": {
            "shelf_N": 20,
            "drive_thru_lane_order": 10,
            "drive_thru_lane_pickup": 3,
            "beverage_urn_size": 29,
            "espresso_c": 1,
            "espresso_batch_size": 38,
            "hotfood_c": 1,
            "beverage_c": 1,
            "dine_in_tables": 25,
            "table_cleaners": 1,
        },
        "penalties": {
            "mobile_late": 0.4,
            "drivethru_p90_breach": 0.2,
            "drivethru_p90_target_minutes": 1.0,
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
                "_default_": 16.0,
            },
        },
        "policies": {
            "pack_priority": ['walkin'],
        },
    },
}

HIGH_LOAD = {
    "name": "high_load_scenario_1",
    "overrides": {
        "service_rates": {
            "cashier": 0.8,
            "window": 1,
            "drive_thru_pickup": 0.5,
            "beverage": 1,
            "beverage_refill": 2.0,
            "espresso": 1,
            "espresso_maintenance": 2.0,
            "hotfood": 1,
            "pack": 0.5,
            "shelf": 0.5,
            "dine_in": 20,
            "table_cleaning": 2,
        },
        "capacities": {
            "shelf_N": 40,
            "drive_thru_lane_order": 10,
            "drive_thru_lane_pickup": 3,
            "beverage_urn_size": 25,
            "espresso_c": 2,
            "espresso_batch_size": 20,
            "hotfood_c": 2,
            "beverage_c": 2,
            "dine_in_tables": 20,
            "table_cleaners": 2,
        },
        "penalties": {
            "mobile_late": 0.4,
            "drivethru_p90_breach": 0.2,
            "pickup_renege": 0.0,
            "balk_loss_pct": 0.4,
        },
        "costs": {
            "price_coffee": 2.75,
            "price_espresso": 4.5,
            "price_hotfood": 4.0,
            "cogs_pct": 0.35,
            "wages_per_hour": {
                "cashier": 17.5,
                "window": 17.5,
                "beverage": 17.5,
                "espresso": 17.5,
                "hotfood": 17.5,
                "pack": 17.5,
                "shelf": 0.0,
                "dine_in": 0.0,
                "dine_in_clean": 17.5,
                "_default_": 0,
            },
        },
        "policies": {
            "pack_priority": ['mobile'],
        },
    },
}

HIGH_LOAD_OPTIMIZED = {
    "name": "high_load_optimized",
    "overrides": {
        "service_rates": {
            "cashier": 0.8,
            "window": 0.9,
            "drive_thru_pickup": 0.45,
            "beverage": 1,
            "beverage_refill": 2.0,
            "espresso": 1,
            "espresso_maintenance": 2.0,
            "hotfood": 1,
            "pack": 0.5,
            "shelf": 0.4,
            "dine_in": 16.0,
            "table_cleaning": 2,
        },
        "capacities": {
            "shelf_N": 40,
            "drive_thru_lane_order": 10,
            "drive_thru_lane_pickup": 3,
            "beverage_urn_size": 25,
            "espresso_c": 1,
            "espresso_batch_size": 39,
            "hotfood_c": 1,
            "beverage_c": 2,
            "dine_in_tables": 24,
            "table_cleaners": 2,
        },
        "penalties": {
            "mobile_late": 0.4,
            "drivethru_p90_breach": 0.2,
            "drivethru_p90_target_minutes": 1.0,
            "pickup_renege": 0.0,
            "balk_loss_pct": 0.4,
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
                "_default_": 16.0,
            },
        },
        "policies": {
            "pack_priority": [],
        },
    },
}

SCENARIOS = [BASELINE, BASELINE_OPTIMIZED, HIGH_LOAD, HIGH_LOAD_OPTIMIZED]
