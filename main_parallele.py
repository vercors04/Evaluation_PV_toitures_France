import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numba
import pandas as pd
import geopandas as gpd

from src.acquisition.telechargement import telecharger_fichier, liste_telechargement
from src.pipeline import traiterDalle
from src.agregation.agregation import mergeCleabs
from src.agregation.select import filtrer
from src.tuile.donnees_dalle import tileBounds
from src.acquisition.batiments import batiments
from src.acquisition.zone import zone
from src.acquisition.dalles import dalles
from src.debug.affichage_terminal import afficherBilan, progressTerminal
from src.config import OUT_DIR_PROCESSED, OUT_DIR_RAW, DIR_GEOJSON, N_COEURS



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


    bilan = runPipeline(echelle, nom_zone, code_dep,
                        on_progress=progressTerminal, on_log=print)
    afficherBilan(bilan)






def runPipeline(echelle, nom_zone, code_dep=None, on_progress=None, on_log=print):
    """
    Traite la zone : dalles, calcul parallele, fusion, filtre, ecriture du gpkg.
    --------
    @param[in] echelle, nom_zone, code_dep : definition de la zone (voir zone)
    @param[in] on_progress : callback (i, total) appele a chaque dalle finie (None = aucun)
    @param[in] on_log      : callback (message) pour les messages (defaut print)

    @return bilan : dict (fichier, total, echecs, moyennes_dalle, temps_globaux, batiments) ;
                    None si zone introuvable ou aucun batiment
    """
    t0 = time.time()
    polygone = zone(echelle, nom_zone.replace("'", "''"), code_dep)
    if polygone is None:
        on_log("zone introuvable"); return None

    gdf_bati = batiments(polygone)
    if gdf_bati is None or gdf_bati.empty:
        on_log("aucun batiment"); return None
    t_bati = time.time() - t0

    nom_zone = nom_zone.replace(" ", "_").replace(",", "")
    gpd.GeoDataFrame(geometry=[polygone], crs=4326).to_crs(2154).to_file(
        os.path.join(DIR_GEOJSON, f"{nom_zone}{code_dep or ''}.geojson"), driver="GeoJSON")

    gpkg_path = os.path.join(OUT_DIR_PROCESSED, f"{nom_zone}{code_dep or ''}.gpkg")


    taches = []
    for nom_mnt, url_mnt, nom_mns, url_mns in liste_telechargement(dalles(polygone)):
        xmin, ymin, xmax, ymax = tileBounds(nom_mns)
        gdf_dalle = gdf_bati.cx[xmin:xmax, ymin:ymax]
        if not gdf_dalle.empty:
            taches.append((nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle))

    total = len(taches)
    resultats  = []
    temps_tous = []
    echecs     = []

    on_log(f"{total} dalles a traiter")

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=N_COEURS,
                             initializer=numba.set_num_threads, initargs=(1,)) as ex:
        for i, (out, temps) in enumerate(ex.map(trait1Dalle, taches), 1):
            if out is None:
                echecs.append(temps.get("nom", "?"))      # dalle en echec
            elif not out.empty:
                resultats.append(out)
                temps_tous.append(temps)
            # sinon : dalle valide mais sans batiment -> on ignore
            if on_progress is not None:
                on_progress(i, total)                     # avancement 1% par 1%
    t_traitement = time.time() - t0

    if not resultats:
        on_log("aucun batiment traite")
        return {"fichier": None, "total": total, "echecs": echecs}


    t0 = time.time()
    g = pd.concat(resultats, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=2154)
    n_avant = len(g)
    g = mergeCleabs(g);  n_merge  = len(g)
    g = filtrer(g);      n_filtre = len(g)

    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)
    g.to_file(gpkg_path, driver="GPKG", layer="batiments")
    t_ecriture = time.time() - t0

    def moyenne(cle):
        vals = [t[cle] for t in temps_tous if cle in t]
        return sum(vals) / len(vals) if vals else 0.0

    # bilan retourne, a presenter en tableau cote terminal ou GUI
    return {
        "fichier": f"{nom_zone}{code_dep or ''}.gpkg",
        "total":   total,
        "echecs":  echecs,
        "moyennes_dalle": {
            "telechargement": moyenne("telechargement"),
            "geometrie":      moyenne("geometrie"),
            "horizon":        moyenne("horizon"),
            "irradiance":     moyenne("irradiance"),
            "agregation":     moyenne("agregation batiment"),
        },
        "temps_globaux": {
            "batiments":  t_bati,        # recuperation des emprises BD TOPO
            "traitement": t_traitement,  # boucle parallele sur les dalles
            "ecriture":   t_ecriture,    # concat + merge + filtre + ecriture
        },
        "batiments": {
            "avant_merge_filtre": n_avant,   # avant fusion inter-dalles et filtres
            "apres_merge":        n_merge,   # apres fusion, avant filtre
            "final":              n_filtre,  # apres filtre
        },
    }





def trait1Dalle(tache):
    """
    Traite une dalle dans un worker : telecharge MNS/MNT, calcule, nettoie les fichiers.
    Definie au niveau module pour rester picklable par ProcessPoolExecutor.
    --------
    @param[in] tache : (nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle)

    @return out, temps : GeoDataFrame de la dalle (None si echec) et dict des durees par etape
    """
    temps = {}
    nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle = tache
    temps["nom"] = nom_mns
    mnt_path = mns_path = None
    try:
        t0 = time.perf_counter()
        with ThreadPoolExecutor(2) as dl:
            f_mnt = dl.submit(telecharger_fichier, url_mnt, nom_mnt, OUT_DIR_RAW)
            f_mns = dl.submit(telecharger_fichier, url_mns, nom_mns, OUT_DIR_RAW)
            mnt_path, mns_path = f_mnt.result(), f_mns.result()
        temps["telechargement"] = time.perf_counter() - t0
        return traiterDalle(mns_path, mnt_path, gdf_dalle, temps=temps), temps

    except Exception:
        return None, temps
    finally:
        for pth in (mns_path, mnt_path):           
            if pth and os.path.exists(pth):
                os.remove(pth)











if __name__ == "__main__":
    t0 = time.time()
    main()
    dt = time.time() - t0
    print(f"Temps total : {int(dt // 60)} min {dt % 60:.0f} s")




