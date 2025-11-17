"""
experiments/optimize_profit.py

Heuristic that searches for high-profit Tim Hortons configurations by
randomly perturbing a handful of staffing/capacity decisions and evaluating the
resulting daily profit. This provides a reproducible way to explore
the decision space without manually editing YAML each time.
"""

from __future__ import annotations
import copy, math, random
from typing import Dict, Tuple
try:
    # When executed as a module: python -m experiments.optimize_profit
    from sim.simulation import run_one_day
    from .run_experiments import load_cfg  # type: ignore
except Exception:  # pragma: no cover - fallback for VSCode "python file.py"
    import os, sys
    ROOT = os.path.dirname(os.path.dirname(__file__))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from sim.simulation import run_one_day  # type: ignore
    from experiments.run_experiments import load_cfg  # type: ignore

# Bounds for decision variables. SERVICE_MULTS entries are multiplicative factors
# applied to the baseline mean times, so 0.8 => 20% faster, 1.2 => 20% slower.
SERVICE_MULTS = {
    "cashier": (0.8, 1.2),
    "window": (0.8, 1.2),
    "hotfood": (0.8, 1.2),
    "pack": (0.8, 1.2),
    "dine_in": (0.8, 1.2),
    "table_cleaning": (0.7, 1.3),
}
# CAPACITY_CHOICES specify integer ranges for the number of parallel servers.
CAPACITY_CHOICES = {
    "espresso_c": (1, 3),
    "hotfood_c": (1, 3),
    "beverage_c": (1, 3),
    "dine_in_tables": (8, 25),
    "table_cleaners": (1, 3),
}

def sample_multiplier(min_max: Tuple[float, float]) -> float:
    """
    Pick a random multiplier in [min, max] inclusive.

    Parameters
    ----------
    min_max : tuple[float, float]
        Lower/upper bounds around 1.0 (e.g., (0.8, 1.2)).
    """
    lo, hi = min_max
    return random.uniform(lo, hi)

def sample_capacity(bounds: Tuple[int, int]) -> int:
    """Pick an integer capacity inside the provided bounds."""
    lo, hi = bounds
    return random.randint(lo, hi)

def build_candidate(cfg: Dict) -> Dict:
    """
    Produce a new configuration by perturbing base service rates/capacities.
    The sampler keeps values within realistic ranges to avoid infeasible models.
    """
    cand = copy.deepcopy(cfg)
    services = cand.setdefault("service_rates", {})
    for k, (lo, hi) in SERVICE_MULTS.items():
        base = cfg["service_rates"].get(k, services.get(k))
        if base is None:
            continue
        services[k] = max(0.05, base * sample_multiplier((lo, hi)))

    caps = cand.setdefault("capacities", {})
    for k, bounds in CAPACITY_CHOICES.items():
        caps[k] = sample_capacity(bounds)

    # Keep SLA penalties intact but can experiment with balk penalty magnitude
    penalties = cand.setdefault("penalties", {})
    penalties["balk_loss_pct"] = random.uniform(0.2, 0.6)
    return cand

def search(iterations: int = 40, seed: int = 2020):
    """
    Run a simple random search for `iterations` samples. Tracks and prints the
    most profitable configuration encountered.
    """
    random.seed(seed)
    base = load_cfg()
    best = (-math.inf, None)
    for i in range(iterations):
        cand = build_candidate(base)
        result = run_one_day(cand)
        profit = result.get("profit_per_day", -math.inf)
        if profit > best[0]:
            best = (profit, cand)
            print(f"[iter {i+1}] New best profit ${profit:,.2f}")
    print("\nBest configuration found:")
    print(f"Profit/day = ${best[0]:,.2f}")
    best_cfg = best[1] or {}
    # output can be copy/pasted directly into experiments/scenarios.py
    print("OPTIMIZE_PROFIT_SEARCH = {")
    print('    "name": "optimize_profit_search",')
    print('    "overrides": {')
    for section in ("service_rates","capacities","penalties"):
        if section in best_cfg:
            print(f'        "{section}": {{')
            for k, v in best_cfg[section].items():
                print(f'            "{k}": {v},')
            print("        },")
    print('        "sim": {')
    for k,v in best_cfg.get("sim", {}).items():
        print(f'            "{k}": {v},')
    print("        },")
    print("    },")
    print("}")

if __name__ == "__main__":
    search()
