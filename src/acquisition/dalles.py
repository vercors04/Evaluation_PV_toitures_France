# src/acquisition/dalles.py
import pandas as pd

from src.acquisition.requetes import lireWFS
from src.config import COUNT

def dalles(polygone):
    """
    Dalles LiDAR HD (MNT et MNS) intersectant la zone, via le WFS IGN (pagine).
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)

    @return res : dict {'MNT': GeoDataFrame, 'MNS': GeoDataFrame} des dalles
                  (colonnes name, url, geometry, ...) ; cle absente si aucune dalle
    """
    minx, miny, maxx, maxy = polygone.bounds
    res = {}
    for couche in ("MNT", "MNS"):
        morceaux, start = [], 0
        while True:
            params = {"SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature",
                      "TYPENAME": f"IGNF_{couche}-LIDAR-HD:dalle", "OUTPUTFORMAT":"application/json",
                      "CQL_FILTER": f"BBOX(geom,{miny},{minx},{maxy},{maxx})",
                      "COUNT": COUNT, "STARTINDEX": start}
            g = lireWFS(params)
            if g.empty:
                break
            morceaux.append(g)
            if len(g) < COUNT:
                break
            start += COUNT
        if morceaux:
            tout = pd.concat(morceaux, ignore_index=True)
            res[couche] = tout[tout.intersects(polygone)].drop_duplicates("name")
    return res