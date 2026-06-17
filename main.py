from src.extract_bounds.commune import commune
from src.extract_bounds.departement import departement
from src.extract_bounds.region import region
from src.util.telechargement import *
from src.pipeline import traiterDalle
import concurrent.futures
import os

OUT_DIR_RAW = "data/raw/TEST/dalles"
OUT_DIR_PROCESSED = os.path.normpath("data/processed/TEST")
GPKG_BDTOPO = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
OUT_DIR  = os.path.normpath("data/processed/TEST")



def main():

    print("Choix de l'échelle territoriale:")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    choix=input("Choisissez l'échelle (1,2 ou 3) :").strip()

    dictionnaire_resultats={}

    if choix == "1":
        nom_commune=input("Entrez une ville ou une commune : ").strip().replace("'", "''")
        num_departement = input("Entrez le numéro de département : ").strip()
        dictionnaire_resultats = commune(nom_commune, num_departement)

    elif choix == "2":
        depart = input("Entrez un département ou son numéro : ").strip().replace("'", "''")
        dictionnaire_resultats = departement(depart)
    
    elif choix == "3":
        nom_region=input("Entrez le nom d'une région: ").strip().replace("'", "''")
        dictionnaire_resultats = region(nom_region)
    else:
        print('Choisissez entre 1,2 et 3.')
        return None
    
    if dictionnaire_resultats:
        liste_dalles = liste_telechargement(dictionnaire_resultats)
        
        for nom_mnt, url_mnt, nom_mns, url_mns in liste_dalles:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:
                    f_mnt = e.submit(telecharger_fichier, url_mnt, nom_mnt, OUT_DIR_RAW)
                    f_mns = e.submit(telecharger_fichier, url_mns, nom_mns, OUT_DIR_RAW)
                    mnt_path = f_mnt.result()
                    mns_path = f_mns.result()
                    out_gpkg = os.path.join(OUT_DIR, os.path.splitext(nom_mns)[0] + "_irradiance.gpkg")
                    traiterDalle(mns_path, mnt_path, GPKG_BDTOPO, out_gpkg)

                    os.remove(mns_path)
                    os.remove(mnt_path)


            except Exception as e:
                print(f"ECHEC dalle {nom_mns} : {e}")
        
       

if __name__ == "__main__":
    main()