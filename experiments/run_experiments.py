"""
experiments/run_experiments.py

Minimal experiment runner that loads config, applies one scenario, runs a single
replication, and prints a small summary.
"""

from __future__ import annotations
import json, copy, yaml, os, sys
from typing import Dict
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

def main():
    cfg = load_cfg()
    for sc in SCENARIOS:
        sc_cfg = apply_overrides(cfg, sc["overrides"])
        res = run_one_day(sc_cfg)
        print(f"Scenario: {sc['name']} -> Summary: " + json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
