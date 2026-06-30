import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from src.acquisition.requetes import lireWFS, compter
from src.config import COUNT, ATTRS_BATI, FILTRES_BATI, N_THREADS


def batiments(polygone):
    """
    Batiments BD TOPO exploitables dans la zone, via le WFS IGN (pages en parallele).
    Filtre : FILTRES_BATI (etat, construction legere, nature...).
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)

    @return gdf : GeoDataFrame Lambert 93 (cleabs + ATTRS_BATI + geometry) ; None si vide
    """
    minx, miny, maxx, maxy = polygone.bounds
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BDTOPO_V3:batiment",
        "OUTPUTFORMAT": "application/json",
        "PROPERTYNAME": ",".join(dict.fromkeys(["cleabs", "geometrie"] + list(FILTRES_BATI) + ATTRS_BATI)),
        "CQL_FILTER": f"BBOX(geometrie,{miny},{minx},{maxy},{maxx})",
        "COUNT": COUNT,
    }


    n = compter(params)
    if n == 0:
        return None


    with ThreadPoolExecutor(max_workers=N_THREADS) as ex:
        morceaux = list(ex.map(lambda s: lireWFS({**params, "STARTINDEX": s}), range(0, n, COUNT)))


    tout = pd.concat(morceaux, ignore_index=True)
    tout = tout[tout.geometry.representative_point().within(polygone)]
    for col, val in FILTRES_BATI.items():
        tout = tout[tout[col].isin(val) if isinstance(val, (list, tuple, set)) else tout[col] == val]
    return (tout[["cleabs", *ATTRS_BATI, "geometry"]]
            .reset_index(drop=True).to_crs(2154))




