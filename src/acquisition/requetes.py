import time
import requests
import geopandas as gpd

from src import config


def lireWFS(params):
    """
    Requete WFS GetFeature, renvoie un GeoDataFrame. Reessaie config.N_ESSAIS_WFS fois avant d'echouer.
    --------
    @param[in] params : parametres de la requete WFS

    @return GeoDataFrame du resultat (leve RuntimeError apres tous les echecs)
    """
    n = config.N_ESSAIS_WFS
    err = ""
    for _ in range(n):
        try:
            txt = requests.get(config.WFS, params=params, timeout=120).text
            if "FeatureCollection" in txt[:300]:
                return gpd.read_file(txt)
            err = txt[:200]
        except requests.RequestException as e:
            err = str(e)
        time.sleep(config.PAUSE_WFS)
    raise RuntimeError(f"WFS a echoue {n}x : {err}")


def compter(params):
    """
    Nombre d'entites correspondant a la requete WFS (numberMatched). Reessaie config.N_ESSAIS_WFS fois.
    --------
    @param[in] params : parametres de la requete WFS

    @return nombre d'entites (leve RuntimeError apres tous les echecs)
    """
    n = config.N_ESSAIS_WFS
    err = ""
    for _ in range(n):
        try:
            r = requests.get(config.WFS, {**params, "COUNT": 1}, timeout=120)
            j = r.json()
            if "numberMatched" in j:
                return j["numberMatched"]
            err = r.text[:200]
        except Exception as e:
            err = str(e)
        time.sleep(config.PAUSE_WFS)
    raise RuntimeError(f"WFS (comptage) a echoue {n}x : {err}")

