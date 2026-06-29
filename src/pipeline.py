import os
import time

from src.tuile.raster import chargerDalle
from src.tuile.donnees_dalle import nomCoord, centreWGS84
from src.geometrie.extract_geom import extractGeom, makeMasques
from src.geometrie.horizon import compHZ
from src.irradiance.meteo.grille_fct import chargerTable
from src.irradiance.irr_calcul import irrPixels
from src.agregation.agregation import agregerBatiment
from src.debug import debug_pipeline as debug
from src.agregation.select import hBat


def traiterDalle(mns_path, mnt_path, gdf, debug_dir=None, temps=None):
    """
    Traite une dalle : geometrie, masques, horizon, irradiance, agregation par batiment.
    --------
    @param[in] mns_path, mnt_path : chemins des rasters MNS / MNT IGN
    @param[in] gdf       : GeoDataFrame des batiments de la dalle (Lambert 93)
    @param[in] debug_dir : si fourni, exporte les rasters intermediaires
    @param[in] temps     : dict optionnel rempli avec la duree de chaque etape

    @return out : GeoDataFrame, 1 ligne par batiment
    """

    mns_name = os.path.basename(mns_path)

    # geometrie
    t0 = time.perf_counter()
    mns, mnt, meta = chargerDalle(mns_path, mnt_path)
    pente, aspect, masque_bat, mnh = extractGeom(mns, mnt, gdf, meta)
    incline_or, incline, plat = makeMasques(pente, aspect, masque_bat)
    toiture = incline | plat
    if temps is not None: temps["geometrie"] = time.perf_counter() - t0



    # horizon
    t0 = time.perf_counter()
    horizon = compHZ(mns, toiture, meta["resolution"])
    if temps is not None: temps["horizon"] = time.perf_counter() - t0


    # irradiance
    t0 = time.perf_counter()
    lat, lon = centreWGS84(*nomCoord(mns_name))
    B, D, SAZ, SEL = chargerTable(lat, lon)
    df  = irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
                    meta["resolution"], B, D, SAZ, SEL, horizon)
    if temps is not None: temps["irradiance"] = time.perf_counter() - t0


    # agregation par batiment
    t0 = time.perf_counter()
    hauteur = hBat (mnh, masque_bat, 0.95)
    out = agregerBatiment(df, gdf, hauteur)
    if temps is not None: temps["agregation batiment"] = time.perf_counter() - t0




    # export debug optionnel
    if debug_dir is not None:
        debug.exportRasters({
            "pente": pente, "aspect": aspect, "mnh": mnh,
            "incline":    incline.astype("int32"),
            "incline_or": incline_or.astype("int32"),
            "plat":       plat.astype("int32"),
        }, meta, debug_dir)
        debug.exportHorizon(horizon, toiture, meta, os.path.join(debug_dir, "horizon"))

    return out
