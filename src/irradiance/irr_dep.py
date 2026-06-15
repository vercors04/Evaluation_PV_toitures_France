import os
import time
import numpy as np

from irr_fct import *


# --- Zone a couvrir (bbox WGS84) ---
LAT_MIN, LAT_MAX = 46.30, 46.60
LON_MIN, LON_MAX = 0.05,  0.40

PAUSE = 1.0             # secondes entre deux requetes


def grilleCellules():
    """
    Grille des centres de cellules couvrant la bbox.
    --------
    @return liste de tuples (lat, lon), multiples de PAS
    """
    lats = np.round(np.arange(LAT_MIN, LAT_MAX + PAS / 2, PAS), 2)
    lons = np.round(np.arange(LON_MIN, LON_MAX + PAS / 2, PAS), 2)
    return [(la, lo) for la in lats for lo in lons]


def construireCellule(lat, lon):
    """
    Construit et sauvegarde la table d'une cellule (methode M1 :
    series horaires PVGIS 2005-2023 + transposition pas-a-pas).
    --------
    @param[in] lat, lon : centre de la cellule, en degres WGS84
    """
    df = telecharger(lat, lon)
    B, D, SAZ, SEL = transpAgr(df["poa_direct"], df["poa_sky_diffuse"], lat, lon)
    np.savez_compressed(cheminTable(lat, lon), B=B, D=D, SAZ=SAZ, SEL=SEL,
                        alphas=ALPHAS, betas=BETAS, lat=lat, lon=lon,
                        source="PVGIS-SARAH3 2005-2023, Perez")


def main():
    os.makedirs(DOSSIER, exist_ok=True)
    pts = grilleCellules()
    print(f"{len(pts)} cellules a construire dans {DOSSIER}/ "
          f"(deja faites : sautees, relance possible a tout moment)")
    ratees = []
    for k, (lat, lon) in enumerate(pts, 1):
        if os.path.exists(cheminTable(lat, lon)):
            continue
        try:
            t0 = time.time()
            construireCellule(lat, lon)
            print(f"[{k}/{len(pts)}] {lat:.2f}, {lon:.2f}  OK  "
                  f"({time.time() - t0:.0f} s)")
        except Exception as e:
            print(f"[{k}/{len(pts)}] {lat:.2f}, {lon:.2f}  ECHEC : {e}")
            ratees.append((lat, lon))
        time.sleep(PAUSE)
    print(f"Termine. {len(ratees)} echec(s) : {ratees}")
    print("Relancer le script pour retenter les echecs.")


if __name__ == "__main__":
    main()
