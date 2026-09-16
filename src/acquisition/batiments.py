from src.acquisition.requetes import paginer
from src import config


def batiments(polygone, on_log=print):
    """
    Batiments BD TOPO de la zone, filtres cote serveur par config.FILTRES_BATI.
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)
    @param[in] on_log   : callback (message) pour les avertissements (defaut print)

    @return GeoDataFrame Lambert 93 (cleabs, ATTRS_BATI, usage_1, nature, geometry) ; None si
            aucun batiment ou si un filtre est une liste vide
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
        "PROPERTYNAME": ",".join(dict.fromkeys(["cleabs", "geometrie", "usage_1", "nature"] + config.ATTRS_BATI)),
        "CQL_FILTER": " AND ".join(clauses),
        "SORTBY": "cleabs",
        "COUNT": config.COUNT,
    }

    tout = paginer(params, "cleabs", on_log)
    if tout.empty:
        return None

    tout = tout[tout.geometry.representative_point().within(polygone)]
    return (tout[list(dict.fromkeys(["cleabs", *config.ATTRS_BATI, "usage_1", "nature", "geometry"]))]
            .reset_index(drop=True).to_crs(2154))
