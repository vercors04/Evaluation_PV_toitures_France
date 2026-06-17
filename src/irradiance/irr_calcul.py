import numpy as np
import pandas as pd

from src.config import N_JOURS, ALPHAS, BETAS

TRIM = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]  


def masquerHorizon(B_pix, horizon, SAZ, SEL):
    """
    Eteint le direct quand le soleil est sous l'horizon du pixel (ombrage, Buffat Eq.6).
    Le diffus n'est pas touche.
    --------
    @param[in] B_pix   : (N, 12, 24) irradiance directe par pixel et (mois, heure)
    @param[in] horizon : (N, n_dir) angle d'horizon par pixel et direction (deg)
    @param[in] SAZ, SEL: (12, 24) azimut et elevation moyens du soleil (deg)

    @return B_pix modifie sur place (direct = 0 a l'ombre)
    """
    n_dir = horizon.shape[1]
    d = np.round(SAZ / (360 / n_dir)).astype(int) % n_dir   # (12,24) direction du soleil
    horizon_soleil = horizon[:, d]                          # (N, 12, 24)
    B_pix[SEL[None, :, :] <= horizon_soleil] = 0.0
    return B_pix


def irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
              res, B, D, SAZ, SEL, horizon):
    """
    Energie annuelle (et par trimestre) de chaque pixel de toit, ombrage compris.
    Pour chaque pixel : profil (mois,heure) de la case (orientation,pente) la plus proche
    -> extinction du direct a l'ombre -> integration sur l'annee -> x surface reelle.
    --------
    @param[in] masque_bat            : 2D int — index gdf + 1 du batiment (0 = hors toit)
    @param[in] pente, aspect         : 2D float (deg)
    @param[in] incline, incline_or, plat : 2D bool — masques de selection
    @param[in] res                   : taille du pixel (m)
    @param[in] B, D                  : tables (n_alphas, n_betas, 12, 24) direct / diffus (W/m2)
    @param[in] SAZ, SEL              : (12, 24) position moyenne du soleil (deg)
    @param[in] horizon               : (N, n_dir) horizon par pixel, MEME ordre que (incline|plat)

    @return df : DataFrame, 1 ligne par pixel de toit, colonnes
                 id, energie, energie_T1..T4 (kWh), surf (m2), pente (deg), secteur,
                 incline, incline_or (bool)
    """
    pas_a = ALPHAS[1] - ALPHAS[0]
    pas_b = BETAS[1] - BETAS[0]

    toit = incline | plat
    assert horizon.shape[0] == toit.sum(), "horizon et masque de toit desynchronises"

    p = pente[toit]
    a = aspect[toit]

    # case (orientation, pente) la plus proche -> profil (mois, heure) par pixel
    i = np.round(a / pas_a).astype(int) % len(ALPHAS)
    j = np.clip(np.round(p / pas_b).astype(int), 0, len(BETAS) - 1)
    B_pix = masquerHorizon(B[i, j], horizon, SAZ, SEL)      # (N,12,24) direct ombrage (copie)
    D_pix = D[i, j]                                         # (N,12,24) diffus

    surf   = res**2 / np.cos(np.radians(p))                
    e_mois = ((B_pix + D_pix) * N_JOURS[None, :, None]).sum(axis=2) / 1000.0   # (N,12) kWh/m2
    e_mois = e_mois * surf[:, None]                         # (N,12) kWh

    df = pd.DataFrame({
        "id":         masque_bat[toit] - 1,                 # index du batiment dans gdf
        "energie":    e_mois.sum(axis=1),                   # kWh/an, tout le toit
        "surf":       surf,
        "pente":      p,
        "secteur":    np.round(a / 45).astype(int) % 8,
        "incline":    incline[toit],
        "incline_or": incline_or[toit],
    })
    for t, mois in enumerate(TRIM, start=1):
        df[f"energie_T{t}"] = e_mois[:, mois].sum(axis=1)
    return df
