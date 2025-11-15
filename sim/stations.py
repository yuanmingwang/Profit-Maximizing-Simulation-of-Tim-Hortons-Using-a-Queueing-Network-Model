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
from .queues import Server

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
    # Convert to seconds
    rates = {k: v * 60.0 for k, v in rates_min.items()}  # Env clock is seconds, config is minutes

    S = {}
    # Front-end
    S["cashier"]  = Server("cashier",  c=1, K=math.inf, service_rate=rates.get("cashier"))
    S["window"]   = Server("window",   c=1, K=math.inf, service_rate=rates.get("window", rates.get("cashier")))
    # Kitchen
    S["espresso"] = Server("espresso", c=caps.get("espresso_c",1), K=math.inf, service_rate=rates.get("espresso"))
    S["hotfood"]  = Server("hotfood",  c=caps.get("hotfood_c",2),  K=math.inf, service_rate=rates.get("hotfood"))
    S["beverage"] = Server("beverage", c=caps.get("beverage_c",2), K=math.inf, service_rate=rates.get("beverage"))
    # Pack & Pickup
    S["pack"]     = Server("pack",     c=1,   K=math.inf, service_rate=rates.get("pack", rates.get("cashier")))
    S["shelf"]    = Server("shelf",    c=1,   K=caps.get("shelf_N", 20), service_rate=rates.get("shelf", rates.get("cashier")))
    return S
