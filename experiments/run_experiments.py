"""
experiments/run_experiments.py

Experiment harness that loads the baseline config, applies scenario overrides,
runs multiple daily replications, and reports KPIs with confidence intervals.
The script is intentionally lightweight so we can tweak scenarios or plug in
other analysis pipelines as needed.
"""

from __future__ import annotations
import copy, yaml, os, sys, math
from typing import Dict, List, Callable
from statistics import mean, stdev, variance, NormalDist
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
    """Apply scenario overrides (recursive merge) on top of the base config."""
    new = copy.deepcopy(cfg)

    def _merge(dst: Dict, src: Dict):
        for key, val in src.items():
            if isinstance(val, dict) and isinstance(dst.get(key), dict):
                _merge(dst[key], val)
            else:
                dst[key] = copy.deepcopy(val)

    _merge(new, overrides)
    return new

def mean_ci(values: List[float], confidence_level: float) -> tuple[float, float]:
    """
    Return (mean, half-width) using a t-distribution critical value (falls back
    to normal only if SciPy is unavailable).
    """
    if not values:
        return 0.0, 0.0
    mu = mean(values)
    n = len(values)
    if n < 2:
        return mu, 0.0
    level = min(max(confidence_level, 0.0), 0.999999)
    alpha = 1.0 - level
    # Use t critical value with df = n-1
    try:  # pragma: no cover
        from scipy.stats import t  # type: ignore
        tcrit = t.ppf(1 - alpha / 2.0, n - 1)
    except Exception:
        # Fallback to normal if SciPy unavailable; this is conservative when n is large.
        tcrit = NormalDist().inv_cdf(1 - alpha / 2.0)
    half = tcrit * (stdev(values) / math.sqrt(n))
    return mu, half

def sample_stddev(values: List[float]) -> float:
    """Return sample standard deviation or 0 if insufficient data."""
    if len(values) < 2:
        return 0.0
    return stdev(values)

def run_crn(cfg: Dict, sc_a: Dict, sc_b: Dict, replications: int, base_seed: int, confidence: float, C : int):
    """
    Run a common-random-number comparison between two scenarios, using the same
    seed stream per replication, and report paired differences and CI of the mean.
    """
    results = []
    # Build base configs
    cfg_a = apply_overrides(cfg, sc_a["overrides"])
    cfg_b = apply_overrides(cfg, sc_b["overrides"])
    for rep in range(replications):
        seed = base_seed + rep
        cfg_a_run = copy.deepcopy(cfg_a); cfg_a_run.setdefault("sim", {})["seed"] = seed
        cfg_b_run = copy.deepcopy(cfg_b); cfg_b_run.setdefault("sim", {})["seed"] = seed
        res_a = run_one_day(cfg_a_run)
        res_b = run_one_day(cfg_b_run)
        results.append((seed, res_a.get("profit_per_day", 0.0), res_b.get("profit_per_day", 0.0)))
    diffs = [b - a for (_, a, b) in results]
    mean_diff = mean(diffs)
    sd_diff = stdev(diffs) if len(diffs) > 1 else 0.0
    level = min(max(confidence, 0.0), 0.999999)
    # alpha = 1.0 - level
    # alpha here should follow the Bonferroni approach
    # Check LectureNotes-Week13.pdf, page 84, 9.2 Comparison of Multiple System Designs
    # a_i = a_E / C, and C = 3 here in our comparasion
    alpha = (1.0 - level) / C
    df = max(1, len(diffs) - 1)
    try:  # pragma: no cover
        from scipy.stats import t  # type: ignore
        tcrit = t.ppf(1 - alpha / 2.0, df)
    except Exception:
        tcrit = NormalDist().inv_cdf(1 - alpha / 2.0)
    half = tcrit * (sd_diff / math.sqrt(len(diffs))) if len(diffs) > 1 else 0.0
    # Print CRN table
    print("CRN paired profit comparison (Scenario2 - Scenario1):")
    print("  Replication | Seed | Profit1 | Profit2 | Difference")
    for idx, (seed, p1, p2) in enumerate(results, start=1):
        print(f"    {idx:2d}        | {seed:4d} | ${p1:,.2f} | ${p2:,.2f} | ${p2 - p1:,.2f}")
    print(f"  Mean difference (profit2 - profit1): ${mean_diff:,.2f}")
    print(f"  Std dev of differences: {sd_diff:,.2f}")
    print(f"  {level*100:.1f}% CI of mean diff: ${mean_diff - half:,.2f} to ${mean_diff + half:,.2f}")

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

def _interp_point(series: List[Dict[str, float]], target_minute: float) -> Dict[str, float]:
    """
    Linearly interpolate cumulative totals at an arbitrary time stamp so that
    per-replication curves can be averaged on a common time grid.
    """
    if not series:
        return {"time_minutes": target_minute, "profit_total": 0.0, "revenue_total": 0.0}
    # If the query time precedes our first observation, treat totals as zero.
    if target_minute <= series[0]["time_minutes"]:
        return {"time_minutes": target_minute, "profit_total": 0.0, "revenue_total": 0.0}
    prev = series[0]
    for pt in series:
        if pt["time_minutes"] >= target_minute:
            if pt["time_minutes"] == target_minute or pt["time_minutes"] == prev["time_minutes"]:
                return {
                    "time_minutes": target_minute,
                    "profit_total": pt.get("profit_total", 0.0),
                    "revenue_total": pt.get("revenue_total", 0.0),
                }
            # Linear interpolation between prev and current
            span = pt["time_minutes"] - prev["time_minutes"]
            w = (target_minute - prev["time_minutes"]) / span
            return {
                "time_minutes": target_minute,
                "profit_total": prev.get("profit_total", 0.0) + w * (pt.get("profit_total", 0.0) - prev.get("profit_total", 0.0)),
                "revenue_total": prev.get("revenue_total", 0.0) + w * (pt.get("revenue_total", 0.0) - prev.get("revenue_total", 0.0)),
            }
        prev = pt
    return {
        "time_minutes": target_minute,
        "profit_total": series[-1].get("profit_total", 0.0),
        "revenue_total": series[-1].get("revenue_total", 0.0),
    }

def aggregate_time_series(results: List[Dict], day_minutes: float, interval_minutes: float) -> List[Dict[str, float]]:
    """
    Aggregate per-replication time series on a fixed interval grid so we can
    plot profit/revenue generated per interval over the simulated day.
    """
    if not results:
        return []
    if interval_minutes <= 0:
        interval_minutes = 6.0
    # Start grid at 0 to include an explicit origin point for plotting.
    grid = [i * interval_minutes for i in range(int(math.ceil(day_minutes / interval_minutes)) + 1)]
    aggregated: List[Dict[str, float]] = []
    # Include the initial zero interval so curves start at time=0 with 0 increment.
    aggregated.append({
        "time_minutes": 0.0,
        "profit_interval": 0.0,
        "revenue_interval": 0.0,
    })
    for idx in range(1, len(grid)):
        end_minute = float(grid[idx])
        start_minute = float(grid[idx - 1])
        profit_vals: List[float] = []
        revenue_vals: List[float] = []
        for res in results:
            series = res.get("time_series", [])
            if not series:
                continue
            prev_pt = _interp_point(series, start_minute)
            curr_pt = _interp_point(series, end_minute)
            profit_vals.append(curr_pt["profit_total"] - prev_pt["profit_total"])
            revenue_vals.append(curr_pt["revenue_total"] - prev_pt["revenue_total"])
        if profit_vals:
            aggregated.append({
                "time_minutes": end_minute,
                "profit_interval": sum(profit_vals) / len(profit_vals),
                "revenue_interval": sum(revenue_vals) / len(revenue_vals),
            })
    return aggregated

def plot_time_series(series: List[Dict[str, float]], warmup_minutes: float, scenario_name: str):
    """
    Persist a PNG plot showing profit/revenue generated per interval versus
    time, with the warm-up cutoff drawn as a vertical line for visual diagnosis.
    """
    if not series:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    x = [pt["time_minutes"] for pt in series]
    y_profit = [pt["profit_interval"] for pt in series]
    y_revenue = [pt["revenue_interval"] for pt in series]
    plt.figure(figsize=(9, 5))
    plt.plot(x, y_profit, label="Profit per interval", color="#d97706")
    plt.plot(x, y_revenue, label="Revenue per interval", color="#2563eb")
    if warmup_minutes > 0:
        plt.axvline(warmup_minutes, color="#f59e0b", linestyle="--", label="Warm-up cutoff")
        # Add the warm-up value as an x-axis tick so the number appears under the axis.
        ticks, _ = plt.xticks()
        tick_list = list(ticks)
        if warmup_minutes not in tick_list:
            tick_list.append(warmup_minutes)
        tick_list = sorted(set(tick_list))
        tick_labels = [f"{int(t)}" if abs(t - int(t)) < 1e-6 else f"{t:.1f}" for t in tick_list]
        plt.xticks(tick_list, tick_labels)
    # Keep the plot domain anchored at time=0 to avoid stray negative padding.
    if x:
        plt.xlim(left=0, right=max(x) + 100)
    plt.xlabel("Time (minutes)")
    plt.ylabel("Performance measure (Profit, Revenue)")
    plt.title(f"{scenario_name}: running averages")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    out_dir = os.path.join(ROOT, "experiments", "output")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = scenario_name.lower().replace(" ", "_")
    out_path = os.path.join(out_dir, f"{safe_name}_profit_curve.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path

def plot_all_scenario_profits(all_results: List[Dict[str, List[Dict[str, float]]]], warmup_minutes: float, interval_minutes: float, day_minutes: float):
    """
    Plot profit/revenue per-interval curves for all scenarios on one figure to
    visualize time-based performance. Expects aggregated time series per scenario:
      - name: scenario name
      - series: list of dicts with time_minutes, profit_interval, revenue_interval
    """
    if not all_results:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    plt.figure(figsize=(9, 5))
    for entry in all_results:
        series = entry.get("series", [])
        if not series:
            continue
        x = [pt["time_minutes"] for pt in series]
        y_profit = [pt["profit_interval"] for pt in series]
        plt.plot(x, y_profit, linewidth=1.5, label=entry.get("name", "scenario"))
    # Align x-limits to the configured plotting horizon
    if day_minutes and interval_minutes > 0:
        plt.xlim(0, day_minutes)
    if warmup_minutes > 0:
        plt.axvline(warmup_minutes, color="#f59e0b", linestyle="--", label="Warm-up cutoff")
        # Add warm-up value as a tick label to highlight the cutoff on the axis.
        ticks, _ = plt.xticks()
        tick_list = list(ticks)
        if warmup_minutes not in tick_list:
            tick_list.append(warmup_minutes)
        tick_list = sorted(set(tick_list))
        tick_labels = [f"{int(t)}" if abs(t - int(t)) < 1e-6 else f"{t:.1f}" for t in tick_list]
        plt.xticks(tick_list, tick_labels)
    plt.xlabel("Time (minutes)")
    plt.ylabel("Performance measure (Profit)")
    plt.title("Profit over Time across scenarios")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    out_dir = os.path.join(ROOT, "experiments", "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "all_scenarios_profit_by_time.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
    return out_path

def main():
    """Entry point: drive all scenarios, replications, and report KPIs."""
    cfg = load_cfg()
    exp_cfg = cfg.get("experiments", {})
    replications = max(1, int(exp_cfg.get("replications", 1)))
    confidence = float(exp_cfg.get("confidence_level", 0.95))
    interval_minutes = float(exp_cfg.get("time_series_interval_minutes", 6.0))
    multi_interval_minutes = float(exp_cfg.get("multi_scenario_interval_minutes", interval_minutes))
    level_pct = confidence * 100.0
    default_seed = cfg.get("sim", {}).get("seed", 0)

    all_profit_lines: List[Dict[str, List[float]]] = []
    max_warmup = 0.0
    for sc in SCENARIOS:
        sc_base_cfg = apply_overrides(cfg, sc["overrides"])
        scenario_seed = sc_base_cfg.get("sim", {}).get("seed", default_seed)
        seed_range = (scenario_seed, scenario_seed + replications - 1)
        warmup_minutes = float(sc_base_cfg.get("sim", {}).get("warmup_minutes", 0.0))
        max_warmup = max(max_warmup, warmup_minutes)
        results = []
        per_seed_profit = []
        for rep in range(replications):
            sc_cfg = copy.deepcopy(sc_base_cfg)
            sc_cfg.setdefault("sim", {})
            # Advance the RNG seed per replication so replications remain iid but scenario-specific seeds stick.
            sc_cfg["sim"]["seed"] = scenario_seed + rep
            res = run_one_day(sc_cfg)
            results.append(res)
            per_seed_profit.append((sc_cfg["sim"]["seed"], res.get("profit_per_day", 0.0)))
        # Capture per-replication profits for cross-scenario plot
        all_profit_lines.append({
            "name": sc["name"],
            "seeds": [s for s, _ in per_seed_profit],
            "profits": [p for _, p in per_seed_profit],
        })

        # Collect KPI distributions across replications so we can report means with CIs.
        profit = mean_ci(series(results, lambda r: r.get("profit_per_day", 0.0)), confidence)
        revenue = mean_ci(series(results, lambda r: r.get("revenue_per_day", 0.0)), confidence)
        profit_sd = sample_stddev(series(results, lambda r: r.get("profit_per_day", 0.0)))
        labor = mean_ci(series(results, lambda r: r.get("labor_cost_per_day", 0.0)), confidence)
        walkin_wait = mean_ci(series(results, lambda r: r.get("avg_front_wait_minutes", {}).get("walkin", 0.0)), confidence)
        drive_wait = mean_ci(series(results, lambda r: r.get("avg_front_wait_minutes", {}).get("drive_thru", 0.0)), confidence)
        drive_pickup_wait = mean_ci(series(results, lambda r: r.get("avg_pickup_wait_minutes", {}).get("drive_thru", 0.0)), confidence)
        mobile_pickup_wait = mean_ci(series(results, lambda r: r.get("avg_pickup_wait_minutes", {}).get("mobile", 0.0)), confidence)
        mobile_ready = mean_ci(series(results, lambda r: r.get("mobile_ready_rate", 0.0) * 100.0), confidence)
        balks = mean_ci(series(results, lambda r: sum(r.get("balked_customers", {}).values())), confidence)
        reneges = mean_ci(series(results, lambda r: sum(r.get("pickup_reneges", {}).values())), confidence)
        penalties = mean_ci(series(results, lambda r: r.get("penalty_total", 0.0)), confidence)
        dine_in_visits = mean_ci(series(results, lambda r: r.get("dine_in_customers", 0.0)), confidence)
        dine_in_time = mean_ci(series(results, lambda r: r.get("avg_dine_in_time_minutes", 0.0)), confidence)
        rev_per_customer = mean_ci(series(results, lambda r: r.get("revenue_per_customer", 0.0)), confidence)
        served = avg_nested(results, "served_by_channel")
        utilizations = {k: round(v * 100.0, 1) for k, v in avg_nested(results, "station_utilization").items()}
        # Build running-mean curves (single-scenario binning and multi-scenario binning)
        day_len = sc_base_cfg.get("sim", {}).get("day_minutes", 0.0)
        agg_series = aggregate_time_series(results, day_len, interval_minutes)
        agg_series_multi = aggregate_time_series(results, day_len, multi_interval_minutes)
        plot_path = plot_time_series(agg_series, warmup_minutes, sc["name"])
        # Save multi-binned series for cross-scenario plot
        all_profit_lines.append({
            "name": sc["name"],
            "series": agg_series_multi,
        })

        print(f"Scenario: {sc['name']} (replications={replications}, {level_pct:.1f}% CI, seeds {seed_range[0]}-{seed_range[1]})")
        # Per-seed profit table for quick diagnostics
        print("  Profit by seed:")
        for seed, val in per_seed_profit:
            print(f"    seed {seed}: ${val:,.2f}")
        print(f"  Profit std dev: {profit_sd:,.2f}")
        print(f"  Profit/day: ${profit[0]:,.2f} ± ${profit[1]:,.2f}")
        print(f"  Revenue/day: ${revenue[0]:,.2f} ± ${revenue[1]:,.2f}")
        print(f"  Labor cost/day: ${labor[0]:,.2f} ± ${labor[1]:,.2f}")
        print(f"  Avg wait walk-in: {walkin_wait[0]:.2f} ± {walkin_wait[1]:.2f} min")
        print(f"  Avg wait drive-thru: {drive_wait[0]:.2f} ± {drive_wait[1]:.2f} min")
        print(f"  Avg pickup wait drive-thru: {drive_pickup_wait[0]:.2f} ± {drive_pickup_wait[1]:.2f} min")
        print(f"  Avg pickup wait mobile: {mobile_pickup_wait[0]:.2f} ± {mobile_pickup_wait[1]:.2f} min")
        print(f"  Mobile ready-by-promise rate: {mobile_ready[0]:.1f}% ± {mobile_ready[1]:.1f}%")
        print(f"  Balked/day: {balks[0]:.2f} ± {balks[1]:.2f}")
        print(f"  Pickup reneges/day: {reneges[0]:.2f} ± {reneges[1]:.2f}")
        print(f"  Penalties/day: ${penalties[0]:,.2f} ± ${penalties[1]:,.2f}")
        print(f"  Dine-in customers/day: {dine_in_visits[0]:.2f} ± {dine_in_visits[1]:.2f}")
        print(f"  Avg dine-in stay (incl cleaning): {dine_in_time[0]:.2f} ± {dine_in_time[1]:.2f} min")
        print(f"  Avg revenue per customer: ${rev_per_customer[0]:.2f} ± ${rev_per_customer[1]:.2f}")
        print(f"  Served by channel (mean customers/day): { {k: round(v, 1) for k, v in served.items()} }")
        print(f"  Server utilization (mean % busy): {utilizations}")
        if plot_path:
            print(f"  Profit, Revenue, Warm-up plot saved to: {plot_path}")
        print("-")

    # Optional CRN comparison between two named scenarios using common random numbers
    crn_pairs = exp_cfg.get("crn_compare")
    if crn_pairs:
        # Normalize to list of pairs
        if isinstance(crn_pairs, tuple):
            crn_pairs = [list(crn_pairs)]
        if isinstance(crn_pairs, list) and crn_pairs and isinstance(crn_pairs[0], (list, tuple)):
            sc_index = {s["name"]: s for s in SCENARIOS}
            # Calculate C using in Bonferroni approach to calculate the confidence interval
            # C = K(K-1)/2, where K = # alternative system design
            # Check LectureNotes-Week13.pdf, page 84, 9.2 Comparison of Multiple System Designs
            K = len(crn_pairs)
            C = K * (K - 1) / 2
            for pair in crn_pairs:
                if len(pair) != 2:
                    print(f"[warn] skipping CRN entry (needs 2 names): {pair}")
                    continue
                sc_a = sc_index.get(pair[0])
                sc_b = sc_index.get(pair[1])
                if sc_a and sc_b:
                    print(f"\nCRN & Bonferroni Comparison: {sc_a['name']} vs {sc_b['name']} (replications={replications}, seeds shared)")
                    run_crn(cfg, sc_a, sc_b, replications, default_seed, confidence, C)
                else:
                    print(f"[warn] CRN pair not found: {pair}")
    # Plot cross-scenario profit curves
    cross_plot = plot_all_scenario_profits(
        all_profit_lines,
        warmup_minutes=max_warmup,
        interval_minutes=multi_interval_minutes,
        day_minutes=cfg.get("sim", {}).get("day_minutes", 0),
    )
    if cross_plot:
        print(f"\nAll-scenario profit-by-seed plot saved to: {cross_plot}")

if __name__ == "__main__":
    main()
