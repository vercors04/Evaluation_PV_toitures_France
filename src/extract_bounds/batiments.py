import geopandas as gpd
import requests
import pandas as pd

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
    
    if echelle == "commune":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}' AND code_insee_du_departement = '{code_dep}'"
    elif echelle == "departement":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}' OR code_insee = '{nom_zone}'"
    elif echelle == "region":
        cql_filter = f"nom_officiel ILIKE '{nom_zone}'"
    else:
        print("Erreur : Échelle non valide.")
        return None
    
    params={
        "SERVICE": "WFS", 
        "VERSION": "1.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": f"BDTOPO_V3:{echelle}",
        "OUTPUTFORMAT": "application/json",
        "CQL_FILTER": cql_filter
    }

    reponse = requests.get(wfs_url, params=params)
    
    gdf = gpd.read_file(reponse.text)
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

        start_index+=2000

    if liste_geodf:
        geodf_complet=pd.concat(liste_geodf,ignore_index=True)
        gdf_final = geodf_complet[geodf_complet.intersects(geom_echelle)]

        print(f"{len(gdf_final)} bâtiments trouvés")
        
        return gdf_final
    else:
        return None
