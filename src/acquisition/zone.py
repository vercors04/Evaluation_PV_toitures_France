# src/acquisition/zone.py
import requests, geopandas as gpd
from shapely.geometry import box

WFS = "https://data.geopf.fr/wfs/ows"

def zone(echelle, nom_zone, code_dep=None):
    """
    Resout l'emprise de la zone d'etude en un polygone WGS84.
    --------
    @param[in] echelle  : 'adresse', 'commune', 'departement' ou 'region'
    @param[in] nom_zone : adresse complete, ou nom du territoire
    @param[in] code_dep : code departement (seulement pour 'commune', pour lever les homonymes)

    @return polygone : geometrie shapely en WGS84 (box autour du point pour une adresse,
                       contour du territoire sinon) ; None si introuvable
    """
    if echelle == "adresse":
        feats = requests.get("https://data.geopf.fr/geocodage/search",
                             params={"q": nom_zone, "limit": 1}).json()["features"]
        if not feats:
            return None
        lon, lat = feats[0]["geometry"]["coordinates"]
        return box(lon-0.002, lat-0.002, lon+0.002, lat+0.002)   # ~1 dalle autour du point

    cql = {
        "commune":     f"nom_officiel ILIKE '{nom_zone}' AND code_insee_du_departement = '{code_dep}'",
        "departement": f"nom_officiel ILIKE '{nom_zone}' OR code_insee = '{nom_zone}'",
        "region":      f"nom_officiel ILIKE '{nom_zone}'",
    }[echelle]

    params = {"SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature",
              "TYPENAME": f"BDTOPO_V3:{echelle}", "OUTPUTFORMAT":"application/json", "CQL_FILTER": cql}
    
    gdf = gpd.read_file(requests.get(WFS, params=params).text)

    return None if gdf.empty else gdf.geometry.iloc[0]