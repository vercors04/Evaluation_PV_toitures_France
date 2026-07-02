import numpy as np
import pandas as pd
from numba import njit, prange
from src import config


@njit(parallel=True, cache=True)
def energiePix(a, p, B, D_h, horizon, dmh, SEL, NJ, pas_a, pas_b):
    """
    Energie mensuelle par pixel (kWh/m2), accumulee sans cube intermediaire.
    --------
    @param[in] a, p     : orientation et pente de chaque pixel (deg), shape (N,)
    @param[in] B        : table directe (n_alphas, n_betas, 12, 24), W/m2
    @param[in] D_h      : table diffuse pre-sommee sur l'heure (n_alphas, n_betas, 12), W/m2
    @param[in] horizon  : angle d'horizon par pixel et direction (N, n_dir), deg
    @param[in] dmh      : direction du soleil par (mois, heure), shape (12, 24)
    @param[in] SEL      : elevation du soleil par (mois, heure), shape (12, 24), deg
    @param[in] NJ       : nombre de jours par mois, shape (12,)
    @param[in] pas_a, pas_b : pas de la grille en orientation et pente (deg)

    @return e_mois : energie mensuelle par pixel, shape (N, 12), kWh/m2
    """
    N = a.shape[0]
    nalpha, nbeta = B.shape[0], B.shape[1]
    e_mois = np.zeros((N, 12), np.float32)

    for n in prange(N):                                   # 1 pixel = 1 tache independante
        # poids bilineaires (orientation, pente), calcules une fois
        fa = a[n] / pas_a
        i0 = int(np.floor(fa)) % nalpha                   # azimut : indice bas
        i1 = (i0 + 1) % nalpha                            #          indice haut (revient a 0 apres 345)
        wa = fa - np.floor(fa)
        fb = p[n] / pas_b
        fb = 0.0 if fb < 0 else (nbeta - 1.0 if fb > nbeta - 1 else fb)   # pente bornee a la grille
        j0 = int(np.floor(fb))
        j1 = j0 + 1 if j0 + 1 < nbeta else nbeta - 1
        wb = fb - j0
        w00 = (1-wa)*(1-wb); w10 = wa*(1-wb); w01 = (1-wa)*wb; w11 = wa*wb

        for m in range(12):
            direct = 0.0
            for h in range(24):
                if SEL[m, h] <= 0.0:                      # nuit
                    continue
                if SEL[m, h] <= horizon[n, dmh[m, h]]:    # soleil sous l'horizon
                    continue
                direct += (w00*B[i0,j0,m,h] + w10*B[i1,j0,m,h]
                           + w01*B[i0,j1,m,h] + w11*B[i1,j1,m,h])
            diffus = (w00*D_h[i0,j0,m] + w10*D_h[i1,j0,m]
                      + w01*D_h[i0,j1,m] + w11*D_h[i1,j1,m])
            e_mois[n, m] = NJ[m] / 1000.0 * (direct + diffus)
    return e_mois


def irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
              res, B, D, SAZ, SEL, horizon):
    """
    Energie par pixel de toit (annuelle et par trimestre), ombrage par l'horizon compris.
    --------
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 hors toit)
    @param[in] pente, aspect : 2D float (deg)
    @param[in] incline, incline_or, plat : 2D bool, masques de selection
    @param[in] res : taille du pixel (m)
    @param[in] B, D : tables (n_alphas, n_betas, 12, 24) direct / diffus (W/m2)
    @param[in] SAZ, SEL : position moyenne du soleil par (mois, heure) (deg)
    @param[in] horizon : horizon par pixel (N, n_dir), meme ordre que incline|plat

    @return df : DataFrame, 1 ligne par pixel (id, energie, energie_T1..T4, surf,
                 pente, secteur, incline, incline_or)
    """
    toit = incline | plat
    assert horizon.shape[0] == toit.sum(), "horizon et masque de toit desynchronises"

    a = aspect[toit].astype(np.float32)
    p = pente[toit].astype(np.float32)

    pas_a = float(config.ALPHAS[1] - config.ALPHAS[0])   # 15
    pas_b = float(config.BETAS[1] - config.BETAS[0])     # 10
    ndir  = horizon.shape[1]
    dmh = (np.round(SAZ / (360 / ndir)).astype(np.int64) % ndir)   # (12,24) direction du soleil
    D_h = D.sum(axis=3).astype(np.float32)                          # diffus pre-somme sur l'heure

    e_mois = energiePix(a, p, B.astype(np.float32), D_h, horizon.astype(np.float32),
                     dmh, SEL.astype(np.float32), config.N_JOURS.astype(np.float32), pas_a, pas_b)

    surf   = res**2 / np.cos(np.radians(p))
    e_mois = e_mois * surf[:, None]                 # (N,12) kWh

    df = pd.DataFrame({
        "id":         masque_bat[toit] - 1,
        "energie":    e_mois.sum(axis=1),
        "surf":       surf,
        "pente":      p,
        "secteur":    np.round(a / 45).astype(int) % 8,
        "incline":    incline[toit],
        "incline_or": incline_or[toit],
    })
    for t, mois in enumerate(config.TRIM, start=1):
        df[f"energie_T{t}"] = e_mois[:, mois].sum(axis=1)
    return df
