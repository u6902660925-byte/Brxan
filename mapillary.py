"""Mapillary client.

We use the Mapillary Graph API to find panoramic images near a target lat/lng
within a region bounding box. The token is read from the ``MAPILLARY_CLIENT_TOKEN``
environment variable so it is never shipped to the browser.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

import httpx


MAPILLARY_GRAPH_URL = "https://graph.mapillary.com/images"


@dataclass
class MapillaryImage:
    id: str
    lng: float
    lat: float


class MapillaryError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("MAPILLARY_CLIENT_TOKEN", "").strip()
    if not token:
        raise MapillaryError(
            "MAPILLARY_CLIENT_TOKEN env var is not set. Get a free client token "
            "from https://www.mapillary.com/dashboard/developers"
        )
    return token


def _bbox_around(lng: float, lat: float, radius_deg: float) -> str:
    return (
        f"{lng - radius_deg},{lat - radius_deg},"
        f"{lng + radius_deg},{lat + radius_deg}"
    )


async def find_pano_in_bbox(
    bbox: tuple[float, float, float, float],
    *,
    rng: random.Random,
    max_attempts: int = 12,
    pano_only: bool = True,
) -> MapillaryImage:
    """Return a single Mapillary image somewhere inside ``bbox``.

    Strategy: pick a random center inside the bbox, expand a small search bbox
    around it and ask Mapillary for images. If nothing is returned, retry with a
    new random center. After a few failures we widen the search radius before
    giving up.
    """
    token = _token()
    min_lng, min_lat, max_lng, max_lat = bbox

    radii = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(max_attempts):
            radius = radii[min(attempt // 2, len(radii) - 1)]
            cx = rng.uniform(min_lng, max_lng)
            cy = rng.uniform(min_lat, max_lat)
            search_bbox = _bbox_around(cx, cy, radius)
            params = {
                "access_token": token,
                "fields": "id,computed_geometry,geometry",
                "bbox": search_bbox,
                "limit": 50,
            }
            if pano_only:
                params["is_pano"] = "true"
            resp = await client.get(MAPILLARY_GRAPH_URL, params=params)
            if resp.status_code != 200:
                # Surface real auth errors quickly; otherwise just retry.
                if resp.status_code in (401, 403):
                    raise MapillaryError(
                        f"Mapillary auth failed ({resp.status_code}): {resp.text[:200]}"
                    )
                continue
            data = resp.json().get("data") or []
            # Drop entries without geometry.
            usable = []
            for d in data:
                geom = d.get("computed_geometry") or d.get("geometry") or {}
                coords = geom.get("coordinates")
                if not coords or len(coords) != 2:
                    continue
                usable.append(
                    MapillaryImage(
                        id=str(d["id"]),
                        lng=float(coords[0]),
                        lat=float(coords[1]),
                    )
                )
            if usable:
                return rng.choice(usable)
            # Fallback: if pano-only returned nothing, try non-pano on the next
            # widened pass so the user still gets imagery.
            if attempt >= 4 and pano_only:
                pano_only = False

    raise MapillaryError(
        "Could not find any Mapillary imagery in the requested region after "
        f"{max_attempts} attempts. Try a different region."
    )
