import os
import time
import numpy as np
from shapely.geometry import box 

from shapely.prepared import prep


from src.irradiance.meteo.grille_fct import telecharger, transpAgr, cheminTable
from src import config



def grilleCellules(polygone):
    """
    Centres des cellules meteo (multiples de PAS) dont la cellule intersecte le polygone.
    --------
    @param[in] polygone : emprise de la zone (shapely, WGS84)

    @return liste de tuples (lat, lon), alignes sur la meme grille que chargerTable
    """
    minx, miny, maxx, maxy = polygone.bounds
    snap = lambda v: round(round(v / config.PAS) * config.PAS, 2)
    lats = np.round(np.arange(snap(miny), snap(maxy) + config.PAS/2, config.PAS), 2)
    lons = np.round(np.arange(snap(minx), snap(maxx) + config.PAS/2, config.PAS), 2)
    dans = prep(polygone)
    h = config.PAS / 2
    return [(la, lo) for la in lats for lo in lons
            if dans.intersects(box(lo - h, la - h, lo + h, la + h))]



def construireCellule(lat, lon):
    """
    Construit et sauvegarde la table d'une cellule
    --------
    @param[in] lat, lon : centre de la cellule, en degres WGS84
    """
    df = telecharger(lat, lon)
    B, D, SAZ, SEL = transpAgr(df["poa_direct"], df["poa_sky_diffuse"], lat, lon)
    chemin = cheminTable(lat, lon)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)          # cree le sous-dossier de la cellule
    np.savez_compressed(chemin, B=B.astype(np.float16), D=D.astype(np.float16),
                        SAZ=SAZ, SEL=SEL,
                        alphas=config.ALPHAS, betas=config.BETAS, lat=lat, lon=lon,
                        source="PVGIS-SARAH3 2005-2023, Perez")

