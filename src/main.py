from extract_bounds.commune import commune
from extract_bounds.departement import departement
from extract_bounds.region import region
from util.telechargement import telecharger_puis_supprimer
from util.telechargement import liste_telechargement


def main():

    """
    Affiche l'interface console interactive permettant à l'utilisateur de choisir l'échelle d'extraction et déclenche la chaîne de traitement.
    ---------------------------------------------------------------------------------------
    @param[in]  Aucun (les paramètres sont saisis dynamiquement via input() par l'utilisateur).

    @param[out] None : Fonction d'orchestration (Point d'entrée du script principal).
    """

    print("Choix de l'échelle territoriale:")
    print("1 : Commune ou Ville")
    print("2 : Département")
    print("3 : Région")
    choix=input("Choisissez l'échelle (1,2 ou 3) :").strip()

    dictionnaire_resultats={}

    if choix == "1":
        nom_commune=input("Entrez une ville ou une commune : ").strip().replace("'", "''")
        num_departement = input("Entrez le numéro de département : ").strip()
        dictionnaire_resultats = commune(nom_commune, num_departement)

    elif choix == "2":
        depart = input("Entrez un département ou son numéro : ").strip().replace("'", "''")
        dictionnaire_resultats = departement(depart)
    
    elif choix == "3":
        nom_region=input("Entrez le nom d'une région: ").strip().replace("'", "''")
        dictionnaire_resultats = region(nom_region)
    else:
        print('Choisissez entre 1,2 et 3.')
        return None
    
    if dictionnaire_resultats:
        liste_dalles = liste_telechargement(dictionnaire_resultats)
        
        for nom_mnt, url_mnt, nom_mns, url_mns in liste_dalles:
            telecharger_puis_supprimer(nom_mnt, url_mnt, nom_mns, url_mns)
            
        print('Test du téléchargement terminé')


if __name__ == "__main__":
    main()