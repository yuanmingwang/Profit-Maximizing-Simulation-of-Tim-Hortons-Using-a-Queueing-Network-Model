# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# network.py
# -----------------------------------------------------------------------------
# Purpose:
#   Router and network wiring. Decides where jobs go on arrival and after
#   service completions, handles joins at pack, and applies simple policies.
#
# Design notes:
#   - Orders hold multiple Items; Items flow separately through kitchen, then
#     PACK waits for all items to be ready before enqueueing a "pack job".
#   - This scaffold keeps policies simple; plug into policies.py as needed.
#
# Usage:
#   router = Router(cfg, stations, metrics)
#   env = Env(router)
# -----------------------------------------------------------------------------

from __future__ import annotations
from typing import Dict, Any, Optional
from .entities import Customer, Order, Item
from .queues import Event
from . import policies

class Router:
    def __init__(self, cfg: dict, stations: Dict[str, Any], metrics):
        self.cfg = cfg
        self.S = stations
        self.M = metrics
        self.orders: Dict[int, Order] = {}

    # Incoming arrivals (already created by arrivals.py)
    def on_arrival(self, env, job: Any, target: str) -> bool:
        server = self.S[target]
        ok = server.enqueue(env, job)
        if not ok:
            # capacity full -> loss/blocking; record if needed
            self.M.note_block(env.t, target, job)
        return ok

    # Timer hooks for policies (e.g., brew cycles), unused in this scaffold
    def on_timer(self, env, **data):
        srv = data.get("server")
        kind = data.get("kind")
        if srv is not None and hasattr(srv, "handle_timer"):
            srv.handle_timer(env, kind=kind)

    # Advance after a server departure
    def advance(self, env, job: Any, from_server):
        kind = getattr(job, "kind", None)
        if from_server.name in ("espresso","hotfood","beverage"):
            # Mark item ready and check order join
            order: Order = job.parent_order  # set by arrivals when creating items
            if order.mark_item_ready(env.t):
                # all items ready -> enqueue to PACK
                self.on_arrival(env, order, target="pack")
        elif from_server.name == "pack":
            # Attempt to move packed order to shelf (finite K can block)
            ok = self.S["shelf"].enqueue(env, job)
            if not ok:
                # If shelf is full, re‑enqueue pack (primitive blocking)
                # A more precise model would hold the pack server busy.
                self.on_arrival(env, job, target="pack")
            else:
                job.t_packed = env.t
                self.M.note_order_packed(job, env.t)
        elif from_server.name == "shelf":
            # Customer picks up immediately in this scaffold
            job.t_picked = env.t
            pickup_wait = 0.0
            if job.t_packed is not None:
                pickup_wait = max(job.t_picked - job.t_packed, 0.0)
            # Customers with finite patience may forfeit their order if wait too long
            if self._pickup_renege(job, pickup_wait):
                self.M.note_pickup_renege(job, pickup_wait, env.t)
            else:
                self.M.note_pickup(job, pickup_wait, env.t)
                self._post_pickup(env, job)
        elif from_server.name == "dine_in":
            # Dine-in visit (including cleaning) finished -> free table
            job.t_left_dine_in = env.t
            self.M.note_dinein_departure(job, env.t)
        elif from_server.name == "dine_in_clean":
            # Cleaning completed -> notify the dine-in server to free a table
            dine_srv = self.S.get("dine_in")
            release = getattr(dine_srv, "release_after_clean", None)
            if callable(release):
                release(env)
        elif from_server.name in ("cashier","window"):
            # Front‑end order entry -> split into items and send to kitchen
            self._fanout_items(env, job)
        else:
            # default: do nothing
            pass

    def _fanout_items(self, env, order: Order):
        # For each item, enqueue to its first station
        for it in order.items:
            it.parent_order = order
            target = it.route[0]
            self.on_arrival(env, it, target=target)
        self.M.note_kitchen_entry(order, env.t)

    def _post_pickup(self, env, order: Order):
        """Route customers after the pickup shelf based on their channel characteristics."""
        cust = getattr(order, "customer", None)
        if not cust:
            return
        if cust.dine_in and "dine_in" in self.S:
            # Dine-in patrons seize a table; cleaning time is baked into the service mean
            ok = self.on_arrival(env, order, target="dine_in")
            if ok:
                order.t_seated = env.t
                self.M.note_dinein_start(order)

    def _pickup_renege(self, order: Order, pickup_wait: float) -> bool:
        cust = getattr(order, "customer", None)
        if cust is None:
            return False
        # Only dine-in and mobile customers renege at pickup
        if not (cust.dine_in or cust.channel == "mobile"):
            return False
        if cust.patience is None:
            return False
        return pickup_wait > cust.patience
