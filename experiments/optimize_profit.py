"""
experiments/optimize_profit.py

Coordinate-ascent style search that sweeps staffing/capacity decisions on a
coarse grid (user-defined steps) to find profitable configurations. Instead of
pure random search, this walks one decision dimension at a time while holding
others fixed, which dramatically reduces the number of simulations compared to
an exhaustive Cartesian grid across all parameters.
"""

from __future__ import annotations
import copy, math
from typing import Dict, Tuple, List
try:
    # When executed as a module: python -m experiments.optimize_profit
    from sim.simulation import run_one_day
    from .run_experiments import load_cfg, apply_overrides  # type: ignore
    from .scenarios import SCENARIOS  # type: ignore
except Exception:  # pragma: no cover - fallback for VSCode "python file.py"
    import os, sys
    ROOT = os.path.dirname(os.path.dirname(__file__))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from sim.simulation import run_one_day  # type: ignore
    from experiments.run_experiments import load_cfg, apply_overrides  # type: ignore
    from experiments.scenarios import SCENARIOS  # type: ignore

# Bounds for decision variables. SERVICE_MULTS entries are multiplicative factors
# applied to the BASE service times, so 0.8 => 20% faster, 1.2 => 20% slower.
SERVICE_MULTS = {
    "cashier": (0.8, 1.2),
    "window": (0.8, 1.2),
    "drive_thru_pickup": (0.8, 1.2),
    "beverage": (0.8, 1.2),
    "beverage_refill": (0.8, 1.2),
    "espresso": (0.8, 1.2),
    "espresso_maintenance": (0.8, 1.2),
    "hotfood": (0.8, 1.2),
    "pack": (0.8, 1.2),
    "shelf": (0.8, 1.2),
    "dine_in": (0.8, 1.2),
    "table_cleaning": (0.8, 1.2),
}
# CAPACITY_CHOICES specify integer ranges for the number of parallel servers.
CAPACITY_CHOICES = {
    "beverage_urn_size": (20, 30),     
    "espresso_c": (1, 3),
    "espresso_batch_size": (35, 45),
    "hotfood_c": (1, 3),
    "beverage_c": (1, 3),
    "dine_in_tables": (15, 25),
    "table_cleaners": (1, 3),
}
# Step sizes for each grid (tweak to trade off runtime vs. resolution).
SERVICE_STEP = 0.1
CAPACITY_STEP = 1
# How many coordinate-ascent passes to perform per scenario (more passes = finer refinement).
COORDINATE_PASSES = 2
# Beam width could be added later; for now, coordinate ascent already prunes the Cartesian explosion.

# Optional absolute service-time search (minutes). When enabled, the grid is
# taken directly from these ranges instead of multiplying the baseline.
USE_ABSOLUTE_SERVICE_TIMES = False
# USE_ABSOLUTE_SERVICE_TIMES = True
SERVICE_TIME_RANGES = {
    "cashier": (0.8, 1.2),
    "window": (0.8, 1.2),
    "beverage": (0.8, 1.2),
    "espresso": (0.8, 1.2),
    "hotfood": (0.8, 1.2),
    "pack": (0.4, 0.6),
    "shelf": (0.4, 0.6),
    "dine_in": (0.8, 1.2),
    "table_cleaning": (0.7, 1.3),
}
SERVICE_TIME_STEP = 0.1

# Optional wage search (absolute $/hr bounds). When enabled, wages are scanned on a grid.
USE_WAGE_SEARCH = True
WAGE_RANGES = {
    "cashier": (16.0, 19.0),
    "window": (16.0, 19.0),
    "beverage": (16.0, 19.0),
    "espresso": (16.0, 19.0),
    "hotfood": (16.0, 19.0),
    "pack": (16.0, 19.0),
    "dine_in_clean": (16.0, 18.0),
    "_default_": (16.0, 19.0),
}
WAGE_STEP = 1.0

# Optional penalty search (absolute dollars or fractions). Bounds are absolute.
USE_PENALTY_SEARCH = True
PENALTY_RANGES = {
    "mobile_late": (0.4, 0.8),
    "drivethru_p90_breach": (0.2, 0.6),
    "pickup_renege": (0.0, 0.4),
    "balk_loss_pct": (0.2, 0.6),
}
PENALTY_STEP = 0.2

# Optional price search (absolute $ per item). Bounds are absolute menu prices.
USE_PRICE_SEARCH = True
PRICE_RANGES = {
    "price_coffee": (1.75, 3.75),
    "price_espresso": (3.50, 5.50),
    "price_hotfood": (3.00, 5.00),
}
PRICE_STEP = 0.5

# Optional pack priority search: list all permutations of channel priorities to scan.
USE_PACK_PRIORITY_SEARCH = True
# Priority lists are tested in the provided order; [] means FIFO (no priority).
PACK_PRIORITY_OPTIONS: List[List[str]] = [
    [],  # FIFO baseline
    # ["drive_thru", "mobile", "walkin"],
    # ["mobile", "drive_thru", "walkin"],
    # ["walkin", "drive_thru", "mobile"],
    ["drive_thru"],
    ["mobile"],
    ["walkin"],
]

# Which scenarios to optimize (match names in scenarios.py). Example: ["baseline", "legacy_baseline"]
# SELECTED_SCENARIOS = ["baseline"]
SELECTED_SCENARIOS = ["high_load"]

# Monte Carlo controls: number of replications per candidate and the seed to start from.
SEARCH_ITERATIONS = 3       # e.g., 5 -> seeds start_seed ... start_seed+4
SEARCH_START_SEED = 3

def float_grid(bounds: Tuple[float, float], step: float) -> List[float]:
    """
    Expand a closed interval [lo, hi] into a list of evenly spaced values using
    the provided step. Example: (0.8, 1.2) with step 0.1 -> [0.8,0.9,1.0,1.1,1.2].
    """
    lo, hi = bounds
    vals: List[float] = []
    if step <= 0:
        step = 0.1
    cur = lo
    while cur <= hi + 1e-9:
        vals.append(round(cur, 4))
        cur += step
    if vals and vals[-1] < hi - 1e-9:
        vals.append(round(hi, 4))
    return vals

def int_grid(bounds: Tuple[int, int], step: int) -> List[int]:
    """Generate integer grid values within [lo, hi] inclusive with stride=step."""
    lo, hi = bounds
    stride = max(1, int(step))
    vals = list(range(int(lo), int(hi) + 1, stride))
    if vals and vals[-1] != hi:
        vals.append(hi)
    return vals

def evaluate(cfg: Dict, iterations: int, start_seed: int) -> float:
    """
    Run multiple replications with seeds start_seed..start_seed+iterations-1 and
    return the average profit/day. This smooths randomness when comparing candidates.
    """
    if iterations <= 0:
        iterations = 1
    profits: List[float] = []
    for i in range(iterations):
        cand = copy.deepcopy(cfg)
        cand.setdefault("sim", {})
        cand["sim"]["seed"] = start_seed + i
        res = run_one_day(cand)
        profits.append(float(res.get("profit_per_day", -math.inf)))
    return sum(profits) / len(profits)

def coord_ascent(base_cfg: Dict, service_step: float, capacity_step: int, passes: int, iterations: int, start_seed: int) -> Tuple[float, Dict]:
    """
    Coordinate ascent across service multipliers and capacity integers:
      - For each dimension, sweep its grid while holding others fixed.
      - Accept the value that yields the best profit for that dimension.
    This keeps runtime ~O(P * G) instead of exploding Cartesian grids.
    """
    current = copy.deepcopy(base_cfg)
    # Clamp starting point to user ranges so the algorithm never leaves bounds.
    if USE_ABSOLUTE_SERVICE_TIMES:
        for key, bounds in SERVICE_TIME_RANGES.items():
            if "service_rates" in current and key in current["service_rates"]:
                lo, hi = bounds
                current["service_rates"][key] = min(max(current["service_rates"][key], lo), hi)
    for key, bounds in CAPACITY_CHOICES.items():
        if "capacities" in current and key in current["capacities"]:
            lo, hi = bounds
            current["capacities"][key] = int(min(max(current["capacities"][key], lo), hi))
    # Start from the provided scenario baseline
    best_profit = evaluate(current, iterations, start_seed)
    for _ in range(max(1, passes)):
        # Sweep service-rate multipliers
        for key in SERVICE_MULTS.keys():
            base_service = base_cfg.get("service_rates", {}).get(key)
            if base_service is None:
                continue
            # Pick grid based on mode: multiplier or absolute service time
            if USE_ABSOLUTE_SERVICE_TIMES and key in SERVICE_TIME_RANGES:
                grid = float_grid(SERVICE_TIME_RANGES[key], SERVICE_TIME_STEP)
            else:
                grid = float_grid(SERVICE_MULTS[key], service_step)
            local_best = best_profit
            # Keep the incumbent within bounds for this coordinate
            if USE_ABSOLUTE_SERVICE_TIMES and key in SERVICE_TIME_RANGES:
                lo, hi = SERVICE_TIME_RANGES[key]
                best_val = min(max(current.get("service_rates", {}).get(key, base_service), lo), hi)
            else:
                best_val = current.get("service_rates", {}).get(key, base_service)
            for val in grid:
                # Only change one coordinate at a time; others remain fixed at current best
                cand = copy.deepcopy(current)
                cand.setdefault("service_rates", {})
                if USE_ABSOLUTE_SERVICE_TIMES and key in SERVICE_TIME_RANGES:
                    lo, hi = SERVICE_TIME_RANGES[key]
                    cand["service_rates"][key] = min(max(val, lo), hi)
                else:
                    cand["service_rates"][key] = max(0.05, base_service * val)
                profit = evaluate(cand, iterations, start_seed)
                if profit > local_best:
                    local_best = profit
                    best_val = cand["service_rates"][key]
            # Commit the best value found for this coordinate
            current["service_rates"][key] = best_val
            best_profit = local_best

        # Sweep capacity integers
        for key, bounds in CAPACITY_CHOICES.items():
            base_cap = base_cfg.get("capacities", {}).get(key)
            if base_cap is None:
                continue
            grid = int_grid(bounds, capacity_step)
            local_best = best_profit
            lo, hi = bounds
            best_val = int(min(max(current.get("capacities", {}).get(key, base_cap), lo), hi))
            for cap in grid:
                # Hold other decisions fixed while scanning this capacity coordinate
                cand = copy.deepcopy(current)
                cand.setdefault("capacities", {})
                # Clamp to bounds to prevent drift
                cand["capacities"][key] = int(min(max(cap, lo), hi))
                profit = evaluate(cand, iterations, start_seed)
                if profit > local_best:
                    local_best = profit
                    best_val = cap
            current["capacities"][key] = best_val
            best_profit = local_best

        # Sweep wages if enabled
        if USE_WAGE_SEARCH:
            wages_cfg = current.setdefault("costs", {}).setdefault("wages_per_hour", {})
            for key, bounds in WAGE_RANGES.items():
                grid = float_grid(bounds, WAGE_STEP)
                lo, hi = bounds
                best_val = min(max(wages_cfg.get(key, (lo + hi) / 2.0), lo), hi)
                local_best = best_profit
                for val in grid:
                    cand = copy.deepcopy(current)
                    cand.setdefault("costs", {}).setdefault("wages_per_hour", {})
                    cand["costs"]["wages_per_hour"][key] = min(max(val, lo), hi)
                    profit = evaluate(cand, iterations, start_seed)
                    if profit > local_best:
                        local_best = profit
                        best_val = cand["costs"]["wages_per_hour"][key]
                wages_cfg[key] = best_val
                best_profit = local_best

        # Sweep penalties if enabled
        if USE_PENALTY_SEARCH:
            pen_cfg = current.setdefault("penalties", {})
            for key, bounds in PENALTY_RANGES.items():
                grid = float_grid(bounds, PENALTY_STEP)
                lo, hi = bounds
                best_val = min(max(pen_cfg.get(key, (lo + hi) / 2.0), lo), hi)
                local_best = best_profit
                for val in grid:
                    cand = copy.deepcopy(current)
                    cand.setdefault("penalties", {})
                    cand["penalties"][key] = min(max(val, lo), hi)
                    profit = evaluate(cand, iterations, start_seed)
                    if profit > local_best:
                        local_best = profit
                        best_val = cand["penalties"][key]
                pen_cfg[key] = best_val
                best_profit = local_best
        # Sweep prices if enabled
        if USE_PRICE_SEARCH:
            price_cfg = current.setdefault("costs", {})
            for key, bounds in PRICE_RANGES.items():
                grid = float_grid(bounds, PRICE_STEP)
                lo, hi = bounds
                best_val = min(max(price_cfg.get(key, (lo + hi) / 2.0), lo), hi)
                local_best = best_profit
                for val in grid:
                    cand = copy.deepcopy(current)
                    cand.setdefault("costs", {})
                    cand["costs"][key] = min(max(val, lo), hi)
                    profit = evaluate(cand, iterations, start_seed)
                    if profit > local_best:
                        local_best = profit
                        best_val = cand["costs"][key]
                price_cfg[key] = best_val
                best_profit = local_best

        # Sweep pack priorities if enabled (finite option set)
        if USE_PACK_PRIORITY_SEARCH:
            pol_cfg = current.setdefault("policies", {})
            best_val = pol_cfg.get("pack_priority", [])
            local_best = best_profit
            for opt in PACK_PRIORITY_OPTIONS:
                cand = copy.deepcopy(current)
                cand.setdefault("policies", {})
                cand["policies"]["pack_priority"] = opt
                profit = evaluate(cand, iterations, start_seed)
                if profit > local_best:
                    local_best = profit
                    best_val = opt
            pol_cfg["pack_priority"] = best_val
            best_profit = local_best
    return best_profit, current

def _print_block(indent: int, key: str, block: Dict):
    """
    Pretty-print a nested block with optional special-casing for wages so they
    appear one per line. Avoid f-string brace issues by concatenating strings.
    """
    pad = " " * indent
    print(f'{pad}"{key}": {{')
    for k, v in block.items():
        if isinstance(v, dict) and k == "wages_per_hour":
            # Print each wage on its own line for readability
            print(f'{pad}    "wages_per_hour": {{')
            for wk, wv in v.items():
                print(f'{pad}        "{wk}": {wv},')
            print(pad + "    },")
        elif isinstance(v, dict):
            _print_block(indent + 4, k, v)
        else:
            print(f'{pad}    "{k}": {v},')
    # Close the current block without triggering f-string brace parsing
    print(pad + "},")

def format_as_scenario(name: str, cfg: Dict):
    """
    Emit a ready-to-paste scenario block mirroring scenarios.py style,
    including costs (prices/wages) so wage/price sweeps are visible.
    """
    print(f'{name.upper()} = {{')
    print(f'    "name": "{name}",')
    print('    "overrides": {')
    for section in ("service_rates", "capacities", "penalties", "costs", "policies"):
        block = cfg.get(section, {})
        if not block:
            continue
        _print_block(8, section, block)
    print("    },")
    print("}")

def search(
    service_step: float = SERVICE_STEP,
    capacity_step: int = CAPACITY_STEP,
    passes: int = COORDINATE_PASSES,
    iterations: int = SEARCH_ITERATIONS,
    start_seed: int = SEARCH_START_SEED,
    scenario_names: List[str] = SELECTED_SCENARIOS,
):
    """
    Run coordinate-ascent search for selected scenarios:
      * Apply scenario overrides on top of baseline config.
      * Sweep service/capacity grids with user-defined steps (multiplier or absolute).
      * For each candidate, average profit across `iterations` seeds starting at `start_seed`.
      * Print best profit and a copy/paste scenario override block.
    """
    base = load_cfg()
    # Build a lookup by scenario name to allow user selection.
    sc_index = {sc["name"]: sc for sc in SCENARIOS}
    targets = scenario_names or [sc["name"] for sc in SCENARIOS]
    for sc_name in targets:
        sc = sc_index.get(sc_name)
        if sc is None:
            print(f"[warn] scenario '{sc_name}' not found; skipping.")
            continue
        print(f"\n=== Searching scenario: {sc['name']} ===")
        base_cfg = apply_overrides(base, sc["overrides"])
        best_profit, best_cfg = coord_ascent(base_cfg, service_step, capacity_step, passes, iterations, start_seed)
        print(f"  Best avg profit/day (over {iterations} seeds): ${best_profit:,.2f}")
        scenario_name = f"{sc['name']}_optimized"
        format_as_scenario(scenario_name, best_cfg)

if __name__ == "__main__":
    # Default steps keep runtime manageable; tweak for finer grids.
    search()
