import requests, geopandas as gpd, pandas as pd

WFS = "https://data.geopf.fr/wfs/ows"
NATURE_OK = ['Indifférenciée', 'Industriel, agricole ou commercial']

def batiments(polygone):
    """
    Batiments BD TOPO exploitables dans la zone, via le WFS IGN (pagine).
    Filtre : en service, non legers, nature residentielle/industrielle (NATURE_OK).
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)

    @return gdf : GeoDataFrame en Lambert 93 (EPSG:2154), colonnes
                  cleabs, nature, usage_1, hauteur, nombre_d_etages, geometry ; None si vide
    """
    minx, miny, maxx, maxy = polygone.bounds
    morceaux, start = [], 0
    while True:
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAME": "BDTOPO_V3:batiment",
            "OUTPUTFORMAT": "application/json",
            "CQL_FILTER": f"BBOX(geometrie,{miny},{minx},{maxy},{maxx})",
            "COUNT": 2000,
            "STARTINDEX": start,
        }
        g = gpd.read_file(requests.get(WFS, params=params).text)
        if g.empty:
            break
        morceaux.append(g)
        if len(g) < 2000:
            break
        start += 2000

    if not morceaux:
        return None
    tout = pd.concat(morceaux, ignore_index=True)
    tout = tout[tout.geometry.representative_point().within(polygone)]
    tout = tout[(tout['etat_de_l_objet'] == "En service")
                & (tout['construction_legere'] == False)
                & tout['nature'].isin(NATURE_OK)]
    return (tout[['cleabs', 'nature', 'usage_1', 'hauteur', 'nombre_d_etages', 'geometry']]
            .reset_index(drop=True).to_crs(2154))