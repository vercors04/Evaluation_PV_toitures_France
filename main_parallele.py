import os
import time
from concurrent.futures import ProcessPoolExecutor

import numba
import pandas as pd
import geopandas as gpd

from src.acquisition.telechargement import telecharger_fichier, liste_telechargement
from src.pipeline import traiterDalle
from src.agregation.agregation import mergeCleabs, merger_cleabs
from src.agregation.select import filtrer
from src.tuile.donnees_dalle import tileBounds
from src.acquisition.batiments import batiments
from src.acquisition.zone import zone
from src.acquisition.dalles import dalles
from src.config import OUT_DIR_PROCESSED, OUT_DIR_RAW, DIR_GEOJSON, N_COEURS


def traiter_une_dalle(tache):
    """
    Traite UNE dalle dans un processus worker : telecharge MNS/MNT, calcule, nettoie.
    Fonction au niveau module = picklable par ProcessPoolExecutor.
    --------
    @param[in] tache : (nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle)

    @return out : GeoDataFrame par batiment de la dalle ; None si echec ou vide
    """
    nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle = tache
    mnt_path = mns_path = None
    try:
        mnt_path = telecharger_fichier(url_mnt, nom_mnt, OUT_DIR_RAW)
        mns_path = telecharger_fichier(url_mns, nom_mns, OUT_DIR_RAW)
        return traiterDalle(mns_path, mnt_path, gdf_dalle)
    except Exception as e:
        print(f"ECHEC dalle {nom_mns} : {e}")
        return None
    finally:
        for pth in (mns_path, mnt_path):           # nettoyage meme en cas d'erreur
            if pth and os.path.exists(pth):
                os.remove(pth)


def main():
    os.makedirs(DIR_GEOJSON, exist_ok=True)
    os.makedirs(OUT_DIR_PROCESSED, exist_ok=True)
    os.makedirs(OUT_DIR_RAW, exist_ok=True)

    print("Choix de l'échelle territoriale:")
    print("0 : Adresse")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    print("4 : France")
    choix = input("Choisissez l'échelle (0,1,2, 3 ou 4) :").strip()

    echelle = ""
    nom_zone = ""
    code_dep = None

    if choix == "0":
        nom_zone = input('Entrez une adresse :').strip()
        echelle = "adresse"
    elif choix == "1":
        nom_zone = input("Entrez une ville ou une commune : ").strip()
        code_dep = input("Entrez le numéro de département : ").strip()
        echelle = "commune"
    elif choix == "2":
        nom_zone = input("Entrez un département ou son numéro : ").strip()
        echelle = "departement"
    elif choix == "3":
        nom_zone = input("Entrez le nom d'une région: ").strip()
        echelle = "region"
    elif choix == "4":
        nom_zone = "France"
        echelle = "nationale"
    else:
        print('Choisissez entre 0,1,2, 3 et 4.')
        return None

    t0 = time.time()
    polygone = zone(echelle, nom_zone.replace("'", "''"), code_dep)
    if polygone is None:
        print("zone introuvable"); return None

    gdf_bati = batiments(polygone)
    if gdf_bati is None or gdf_bati.empty:
        print("aucun batiment"); return None
    print(f"Temps batiments : {time.time()-t0:.1f}s")

    nom_zone = nom_zone.replace(" ", "_").replace(",", "")
    gpd.GeoDataFrame(geometry=[polygone], crs=4326).to_crs(2154).to_file(
        os.path.join(DIR_GEOJSON, f"{nom_zone}.geojson"), driver="GeoJSON")

    gpkg_path = os.path.join(OUT_DIR_PROCESSED, f"{nom_zone}{code_dep or ''}.gpkg")

    # --- une tache par dalle non vide ---
    taches = []
    for nom_mnt, url_mnt, nom_mns, url_mns in liste_telechargement(dalles(polygone)):
        xmin, ymin, xmax, ymax = tileBounds(nom_mns)
        gdf_dalle = gdf_bati.cx[xmin:xmax, ymin:ymax]
        if not gdf_dalle.empty:
            taches.append((nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle))
    print(f"{len(taches)} dalles a traiter")

    # --- traitement des dalles EN PARALLELE (processus) ---
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=N_COEURS,
                             initializer=numba.set_num_threads, initargs=(1,)) as ex:
        resultats = [out for out in ex.map(traiter_une_dalle, taches)
                     if out is not None and not out.empty]
    print(f"Traitement dalles : {time.time()-t0:.1f}s")

    if not resultats:
        print("aucun batiment traite"); return None

    # --- fusion finale + UNE seule ecriture ---
    t0 = time.time()
    g = pd.concat(resultats, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=2154)
    print("nombre bat avant merge+filtre  :", len(g))
    g = mergeCleabs(g);  print("apres merge      :", len(g))
    g = filtrer(g);      print("apres filtre     :", len(g))

    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)
    g.to_file(gpkg_path, driver="GPKG", layer="batiments")
    print(f"Filtrage + ecriture : {time.time()-t0:.1f}s")
    print(f"Final : {len(g)} batiments")
    print(f"fichier enregistré  : {nom_zone}{code_dep or ''}.gpkg")


if __name__ == "__main__":
    t0 = time.time()
    main()
    dt = time.time() - t0
    print(f"Temps total : {int(dt // 60)} min {dt % 60:.0f} s")