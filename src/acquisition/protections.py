import pandas as pd
import geopandas as gpd
import shapely
from shapely.geometry import box

from src.acquisition.requetes import lireWFS, compter, paginer
from src import config


def zonesProtegees(couche, champ, filtre, crs, bornes, on_log=print):
    """
    Zones d'une couche de protection dans l'emprise, en Lambert 93.
    --------
    @param[in] couche, champ, filtre, crs : couche WFS, champ geometrique, filtre CQL et
                                            CRS de la BBOX (voir config.PROTECTIONS)
    @param[in] bornes : (minx, miny, maxx, maxy) de la zone, en WGS84
    @param[in] on_log : callback (message) pour les avertissements (defaut print)

    @return GeoDataFrame des zones (vide si la couche n'en a aucune ici)
    """
    minx, miny, maxx, maxy = bornes
    if crs == 4326:
        clauses = [f"BBOX({champ},{miny},{minx},{maxy},{maxx})"]
    else:
        b = gpd.GeoSeries([box(minx, miny, maxx, maxy)], crs=4326).to_crs(crs).total_bounds
        clauses = [f"BBOX({champ},{b[0]},{b[1]},{b[2]},{b[3]})"]
    if filtre:
        clauses.append(filtre)

    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": couche,
        "OUTPUTFORMAT": "application/json",
        "CQL_FILTER": " AND ".join(clauses),
        "COUNT": config.COUNT,
    }
    n = compter(params)
    if n == 0:
        return gpd.GeoDataFrame()

    g = lireWFS(params) if n <= config.COUNT else paginer({**params, "SORTBY": "gid"}, "gid", on_log)
    if g.crs is None:
        g = g.set_crs(crs)
    return g.to_crs(2154)


def marquerProtections(gdf, polygone, on_log=print):
    """
    Marque les batiments dont le point interieur tombe dans une zone de config.PROTECTIONS_OK,
    et les retire si config.PROTECTIONS_EXCLURE. Couche indisponible : colonne absente, ou
    erreur en mode suppression.
    --------
    @param[in] gdf      : GeoDataFrame des batiments (Lambert 93, colonne geometry)
    @param[in] polygone : emprise de la zone (shapely, WGS84)
    @param[in] on_log   : callback (message) pour les avertissements (defaut print)

    @return gdf, bilan : GeoDataFrame marque (et filtre), dict {couche: batiments marques,
                         marques, supprimes, indisponibles}
    """
    couches = [c for c in config.PROTECTIONS if c in config.PROTECTIONS_OK]
    if not couches:
        return gdf, {}

    gdf = gdf.copy()
    points = gdf.geometry.representative_point()
    marque = pd.Series(False, index=gdf.index)
    bilan = {"indisponibles": []}

    for nom in couches:
        colonne, *couche = config.PROTECTIONS[nom]
        try:
            zones = zonesProtegees(*couche, polygone.bounds, on_log)
        except Exception as e:
            if config.PROTECTIONS_EXCLURE:
                raise
            on_log(f"[avertissement] {nom} indisponible, colonne absente : {e}")
            bilan["indisponibles"].append(nom)
            continue
        if zones.empty:
            touche = pd.Series(False, index=gdf.index)
        else:
            unies = zones.union_all()
            shapely.prepare(unies)
            touche = pd.Series(shapely.contains_xy(unies, points.x.values, points.y.values),
                               index=gdf.index)
        gdf.insert(gdf.columns.get_loc("geometry"), colonne, touche.to_numpy())
        marque |= touche
        bilan[nom] = int(touche.sum())

    bilan["marques"] = int(marque.sum())
    bilan["supprimes"] = bilan["marques"] if config.PROTECTIONS_EXCLURE else 0
    return (gdf[~marque].copy() if config.PROTECTIONS_EXCLURE else gdf), bilan
