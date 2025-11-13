"""
sim package initializer.

This package contains the simulation engine, primitives (queues/servers),
routing logic, policies, and metric collection used by the Tim Hortons
queueing‑network model for CSC 546.
"""
__all__ = [
    "entities", "queues", "stations", "network",
    "arrivals", "policies", "metrics", "simulation",
]
