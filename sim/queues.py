# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# queues.py
# -----------------------------------------------------------------------------
# Purpose:
#   Minimal discrete‑event primitives: Event, Env, and a generic Server with
#   FIFO queue, c servers, and finite buffer K (for MM1 / MMC / MM1K).
#
# Design notes:
#   - Service times are exponential by default (M/M/*); override draw_service
#     if you need general (G) service via custom distributions.
#   - Routing is delegated to env.router (defined in sim.network).
#
# Usage:
#   from sim.queues import Env, Event, Server
# -----------------------------------------------------------------------------

from __future__ import annotations
import heapq, math, random
from typing import Any, List, Optional

class Event:
    """Minimal event object for the Future Event List (FEL)."""
    __slots__ = ("t", "kind", "data")
    def __init__(self, t: float, kind: str, data: dict):
        self.t = t; self.kind = kind; self.data = data
    def __lt__(self, other: "Event"):
        return self.t < other.t

class Env:
    """Simulation environment holding the clock, FEL, and a router hook.

    Attributes
    ----------
    t : float
        Simulation time (seconds).
    FEL : list[Event]
        Min‑heap of scheduled events.
    router : object
        Object with methods on_arrival/on_timer/advance used by the model.
    """
    def __init__(self, router):
        self.t: float = 0.0
        self.FEL: List[Event] = []
        self.router = router

    def schedule(self, ev: Event):
        heapq.heappush(self.FEL, ev)

    def run_until(self, T_end: float):
        while self.FEL and self.t <= T_end:
            ev = heapq.heappop(self.FEL)
            self.t = ev.t
            kind, data = ev.kind, ev.data
            if kind == "arrival":
                self.router.on_arrival(self, **data)
            elif kind == "departure":
                data["server"].on_departure(self, data["job"])
            elif kind == "timer":
                self.router.on_timer(self, **data)

class Server:
    """Generic FIFO server with c parallel servers and buffer limit K.

    Parameters
    ----------
    name : str
        Station name for logging/metrics.
    c : int
        Number of parallel servers (default 1).
    K : float
        System capacity = in_service + in_queue (default inf).

    Notes
    -----
    - draw_service() assumes exponential with rate passed in job.svc_params["rate"].
    - Set K to math.inf for unlimited buffer; for loss/blocking, check can_join().
    """
    def __init__(self, name: str, c: int = 1, K: float = math.inf, service_rate: float | None = None):
        self.name = name
        self.c = c
        self.K = K
        self.queue: List[Any] = []
        self.in_service: int = 0
        self.busy_time: float = 0.0
        self.last_change: float = 0.0
        self.service_rate = service_rate  # fallback when job has no svc_params

    # Capacity check for loss or upstream blocking
    def can_join(self) -> bool:
        return len(self.queue) + self.in_service < self.K

    def enqueue(self, env: Env, job: Any) -> bool:
        if not self.can_join():
            return False
        self.queue.append(job)
        self.try_start_service(env)
        return True

    def draw_service(self, job: Any) -> float:
        """Draw a service time.
        Priority: job.svc_params['rate'] if present; otherwise fall back to
        the station-level `service_rate` provided at construction, otherwise
        a benign default (0.5 min per customer).
        """
        # Priority: job mean_min > job rate_per_min > station mean > station rate > default
        rate = None
        # 1) Try job-level svc_params if available
        if hasattr(job, "svc_params"):
            rate = job.svc_params.get("rate")
            # sp = getattr(job, "svc_params", None)
            # if isinstance(sp, dict):
            #     rate = sp.get("rate", None)
        
        # 2) Fall back to station-level rate
        if rate is None:
            rate = 1.0 / self.service_rate #if self.service_rate is not None else (0.5)
        return random.expovariate(rate)

    def try_start_service(self, env: Env):
        while self.queue and self.in_service < self.c:
            job = self.queue.pop(0)
            st = self.draw_service(job)
            self.in_service += 1
            self._mark_busy(env.t)
            env.schedule(Event(env.t + st, "departure", {"server": self, "job": job}))

    def on_departure(self, env: Env, job: Any):
        self.in_service -= 1
        self._mark_busy(env.t)
        # Advance job through the network
        env.router.advance(env, job, from_server=self)
        # Start next service if possible
        self.try_start_service(env)

    def _mark_busy(self, now: float):
        # crude utilization bookkeeping: add elapsed time if any server busy
        dt = now - self.last_change
        if self.in_service > 0:
            self.busy_time += dt
        self.last_change = now
