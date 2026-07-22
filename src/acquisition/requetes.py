import time
import requests
import geopandas as gpd

from src import config
_session = requests.Session()

def lireWFS(params):
    """
    Requete WFS GetFeature, renvoie un GeoDataFrame. Reessaie config.N_ESSAIS_WFS fois avant d'echouer.
    --------
    @param[in] params : parametres de la requete WFS

    @return GeoDataFrame du resultat (leve RuntimeError apres tous les echecs)
    """
    n, pause = config.N_ESSAIS_WFS, config.PAUSE_WFS
    err = ""
    for essai in range(1, n + 1):
        try:
            txt = _session.get(config.WFS, params=params, timeout=120).text
            if "FeatureCollection" in txt[:300]:
                return gpd.read_file(txt)
            err = txt[:200]
        except Exception as e:
            err = str(e)
        if essai < n:
            time.sleep(pause * essai)
    raise RuntimeError(f"WFS a echoue {n}x : {err}")


def compter(params):
    """
    Nombre d'entites correspondant a la requete WFS (numberMatched). Reessaie config.N_ESSAIS_WFS fois.
    --------
    @param[in] params : parametres de la requete WFS

    @return nombre d'entites (leve RuntimeError apres tous les echecs)
    """
    n, pause = config.N_ESSAIS_WFS, config.PAUSE_WFS
    err = ""
    for essai in range(1, n + 1):
        try:
            r = _session.get(config.WFS, params={**params, "COUNT": 1}, timeout=120)
            j = r.json()
            if "numberMatched" in j:
                return j["numberMatched"]
            err = r.text[:200]
        except Exception as e:
            err = str(e)
        if essai < n:
            time.sleep(pause * essai)
    raise RuntimeError(f"WFS (comptage) a echoue {n}x : {err}")

