import os
import time

from src.tuile.raster import chargerDalle
from src.tuile.donnees_dalle import nomCoord, centreWGS84
from src.geometrie.extract_geom import extractGeom, makeMasques
from src.geometrie.horizon import compHZ
from src.irradiance.meteo.irr_fct import chargerTable
from src.irradiance.irr_calcul import irrPixels
from src.agregation.agregation import agregerBatiment
from src.debug import debug_pipeline as debug
from src.agregation.select import hBat


def traiterDalle(mns_path, mnt_path, gdf, debug_dir=None):
    """
    Traite une dalle : geometrie -> masques -> horizon -> irradiance -> agregation par batiment.
    --------
    @param[in] mns_path, mnt_path : chemins des rasters MNS / MNT IGN
    @param[in] gdf                : GeoDataFrame des batiments de la dalle (Lambert 93)
    @param[in] debug_dir          : si fourni, exporte les rasters de debug

    @return out : GeoDataFrame, 1 ligne par batiment
    """

    mns_name = os.path.basename(mns_path)

    # ------ Lecture des raster, chargements des masques et donnees ------
    t0 = time.time()
    mns, mnt, meta = chargerDalle(mns_path, mnt_path)
    pente, aspect, masque_bat, mnh = extractGeom(mns, mnt, gdf, meta)
    incline_or, incline, plat = makeMasques(pente, aspect, masque_bat)
    toiture = incline | plat
    print(f"Geometrie  : {time.time()-t0:.1f}s")



    # ------ horizon ------
    t0 = time.time()
    horizon = compHZ(mns, toiture, meta["resolution"])
    print(f"Horizon    : {time.time()-t0:.1f}s")



    # ------ irradiance par pixel ------
    t0 = time.time()
    lat, lon = centreWGS84(*nomCoord(mns_name))
    B, D, SAZ, SEL = chargerTable(lat, lon)
    df  = irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
                    meta["resolution"], B, D, SAZ, SEL, horizon)
    


    # ------ agregation par bat + ecriture ------
    hauteur = hBat (mnh, masque_bat, 0.95)
    out = agregerBatiment(df, gdf, hauteur)
    print(f"Irradiance : {time.time()-t0:.1f}s ")




    # ------ debug pour visualisation ------
    if debug_dir is not None:
        debug.exportRasters({
            "pente": pente, "aspect": aspect, "mnh": mnh,
            "incline":    incline.astype("int32"),
            "incline_or": incline_or.astype("int32"),
            "plat":       plat.astype("int32"),
        }, meta, debug_dir)
        debug.exportHorizon(horizon, toiture, meta, os.path.join(debug_dir, "horizon"))

    return out
