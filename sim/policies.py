# Copyright (c) 2025
# MIT License
# -----------------------------------------------------------------------------
# policies.py
# -----------------------------------------------------------------------------
# Purpose:
#   Placeholders for priority and operational policies (e.g., pack station
#   priority among channels, brew schedules, maintenance, balking thresholds).
#
# Design notes:
#   - Keep pure functions to ease testing (policy -> decision).
#   - Timer‑based policies can schedule 'timer' events via env.schedule().
#
# Usage:
#   from sim.policies import pick_next_at_pack
# -----------------------------------------------------------------------------

from __future__ import annotations

def pick_next_at_pack(queue):
    """Example policy hook (not used in the minimal scaffold)."""
    # FCFS by default; replace with priority among channel types if desired.
    return queue[0] if queue else None
