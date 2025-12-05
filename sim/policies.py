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
    """
    Placeholder kept for backward compatibility; real logic now lives in
    PackServer inside stations.py and uses the configured priority list.
    """
    return queue[0] if queue else None
