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
from typing import List, Tuple
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

    # Walk‑in
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["walkin"]):
        # make one simple order with 1 beverage item as placeholder
        cust = Customer("walkin", arrival_time=ts)
        order = Order(oid=int(ts*1000), customer=cust, items=[], t_created=ts)
        order.items = [Item("beverage", {"rate": 1/25.0}, ("beverage",))]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "cashier"}))

    # Drive‑thru
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["drive_thru"]):
        cust = Customer("drive_thru", arrival_time=ts)
        order = Order(oid=int(ts*1000)+1, customer=cust, items=[], t_created=ts)
        order.items = [Item("hotfood", {"rate": 1/40.0}, ("hotfood",))]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "window"}))

    # Mobile (deterministic promises for demo)
    start = rates["mobile_promises"]["start"]
    end   = rates["mobile_promises"]["end"]
    step  = rates["mobile_promises"]["interval"]    # minutes
    offset = rates["mobile_promises"].get("promise_offset", 5)  # minutes
    for m in range(start, end, step):
        ts = float(m)  # minutes
        cust = Customer("mobile", arrival_time=ts, promised_pickup=ts + offset)
        order = Order(oid=int(ts*1000)+2, customer=cust, items=[], t_created=ts)
        order.items = [Item("espresso", {"rate": 1/30.0}, ("espresso",))]
        # In Option B, mobile "release" to kitchen can be before pickup time
        env.schedule(Event(ts, "arrival", {"job": order, "target": "cashier"}))
