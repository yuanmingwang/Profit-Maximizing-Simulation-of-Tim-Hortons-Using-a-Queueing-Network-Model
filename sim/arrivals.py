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

    # Convert configured mean station times (minutes) into per-second service rates
    svc_rates = {}
    for station, mean_min in cfg.get("service_rates", {}).items():
        mean_sec = mean_min * 60.0
        svc_rates[station] = 1.0 / mean_sec if mean_sec > 0 else None
    # deterministic routes per menu item (extend here for multi-stage items)
    item_routes: Dict[str, Tuple[str, ...]] = {
        "beverage": ("beverage",),
        "hotfood": ("hotfood",),
        "espresso": ("espresso",),
    }
    order_mix_cfg = cfg.get("order_mix", {})

    def _make_item(kind: str, route: Tuple[str, ...]) -> Item:
        """
        Helper to manufacture a kitchen Item for the current order.

        Parameters
        kind: str
            Friendly name for downstream routing/metrics (e.g., "beverage").
        route: tuple[str,...]
            Sequence of station names this item must visit (usually length 1).

        Returns
        Item
            A fully-formed Item carrying price/cogs annotations so the metrics
            module can compute revenue and profit contributions.
        """
        first_station = route[0]
        svc_rate = svc_rates.get(first_station)
        if svc_rate is None:
            raise ValueError(f"No service rate configured for station {first_station}")
        price = price_map.get(kind, 0.0)
        return Item(
            kind,
            {"rate": svc_rate},
            route,
            price=price,
            cogs=price * cogs_pct,
        )

    def _get_mix(channel: str) -> Dict[str, float]:
        """Lookup item inclusion probabilities for a given channel."""
        return order_mix_cfg.get(channel) or order_mix_cfg.get("default", {})

    def _sample_item_names(channel: str) -> List[str]:
        """
        Draw a list of item kinds for the specified channel based on config
        probabilities. Ensures at least one item by falling back to the highest
        probability entry when all Bernoulli trials fail.
        """
        mix = _get_mix(channel)
        picked: List[str] = []
        for name, prob in mix.items():
            if name not in item_routes:
                continue
            if random.random() < float(prob):
                picked.append(name)
        if not picked:
            if mix:
                fallback = max(mix.items(), key=lambda kv: kv[1])[0]
                if fallback in item_routes:
                    picked.append(fallback)
            if not picked:
                picked.append("beverage")
        return picked

    # Walk‑in arrivals (NHPP). Each order draws item mix based on config weights.
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["walkin"]):
        cust = Customer(
            "walkin",
            arrival_time=ts,
            dine_in=True,
            patience=patience_vals.get("dine_in"),
        )
        order = Order(oid=int(ts*1000), customer=cust, items=[], t_created=ts)
        order.items = [
            _make_item(name, item_routes[name]) for name in _sample_item_names("walkin")
        ]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "cashier"}))

    # Drive‑thru arrivals: customers join the window queue with sampled menus.
    for ts in _gen_nhpp_arrivals(0, sim_minutes, rates["drive_thru"]):
        cust = Customer("drive_thru", arrival_time=ts)
        order = Order(oid=int(ts*1000)+1, customer=cust, items=[], t_created=ts)
        order.items = [
            _make_item(name, item_routes[name]) for name in _sample_item_names("drive_thru")
        ]
        env.schedule(Event(ts, "arrival", {"job": order, "target": "window"}))

    # Mobile arrivals can follow NHPP dayparts or fall back to deterministic promises
    mobile_dayparts = rates.get("mobile")
    promises_cfg = rates.get("mobile_promises", {})
    offset_min = promises_cfg.get("promise_offset", 5)

    def _schedule_mobile(ts_seconds: float):
        """Create a mobile order released at ts_seconds into the simulation."""
        promised_pickup = ts_seconds + offset_min * 60.0
        cust = Customer(
            "mobile",
            arrival_time=ts_seconds,
            promised_pickup=promised_pickup,
            patience=patience_vals.get("mobile"),
        )
        order = Order(oid=int(ts_seconds*1000)+2, customer=cust, items=[], t_created=ts_seconds)
        order.items = [
            _make_item(name, item_routes[name]) for name in _sample_item_names("mobile")
        ]
        env.schedule(Event(ts_seconds, "arrival", {"job": order, "target": "cashier"}))

    if mobile_dayparts:
        for ts in _gen_nhpp_arrivals(0, sim_minutes, mobile_dayparts):
            _schedule_mobile(ts)
    else:
        start = promises_cfg.get("start", 0)
        end   = promises_cfg.get("end", sim_minutes)
        step  = promises_cfg.get("interval", 5)
        for m in range(start, end, step):
            ts = float(m) * 60.0
            _schedule_mobile(ts)
