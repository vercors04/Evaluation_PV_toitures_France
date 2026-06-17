import geopandas as gpd
import pandas as pd
import requests
import shapely.ops

def departement(recherche_dep):
    """
    Interroge l'API WFS IGN (BDTOPO) pour l'emprise d'un département et récupère les dalles LiDAR intersectées via une pagination sécurisée (COUNT/STARTINDEX).
    ---------------------------------------------------------------------------------------
    @param[in]  recherche_dep : Nom officiel ou numéro/code INSEE du département.

    @param[out] resultats_dalles : Dictionnaire classant les dalles intersectées (dédoublonnées) :
                                   {
                                     'MNT' : GeoDataFrame (fusion des requêtes paginées),
                                     'MNS' : GeoDataFrame (fusion des requêtes paginées)
                                   }
                                   Peut retourner un dictionnaire vide en cas d'échec de la requête.
    """

    resultats_dalles = {}
    wfs_url="https://data.geopf.fr/wfs/ows"


    arguments = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "BDTOPO_V3:departement",
        "OUTPUTFORMAT": "application/json",
        "COUNT": "1",
        "CQL_FILTER": f"nom_officiel ILIKE '{recherche_dep}' OR code_insee = '{recherche_dep}'"
    }
    
    try:
        reponse = requests.get(wfs_url, params=arguments)
        
        gdf = gpd.read_file(reponse.text)
        
        if gdf.empty:
            print("Aucun departement trouvé.")
        else:
            print(gdf[['nom_officiel','geometry']])

            enveloppe = gdf.geometry.iloc[0].envelope
            enveloppe_inversee = shapely.ops.transform(lambda x, y: (y, x), enveloppe)
            depart_enveloppe_wkt = enveloppe_inversee.wkt

            resultats_dalles={}

            for type_couche in ['MNT','MNS']:

                continuer=True
                index_debut=0
                toutes_les_dalles=[]

                while continuer==True:

                    url_lidar="https://data.geopf.fr/wfs/ows"
                    parametres = {
                                "SERVICE": "WFS",
                                "VERSION": "2.0.0",
                                "REQUEST": "GetFeature",
                                "TYPENAME": f"IGNF_{type_couche}-LIDAR-HD:dalle",
                                "OUTPUTFORMAT": "application/json",
                                "COUNT":"5000",
                                "CQL_FILTER": f"INTERSECTS(geom, {depart_enveloppe_wkt})",
                                "STARTINDEX": f"{index_debut}"
                            }

                    try:
                        reponses = requests.get(url_lidar, params=parametres)
                        geodf = gpd.read_file(reponses.text)
                        
                        if geodf.empty:
                            continuer=False
                            break
                            
                        gdf_lambert = gdf.to_crs(geodf.crs)
                        
                        dalles_depart = gpd.sjoin(geodf, gdf_lambert, predicate="intersects")
                        
                        if dalles_depart.empty:
                            continuer=False 
                            break
                        else:
                            print(f"\n {len(dalles_depart)} dalles {type_couche} trouvées ") 
                            print(dalles_depart[['name','url']])
                            toutes_les_dalles.append(dalles_depart)
                            index_debut+=5000

                    except Exception as e:
                        print(f"Erreur : {e}")

                if toutes_les_dalles:
                    dalles_finales = pd.concat(toutes_les_dalles)
                    dalles_finales = dalles_finales.drop_duplicates(subset='geometry') 
                    resultats_dalles[type_couche] = dalles_finales
                    print(f"{len(dalles_finales)} dalles MNS et {len(dalles_finales)} dalles MNT trouvées")
                    gdf.to_file(f"data/processed/departements/departement_{recherche_dep}.geojson", driver="GeoJSON")
                else:
                    print(f"Aucune dalle {type_couche} n'a pu être récupérée au total.")
                    return resultats_dalles
    except Exception as e:
        print(f"Erreur : {e}")
    return resultats_dalles
