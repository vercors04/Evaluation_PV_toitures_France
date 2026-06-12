import os
import time
import numpy as np

from irr_fct import *   


# --- Zone a couvrir (bbox WGS84) ---
LAT_MIN, LAT_MAX = 46.30, 46.60
LON_MIN, LON_MAX = 0.05,  0.40
PAS = 0.05 #pas grille meteo

DOSSIER = "data/tables"      # un .npz par cellule, ecrit ici
PAUSE = 1.0             # secondes entre deux requetes 


def cheminTable(lat, lon):
    """
    Chemin du fichier table d'une cellule.
    --------
    @param[in] lat, lon : centre de cellule, multiples de PAS (degres WGS84)

    @return chemin du .npz (ex: tables/table_46.55_0.35.npz)
    """
    return os.path.join(DOSSIER, f"table_{lat:.2f}_{lon:.2f}.npz")


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
    B, D = transpAgr(df["poa_direct"], df["poa_sky_diffuse"], lat, lon)
    np.savez_compressed(cheminTable(lat, lon), B=B, D=D,
                        alphas=ALPHAS, betas=BETAS, lat=lat, lon=lon,
                        source="PVGIS-SARAH3 2005-2023, Perez")

cache = {}
def chargerTable(lat, lon):
    """
    Charge la table de la cellule contenant un point quelconque
    (ex: le centre d'une tuile LiDAR). C'est LE point d'entree pour
    la pipeline tuile : centreWGS84(...) -> chargerTable(...) -> B, D.
    --------
    @param[in] lat, lon : coordonnees quelconques, en degres WGS84

    @return B, D : tableaux (n_alphas, n_betas, 12, 24) en W/m2
    """
    la = round(round(lat / PAS) * PAS, 2)
    lo = round(round(lon / PAS) * PAS, 2)

    if (la, lo) not in cache:
        d = np.load(cheminTable(la, lo))
        cache[(la, lo)] = (d["B"], d["D"])

    return cache[(la, lo)]

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