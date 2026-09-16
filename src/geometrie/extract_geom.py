import math

import numpy as np
from numba import njit, prange
from rasterio.features import rasterize

from src import config


@njit(parallel=True, cache=True)
def gradMasque(mns, pts_ok, masque_bat, res):
    """
    Pente et aspect par differences finies, decentrees au bord et limitees aux voisins du
    meme batiment.
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


@njit(cache=True)
def ajustePlan(mns, pts_ok, masque_bat, res, i, j, k, di0, di1, dj0, dj1):
    """
    Plan des moindres carres (Cramer) sur une fenetre autour de (i, j), limitee aux pixels
    valides du batiment k.
    --------
    @param[in] mns, pts_ok, masque_bat, res : voir gradPlan
    @param[in] i, j     : pixel courant
    @param[in] k        : index du batiment (masque_bat[i, j])
    @param[in] di0, di1 : bornes de la fenetre en lignes, relatives a i (incluses)
    @param[in] dj0, dj1 : bornes en colonnes, relatives a j (incluses)

    @return ga, gb : gradients vers l'est et vers le nord (m/m)
    @return residu : moyenne quadratique des ecarts au plan (m), -1 si plan indetermine
    @return n      : nombre de points utilises
    """
    H, W = mns.shape
    z0 = mns[i, j]
    sxx = sxy = syy = sx = sy = n = 0.0
    sxz = syz = sz = szz = 0.0
    for di in range(di0, di1 + 1):
        a_ = i + di
        if a_ < 0 or a_ >= H:
            continue
        for dj in range(dj0, dj1 + 1):
            b_ = j + dj
            if b_ < 0 or b_ >= W:
                continue
            if not pts_ok[a_, b_] or masque_bat[a_, b_] != k:
                continue
            x = dj * res
            y = -di * res
            z = mns[a_, b_] - z0
            sxx += x * x; sxy += x * y; syy += y * y
            sx  += x;     sy  += y;     n   += 1.0
            sxz += x * z; syz += y * z; sz  += z; szz += z * z

    det = (sxx * (syy * n - sy * sy) - sxy * (sxy * n - sy * sx)
           + sx * (sxy * sy - syy * sx))
    if abs(det) < 1e-9:
        return 0.0, 0.0, -1.0, n

    ga = (sxz * (syy * n - sy * sy) - sxy * (syz * n - sy * sz)
          + sx * (syz * sy - syy * sz)) / det
    gb = (sxx * (syz * n - sy * sz) - sxz * (sxy * n - sy * sx)
          + sx * (sxy * sz - syz * sx)) / det
    gc = (sxx * (syy * sz - sy * syz) - sxy * (sxy * sz - sy * sxz)
          + sx * (sxy * syz - syy * sxz)) / det
    sse = szz - (ga * sxz + gb * syz + gc * sz)
    return ga, gb, (math.sqrt(sse / n) if sse > 0.0 else 0.0), n


@njit(parallel=True, cache=True)
def gradPlan(mns, pts_ok, masque_bat, res, rayon, residu_pan):
    """
    Pente, aspect et residu d'un plan ajuste sur une fenetre (2*rayon+1)^2 du meme batiment ;
    au-dela de residu_pan, pente reestimee sur la demi-fenetre la plus plane.
    --------
    @param[in] mns        : 2D float de la dalle (NaN hors donnees)
    @param[in] pts_ok     : 2D bool, pixels de toit valides
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 = fond)
    @param[in] res        : taille du pixel (m)
    @param[in] rayon      : demi-cote de la fenetre (px)
    @param[in] residu_pan : seuil de reajustement (m) ; 0 = off

    @return pente, aspect : 2D float (deg), NaN hors toit ; aspect boussole (0=N, 90=E)
    @return residu        : 2D float, residu de la fenetre complete (m)
    """
    H, W = mns.shape
    pente  = np.full((H, W), np.nan)
    aspect = np.full((H, W), np.nan)
    residu = np.full((H, W), np.nan)

    for i in prange(H):
        for j in range(W):
            if not pts_ok[i, j]:
                continue
            k = masque_bat[i, j]

            e = w_ = s_ = n_ = False
            if j + 1 < W:  e  = pts_ok[i, j + 1] and masque_bat[i, j + 1] == k
            if j - 1 >= 0: w_ = pts_ok[i, j - 1] and masque_bat[i, j - 1] == k
            if i + 1 < H:  s_ = pts_ok[i + 1, j] and masque_bat[i + 1, j] == k
            if i - 1 >= 0: n_ = pts_ok[i - 1, j] and masque_bat[i - 1, j] == k
            if not ((e or w_) and (s_ or n_)):
                continue

            ga, gb, r, n = ajustePlan(mns, pts_ok, masque_bat, res, i, j, k,
                                      -rayon, rayon, -rayon, rayon)
            if r < 0.0:
                continue

            r_plein = r
            if residu_pan > 0.0 and r > residu_pan:
                for c in range(4):
                    if c == 0:   a0, a1, b0, b1 = -rayon, 0, -rayon, rayon
                    elif c == 1: a0, a1, b0, b1 = 0, rayon, -rayon, rayon
                    elif c == 2: a0, a1, b0, b1 = -rayon, rayon, -rayon, 0
                    else:        a0, a1, b0, b1 = -rayon, rayon, 0, rayon
                    g1, g2, r1, n1 = ajustePlan(mns, pts_ok, masque_bat, res,
                                                i, j, k, a0, a1, b0, b1)
                    if r1 >= 0.0 and n1 >= 4.0 and r1 < r:
                        ga, gb, r = g1, g2, r1

            pente[i, j]  = math.degrees(math.atan(math.hypot(ga, gb)))
            aspect[i, j] = math.degrees(math.atan2(-ga, -gb)) % 360.0
            residu[i, j] = r_plein

    return pente, aspect, residu


def extractGeom(mns, mnt, gdf, meta):
    """
    Geometrie des toitures depuis MNS, MNT et BD TOPO, avant seuils de selection.
    --------
    @param[in] mns, mnt : tableaux 2D de la dalle (NaN hors donnees)
    @param[in] gdf      : GeoDataFrame BD TOPO (index entier)
    @param[in] meta     : profil rasterio (cles "transform" et "resolution")

    @return pente, aspect : 2D float (deg), NaN hors toit retenu ; aspect boussole (0=N, 90=E)
    @return masque_bat    : 2D int, index gdf + 1 (0 hors toit retenu)
    @return masque_haut   : 2D int, idem avant critere de pente (sert a la hauteur)
    @return mnh           : 2D float, hauteur au-dessus du sol (m)
    """
    mnh = mns - mnt

    masque_bat = rasterize(
        zip(gdf.geometry.buffer(config.BUFFER), gdf.index + 1),
        out_shape=mns.shape, transform=meta["transform"], fill=0, dtype="int32")

    pts_ok = (masque_bat > 0) & (mnh >= config.MNH_MIN) & np.isfinite(mns) & np.isfinite(mnt)

    masque_haut = np.where(pts_ok, masque_bat, 0).astype("int32")

    if config.METHODE_PENTE == "plan":
        pente, aspect, residu = gradPlan(mns, pts_ok, masque_bat, meta["resolution"],
                                         config.RAYON_PLAN, config.RESIDU_PAN_M)
        if config.RESIDU_MAX_M > 0:
            pente = np.where(residu <= config.RESIDU_MAX_M, pente, np.nan)
    else:
        pente, aspect = gradMasque(mns, pts_ok, masque_bat, meta["resolution"])

    masque_bat = np.where(np.isfinite(pente), masque_bat, 0).astype("int32")
    return pente, aspect, masque_bat, masque_haut, mnh


def makeMasques(pente, aspect, masque_bat):
    """
    Masques de toiture selon les seuils de pente et la fenetre d'azimut.
    --------
    @param[in] pente, aspect : 2D float (deg), NaN hors toit valide
    @param[in] masque_bat    : 2D int, index gdf + 1 (0 hors toit valide)

    @return incline_or : 2D bool, incline et dans l'arc AZ_MIN -> AZ_MAX (sens horaire)
    @return incline    : 2D bool, pente dans [PENTE_PLAT, PENTE_MAX]
    @return plat       : 2D bool, pente < PENTE_PLAT
    """
    valid      = masque_bat > 0
    incline    = valid & (pente >= config.PENTE_PLAT) & (pente <= config.PENTE_MAX)
    debut, fin = config.AZ_MIN % 360.0, config.AZ_MAX % 360.0
    if config.AZ_MAX - config.AZ_MIN >= 360:
        incline_or = incline.copy()
    elif debut <= fin:
        incline_or = incline & (aspect >= debut) & (aspect <= fin)
    else:
        incline_or = incline & ((aspect >= debut) | (aspect <= fin))
    plat       = valid & (pente < config.PENTE_PLAT)
    return incline_or, incline, plat


@njit(parallel=True, cache=True)
def eroderToit(masque_bat, toiture, rayon_px):
    """
    Pixels de toit dont tout le voisinage de rayon rayon_px est du meme batiment et du toit.
    --------
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 hors toit)
    @param[in] toiture    : 2D bool, pixels de toit retenus
    @param[in] rayon_px   : recul (px) ; 0 = sans effet

    @return 2D bool, pixels equipables
    """
    if rayon_px <= 0:
        return toiture.copy()

    H, W = masque_bat.shape
    out = np.zeros((H, W), np.bool_)
    r2 = rayon_px * rayon_px
    for i in prange(H):
        for j in range(W):
            if not toiture[i, j]:
                continue
            k = masque_bat[i, j]
            ok = True
            for di in range(-rayon_px, rayon_px + 1):
                for dj in range(-rayon_px, rayon_px + 1):
                    if di * di + dj * dj > r2:
                        continue
                    a = i + di
                    b = j + dj
                    if (a < 0 or a >= H or b < 0 or b >= W
                            or not toiture[a, b] or masque_bat[a, b] != k):
                        ok = False
                        break
                if not ok:
                    break
            out[i, j] = ok
    return out
