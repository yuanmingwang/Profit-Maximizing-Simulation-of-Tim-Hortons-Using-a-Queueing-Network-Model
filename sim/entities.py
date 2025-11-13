# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# entities.py
# -----------------------------------------------------------------------------
# Purpose:
#   Entity definitions for the Tim Hortons DES: Customer, Item, Order.
#   These objects carry attributes needed for routing, timing, and policies.
#
# Design notes:
#   - Orders are logical containers made of Items; Items are the work that
#     actually flows through kitchen stations (espresso/hotfood/beverage).
#   - Customers keep channel (walkin|drive_thru|mobile), promises, patience.
#
# Usage:
#   from sim.entities import Customer, Item, Order
# -----------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

@dataclass
class Customer:
    channel: str                     # 'walkin' | 'drive_thru' | 'mobile'
    arrival_time: float
    dine_in: bool = False
    promised_pickup: Optional[float] = None   # for mobile
    patience: Optional[float] = None          # for reneging at pickup

@dataclass
class Item:
    kind: str                        # 'beverage' | 'espresso' | 'hotfood'
    svc_params: Dict[str, float]     # e.g., {'rate': 1/20} per second
    route: Tuple[str, ...]           # kitchen station path (usually len 1)

@dataclass
class Order:
    oid: int
    customer: Customer
    items: List[Item]
    t_created: float
    t_ready: Optional[float] = None
    t_packed: Optional[float] = None
    t_picked: Optional[float] = None

    # Helpers to check if all items are ready (for pack station join)
    ready_items: int = 0

    def mark_item_ready(self):
        self.ready_items += 1
        return self.ready_items == len(self.items)
