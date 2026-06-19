import geopandas as gpd
import pandas as pd
import requests
import shapely.ops

def adresse():
    numero=input("Numéro: ").strip().replace("'", "''")
    voie=input("Rue (sans accent): ").strip().replace("'", "''")
    commune=input("Commune ou ville: ").strip().replace("'", "''")
    
    url_wfs="https://data.geopf.fr/wfs/ows"

    params={
        "SERVICE": "WFS", 
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BAN.DATA.GOUV:ban",
        "OUTPUTFORMAT": "application/json",
        "CQL_FILTER": f"numero='{numero}' AND nom_voie ILIKE '%{voie}%' AND nom_commune ILIKE '%{commune}%'"
        }
    
    reponse=requests.get(url_wfs,params=params)
   
    gdf=gpd.read_file(reponse.text)
    
    if gdf.empty:
        print("Aucune adresse trouvée")
        return None

    print(gdf)

if __name__ == "__main__":
    adresse()