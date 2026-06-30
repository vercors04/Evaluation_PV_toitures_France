"""
    python -m src.irradiance.meteo.main_meteo_parallele
"""
import os
import time
from concurrent.futures import ProcessPoolExecutor

from src.acquisition.zone import zone
from src.irradiance.meteo.grille_calculs import grilleCellules, construireCellule
from src.irradiance.meteo.grille_fct import cheminTable
from src.config import DOSSIER, N_COEURS



def _faire(cellule):
    """Construit une cellule si absente. Fonction au niveau module = picklable par les processus."""
    lat, lon = cellule
    if os.path.exists(cheminTable(lat, lon)):
        return (lat, lon, "deja fait")
    try:
        construireCellule(lat, lon)
        return (lat, lon, "OK")
    except Exception as e:
        return (lat, lon, f"ECHEC : {e}")


def main():
    os.makedirs(DOSSIER, exist_ok=True)

    print("Choix de l'echelle territoriale:")
    print("0 : Adresse\n1 : Commune\n2 : Departement\n3 : Region\n4 : France")
    choix = input("Choisissez l'echelle (0-4) : ").strip()

    code_dep = None
    if choix == "0":
        echelle, nom_zone = "adresse", input("Entrez une adresse : ").strip()
    elif choix == "1":
        echelle, nom_zone = "commune", input("Entrez une commune : ").strip()
        code_dep = input("Entrez le numero de departement : ").strip()
    elif choix == "2":
        echelle, nom_zone = "departement", input("Entrez un departement (nom ou numero) : ").strip()
    elif choix == "3":
        echelle, nom_zone = "region", input("Entrez le nom d'une region : ").strip()
    elif choix == "4":
        echelle, nom_zone = "nationale", "France"
    else:
        print("Choisissez entre 0 et 4."); return

    polygone = zone(echelle, nom_zone.replace("'", "''"), code_dep)
    if polygone is None:
        print("zone introuvable"); return

    pts = grilleCellules(polygone)
    print(f"{len(pts)} cellules a construire dans {DOSSIER}/ sur {N_COEURS} coeurs (reprise possible)")
    ratees, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=N_COEURS) as ex:
        for k, (lat, lon, etat) in enumerate(ex.map(_faire, pts), 1):
            print(f"[{k}/{len(pts)}] {lat:.2f}, {lon:.2f}  {etat}")
            if etat.startswith("ECHEC"):
                ratees.append((lat, lon))
    print(f"Termine en {time.time() - t0:.0f}s. {len(ratees)} echec(s) : {ratees}")


if __name__ == "__main__":
    main()
