import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from src.acquisition.requetes import lireWFS, compter
from src import config


def batiments(polygone, on_log=print):
    """
    Batiments BD TOPO exploitables dans la zone, via le WFS IGN (pages en parallele).
    Filtre applique cote serveur : FILTRES_BATI (etat, construction legere, nature, usage).
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)
    @param[in] on_log   : callback (message) pour les avertissements (defaut print)

    @return gdf : GeoDataFrame Lambert 93 (cleabs + ATTRS_BATI + geometry) ;
                  None si aucun batiment ou si un des filtres est une liste vide
    """
    minx, miny, maxx, maxy = polygone.bounds
    clauses = [f"BBOX(geometrie,{miny},{minx},{maxy},{maxx})"]
    for col, val in config.FILTRES_BATI.items():
        if isinstance(val, bool):
            clauses.append(f"{col} = {str(val).lower()}")
        elif not val:
            return None
        
        else:
            vals = ", ".join("'" + str(v).replace("'", "''") + "'" for v in val)
            clauses.append(f"{col} IN ({vals})")
        
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BDTOPO_V3:batiment",
        "OUTPUTFORMAT": "application/json",
        "PROPERTYNAME": ",".join(dict.fromkeys(["cleabs", "geometrie"] + config.ATTRS_BATI)),
        "CQL_FILTER": " AND ".join(clauses),
        "COUNT": config.COUNT,
    }


    n = compter(params)
    if n == 0:
        return None


    with ThreadPoolExecutor(max_workers=config.N_THREADS) as ex:
        morceaux = list(ex.map(lambda s: lireWFS({**params, "STARTINDEX": s}), range(0, n, config.COUNT)))


    tout = pd.concat(morceaux, ignore_index=True).drop_duplicates("cleabs")
    if len(tout) != n:
        on_log(f"[avertissement] WFS batiments : {n} attendus, {len(tout)} recus (pagination instable ?)")
    tout = tout[tout.geometry.representative_point().within(polygone)]
    return (tout[["cleabs", *config.ATTRS_BATI, "geometry"]]
            .reset_index(drop=True).to_crs(2154))




