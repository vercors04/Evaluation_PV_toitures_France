import geopandas as gpd
import pandas as pd
import requests
import shapely.ops

def commune(nom_commune,num_departement):

    """
    Interroge l'API WFS IGN (BDTOPO) pour récupérer l'emprise géométrique d'une commune, puis identifie les dalles LiDAR qui l'intersectent.
    ---------------------------------------------------------------------------------------
    @param[in]  nom_commune     : Nom officiel de la commune recherchée (ex: "Paris").
    @param[in]  num_departement : Numéro ou code INSEE du département pour éviter les homonymes.

    @param[out] resultats_dalles : Dictionnaire classant les dalles intersectées :
                                   {
                                     'MNT' : GeoDataFrame des dalles MNT (avec colonnes 'name', 'url', etc.),
                                     'MNS' : GeoDataFrame des dalles MNS
                                   }
                                   Peut retourner un dictionnaire vide si aucune dalle ou commune n'est trouvée.
    """


    resultats_dalles = {}
    wfs_url="https://data.geopf.fr/wfs/ows"


    arguments = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BDTOPO_V3:commune",
        "OUTPUTFORMAT": "application/json",
        "CQL_FILTER": f"nom_officiel ILIKE '{nom_commune}' AND code_insee_du_departement = '{num_departement}'"
    }

    try:
        reponse = requests.get(wfs_url, params=arguments)
        
        gdf = gpd.read_file(reponse.text)
        
        if gdf.empty:
            print("Aucune commune trouvée.")
        else:
            print(gdf[['nom_officiel', 'code_insee','geometry']])
            enveloppe = gdf.geometry.iloc[0].envelope
            enveloppe_inversee = shapely.ops.transform(lambda x, y: (y, x), enveloppe)
            commune_enveloppe_wkt = enveloppe_inversee.wkt

            resultats_dalles={}
            for type_couche in ['MNT','MNS']:

                url_mn="https://data.geopf.fr/wfs/ows"
                parametres = {
                            "SERVICE": "WFS",
                            "VERSION": "2.0.0",
                            "REQUEST": "GetFeature",
                            "TYPENAME": f"IGNF_{type_couche}-LIDAR-HD:dalle",
                            "OUTPUTFORMAT": "application/json",
                            "CQL_FILTER": f"INTERSECTS(geom, {commune_enveloppe_wkt})"
                        }

                try:
                    reponses = requests.get(url_mn, params=parametres)
                    geodf = gpd.read_file(reponses.text)
                    
                    if geodf.empty:
                        print(f"Aucune dalle {type_couche} trouvée dans cette zone.")
                        return None
                        
                    gdf_lambert = gdf.to_crs(geodf.crs)
                    
                    dalles_commune = gpd.sjoin(geodf, gdf_lambert, predicate="intersects")
                    
                    if dalles_commune.empty:
                        print("Erreur.")
                    else:
                        print(f"\n {len(dalles_commune)} dalles {type_couche} trouvées ")
                        
                        print(dalles_commune[['name','url']])
                    
                        resultats_dalles[type_couche] = dalles_commune
                

                except Exception as e:
                    print(f"Erreur : {e}")
            gdf.to_file(f"data/raw/TEST/geojson/{nom_commune}.geojson", driver="GeoJSON")
            return resultats_dalles
    except Exception as e:
        print(f"Erreur : {e}")

    return resultats_dalles