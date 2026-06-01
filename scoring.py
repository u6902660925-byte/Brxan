"""Distance + score helpers shared between rounds and leaderboards."""

from __future__ import annotations

import math


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def score_for_distance(distance_km: float, *, max_score: int = 5000) -> int:
    """GeoGuessr-style exponential decay: 5000 points for a perfect guess,
    falling off quickly with distance. ``2000 km`` is the practical "world"
    half-life; tune as needed.
    """
    if distance_km <= 0:
        return max_score
    decay = math.exp(-distance_km / 2000.0)
    return max(0, round(max_score * decay))
