"""
experiments/run_experiments.py

Experiment harness that loads the baseline config, applies scenario overrides,
runs multiple daily replications, and reports KPIs with confidence intervals.
"""

from __future__ import annotations
import copy, yaml, os, sys, math
from typing import Dict, List, Callable
from statistics import mean, stdev, NormalDist
try:
    # When executed as a module: python -m experiments.run_experiments
    from .scenarios import SCENARIOS  # type: ignore
except Exception:  # pragma: no cover
    # When run as a script in VSCode/terminal
    import os, sys
    ROOT = os.path.dirname(os.path.dirname(__file__))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from experiments.scenarios import SCENARIOS  # type: ignore

from sim.simulation import run_one_day

ROOT = os.path.dirname(os.path.dirname(__file__))

def load_cfg() -> Dict:
    with open(os.path.join(ROOT, "config", "baseline.yaml"), "r") as f:
        return yaml.safe_load(f)
    # if service rate
    # with open(os.path.join(ROOT, "config", "baseline.yaml"), "r") as f:
    #     # Safe eval for simple expressions in YAML like 1.0/45.0
    #     raw = f.read()
    # # Evaluate simple math in the YAML by a two‑step: yaml->str replace is risky;
    # # for the scaffold we allow 1.0/45.0 only in code; here we precompute below.
    # cfg = yaml.safe_load(raw)
    # # Precompute 'service_rates' if they used a/b style
    # sr = cfg.get("service_rates", {})
    # for k,v in list(sr.items()):
    #     if isinstance(v, str) and "/" in v:
    #         num, den = v.split("/")
    #         sr[k] = float(num) / float(den)
    # cfg["service_rates"] = sr
    # return cfg

def apply_overrides(cfg: Dict, overrides: Dict) -> Dict:
    new = copy.deepcopy(cfg)
    for k, v in overrides.items():
        new[k] = v
    return new

def mean_ci(values: List[float], confidence_level: float) -> tuple[float, float]:
    """Return (mean, half-width) for a normal-approximation CI."""
    if not values:
        return 0.0, 0.0
    mu = mean(values)
    if len(values) < 2:
        return mu, 0.0
    level = min(max(confidence_level, 0.0), 0.999999)
    alpha = 1.0 - level
    z = NormalDist().inv_cdf(1 - alpha / 2.0)
    half = z * (stdev(values) / math.sqrt(len(values)))
    return mu, half

def series(results: List[Dict], extractor: Callable[[Dict], float]) -> List[float]:
    """Collect a numeric series from each replication result."""
    return [float(extractor(res)) for res in results]

def avg_nested(results: List[Dict], key: str) -> Dict[str, float]:
    """Average nested dictionaries (e.g., served_by_channel) across replications."""
    if not results:
        return {}
    totals: Dict[str, float] = {}
    for res in results:
        nested = res.get(key, {})
        for subk, val in nested.items():
            totals[subk] = totals.get(subk, 0.0) + float(val)
    return {subk: totals[subk] / len(results) for subk in totals}

def main():
    cfg = load_cfg()
    exp_cfg = cfg.get("experiments", {})
    replications = max(1, int(exp_cfg.get("replications", 1)))
    confidence = float(exp_cfg.get("confidence_level", 0.95))
    base_seed = cfg.get("sim", {}).get("seed", 0)
    level_pct = confidence * 100.0

    for sc in SCENARIOS:
        results = []
        for rep in range(replications):
            sc_cfg = apply_overrides(cfg, sc["overrides"])
            sc_cfg.setdefault("sim", {})
            sc_cfg["sim"]["seed"] = base_seed + rep
            results.append(run_one_day(sc_cfg))

        profit = mean_ci(series(results, lambda r: r.get("profit_per_day", 0.0)), confidence)
        revenue = mean_ci(series(results, lambda r: r.get("revenue_per_day", 0.0)), confidence)
        labor = mean_ci(series(results, lambda r: r.get("labor_cost_per_day", 0.0)), confidence)
        walkin_wait = mean_ci(series(results, lambda r: r.get("avg_front_wait_minutes", {}).get("walkin", 0.0)), confidence)
        drive_wait = mean_ci(series(results, lambda r: r.get("avg_front_wait_minutes", {}).get("drive_thru", 0.0)), confidence)
        mobile_ready = mean_ci(series(results, lambda r: r.get("mobile_ready_rate", 0.0) * 100.0), confidence)
        balks = mean_ci(series(results, lambda r: sum(r.get("balked_customers", {}).values())), confidence)
        reneges = mean_ci(series(results, lambda r: sum(r.get("pickup_reneges", {}).values())), confidence)
        penalties = mean_ci(series(results, lambda r: r.get("penalty_total", 0.0)), confidence)
        served = avg_nested(results, "served_by_channel")
        utilizations = {k: round(v * 100.0, 1) for k, v in avg_nested(results, "station_utilization").items()}

        print(f"Scenario: {sc['name']} (replications={replications}, {level_pct:.1f}% CI)")
        print(f"  Profit/day: ${profit[0]:,.2f} ± ${profit[1]:,.2f}")
        print(f"  Revenue/day: ${revenue[0]:,.2f} ± ${revenue[1]:,.2f}")
        print(f"  Labor cost/day: ${labor[0]:,.2f} ± ${labor[1]:,.2f}")
        print(f"  Avg wait walk-in: {walkin_wait[0]:.2f} ± {walkin_wait[1]:.2f} min")
        print(f"  Avg wait drive-thru: {drive_wait[0]:.2f} ± {drive_wait[1]:.2f} min")
        print(f"  Mobile ready-by-promise rate: {mobile_ready[0]:.1f}% ± {mobile_ready[1]:.1f}%")
        print(f"  Balked/day: {balks[0]:.2f} ± {balks[1]:.2f}")
        print(f"  Pickup reneges/day: {reneges[0]:.2f} ± {reneges[1]:.2f}")
        print(f"  Penalties/day: ${penalties[0]:,.2f} ± ${penalties[1]:,.2f}")
        print(f"  Served by channel (mean customers/day): { {k: round(v, 1) for k, v in served.items()} }")
        print(f"  Station utilization (mean % busy): {utilizations}")
        print("-")

if __name__ == "__main__":
    main()
