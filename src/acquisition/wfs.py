import time
import requests
import geopandas as gpd

WFS = "https://data.geopf.fr/wfs/ows"


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
