from src.extract_bounds.commune import commune
from src.extract_bounds.departement import departement
from src.extract_bounds.region import region
from src.util.telechargement import *
from src.pipeline import traiterDalle
import concurrent.futures
from src.tuile.bd_topo import loadBuild
from src.tuile.donnees_dalle import tileBounds
import os
from src.config import OUT_DIR_PROCESSED, OUT_DIR_RAW, GPKG_BDTOPO, DIR_GEOJSON
import geopandas as gpd
from src.extract_bounds.batiments import batiments


def main():

    print("Choix de l'échelle territoriale:")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    choix=input("Choisissez l'échelle (1,2 ou 3) :").strip()

    dictionnaire_resultats={}
    echelle=''
    nom_zone=''
    num_departement=None


    if choix == "1":
        echelle='commune'
        nom_zone=input("Entrez une ville ou une commune : ").strip().replace("'", "''").replace(" ", "_") 
        num_departement = input("Entrez le numéro de département : ").strip()
        dictionnaire_resultats = commune(nom_zone, num_departement)
        polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + num_departement + ".geojson"))

    elif choix == "2":
        echelle='departement'
        nom_zone = input("Entrez un département ou son numéro : ").strip().replace("'", "''").replace(" ", "_") 
        dictionnaire_resultats = departement(nom_zone)
        polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + ".geojson"))
   
    elif choix == "3":
        echelle='region'
        nom_zone=input("Entrez le nom d'une région: ").strip().replace("'", "''").replace(" ", "_") 
        dictionnaire_resultats = region(nom_zone)
        polygone = gpd.read_file(os.path.join(DIR_GEOJSON, nom_zone + ".geojson"))

    else:
        print('Choisissez entre 1,2 et 3.')
        return None
    
    gpkg_path = os.path.join(OUT_DIR_PROCESSED, f"{nom_zone}.gpkg")

    

    if dictionnaire_resultats:
        bati = batiments(echelle,nom_zone,num_departement)
        liste_dalles = liste_telechargement(dictionnaire_resultats)
        
        for nom_mnt, url_mnt, nom_mns, url_mns in liste_dalles:
            try:
                gdf = loadBuild(bati, tileBounds(nom_mns), polygone)
                if gdf.empty:
                    print(f"{nom_mns} : 0 batiments, dalle pas traitee")
                    continue 

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: 
                    f_mnt = ex.submit(telecharger_fichier, url_mnt, nom_mnt, OUT_DIR_RAW)
                    f_mns = ex.submit(telecharger_fichier, url_mns, nom_mns, OUT_DIR_RAW)

                mnt_path = f_mnt.result()
                mns_path = f_mns.result()

                out = traiterDalle(mns_path, mnt_path, gdf, polygone)
                if out is not None and not out.empty:
                    out.to_file(gpkg_path, driver="GPKG", layer="batiments",
                            mode="a" if os.path.exists(gpkg_path) else "w") #si le fichier existe pas encore write sinon append
                    
                    os.remove(mns_path)
                    os.remove(mnt_path)


            except Exception as e:
                print(f"ECHEC dalle {nom_mns} : {e}")
        
       

if __name__ == "__main__":
    main()