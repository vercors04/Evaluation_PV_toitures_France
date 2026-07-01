import numpy as np
from rasterio.features import rasterize
from scipy.ndimage import binary_erosion

from src import config


def extractGeom(mns, mnt, gdf, meta):
    """
    Geometrie des toitures depuis MNS, MNT et BD TOPO (sans seuils de selection).
    Tampon config.BUFFER autour des batiments, hauteur min config.MNH_MIN.
    --------
    @param[in] mns, mnt : tableaux 2D de la dalle (NaN hors donnees)
    @param[in] gdf      : GeoDataFrame BD TOPO filtre (index 0..n-1)
    @param[in] meta     : profil rasterio (cles "transform" et "resolution")

    @return pente, aspect : 2D float (deg), NaN hors pixels de toit valides
    @return masque_bat    : 2D int, index gdf + 1 du batiment (0 hors toit valide)
    @return mnh           : 2D float, hauteur au-dessus du sol (m)
    """
    mnh = mns - mnt

    masque_bat = rasterize(
        zip(gdf.geometry.buffer(config.BUFFER), gdf.index + 1),    # 0 = fond
        out_shape=mns.shape, transform=meta["transform"], fill=0, dtype="int32")

    pts_ok = (masque_bat > 0) & (mnh >= config.MNH_MIN) & np.isfinite(mns) & np.isfinite(mnt)

    dz_dligne, dz_dcol = np.gradient(mns, meta["resolution"])
    pente  = np.degrees(np.arctan(np.hypot(dz_dcol, dz_dligne)))
    aspect = np.degrees(np.arctan2(-dz_dcol, dz_dligne)) % 360

    # erosion : retire les bords de toit
    valid = binary_erosion(pts_ok, np.ones((3, 3), dtype=bool))

    masque_bat = np.where(valid, masque_bat, 0).astype("int32")   
    pente[~valid]  = np.nan
    aspect[~valid] = np.nan
    return pente, aspect, masque_bat, mnh


def makeMasques(pente, aspect, masque_bat):
    """
    Applique les seuils de selection et renvoie les masques booleens de toiture.
    Separe de extractGeom pour faire varier les seuils sans tout recalculer.
    --------
    @param[in] pente, aspect : 2D float (deg), NaN hors toit valide
    @param[in] masque_bat    : 2D int, index gdf + 1 (0 hors toit valide)

    @return incline_or : 2D bool, incline et oriente (azimut config.AZ_MIN..AZ_MAX)
    @return incline    : 2D bool, incline toutes orientations (config.PENTE_PLAT..PENTE_MAX)
    @return plat       : 2D bool, plat (< config.PENTE_PLAT)
    """
    valid      = masque_bat > 0
    incline    = valid & (pente >= config.PENTE_PLAT) & (pente <= config.PENTE_MAX)
    incline_or = incline & (aspect >= config.AZ_MIN) & (aspect <= config.AZ_MAX)
    plat       = valid & (pente < config.PENTE_PLAT)
    return incline_or, incline, plat
