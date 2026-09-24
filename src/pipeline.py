import os
import time
import json
import shutil
import hashlib
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numba
import numpy as np
import pandas as pd
import geopandas as gpd

from src.tuile.raster import chargerDalle
from src.tuile.donnees_dalle import nomCoord, centreWGS84, tileBounds, enMetropole
from src.geometrie.extract_geom import extractGeom, makeMasques, eroderToit
from src.geometrie.horizon import compHZ
from src.geometrie.horizon_loin import mntRelief, hzLoin
from src.irradiance.meteo.grille_fct import chargerTable, tablesMeteo
from src.irradiance.irr_calcul import irrPixels
from src.irradiance.pose_plat import posesBatiments, description
from src.agregation.agregation import agregerBatiment, mergeCleabs
from src.agregation.select import filtrer, hBat
from src.acquisition.telechargement import telechargerFichier, listeTelechargement, urlWms
from src.acquisition.batiments import batiments
from src.acquisition.protections import marquerProtections
from src.acquisition.zone import zone, listeDepartements
from src.acquisition.dalles import dalles
from src import config


def nomFichier(nom_zone, code_dep=None):
    """
    Nom de fichier d'une zone : espaces remplaces, caracteres interdits retires.
    --------
    @param[in] nom_zone : nom de la zone
    @param[in] code_dep : code departement ajoute en suffixe (None = aucun)

    @return nom sans extension
    """
    nom = "".join(c for c in nom_zone.replace(" ", "_") if c not in ',/:*?"<>|\\')
    return f"{nom}{code_dep or ''}"


def dossierTravail(nom_fichier, polygone, on_log=print):
    """
    Dossier des dalles calculees de la zone (config.DIR_EN_COURS), vide s'il vient d'une zone ou
    de reglages differents.
    --------
    @param[in] nom_fichier : nom de la zone (voir nomFichier)
    @param[in] polygone    : emprise de la zone (shapely, WGS84)
    @param[in] on_log      : callback (message)

    @return chemin du dossier
    """
    dossier = os.path.join(config.DIR_EN_COURS, nom_fichier)
    chemin = os.path.join(dossier, "etat.json")
    etat = {"zone": hashlib.sha1(polygone.wkb).hexdigest(),
            "parametres": {k: v for k, v in config.snapshot().items()
                           if k not in config.SANS_EFFET_DALLE}}
    if os.path.isdir(dossier):
        try:
            with open(chemin, encoding="utf-8") as f:
                meme = json.load(f) == etat
        except (OSError, ValueError):
            meme = False
        if not meme:
            on_log("dalles du calcul precedent ecartees : zone ou reglages differents")
            shutil.rmtree(dossier)
    os.makedirs(dossier, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False)
    return dossier


def traiterDalle(mns_path, mnt_path, gdf, relief=None, temps=None):
    """
    Traite une dalle : geometrie, masques, horizon, irradiance, agregation par batiment.
    --------
    @param[in] mns_path, mnt_path : chemins des rasters MNS / MNT IGN
    @param[in] gdf       : GeoDataFrame des batiments de la dalle (Lambert 93)
    @param[in] relief    : MNT grossier de la zone pour l'horizon lointain (voir
                           mntRelief) ; None = ombrage proche seul
    @param[in] temps     : dict optionnel rempli avec la duree de chaque etape

    @return out : GeoDataFrame, 1 ligne par batiment
    """

    mns_name = os.path.basename(mns_path)

    t0 = time.perf_counter()
    mns, mnt, meta, mns_large = chargerDalle(mns_path, mnt_path)
    pente, aspect, masque_bat, masque_haut, mnh = extractGeom(mns, mnt, gdf, meta)
    incline_or, incline, plat = makeMasques(pente, aspect, masque_bat)
    toiture = incline | plat
    utile = eroderToit(masque_bat, toiture,
                       int(round(config.RECUL_M / meta["resolution"])))
    if temps is not None: temps["geometrie"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    if mns_large.shape != mns.shape:
        m = (mns_large.shape[0] - mns.shape[0]) // 2
        toiture_large = np.zeros(mns_large.shape, np.bool_)
        toiture_large[m:m + toiture.shape[0], m:m + toiture.shape[1]] = toiture
    else:
        toiture_large = toiture
    horizon = compHZ(mns_large, toiture_large, meta["resolution"], config.N_DIRECTIONS,
                     0.0, config.DIST_MAX_M, config.CAP, config.PAS_RAYON_DIV)

    hz_loin = hzLoin(relief, meta, mns, toiture)
    if hz_loin is not None:
        horizon = np.maximum(horizon, hz_loin)
    if temps is not None: temps["horizon"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    lat, lon = centreWGS84(*nomCoord(mns_name))
    B, D, SAZ, SEL, profils = chargerTable(lat, lon)
    poses = posesBatiments(masque_bat, plat, pente, meta["resolution"], gdf,
                           tileBounds(mns_name))
    df  = irrPixels(masque_bat, pente, aspect, incline, incline_or, plat, utile,
                    meta["resolution"], B, D, SAZ, SEL, profils, horizon, lat, poses)
    if temps is not None: temps["irradiance"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    hauteur = hBat(mnh, masque_haut, 0.95)
    out = agregerBatiment(df, gdf, hauteur)
    if temps is not None: temps["agregation batiment"] = time.perf_counter() - t0

    return out


def runPipeline(echelle, nom_zone, code_dep=None, on_progress=None, on_log=print):
    """
    Traite la zone : dalles, calcul parallele, fusion, filtre, protections, ecriture du gpkg.
    Les dalles finies sont ecrites dans config.DIR_EN_COURS et effacees a la fin ; gardees si
    une dalle a echoue, un calcul relance reprend alors aux dalles manquantes.
    --------
    @param[in] echelle, nom_zone, code_dep : definition de la zone (voir zone)
    @param[in] on_progress : callback (i, total) a chaque dalle finie (None = aucun)
    @param[in] on_log      : callback (message) pour les messages (defaut print)

    @return bilan : dict (fichier, total, echecs, moyennes_dalle, temps_globaux, batiments,
                    protections) ; None si zone introuvable, hors metropole ou sans batiment ;
                    bilan reduit (fichier None) si aucune dalle n'aboutit
    """
    t_total = time.time()
    t0 = time.time()
    polygone = zone(echelle, nom_zone, code_dep)
    if polygone is None:
        on_log("zone introuvable"); return None
    point = polygone.representative_point()
    if not enMetropole(point.y, point.x):
        on_log("zone hors metropole"); return None

    gdf_bati = batiments(polygone, on_log=on_log)
    if gdf_bati is None or gdf_bati.empty:
        on_log("aucun batiment"); return None
    t_bati = time.time() - t0

    nom_fichier = nomFichier(nom_zone, code_dep)
    zone_l93 = gpd.GeoDataFrame(geometry=[polygone], crs=4326).to_crs(2154)
    if echelle != "polygone":
        zone_l93.to_file(os.path.join(config.DIR_GEOJSON, f"{nom_fichier}.geojson"),
                         driver="GeoJSON")
    gpkg_path = os.path.join(config.OUT_DIR_PROCESSED, f"{nom_fichier}.gpkg")

    taches = []
    for nom_mnt, url_mnt, nom_mns, url_mns in listeTelechargement(dalles(polygone, on_log=on_log)):
        xmin, ymin, xmax, ymax = tileBounds(nom_mns)
        gdf_dalle = gdf_bati.cx[xmin:xmax, ymin:ymax]
        if not gdf_dalle.empty:
            taches.append((nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle))

    relief = None
    if taches:
        try:
            relief = mntRelief(taches[0][1], zone_l93.total_bounds, nom_fichier, on_log)
        except Exception as e:
            on_log(f"relief indisponible, horizon lointain ignore : {e}")
    taches = [t + (relief,) for t in taches]

    total = len(taches)
    dossier = dossierTravail(nom_fichier, polygone, on_log)
    chemins = [os.path.join(dossier, f"{t[2]}.pkl") for t in taches]
    a_faire = [t for t, c in zip(taches, chemins) if not os.path.exists(c)]
    faites = total - len(a_faire)
    temps_tous = []
    echecs     = []
    on_log(f"{total} dalles a traiter" + (f", {faites} deja calculees" if faites else ""))

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=config.N_COEURS,
                             initializer=numba.set_num_threads, initargs=(1,)) as ex:
        for i, (out, temps) in enumerate(ex.map(traiterTache, a_faire), 1):
            if out is None:
                echecs.append({"nom": temps["nom"], "erreur": temps.get("erreur", "")})
                on_log(f"echec dalle {temps['nom']}")
            else:
                chemin = os.path.join(dossier, f"{temps['nom']}.pkl")
                out.to_pickle(chemin + ".tmp")
                os.replace(chemin + ".tmp", chemin)
                temps_tous.append(temps)
            if on_progress is not None:
                on_progress(faites + i, total)
    t_traitement = time.time() - t0

    resultats = [r for r in (pd.read_pickle(c) for c in chemins if os.path.exists(c))
                 if not r.empty]
    if not resultats:
        on_log("aucun batiment traite")
        return {"fichier": None, "total": total, "echecs": echecs}

    t0 = time.time()
    g = pd.concat(resultats, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=2154)
    n_avant = len(g)
    g = mergeCleabs(g);  n_merge  = len(g)
    g = filtrer(g);      n_filtre = len(g)
    cols = (["cleabs"] + config.ATTRS_BATI + ["pose_plat"]
            + [c for grp in config.SORTIE_GARDEES for c in config.GROUPES_SORTIE[grp]]
            + ["geometry"])
    g = g[[c for c in cols if c in g.columns]]
    g, protections = marquerProtections(g, polygone, on_log=on_log)

    centres = [centreWGS84(*nomCoord(t[2])) for t in taches]
    metadonnees = {
        "parametres":    json.dumps(config.snapshot(), ensure_ascii=False),
        "poses":         json.dumps(description([la for la, _ in centres]), ensure_ascii=False),
        "meteo":         json.dumps(tablesMeteo(centres), ensure_ascii=False),
        "zone":          json.dumps({"echelle": echelle, "nom_zone": nom_zone, "code_dep": code_dep},
                                    ensure_ascii=False),
        "batiments":     json.dumps({"avant_merge_filtre": n_avant, "apres_merge": n_merge,
                                     "apres_filtre": n_filtre, "final": len(g)}, ensure_ascii=False),
        "dalles":        json.dumps({"total": total, "calculees": total - len(echecs),
                                     "echecs": echecs}, ensure_ascii=False),
        "protections":   json.dumps(protections, ensure_ascii=False),
        "date_creation": datetime.now().isoformat(timespec="seconds"),
    }
    g.to_file(gpkg_path, driver="GPKG", layer="batiments", dataset_metadata=metadonnees)
    if echecs:
        on_log(f"{len(echecs)} dalle(s) en echec : les dalles calculees sont gardees, "
               f"relancer la zone ne refera que les manquantes")
    else:
        shutil.rmtree(dossier, ignore_errors=True)
    t_ecriture = time.time() - t0

    def moyenne(cle):
        vals = [t[cle] for t in temps_tous if cle in t]
        return sum(vals) / len(vals) if vals else 0.0

    return {
        "fichier": f"{nom_fichier}.gpkg",
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
            "batiments":  t_bati,
            "traitement": t_traitement,
            "ecriture":   t_ecriture,
            "total":      time.time() - t_total,
        },
        "batiments": {
            "avant_merge_filtre": n_avant,
            "apres_merge":        n_merge,
            "apres_filtre":       n_filtre,
            "final":              len(g),
        },
        "protections": protections,
    }


_dl = None


def telechargeur():
    """
    Pool de deux fils du processus, reutilise d'une dalle a l'autre.
    --------
    @return ThreadPoolExecutor
    """
    global _dl
    if _dl is None:
        _dl = ThreadPoolExecutor(2)
    return _dl


def traiterTache(tache):
    """
    Traite une dalle dans un processus : telecharge MNS et MNT, calcule, supprime les fichiers.
    --------
    @param[in] tache : (nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle, relief)

    @return out, temps : GeoDataFrame de la dalle (None si echec), dict des durees par etape
    """
    temps = {}
    nom_mnt, url_mnt, nom_mns, url_mns, gdf_dalle, relief = tache
    temps["nom"] = nom_mns
    mnt_path = mns_path = None
    try:
        t0 = time.perf_counter()
        dl = telechargeur()
        f_mnt = dl.submit(telechargerFichier, urlWms(url_mnt, res_m=config.RES_MNT_M),
                          nom_mnt, config.OUT_DIR_RAW)
        f_mns = dl.submit(telechargerFichier, urlWms(url_mns, marge_m=config.DIST_MAX_M),
                          nom_mns, config.OUT_DIR_RAW)
        mnt_path, mns_path = f_mnt.result(), f_mns.result()
        temps["telechargement"] = time.perf_counter() - t0
        return traiterDalle(mns_path, mnt_path, gdf_dalle, relief, temps=temps), temps

    except Exception as e:
        temps["erreur"] = str(e)
        return None, temps
    finally:
        for pth in (mns_path, mnt_path):
            if pth and os.path.exists(pth):
                os.remove(pth)


def runPipelineDecoupe(echelle, nom_zone, on_progress=None, on_log=print):
    """
    Calcule une region ou la France departement par departement ; un echec n'arrete pas les
    suivants, les departements dont le gpkg existe sont sautes.
    --------
    @param[in] echelle  : 'region' ou 'nationale'
    @param[in] nom_zone : nom de la region (ignore pour 'nationale')
    @param[in] on_progress, on_log : memes callbacks que runPipeline

    @return bilan agrege (memes cles que runPipeline) ; None si zone introuvable
    """
    noms = listeDepartements(echelle, nom_zone)
    if not noms:
        on_log("zone introuvable"); return None

    t_total = time.time()
    total_dalles, n_avant, n_merge, n_final = 0, 0, 0, 0
    t_bati_tot, t_traitement_tot, t_ecriture_tot = 0.0, 0.0, 0.0
    echecs, fichiers, deja_faits = [], [], []

    for i, nom in enumerate(noms, 1):
        gpkg_path = os.path.join(config.OUT_DIR_PROCESSED, f"{nomFichier(nom)}.gpkg")
        if os.path.exists(gpkg_path):
            on_log(f"=== departement {nom} ({i}/{len(noms)}) : deja fait, ignore ===")
            deja_faits.append(nom)
            continue

        on_log(f"=== departement {nom} ({i}/{len(noms)}) ===")
        bilan, erreur = None, None
        for essai in range(1, config.N_ESSAIS_DEPARTEMENT + 1):
            try:
                bilan = runPipeline("departement", nom, None, on_progress=on_progress, on_log=on_log)
                erreur = None
                break
            except Exception as e:
                erreur = str(e)
                on_log(f"[ERREUR] departement {nom}, essai {essai}/{config.N_ESSAIS_DEPARTEMENT} : {e}")
                if essai < config.N_ESSAIS_DEPARTEMENT:
                    time.sleep(config.PAUSE_DEPARTEMENT)

        if erreur is not None:
            echecs.append({"nom": nom, "erreur": erreur})
            continue
        if bilan is None:
            on_log(f"departement {nom} : zone introuvable ou aucun batiment")
            continue

        total_dalles += bilan.get("total", 0)
        echecs += bilan.get("echecs", [])
        bat = bilan.get("batiments", {})
        n_avant  += bat.get("avant_merge_filtre", 0)
        n_merge  += bat.get("apres_merge", 0)
        n_final  += bat.get("final", 0)
        glob = bilan.get("temps_globaux", {})
        t_bati_tot       += glob.get("batiments", 0.0)
        t_traitement_tot += glob.get("traitement", 0.0)
        t_ecriture_tot   += glob.get("ecriture", 0.0)
        moy = bilan.get("moyennes_dalle", {})
        if moy:
            on_log("   temps moyen/dalle (s) : " + ", ".join(f"{k}={v:.2f}" for k, v in moy.items()))
        if bilan.get("fichier"):
            fichiers.append(bilan["fichier"])

    return {
        "fichier": (f"{len(fichiers)} fichier(s) calcules + {len(deja_faits)} deja fait(s), "
                    f"dans {config.OUT_DIR_PROCESSED}"),
        "total": total_dalles,
        "echecs": echecs,
        "batiments": {"avant_merge_filtre": n_avant, "apres_merge": n_merge, "final": n_final},
        "temps_globaux": {
            "batiments": t_bati_tot, "traitement": t_traitement_tot,
            "ecriture": t_ecriture_tot, "total": time.time() - t_total,
        },
    }
