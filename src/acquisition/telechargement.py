import os, time, requests


def telecharger_fichier(url, nom_fichier, dossier_dest='data/raw/TEST', n_essais=4, pause=3):
    """
    Télécharge un fichier distant en continu (stream) et le sauvegarde localement.
    ---------------------------------------------------------------------------------------
    @param[in]  url          : Lien HTTP(S) de téléchargement du fichier.
    @param[in]  dossier_dest : Chemin du dossier cible (créé automatiquement si inexistant).

    @param[out] chemin       : Chaîne de caractères (str), chemin absolu ou relatif du fichier téléchargé.
    """
    os.makedirs(dossier_dest, exist_ok=True)
    chemin = os.path.join(dossier_dest, nom_fichier)

    for essai in range(1, n_essais + 1):
        try:
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            with open(chemin, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"{nom_fichier} telecharge")
            return chemin  #si tout ok un seul essai
        

        except requests.RequestException as e:
            print(f"  {nom_fichier} : essai {essai}/{n_essais} echoue ({e})")
            if essai < n_essais:
                time.sleep(pause * essai)  
                
    raise RuntimeError(f"echec apres {n_essais} essais : {nom_fichier}")



def liste_telechargement(dictionnaire_resultats):

    """
    Apparie les dalles MNT et MNS d'une même zone en se basant sur leur identifiant pour préparer le téléchargement.
    ---------------------------------------------------------------------------------------
    @param[in]  dictionnaire_resultats : Dictionnaire contenant les métadonnées géographiques :
                                         {
                                           'MNT' : GeoDataFrame des dalles MNT,
                                           'MNS' : GeoDataFrame des dalles MNS
                                         }

    @param[out] liste_paires           : Liste de tuples, un par paire de dalles appariées :
                                         [
                                           (nom_mnt, url_mnt, nom_mns, url_mns),
                                           ...
                                         ]
                                         Retourne une liste vide si des données sont manquantes.
    """

    if 'MNT' not in dictionnaire_resultats or 'MNS' not in dictionnaire_resultats:
        print('données MNS ou MNT manquantes')
        return[]
    
    dico_mnt={}
    for index,ligne in dictionnaire_resultats['MNT'].iterrows():
        id_dalle=ligne['name'].replace('MNT','')
        dico_mnt[id_dalle]=(ligne['url'],f"{ligne['name']}.tif")

    dico_mns={}
    for index,ligne in dictionnaire_resultats['MNS'].iterrows():
        id_dalle=ligne['name'].replace('MNS','')
        dico_mns[id_dalle]=(ligne['url'],f"{ligne['name']}.tif")
    
    liste_paires=[]
    for id_dalle, (url_mnt,nom_mnt) in dico_mnt.items():
        if id_dalle in dico_mns:
            url_mns, nom_mns = dico_mns[id_dalle]
            liste_paires.append((nom_mnt, url_mnt, nom_mns, url_mns))
    
    print(f"{len(liste_paires)} paires trouvées")
    return liste_paires

