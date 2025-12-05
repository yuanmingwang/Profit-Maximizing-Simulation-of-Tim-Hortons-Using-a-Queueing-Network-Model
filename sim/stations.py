# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# stations.py
# -----------------------------------------------------------------------------
# Purpose:
#   Define concrete station/server instances (cashier, espresso, hotfood,
#   beverage, pack, shelf, window, etc.) for the network, using Server.
#
# Design notes:
#   - In a richer model, stations could subclass Server to override service time
#     distributions or add setup/maintenance. Here we keep a thin wrapper.
#
# Usage:
#   from sim.stations import make_stations
# -----------------------------------------------------------------------------

from __future__ import annotations
import math
from typing import Dict
from .queues import Server, BatchServer, PickupServer

class DineInServer(Server):
    """
    Specialized server for dine-in seating that keeps each table unavailable
    until a downstream cleaning server finishes wiping it.

    The departure hook defers releasing capacity until the cleaning stage calls
    back via `release_after_clean`, which mirrors the real-world requirement
    that a table cannot be reused immediately after a guest leaves.
    """
    def __init__(self, name: str, cleaning_server: Server, c: int, K: int, service_rate: float | None):
        super().__init__(name, c=c, K=K, service_rate=service_rate)
        self.cleaning_server = cleaning_server
        self._pending_releases = 0

    def on_departure(self, env, job):
        """
        Override Server.on_departure to:
          1. Forward completion to the router (for metrics and next-stage logic).
          2. Immediately enqueue the vacated table for cleaning.
          3. Defer releasing the table capacity until cleaning is done.
        """
        wait = self._extract_wait(job, env.t)
        if wait is not None:
            metrics = getattr(env.router, "M", None)
            if metrics is not None:
                metrics.note_wait(self.name, job, wait, env.t)
        env.router.advance(env, job, from_server=self)
        # Cleaning queue represents bussers wiping the table; capacity may block.
        ok = self.cleaning_server.enqueue(env, job)
        if not ok:
            # If cleaning queue is finite and full, log the block and retry.
            env.router.M.note_block(env.t, self.cleaning_server.name, job)
            # Best-effort re-enqueue; in practice the cleaning queue is infinite.
            self.cleaning_server.enqueue(env, job)
        self._pending_releases += 1

    def release_after_clean(self, env):
        """
        Invoked when the cleaning server finishes wiping a table. At this point
        the seat becomes usable again, so release one unit of capacity and
        immediately try to start the next waiting party.
        """
        if self._pending_releases <= 0:
            return
        self._pending_releases -= 1
        self.in_service -= 1
        self._mark_busy(env.t)
        self.try_start_service(env)

def make_stations(cfg: dict) -> Dict[str, Server]:
    """
    Create all stations from config using mean service times specified in MINUTES in YAML.
    The Env still runs in SECONDS, so convert minutes → seconds here.

    Parameters
    ----------
    cfg : dict
        Parsed YAML config with 'service_rates' and 'capacities'.

    Returns
    -------
    dict[str, Server]
        Mapping station name -> Server instance.
    """
    caps = cfg["capacities"]
    rates_min = cfg.get("service_rates", {})  # mean times in MINUTES
    # Convert to seconds (Env clock is in seconds, config supplied in minutes)
    rates = {k: v * 60.0 for k, v in rates_min.items()}
    dine_cfg = cfg.get("dine_in", {})

    S = {}
    # Front-end
    S["cashier"]  = Server("cashier",  c=1, K=math.inf, service_rate=rates.get("cashier"))
    # Drive-thru order window with finite lane capacity (balking when full)
    S["window"]   = Server("window",   c=1, K=caps.get("drive_thru_lane_order", math.inf), service_rate=rates.get("window", rates.get("cashier")))
    # Kitchen
    # Espresso with maintenance cycles (limited shots then downtime)
    espresso_batch = cfg.get("espresso", {}).get("batch_size", cfg.get("capacities", {}).get("espresso_batch_size", None))
    espresso_maint = cfg.get("espresso", {}).get("maintenance_minutes", cfg.get("service_rates", {}).get("espresso_maintenance", None))
    if espresso_batch and espresso_maint:
        S["espresso"] = BatchServer(
            "espresso",
            c=caps.get("espresso_c",1),
            K=math.inf,
            service_rate=rates.get("espresso"),
            batch_size=int(espresso_batch),
            downtime=espresso_maint * 60.0,
        )
    else:
        S["espresso"] = Server("espresso", c=caps.get("espresso_c",1), K=math.inf, service_rate=rates.get("espresso"))

    S["hotfood"]  = Server("hotfood",  c=caps.get("hotfood_c",2),  K=math.inf, service_rate=rates.get("hotfood"))

    # Beverage with urn cycles (finite pours then refill downtime)
    bev_batch = cfg.get("beverage", {}).get("urn_size", cfg.get("capacities", {}).get("beverage_urn_size", None))
    bev_refill = cfg.get("beverage", {}).get("refill_minutes", cfg.get("service_rates", {}).get("beverage_refill", None))
    if bev_batch and bev_refill:
        S["beverage"] = BatchServer(
            "beverage",
            c=caps.get("beverage_c",2),
            K=math.inf,
            service_rate=rates.get("beverage"),
            batch_size=int(bev_batch),
            downtime=bev_refill * 60.0,
        )
    else:
        S["beverage"] = Server("beverage", c=caps.get("beverage_c",2), K=math.inf, service_rate=rates.get("beverage"))
    # Drive-thru pickup window with finite staging lane
    S["drive_thru_pickup"] = PickupServer(
        "drive_thru_pickup",
        c=1,
        K=caps.get("drive_thru_lane_pickup", math.inf),
        service_rate=rates.get("drive_thru_pickup", rates.get("window")),
    )
    # Pack & Pickup
    S["pack"]     = Server("pack",     c=1,   K=math.inf, service_rate=rates.get("pack", rates.get("cashier")))
    # Pickup shelf modeled as FIFO pickup server; customers wait until their packed order reaches head of queue.
    S["shelf"]    = PickupServer("shelf",    c=1,   K=caps.get("shelf_N", 20), service_rate=rates.get("shelf", rates.get("cashier")))
    # Dine-in seating with explicit cleaning stage (tables remain blocked until busser finishes)
    num_tables = dine_cfg.get("tables", caps.get("dine_in_tables", 25))
    cleaners = caps.get("table_cleaners", 1)
    cleaning_rate = rates.get("table_cleaning", None)
    if num_tables and cleaning_rate is not None:
        S["dine_in_clean"] = Server("dine_in_clean", c=cleaners, K=math.inf, service_rate=cleaning_rate)
        S["dine_in"] = DineInServer(
            "dine_in",
            cleaning_server=S["dine_in_clean"],
            c=num_tables,
            K=num_tables,
            service_rate=rates.get("dine_in"),
        )
    elif num_tables:
        S["dine_in"] = Server("dine_in", c=num_tables, K=num_tables, service_rate=rates.get("dine_in"))
    return S
