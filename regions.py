"""Curated region/country pools for location selection.

Each entry is a bounding box (min_lng, min_lat, max_lng, max_lat). When a region
is requested we randomly sample a point inside its bbox and ask Mapillary for a
nearby panorama. Because a country bbox can include water/empty land we let
Mapillary do the actual filtering — if the first pick has no imagery we retry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    code: str
    name: str
    bbox: tuple[float, float, float, float]  # min_lng, min_lat, max_lng, max_lat


REGIONS: dict[str, Region] = {
    "world": Region("world", "World", (-180.0, -60.0, 180.0, 75.0)),
    "europe": Region("europe", "Europe", (-10.0, 35.0, 40.0, 70.0)),
    "north_america": Region(
        "north_america", "North America", (-140.0, 15.0, -55.0, 60.0)
    ),
    "south_america": Region(
        "south_america", "South America", (-82.0, -55.0, -34.0, 12.0)
    ),
    "asia": Region("asia", "Asia", (60.0, 5.0, 145.0, 55.0)),
    "africa": Region("africa", "Africa", (-18.0, -35.0, 52.0, 37.0)),
    "oceania": Region("oceania", "Oceania", (110.0, -47.0, 180.0, -8.0)),
    "us": Region("us", "United States", (-125.0, 25.0, -66.0, 49.0)),
    "uk": Region("uk", "United Kingdom", (-8.5, 49.5, 2.0, 60.5)),
    "japan": Region("japan", "Japan", (129.0, 31.0, 146.0, 46.0)),
    "france": Region("france", "France", (-5.0, 41.5, 9.5, 51.5)),
    "germany": Region("germany", "Germany", (5.5, 47.0, 15.5, 55.5)),
    "australia": Region("australia", "Australia", (113.0, -44.0, 154.0, -10.0)),
    "brazil": Region("brazil", "Brazil", (-74.0, -34.0, -34.0, 5.5)),
    "india": Region("india", "India", (68.0, 7.0, 97.5, 36.0)),
    "canada": Region("canada", "Canada", (-141.0, 42.0, -52.0, 70.0)),
    "italy": Region("italy", "Italy", (6.5, 36.5, 18.5, 47.5)),
    "spain": Region("spain", "Spain", (-9.5, 35.5, 4.5, 44.0)),
    "mexico": Region("mexico", "Mexico", (-118.0, 14.5, -86.0, 33.0)),
}


def list_regions() -> list[dict]:
    return [{"code": r.code, "name": r.name} for r in REGIONS.values()]


def get_region(code: str) -> Region:
    return REGIONS.get(code, REGIONS["world"])
