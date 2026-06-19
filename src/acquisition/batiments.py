import geopandas as gpd
import requests
import pandas as pd
from shapely.geometry import box

def batiments(echelle, nom_zone, code_dep=None):
    """
    Interroge l'API WFS IGN pour récupérer les bâtiments selon l'échelle territoriale.
    ---------------------------------------------------------------------------------------
    @param[in] echelle       : 'commune', 'departement', ou 'region'
    @param[in] nom_recherche : Nom du territoire (ex: "Cloué", "Vienne", "Bretagne")
    @param[in] code_dep      : Optionnel, requis uniquement pour différencier les communes homonymes
    
    @param[out] gdf_final    : GeoDataFrame contenant les bâtiments découpés sur le territoire
    """

    wfs_url = "https://data.geopf.fr/wfs/ows"

    if echelle == "adresse":
        r = requests.get("https://data.geopf.fr/geocodage/search",
                         params={"q": nom_zone, "limit": 1})
        lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
        minx, miny, maxx, maxy = lon-0.015, lat-0.015, lon+0.015, lat+0.015
        geom_echelle = box(minx, miny, maxx, maxy)
    
    elif echelle == "commune":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}' AND code_insee_du_departement = '{code_dep}'"

    elif echelle == "departement":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}' OR code_insee = '{nom_zone}'"

    elif echelle == "region":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}'"


    else:
        raise ValueError(f"echelle invalide : {echelle}")
    
    if echelle != "adresse":
        params={
            "SERVICE": "WFS", 
            "VERSION": "1.0.0",
            "REQUEST": "GetFeature",
            "TYPENAME": f"BDTOPO_V3:{echelle}",
            "OUTPUTFORMAT": "application/json",
            "CQL_FILTER": cql_filter
        }


        gdf = gpd.read_file(requests.get(wfs_url, params=params).text)
        if gdf.empty:
            print('Pas de territoire trouvé')
            return None
        
        geom_echelle = gdf.geometry.iloc[0]
        minx, miny, maxx, maxy = gdf.total_bounds


    limit=2000
    start_index=0
    liste_geodf=[]

    while True:
        args={
            "SERVICE": "WFS", 
            "VERSION": "2.0.0", 
            "REQUEST": "GetFeature",
            "TYPENAME": "BDTOPO_V3:batiment", 
            "OUTPUTFORMAT": "application/json",
            "CQL_FILTER": f"BBOX(geometrie,{miny},{minx},{maxy},{maxx})",
            "COUNT": limit,
            "STARTINDEX": start_index
        }
        reponses = requests.get(wfs_url, params=args)
        
        geodf = gpd.read_file(reponses.text)

        if geodf.empty:
            break

        liste_geodf.append(geodf)

        if len(geodf)<limit:
            break

        start_index+=limit

    if liste_geodf:
        geodf_complet=pd.concat(liste_geodf,ignore_index=True)
        gdf_final = geodf_complet[geodf_complet.intersects(geom_echelle)]
        NATURE_OK = ['Indifférenciée', 'Industriel, agricole ou commercial']

        gdf_final = gdf_final[
            (gdf_final['etat_de_l_objet'] == 'En service') &
            (gdf_final['construction_legere'] == False) &
            (gdf_final['nature'].isin(NATURE_OK))
        ]


        gdf_final = (gdf_final[['cleabs', 'nature', 'usage_1', 'hauteur',
                                        'nombre_d_etages', 'geometry']].reset_index(drop=True)) .to_crs(2154)

        print(f"{len(gdf_final)} batiments retenus")
        return gdf_final
    return None
