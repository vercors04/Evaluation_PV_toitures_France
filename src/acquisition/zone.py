import requests
from shapely.geometry import box, Point

from src.acquisition.requetes import lireWFS

def zone(echelle, nom_zone, code_dep=None):
    """
    Resout l'emprise de la zone d'etude en un polygone WGS84.
    --------
    @param[in] echelle  : 'adresse', 'commune', 'departement', 'region' ou 'nationale'
    @param[in] nom_zone : adresse complete, ou nom du territoire
    @param[in] code_dep : code departement (seulement pour 'commune', pour lever les homonymes)

    @return polygone : geometrie shapely en WGS84 (cercle d'environ 40 m autour du point
                       geocode pour une adresse, contour du territoire sinon) ; None si introuvable
    """
    if echelle == "nationale":
        params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                  "TYPENAME": "BDTOPO_V3:region", "OUTPUTFORMAT": "application/json",
                  "COUNT": 100}
        gdf = lireWFS(params)
        if gdf.empty:
            return None
        france = gdf.geometry.union_all()                       # (unary_union si vieille version)
        return france    # .intersection(box(-5.5, 41.0, 10.0, 51.5)) pour exclure l'outre-mer
    

    if echelle == "adresse":
        feats = requests.get("https://data.geopf.fr/geocodage/search",
                             params={"q": nom_zone, "limit": 1}).json()["features"]
        if not feats:
            return None
        lon, lat = feats[0]["geometry"]["coordinates"]
        return Point(lon, lat).buffer(0.0004)   # ~40 m


    nom_zone = nom_zone.replace("'", "''")
    cql = {
        "commune":     f"nom_officiel ILIKE '{nom_zone}' AND code_insee_du_departement = '{code_dep}'",
        "departement": f"nom_officiel ILIKE '{nom_zone}' OR code_insee = '{nom_zone}'",
        "region":      f"nom_officiel ILIKE '{nom_zone}'",
    }[echelle]

    params = {"SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature",
              "TYPENAME": f"BDTOPO_V3:{echelle}", "OUTPUTFORMAT":"application/json", "CQL_FILTER": cql}
    
    gdf = lireWFS(params)

    return None if gdf.empty else gdf.geometry.iloc[0]




# fonction a supprimer si l'echelle region/nationale se calcule un jour en un seul run
def listeDepartements(echelle, nom_zone):
    """
    Noms officiels des departements composant une region ou la France entiere (DOM inclus).
    --------
    @param[in] echelle  : 'region' ou 'nationale'
    @param[in] nom_zone : nom de la region (ignore si echelle == 'nationale')

    @return liste des noms officiels de departement (str) ; [] si region introuvable
    """
    params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
              "TYPENAME": "BDTOPO_V3:departement", "OUTPUTFORMAT": "application/json",
              "COUNT": 200}
    gdf = lireWFS(params)

    if echelle == "nationale":
        return sorted(gdf["nom_officiel"].tolist())

    region_poly = zone("region", nom_zone)
    if region_poly is None:
        return []
    dans_region = gdf[gdf.geometry.representative_point().within(region_poly)]
    return sorted(dans_region["nom_officiel"].tolist())