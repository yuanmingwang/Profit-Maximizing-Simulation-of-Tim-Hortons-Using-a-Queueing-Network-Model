# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# metrics.py
# -----------------------------------------------------------------------------
# Purpose:
#   Collect and summarize KPIs: waits, utilizations, throughput, and profit.
#
# Design notes:
#   - Keep side‑effect methods (note_*) for instrumentation from the router.
#   - Summaries return JSON‑serializable dicts for easy tabulation.
#
# Usage:
#   M = Metrics(cfg); M.summary()
# -----------------------------------------------------------------------------

from __future__ import annotations
from typing import Dict, Any
from collections import defaultdict
import math

class Metrics:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.warmup_sec = cfg.get("sim", {}).get("warmup_minutes", 0) * 60.0
        self.pickups = 0
        self.kitchen_entries = 0
        self.wait_totals = defaultdict(float)     # accumulated front counter waits per channel
        self.wait_counts = defaultdict(int)       # service counts for averaging front waits
        self.wait_samples = defaultdict(list)     # raw wait samples per channel for percentile/penalties
        self.pickup_wait_totals = defaultdict(float)  # post-pack waits separated by channel
        self.channel_served = defaultdict(int)    # throughput per channel
        self.mobile_ready_on_time = 0
        self.mobile_promises = 0
        self.mobile_late = 0
        self.revenue_total = 0.0
        self.cogs_total = 0.0
        self.penalties = defaultdict(float)
        self.balks = defaultdict(int)
        self.pickup_reneges = defaultdict(int)
        self.dine_in_customers = 0
        self.dine_in_time_total = 0.0
        # Raw counters (include warm-up) for time-series diagnostics
        self.raw_revenue_total = 0.0
        self.raw_cogs_total = 0.0
        self.raw_penalty_total = 0.0
        self.raw_customers = 0
        cost_cfg = cfg.get("costs", {})
        self.price_map = {
            "beverage": cost_cfg.get("price_coffee", 0.0),
            "espresso": cost_cfg.get("price_espresso", 0.0),
            "hotfood": cost_cfg.get("price_hotfood", 0.0),
        }
        self.cogs_pct = cost_cfg.get("cogs_pct", 0.0)
        self.wages_per_hour = cost_cfg.get("wages_per_hour", {})
        self.stations: Dict[str, Any] = {}
        self.labor_rate_per_sec = 0.0
        self.time_series: list[Dict[str, float]] = []

    def _active(self, t: float) -> bool:
        """Return True if t is beyond the warm-up period."""
        return t >= self.warmup_sec

    def note_kitchen_entry(self, order, t: float):
        if not self._active(t):
            return
        self.kitchen_entries += 1

    def attach_stations(self, stations: Dict[str, Any]):
        """Attach station set and compute per-second labor burn rate for raw tracking."""
        self.stations = stations
        default_wage = self.wages_per_hour.get("_default_", 0.0)
        total_wage_per_hour = 0.0
        for name, st in stations.items():
            wage_hr = self.wages_per_hour.get(name, default_wage)
            total_wage_per_hour += wage_hr * getattr(st, "c", 1)
        self.labor_rate_per_sec = total_wage_per_hour / 3600.0

    def note_wait(self, server_name: str, job, wait: float, t: float):
        if not self._active(t):
            return
        cust = getattr(job, "customer", None)
        if cust is None:
            return
        channel = cust.channel
        if server_name == "cashier" and channel == "walkin":
            self.wait_totals[channel] += wait
            self.wait_counts[channel] += 1
            self.wait_samples[channel].append(wait)
        elif server_name == "window" and channel == "drive_thru":
            self.wait_totals[channel] += wait
            self.wait_counts[channel] += 1
            self.wait_samples[channel].append(wait)

    def note_order_packed(self, order, t: float):
        if not self._active(t):
            return
        cust = getattr(order, "customer", None)
        if cust is None or cust.channel != "mobile":
            return
        self.mobile_promises += 1  # every packed mobile order counts toward promised denominator
        promised = cust.promised_pickup
        ready_time = order.t_packed or order.t_ready
        penalty = self.cfg.get("penalties", {}).get("mobile_late", 0.0)
        if promised is not None and ready_time is not None and ready_time > promised:
            self.mobile_late += 1
            if penalty:
                self.penalties["mobile_late"] += penalty
                self.raw_penalty_total += penalty
        else:
            self.mobile_ready_on_time += 1

    def note_pickup(self, order, pickup_wait: float, t: float):
        order_value = order.total_price()
        if order_value == 0.0:
            order_value = sum(self.price_map.get(it.kind, 0.0) for it in order.items)
        # Raw counters for warm-up diagnostics
        self.raw_revenue_total += order_value
        self.raw_cogs_total += order_value * self.cogs_pct
        self.raw_customers += 1
        self._record_time_series(t)

        if not self._active(t):
            return
        self.pickups += 1
        cust = getattr(order, "customer", None)
        channel = cust.channel if cust else "unknown"
        self.channel_served[channel] += 1
        self.pickup_wait_totals[channel] += pickup_wait
        self.revenue_total += order_value
        self.cogs_total += order_value * self.cogs_pct

    def note_pickup_renege(self, order, pickup_wait: float, t: float):
        if not self._active(t):
            return
        cust = getattr(order, "customer", None)
        channel = cust.channel if cust else "unknown"
        self.pickup_reneges[channel] += 1
        penalty = self.cfg.get("penalties", {}).get("pickup_renege", 0.0)
        if penalty:
            self.penalties["pickup_renege"] += penalty
            self.raw_penalty_total += penalty

    def note_block(self, t, station, job):
        if not self._active(t):
            return
        cust = getattr(job, "customer", None)
        if cust is None:
            return
        # Treat blocked entries at finite buffers as balks/lost demand
        self.balks[cust.channel] += 1
        pct = self.cfg.get("penalties", {}).get("balk_loss_pct", 0.0)
        if pct:
            order_value = self._estimate_order_value(job)
            if order_value > 0:
                penalty_val = order_value * pct
                self.penalties["balk_loss"] += penalty_val
                self.raw_penalty_total += penalty_val

    def _estimate_order_value(self, entity) -> float:
        if hasattr(entity, "total_price"):
            val = entity.total_price()
            if val:
                return val
        parent = getattr(entity, "parent_order", None)
        if parent is not None and hasattr(parent, "total_price"):
            val = parent.total_price()
            if val:
                return val
        items = getattr(entity, "items", None)
        if items:
            return sum(self.price_map.get(getattr(it, "kind", ""), 0.0) for it in items)
        return 0.0

    def note_dinein_start(self, order):
        """Track when a dine-in guest seizes a table."""
        # Seat starts at post-pickup time; warm-up handled by caller
        self.dine_in_customers += 1

    def note_dinein_departure(self, order, t_depart: float):
        """Accumulate total dine-in table occupancy (including cleaning time)."""
        if not self._active(t_depart):
            return
        if order.t_seated is None:
            return
        dwell = max(t_depart - order.t_seated, 0.0)
        self.dine_in_time_total += dwell

    def _record_time_series(self, t: float):
        """
        Capture a cumulative point for warm-up plots using raw counters (includes warm-up):
          - cumulative revenue to time t
          - cumulative profit to time t (revenue - cogs - penalties - labor burned to time t)
          - cumulative customers to time t
        """
        if self.raw_customers <= 0:
            return
        labor_cost_raw = self.labor_rate_per_sec * t
        profit_raw = self.raw_revenue_total - self.raw_cogs_total - self.raw_penalty_total - labor_cost_raw
        self.time_series.append({
            "time_minutes": t / 60.0,
            "revenue_total": self.raw_revenue_total,
            "profit_total": profit_raw,
            "customers_total": self.raw_customers,
        })

    def summary(self) -> Dict:
        day_minutes = self.cfg["sim"]["day_minutes"]
        staff_count = sum(getattr(st, "c", 0) for st in self.stations.values()) if self.stations else 0
        labor_sched_minutes = day_minutes * staff_count
        labor_busy_minutes = 0.0
        station_utilization: Dict[str, float] = {}
        if self.stations:
            day_seconds = day_minutes * 60.0
            for name, st in self.stations.items():
                busy_sec = getattr(st, "busy_time", 0.0)
                labor_busy_minutes += busy_sec / 60.0
                denom = day_seconds * getattr(st, "c", 1)
                station_utilization[name] = busy_sec / denom if denom > 0 else 0.0
        labor_cost = 0.0
        if self.wages_per_hour:
            day_hours = day_minutes / 60.0
            default_wage = self.wages_per_hour.get("_default_", 0.0)
            for name, st in self.stations.items():
                wage_hr = self.wages_per_hour.get(name, default_wage)
                labor_cost += wage_hr * day_hours * getattr(st, "c", 1)
        else:
            wage_per_min = self.cfg.get("costs", {}).get("wage_per_min", 0.0)
            labor_cost = labor_sched_minutes * wage_per_min
        penalties_total = sum(self.penalties.values())
        profit = self.revenue_total - self.cogs_total - labor_cost - penalties_total
        # Drive-thru p90 and breach penalties (per-customer if wait exceeds target)
        drive_p90 = 0.0
        drive_breaches = 0
        if self.wait_samples.get("drive_thru"):
            waits = sorted(self.wait_samples["drive_thru"])
            idx = int(math.ceil(0.9 * len(waits))) - 1
            idx = max(0, min(idx, len(waits) - 1))
            drive_p90 = waits[idx] / 60.0
            target_min = self.cfg.get("penalties", {}).get("drivethru_p90_target_minutes", None)
            penalty_amt = self.cfg.get("penalties", {}).get("drivethru_p90_breach", 0.0)
            if target_min is not None and penalty_amt:
                target_sec = target_min * 60.0
                drive_breaches = sum(1 for w in waits if w > target_sec)
                if drive_breaches > 0:
                    self.penalties["drivethru_p90_breach"] += penalty_amt * drive_breaches
                    penalties_total += penalty_amt * drive_breaches
                    profit -= penalty_amt * drive_breaches
        avg_waits = {}
        for channel in ("walkin", "drive_thru"):
            total = self.wait_totals.get(channel, 0.0)
            count = self.wait_counts.get(channel, 0)
            avg_waits[channel] = (total / count / 60.0) if count > 0 else 0.0
        avg_pickup_waits = {}
        for channel, total in self.pickup_wait_totals.items():
            served = self.channel_served.get(channel, 0)
            avg_pickup_waits[channel] = (total / served / 60.0) if served > 0 else 0.0
        avg_dine_in_time = (
            (self.dine_in_time_total / self.dine_in_customers) / 60.0
            if self.dine_in_customers > 0 else 0.0
        )
        total_customers = sum(self.channel_served.values())
        rev_per_customer = (self.revenue_total / total_customers) if total_customers > 0 else 0.0
        return {
            "pickups": self.pickups,
            "kitchen_entries": self.kitchen_entries,
            "avg_front_wait_minutes": avg_waits,
            "avg_pickup_wait_minutes": avg_pickup_waits,
            "mobile_ready_rate": (
                self.mobile_ready_on_time / self.mobile_promises if self.mobile_promises else 0.0
            ),
            "mobile_promises": self.mobile_promises,
            "mobile_ready_on_time": self.mobile_ready_on_time,
            "mobile_late": self.mobile_late,
            "balked_customers": dict(self.balks),
            "pickup_reneges": dict(self.pickup_reneges),
            "revenue_per_day": self.revenue_total,
            "cogs_per_day": self.cogs_total,
            "labor_cost_per_day": labor_cost,
            "labor_sched_minutes": labor_sched_minutes,
            "labor_busy_minutes": labor_busy_minutes,
            "penalties": dict(self.penalties),
            "penalty_total": penalties_total,
            "profit_per_day": profit,
            "served_by_channel": dict(self.channel_served),
            "station_utilization": station_utilization,
            "dine_in_customers": self.dine_in_customers,
            "avg_dine_in_time_minutes": avg_dine_in_time,
            "revenue_per_customer": rev_per_customer,
            # Raw time-series for warm-up diagnostics and plotting (includes warm-up period).
            "time_series": list(self.time_series),
            "drive_thru_p90_wait_minutes": drive_p90,
            "drive_thru_breach_count": drive_breaches,
        }
