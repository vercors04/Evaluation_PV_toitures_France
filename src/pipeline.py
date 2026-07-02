import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numba
import pandas as pd
import geopandas as gpd

from src.tuile.raster import chargerDalle
from src.tuile.donnees_dalle import nomCoord, centreWGS84, tileBounds
from src.geometrie.extract_geom import extractGeom, makeMasques
from src.geometrie.horizon import compHZ
from src.irradiance.meteo.grille_fct import chargerTable
from src.irradiance.irr_calcul import irrPixels
from src.agregation.agregation import agregerBatiment, mergeCleabs
from src.agregation.select import filtrer, hBat
from src.acquisition.telechargement import telechargerFichier, listeTelechargement
from src.acquisition.batiments import batiments
from src.acquisition.zone import zone
from src.acquisition.dalles import dalles
from src.debug import debug_pipeline as debug
from src import config


def traiterDalle(mns_path, mnt_path, gdf, debug_dir=None, temps=None):
    """
    Traite une dalle : geometrie, masques, horizon, irradiance, agregation par batiment.
    --------
    @param[in] mns_path, mnt_path : chemins des rasters MNS / MNT IGN
    @param[in] gdf       : GeoDataFrame des batiments de la dalle (Lambert 93)
    @param[in] debug_dir : si fourni, exporte les rasters intermediaires
    @param[in] temps     : dict optionnel rempli avec la duree de chaque etape

    @return out : GeoDataFrame, 1 ligne par batiment
    """

    mns_name = os.path.basename(mns_path)

    # geometrie
    t0 = time.perf_counter()
    mns, mnt, meta = chargerDalle(mns_path, mnt_path)
    pente, aspect, masque_bat, mnh = extractGeom(mns, mnt, gdf, meta)
    incline_or, incline, plat = makeMasques(pente, aspect, masque_bat)
    toiture = incline | plat
    if temps is not None: temps["geometrie"] = time.perf_counter() - t0



    # horizon
    t0 = time.perf_counter()
    horizon = compHZ(mns, toiture, meta["resolution"],
                     config.N_DIRECTIONS, config.DIST_MAX_M, config.CAP)
    if temps is not None: temps["horizon"] = time.perf_counter() - t0


    # irradiance
    t0 = time.perf_counter()
    lat, lon = centreWGS84(*nomCoord(mns_name))
    B, D, SAZ, SEL = chargerTable(lat, lon)
    df  = irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
                    meta["resolution"], B, D, SAZ, SEL, horizon)
    if temps is not None: temps["irradiance"] = time.perf_counter() - t0


    # agregation par batiment
    t0 = time.perf_counter()
    hauteur = hBat (mnh, masque_bat, 0.95)
    out = agregerBatiment(df, gdf, hauteur)
    if temps is not None: temps["agregation batiment"] = time.perf_counter() - t0




    # export debug optionnel
    if debug_dir is not None:
        debug.exportRasters({
            "pente": pente, "aspect": aspect, "mnh": mnh,
            "incline":    incline.astype("int32"),
            "incline_or": incline_or.astype("int32"),
            "plat":       plat.astype("int32"),
        }, meta, debug_dir)
        debug.exportHorizon(horizon, toiture, meta, os.path.join(debug_dir, "horizon"))

    return out


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
    t_total = time.time()
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
        os.path.join(config.DIR_GEOJSON, f"{nom_zone}{code_dep or ''}.geojson"), driver="GeoJSON")

    gpkg_path = os.path.join(config.OUT_DIR_PROCESSED, f"{nom_zone}{code_dep or ''}.gpkg")


    taches = []
    for nom_mnt, url_mnt, nom_mns, url_mns in listeTelechargement(dalles(polygone)):
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
    with ProcessPoolExecutor(max_workers=config.N_COEURS,
                             initializer=numba.set_num_threads, initargs=(1,)) as ex:
        for i, (out, temps) in enumerate(ex.map(trait1Dalle, taches), 1):
            if out is None:
                echecs.append({"nom": temps.get("nom", "?"), "erreur": temps.get("erreur", "")})      
                on_log(f"echec dalle {temps.get('nom','?')}") 
            elif not out.empty:
                resultats.append(out)
                temps_tous.append(temps)
            if on_progress is not None:
                on_progress(i, total)                     
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
    cols = (["cleabs"] + config.ATTRS_BATI
            + [c for grp in config.SORTIE_GARDEES for c in config.GROUPES_SORTIE[grp]]
            + ["geometry"])
    g = g[[c for c in cols if c in g.columns]] 
    
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)
    g.to_file(gpkg_path, driver="GPKG", layer="batiments")
    t_ecriture = time.time() - t0

    def moyenne(cle):
        vals = [t[cle] for t in temps_tous if cle in t]
        return sum(vals) / len(vals) if vals else 0.0

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
            "total":      time.time() - t_total,
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
            f_mnt = dl.submit(telechargerFichier, url_mnt, nom_mnt, config.OUT_DIR_RAW)
            f_mns = dl.submit(telechargerFichier, url_mns, nom_mns, config.OUT_DIR_RAW)
            mnt_path, mns_path = f_mnt.result(), f_mns.result()
        temps["telechargement"] = time.perf_counter() - t0
        return traiterDalle(mns_path, mnt_path, gdf_dalle, temps=temps), temps

    except Exception as e:
        temps["erreur"] = str(e)
        return None, temps
    finally:
        for pth in (mns_path, mnt_path):           
            if pth and os.path.exists(pth):
                os.remove(pth)

