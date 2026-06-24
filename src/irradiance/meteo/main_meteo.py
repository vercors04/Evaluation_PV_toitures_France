import os

from src.irradiance.meteo.grille_calculs import construire
from src.acquisition.zone import zone
from src.config import DOSSIER

def main():
    os.makedirs(DOSSIER, exist_ok=True)

    print("Choix de l'échelle territoriale:")
    print("0 : Adresse")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    print("4 : France")
    choix=input("Choisissez l'échelle (0,1,2, 3 ou 4) :").strip()

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

    elif choix == "4":
        nom_zone="France"
        echelle="nationale"

    else:
        print('Choisissez entre 0,1,2, 3 et 4.')
        return None

    polygone = zone(echelle, nom_zone.replace("'", "''"), code_dep)
    if polygone is None:
        print("zone introuvable"); return
    construire(polygone)

if __name__ == "__main__":
    main()
