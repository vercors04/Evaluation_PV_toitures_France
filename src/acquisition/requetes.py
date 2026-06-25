import time
import requests
import geopandas as gpd

from src.config import WFS


def lireWFS(params, n=4):
    """
    Lit une couche du WFS IGN, en retentant si le serveur renvoie une erreur transitoire.
    --------
    @param[in] params : parametres de la requete WFS (dict)
    @param[in] n      : nombre de tentatives avant abandon

    @return GeoDataFrame de la reponse ; leve RuntimeError apres n echecs
    """
    for _ in range(n):
        txt = requests.get(WFS, params=params, timeout=120).text
        if "ExceptionReport" not in txt[:500]:          # reponse valide (pas une page d'erreur)
            return gpd.read_file(txt)
        time.sleep(2)                                   # backend capricieux -> on retente
    raise RuntimeError(f"WFS a echoue {n}x : {txt[:200]}")


def compter(params, n=4):
    """
    Nombre total de features correspondant a une requete WFS (numberMatched),
    sans rapatrier les donnees (COUNT=1). Retente si le serveur renvoie une erreur transitoire.
    --------
    @param[in] params : parametres de la requete WFS (dict) ; COUNT est force a 1
    @param[in] essais : nombre de tentatives avant abandon

    @return numberMatched : nombre total de features (int) ; leve RuntimeError apres `essais` echecs
    """
    for _ in range(n):
        r = requests.get(WFS, {**params, "COUNT": 1}, timeout=120)
        if "ExceptionReport" not in r.text[:500]:
            return r.json()["numberMatched"]
        time.sleep(2)
    raise RuntimeError("WFS (comptage) a echoue")

