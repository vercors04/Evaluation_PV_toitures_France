import os
import time
import numpy as np
from shapely.geometry import box 

from shapely.prepared import prep


from src.irradiance.meteo.grille_fct import telecharger, transpAgr, cheminTable
from src.config import (PAS, ALPHAS, BETAS, DOSSIER, PAUSE)



def grilleCellules(polygone):
    """
    Centres des cellules meteo (multiples de PAS) dont la cellule intersecte le polygone.
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)

    @return liste de tuples (lat, lon), alignes sur la meme grille que chargerTable
    """
    minx, miny, maxx, maxy = polygone.bounds
    snap = lambda v: round(round(v / PAS) * PAS, 2)
    lats = np.round(np.arange(snap(miny), snap(maxy) + PAS/2, PAS), 2)
    lons = np.round(np.arange(snap(minx), snap(maxx) + PAS/2, PAS), 2)
    dans = prep(polygone)
    h = PAS / 2
    return [(la, lo) for la in lats for lo in lons
            if dans.intersects(box(lo - h, la - h, lo + h, la + h))]



def construireCellule(lat, lon):
    """
    Construit et sauvegarde la table d'une cellule
    --------
    @param[in] lat, lon : centre de la cellule, en degres WGS84
    """
    df = telecharger(lat, lon)
    B, D, SAZ, SEL = transpAgr(df["poa_direct"], df["poa_sky_diffuse"], lat, lon)
    chemin = cheminTable(lat, lon)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)          # cree le sous-dossier de la cellule
    np.savez_compressed(chemin, B=B.astype(np.float16), D=D.astype(np.float16),
                        SAZ=SAZ, SEL=SEL,
                        alphas=ALPHAS, betas=BETAS, lat=lat, lon=lon,
                        source="PVGIS-SARAH3 2005-2023, Perez")


def construire(polygone):
    """
    Construit en serie les tables meteo de toutes les cellules de la zone.
    Saute les cellules deja faites (reprise possible) et liste les echecs a la fin.
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)
    """
    pts = grilleCellules(polygone)
    print(f"{len(pts)} cellules a construire dans {DOSSIER}/ (reprise possible)")
    ratees = []
    for k, (lat, lon) in enumerate(pts, 1):
        if os.path.exists(cheminTable(lat, lon)):
            continue
        try:
            t0 = time.time(); construireCellule(lat, lon)
            print(f"[{k}/{len(pts)}] {lat:.2f}, {lon:.2f}  OK  ({time.time()-t0:.0f} s)")
        except Exception as e:
            print(f"[{k}/{len(pts)}] {lat:.2f}, {lon:.2f}  ECHEC : {e}"); ratees.append((lat, lon))
        time.sleep(PAUSE)
    print(f"Termine. {len(ratees)} echec(s) : {ratees}")
