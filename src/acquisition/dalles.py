from src.acquisition.requetes import paginer
from src import config


def dalles(polygone, on_log=print):
    """
    Dalles LiDAR HD intersectant la zone (couche de metadonnees WFS, URL GetMap WMS).
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)
    @param[in] on_log   : callback (message) pour les avertissements (defaut print)

    @return GeoDataFrame des dalles (url_mns, url_mnt, coordonnees_nw, geometry) ; vide si la
            zone n'est pas couverte
    """
    minx, miny, maxx, maxy = polygone.bounds
    params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
              "TYPENAME": "IGNF_LIDAR-HD_METADONNEE:metadata",
              "OUTPUTFORMAT": "application/json",
              "CQL_FILTER": f"BBOX(geom,{miny},{minx},{maxy},{maxx})",
              "SORTBY": "coordonnees_nw",
              "COUNT": config.COUNT}

    tout = paginer(params, "coordonnees_nw", on_log)
    if tout.empty:
        return tout
    return tout[tout.intersects(polygone)]
