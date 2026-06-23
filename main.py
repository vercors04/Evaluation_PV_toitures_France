from src.acquisition.telechargement import telecharger_fichier, liste_telechargement
from src.pipeline import traiterDalle
from src.agregation.agregation import merger_cleabs, mergeCleabs
from src.agregation.select import filtrer
from src.tuile.donnees_dalle import tileBounds
from src.acquisition.batiments import batiments
from src.acquisition.zone import zone  
from src.acquisition.dalles import dalles
import os
import concurrent.futures
import geopandas as gpd
import time

from src.config import OUT_DIR_PROCESSED, OUT_DIR_RAW, DIR_GEOJSON


def main():
    
    os.makedirs(DIR_GEOJSON, exist_ok=True)
    os.makedirs(OUT_DIR_PROCESSED, exist_ok=True)
    os.makedirs(OUT_DIR_RAW, exist_ok=True)



    print("Choix de l'échelle territoriale:")
    print("0 : Adresse")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    choix=input("Choisissez l'échelle (0,1,2 ou 3) :").strip()

    echelle=""
    nom_zone=""
    code_dep=None

    if choix=="0":
        nom_zone=input('Entrez une adresse :').strip()
        echelle="adresse"

    elif choix == "1":
        nom_zone=input("Entrez une ville ou une commune : ").strip()
        code_dep = input("Entrez le numéro de département : ").strip()
        echelle="commune"

    elif choix == "2":
        nom_zone = input("Entrez un département ou son numéro : ").strip()
        echelle="departement"
   
    elif choix == "3":
        nom_zone=input("Entrez le nom d'une région: ").strip()
        echelle="region"

    else:
        print('Choisissez entre 0,1,2 et 3.')
        return None
    
    t0 = time.time()
    polygone = zone(echelle, nom_zone.replace("'", "''"), code_dep)
    if polygone is None:
        print("zone introuvable"); return None

    gdf_bati = batiments(polygone)
    if gdf_bati is None or gdf_bati.empty:
        print("aucun batiment"); return None

    print(f"Temps batiments : {time.time()-t0:.1f}s")

    nom_zone=nom_zone.replace("'", "''").replace(" ", "_").replace(",", "") 

    gpd.GeoDataFrame(geometry=[polygone], crs=4326).to_crs(2154).to_file(
    os.path.join(DIR_GEOJSON, f"{nom_zone}.geojson"), driver="GeoJSON")

    gpkg_path = os.path.join(OUT_DIR_PROCESSED, f"{nom_zone}{code_dep or ''}.gpkg")
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)
            
    for nom_mnt, url_mnt, nom_mns, url_mns in liste_telechargement(dalles(polygone)):
        try:
            xmin, ymin, xmax, ymax = tileBounds(nom_mns)
            gdf_dalle = gdf_bati.cx[xmin:xmax, ymin:ymax] #renvoie les bat qui sont dans la tuile, pareil que gdf_bati[gdf_bati.intersects(box(xmin,ymin,xmax,ymax))]
            if gdf_dalle.empty:
                print(f"{nom_mns} : 0 batiments, dalle pas traitee")
                continue 

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: 
                t0 = time.time()
                f_mnt = ex.submit(telecharger_fichier, url_mnt, nom_mnt, OUT_DIR_RAW)
                f_mns = ex.submit(telecharger_fichier, url_mns, nom_mns, OUT_DIR_RAW)

            mnt_path = f_mnt.result()
            mns_path = f_mns.result()
            print(f"Telechargement MNS MNT : {time.time()-t0:.1f}s")


            out = traiterDalle(mns_path, mnt_path, gdf_dalle)
            if out is not None and not out.empty:
                out.to_file(gpkg_path, driver="GPKG", layer="batiments",
                        mode="a" if os.path.exists(gpkg_path) else "w") #si le fichier existe pas encore write sinon append
                    
            os.remove(mns_path)
            os.remove(mnt_path)


        except Exception as e:
            print(f"ECHEC dalle {nom_mns} : {e}")
        


    #supression filtre fin 
    if os.path.exists(gpkg_path):
        t0 = time.time()
        g = gpd.read_file(gpkg_path)
        print("nombre bat avant merge+filtre  :", len(g))

        g = mergeCleabs(g)       
        print("apres merge      :", len(g))

        g = filtrer(g)           
        print("apres filtre     :", len(g))

        print(f"Filtrage batiment post gpkg : {time.time()-t0:.1f}s")

        g.to_file(gpkg_path, driver="GPKG", layer="batiments")  
        print(f"Final : {len(g)} batiments")
        print(f"fichier enregistré  : {nom_zone}{code_dep or ''}.gpkg")

if __name__ == "__main__":
    t0 = time.time()
    main()
    dt = time.time() - t0
    print(f"Temps total : {int(dt // 60)} min {dt % 60:.0f} s")