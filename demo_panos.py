"""Bundled equirectangular panoramas used for demo mode (no API key required).

Sources are Pannellum's CC-licensed demo images and Wikimedia Commons images.
Each entry includes a verified lat/lng so the scoring works.
"""

from __future__ import annotations

from dataclasses import dataclass


def _wikimedia(filename: str, width: int = 2048) -> str:
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width={width}"


@dataclass(frozen=True)
class DemoPano:
    id: str
    name: str
    url: str
    lat: float
    lng: float


PANORAMAS: list[DemoPano] = [
    DemoPano(
        id="cerro-toco",
        name="Cerro Toco, Atacama Desert, Chile",
        url="https://pannellum.org/images/cerro-toco-0.jpg",
        lat=-22.9583,
        lng=-67.7770,
    ),
    DemoPano(
        id="alma",
        name="ALMA Observatory, Chile",
        url="https://pannellum.org/images/alma.jpg",
        lat=-23.0067,
        lng=-67.7544,
    ),
    DemoPano(
        id="bma",
        name="Baltimore Museum of Art, USA",
        url="https://pannellum.org/images/bma-1.jpg",
        lat=39.3262,
        lng=-76.6201,
    ),
    DemoPano(
        id="wtc-roof",
        name="Roof of the World Trade Center, NYC (2001)",
        url=_wikimedia(
            "360-degree_Panorama_from_the_roof_of_the_New_York_World_Trade_Center.jpg"
        ),
        lat=40.7127,
        lng=-74.0134,
    ),
    DemoPano(
        id="mauna-kea",
        name="Mauna Kea Summit, Hawaii",
        url=_wikimedia(
            "Maunakea_panorama_-_daytime_(noirlab-20120202-mk-summit-fe-pano-stils-001-p).jpg"
        ),
        lat=19.8208,
        lng=-155.4681,
    ),
    DemoPano(
        id="dent-vaulion",
        name="Dent de Vaulion, Swiss Jura",
        url=_wikimedia("Dent_de_Vaulion_-_360_degree_panorama.jpg"),
        lat=46.6913,
        lng=6.3688,
    ),
    DemoPano(
        id="duisburg",
        name="Landschaftspark Duisburg-Nord, Germany",
        url=_wikimedia("Landschaftspark-Duisburg-Nord_Hochofen_Panorama.jpg"),
        lat=51.4806,
        lng=6.7801,
    ),
    DemoPano(
        id="sagrada-familia",
        name="Sagrada Família, Barcelona",
        url=_wikimedia(
            "Sagrada_Familia_column_vertical_equirectangular_panorama_2010.jpg"
        ),
        lat=41.4036,
        lng=2.1744,
    ),
    DemoPano(
        id="mississippi",
        name="Pine Bend Bluffs, Mississippi River, Minnesota",
        url=_wikimedia(
            "Mississippi_River_Trail_-_Equirectangular_Panorama,_Minnesota_(Pine_Bend_Bluffs)_(27522421457).jpg"
        ),
        lat=44.7785,
        lng=-93.0117,
    ),
    DemoPano(
        id="narada-falls",
        name="Narada Falls, Mount Rainier, USA",
        url=_wikimedia(
            "Narada_Falls,_Mount_Rainier_National_Park,_equirectangular_panorama_01.jpg"
        ),
        lat=46.7747,
        lng=-121.7468,
    ),
    DemoPano(
        id="wittenberg",
        name="Castle Church, Lutherstadt Wittenberg, Germany",
        url=_wikimedia(
            "Castle_Church_of_Lutherstadt_Wittenberg_(interior,_full_spherical_panoramic_image,_equirectangular_projection).jpg"
        ),
        lat=51.8665,
        lng=12.6377,
    ),
    DemoPano(
        id="rheingauer",
        name="Rheingauer Dom, Geisenheim, Germany",
        url=_wikimedia(
            "Rheingauer_Dom,_Geisenheim,_360_Panorama_(Equirectangular_projection).jpg"
        ),
        lat=49.9907,
        lng=7.9667,
    ),
    DemoPano(
        id="seattle-fred-rogers",
        name="Seattle, Fred Rogers Building",
        url=_wikimedia(
            "Seattle_-_equirectangular_panorama_of_Fred_Rogers_Building_on_Terry_Avenue.jpg"
        ),
        lat=47.6172,
        lng=-122.3344,
    ),
]


def list_demo_panos() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "lat": p.lat,
            "lng": p.lng,
        }
        for p in PANORAMAS
    ]


def get_demo_pano(pano_id: str) -> DemoPano | None:
    for p in PANORAMAS:
        if p.id == pano_id:
            return p
    return None
