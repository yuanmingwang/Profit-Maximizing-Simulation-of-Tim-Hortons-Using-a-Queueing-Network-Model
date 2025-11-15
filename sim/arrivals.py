# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# arrivals.py
# -----------------------------------------------------------------------------
# Purpose:
#   Generate exogenous arrivals: walk‑in, drive‑thru, and mobile releases.
#   Supports piecewise‑constant nonhomogeneous Poisson (NHPP) via thinning.
#
# Design notes:
#   - For clarity, this scaffold uses a simple "generate then schedule" loop.
#   - Mobile promises are mocked as deterministic intervals; can swap with 
#     future schedule logic from Option B.
#
# Usage:
#   schedule_arrivals(env, router, cfg)
# -----------------------------------------------------------------------------

from __future__ import annotations
import random, math
from typing import List, Tuple, Dict
from .queues import Event
from .entities import Customer, Order, Item

def _pc_rate(time_min, dayparts: List[Tuple[int,int,float]]) -> float:
    # piecewise constant rate lookup: dayparts are [start, end, rate]
    for a,b,lam in dayparts:
        if a <= time_min < b:
            return lam
    return 0.0

def _gen_nhpp_arrivals(start, end, dayparts):
    # naive NHPP: sample each minute with Poisson(lam*1min)
    t = start
    arr = []
    while t < end:
        lam = _pc_rate(t, dayparts)
        # expected arrivals per minute; draw Poisson and place uniformly within minute
        k = random.poisson(lam) if hasattr(random, "poisson") else (1 if random.random() < lam else 0)
        for _ in range(k):
            arr.append(t*60 + random.random()*60.0)  # seconds
        t += 1
    return sorted(arr)

def schedule_arrivals(env, router, cfg):
    # Parse config
    rates = cfg["arrival_rates"]
    sim_minutes = cfg["sim"]["day_minutes"]
    costs = cfg.get("costs", {})
    price_map: Dict[str, float] = {
        "beverage": costs.get("price_coffee", 0.0),
        "espresso": costs.get("price_espresso", 0.0),
        "hotfood": costs.get("price_hotfood", 0.0),
    }
    cogs_pct = costs.get("cogs_pct", 0.0)
    patience_cfg = cfg.get("customers", {}).get("pickup_patience_minutes", {})
    # Convert pickup patience from config minutes to seconds so it aligns with env clock
    patience_vals = {
        "dine_in": float(patience_cfg.get("dine_in", 8.0)) * 60.0,
        "mobile": float(patience_cfg.get("mobile", 5.0)) * 60.0,
    }

    def _make_item(kind: str, svc_rate: float, route: Tuple[str, ...]) -> Item:
        """Attach price/COGS so downstream metrics can tabulate revenue."""
        price = price_map.get(kind, 0.0)
        return Item(
            kind,
            {"rate": svc_rate},
            route,
            price=price,
            cogs=price * cogs_pct,
        )

    # Walk‑in
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["walkin"]):
        # make one simple order with 1 beverage item as placeholder
        cust = Customer(
            "walkin",
            arrival_time=ts,
            dine_in=True,
            patience=patience_vals.get("dine_in"),
        )
        order = Order(oid=int(ts*1000), customer=cust, items=[], t_created=ts)
        order.items = [_make_item("beverage", 1/25.0, ("beverage",))]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "cashier"}))

    # Drive‑thru
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["drive_thru"]):
        cust = Customer("drive_thru", arrival_time=ts)
        order = Order(oid=int(ts*1000)+1, customer=cust, items=[], t_created=ts)
        order.items = [_make_item("hotfood", 1/40.0, ("hotfood",))]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "window"}))

    # Mobile (deterministic promises for demo)
    start = rates["mobile_promises"]["start"]
    end   = rates["mobile_promises"]["end"]
    step  = rates["mobile_promises"]["interval"]    # minutes
    offset = rates["mobile_promises"].get("promise_offset", 5)  # minutes
    for m in range(start, end, step):
        ts = float(m) * 60.0  # seconds
        promised_pickup = ts + offset * 60.0
        cust = Customer(
            "mobile",
            arrival_time=ts,
            promised_pickup=promised_pickup,
            patience=patience_vals.get("mobile"),
        )
        order = Order(oid=int(ts*1000)+2, customer=cust, items=[], t_created=ts)
        order.items = [_make_item("espresso", 1/30.0, ("espresso",))]
        # In Option B, mobile "release" to kitchen can be before pickup time
        env.schedule(Event(ts, "arrival", {"job": order, "target": "cashier"}))
