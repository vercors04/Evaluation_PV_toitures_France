import os

from src.pipeline import runPipeline
from src.debug.affichage_terminal import afficherBilan, progressTerminal
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




if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()





