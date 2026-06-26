import time
import requests
import geopandas as gpd

from src.config import WFS


def lireWFS(params, n=8):
    err = ""
    for _ in range(n):
        try:
            txt = requests.get(WFS, params=params, timeout=120).text
            if "FeatureCollection" in txt[:300]:          
                return gpd.read_file(txt)
            err = txt[:200]                              
        except requests.RequestException as e:
            err = str(e)
        time.sleep(2)
    raise RuntimeError(f"WFS a echoue {n}x : {err}")


def compter(params, n=8):
    err = ""
    for _ in range(n):
        try:
            r = requests.get(WFS, {**params, "COUNT": 1}, timeout=120)
            j = r.json()
            if "numberMatched" in j:
                return j["numberMatched"]
            err = r.text[:200]
        except Exception as e:
            err = str(e)
        time.sleep(2)
    raise RuntimeError(f"WFS (comptage) a echoue {n}x : {err}")

