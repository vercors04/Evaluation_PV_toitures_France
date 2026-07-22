import math

import numpy as np
from numba import njit, prange
from rasterio.features import rasterize

from src import config


@njit(parallel=True, cache=True)
def gradMasque(mns, pts_ok, masque_bat, res):
    """
    Pente et aspect du MNS par differences finies, decentrees au bord et limitees
    aux voisins du meme batiment (masque_bat == k). Remplace l'erosion (numba).
    --------
    @param[in] mns        : 2D float de la dalle (NaN hors donnees)
    @param[in] pts_ok     : 2D bool, pixels de toit valides
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 = fond)
    @param[in] res        : taille du pixel (m)

    @return pente, aspect : 2D float (deg), NaN hors toit ; aspect boussole (0=N, 90=E)
    """
    H, W = mns.shape
    pente  = np.full((H, W), np.nan)
    aspect = np.full((H, W), np.nan)
    r2 = 2.0 * res
    for i in prange(H):
        for j in range(W):
            if not pts_ok[i, j]:
                continue
            k = masque_bat[i, j]
            z0 = mns[i, j]

            # dz/dcol : voisins est/ouest du meme batiment
            e = w_ = False
            if j + 1 < W:
                e = pts_ok[i, j + 1] and masque_bat[i, j + 1] == k
            if j - 1 >= 0:
                w_ = pts_ok[i, j - 1] and masque_bat[i, j - 1] == k
            if e and w_:
                dz_dc = (mns[i, j + 1] - mns[i, j - 1]) / r2
            elif e:
                dz_dc = (mns[i, j + 1] - z0) / res
            elif w_:
                dz_dc = (z0 - mns[i, j - 1]) / res
            else:
                continue

            # dz/dligne : voisins sud/nord du meme batiment
            s = n = False
            if i + 1 < H:
                s = pts_ok[i + 1, j] and masque_bat[i + 1, j] == k
            if i - 1 >= 0:
                n = pts_ok[i - 1, j] and masque_bat[i - 1, j] == k
            if s and n:
                dz_dl = (mns[i + 1, j] - mns[i - 1, j]) / r2
            elif s:
                dz_dl = (mns[i + 1, j] - z0) / res
            elif n:
                dz_dl = (z0 - mns[i - 1, j]) / res
            else:
                continue

            pente[i, j]  = math.degrees(math.atan(math.hypot(dz_dc, dz_dl)))
            aspect[i, j] = math.degrees(math.atan2(-dz_dc, dz_dl)) % 360.0

    return pente, aspect


def extractGeom(mns, mnt, gdf, meta):
    """
    Geometrie des toitures depuis MNS, MNT et BD TOPO (sans seuils de selection).
    Tampon config.BUFFER autour des batiments, hauteur min config.MNH_MIN.
    --------
    @param[in] mns, mnt : tableaux 2D de la dalle (NaN hors donnees)
    @param[in] gdf      : GeoDataFrame BD TOPO filtre (index 0..n-1)
    @param[in] meta     : profil rasterio (cles "transform" et "resolution")

    @return pente, aspect : 2D float (deg), NaN hors pixels de toit valides ;
                            aspect en convention boussole (0=N, 90=E)
    @return masque_bat    : 2D int, index gdf + 1 du batiment (0 hors toit valide)
    @return mnh           : 2D float, hauteur au-dessus du sol (m)
    """
    mnh = mns - mnt

    masque_bat = rasterize(
        zip(gdf.geometry.buffer(config.BUFFER), gdf.index + 1),    # 0 = fond
        out_shape=mns.shape, transform=meta["transform"], fill=0, dtype="int32")

    pts_ok = (masque_bat > 0) & (mnh >= config.MNH_MIN) & np.isfinite(mns) & np.isfinite(mnt)

    # pente/aspect : gradient decentre par batiment (remplace np.gradient + erosion)
    pente, aspect = gradMasque(mns, pts_ok, masque_bat, meta["resolution"])

    masque_bat = np.where(np.isfinite(pente), masque_bat, 0).astype("int32")
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
