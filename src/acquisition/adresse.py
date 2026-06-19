import geopandas as gpd
import pandas as pd
import requests

def adresse_vers_coords(nom_zone: str):
    """
    Géocode une adresse textuelle pour identifier et récupérer les dalles LiDAR HD associées.
    ---------------------------------------------------------------------------------------
    @param[in] nom_zone          : L'adresse textuelle complète saisie par l'utilisateur 
                                   (ex: "107 boulevard de vitré rennes")
    
    @param[out] resultats_dalles : Dictionnaire contenant deux clés ('MNS' et 'MNT'), associées 
                                   chacune à un GeoDataFrame des métadonnées de la dalle de 1 km² 
                                   (ou None/vide si l'adresse est introuvable)
    """
    r = requests.get(
        "https://data.geopf.fr/geocodage/search",
        params={"q": nom_zone, "limit": 1}
    )
    lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
    print(f"lon={lon}, lat={lat}")

    resultats_dalles={}
    url_mn="https://data.geopf.fr/wfs/ows"
    if lon and lat :
        lon_min,lon_max=lon - 0.0005, lon + 0.0005
        lat_min,lat_max=lat - 0.0005, lat + 0.0005
        for type_couche in ['MNS','MNT']:
            args={
                "SERVICE": "WFS",
                "VERSION": "2.0.0",
                "REQUEST": "GetFeature",
                "TYPENAME": f"IGNF_{type_couche}-LIDAR-HD:dalle",
                "OUTPUTFORMAT": "application/json",
                "CQL_FILTER": f"BBOX(geom,{lat_min},{lon_min},{lat_max},{lon_max})"
                }
        
            reponse=requests.get(url_mn,params=args)
            gdf=gpd.read_file(reponse.text)
            if gdf.empty:
                print("erreur adresse non valide")
                return None
            else :
                resultats_dalles[type_couche]=gdf
    
    print(resultats_dalles)
    return resultats_dalles
