from src.acquisition.commune import commune
from src.acquisition.departement import departement
from src.acquisition.region import region
from src.acquisition.telechargement import *
from src.pipeline import traiterDalle
import concurrent.futures
#from src.tuile.bd_topo import loadBuild
from src.tuile.donnees_dalle import tileBounds
import os
from src.config import OUT_DIR_PROCESSED, OUT_DIR_RAW, DIR_GEOJSON
import geopandas as gpd
from src.acquisition.batiments import batiments


def main():
    
    os.makedirs(DIR_GEOJSON, exist_ok=True)
    os.makedirs(OUT_DIR_PROCESSED, exist_ok=True)
    os.makedirs(OUT_DIR_RAW, exist_ok=True)



    print("Choix de l'échelle territoriale:")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    choix=input("Choisissez l'échelle (1,2 ou 3) :").strip()

    dictionnaire_resultats={}
    echelle=""
    nom_zone=""
    code_dep=None


    if choix == "1":
        nom_zone=input("Entrez une ville ou une commune : ").strip().replace("'", "''").replace(" ", "_") 
        code_dep = input("Entrez le numéro de département : ").strip()
        dictionnaire_resultats = commune(nom_zone, code_dep)
        echelle="commune"
        #polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + num_departement + ".geojson"))

    elif choix == "2":
        nom_zone = input("Entrez un département ou son numéro : ").strip().replace("'", "''").replace(" ", "_") 
        dictionnaire_resultats = departement(nom_zone)
        echelle="departement"
        #polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + ".geojson"))
   
    elif choix == "3":
        nom_zone=input("Entrez le nom d'une région: ").strip().replace("'", "''").replace(" ", "_") 
        dictionnaire_resultats = region(nom_zone)
        echelle="region"
        #polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + ".geojson"))

    else:
        print('Choisissez entre 1,2 et 3.')
        return None
    
    gdf_bati = batiments(echelle, nom_zone, code_dep) 

    if gdf_bati is None or gdf_bati.empty:
        print("Pas de bat dans cette region / mal orthographie"); return None
    


    gpkg_path = os.path.join(OUT_DIR_PROCESSED, f"{nom_zone}.gpkg")

    

    if dictionnaire_resultats:

        liste_dalles = liste_telechargement(dictionnaire_resultats)
        
        for nom_mnt, url_mnt, nom_mns, url_mns in liste_dalles:
            try:
                xmin, ymin, xmax, ymax = tileBounds(nom_mns)
                gdf_dalle = gdf_bati.cx[xmin:xmax, ymin:ymax] #renvoie les bat qui sont dans la tuile, pareil que gdf_bati[gdf_bati.intersects(box(xmin,ymin,xmax,ymax))]
                if gdf_dalle.empty:
                    print(f"{nom_mns} : 0 batiments, dalle pas traitee")
                    continue 

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: 
                    f_mnt = ex.submit(telecharger_fichier, url_mnt, nom_mnt, OUT_DIR_RAW)
                    f_mns = ex.submit(telecharger_fichier, url_mns, nom_mns, OUT_DIR_RAW)

                mnt_path = f_mnt.result()
                mns_path = f_mns.result()

                out = traiterDalle(mns_path, mnt_path, gdf_dalle)
                if out is not None and not out.empty:
                    out.to_file(gpkg_path, driver="GPKG", layer="batiments",
                            mode="a" if os.path.exists(gpkg_path) else "w") #si le fichier existe pas encore write sinon append
                    
                os.remove(mns_path)
                os.remove(mnt_path)


            except Exception as e:
                print(f"ECHEC dalle {nom_mns} : {e}")
        
       

if __name__ == "__main__":
    main()