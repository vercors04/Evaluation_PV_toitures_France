import numpy as np
import pandas as pd
from numba import njit, prange
from src.config import N_JOURS, ALPHAS, BETAS

TRIM = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]




@njit(parallel=True, cache=True)
def energiePix(a, p, B, D_h, horizon, dmh, SEL, NJ, pas_a, pas_b):
    """Energie mensuelle par pixel (N,12) en kWh/m2, sans jamais construire de cube."""
    N = a.shape[0]
    nalpha, nbeta = B.shape[0], B.shape[1]
    e_mois = np.zeros((N, 12), np.float32)

    for n in prange(N):                                   # 1 pixel = 1 tache (independantes)
        # --- poids bilineaires (orientation, pente) du pixel, calcules UNE fois ---
        fa = a[n] / pas_a
        i0 = int(np.floor(fa)) % nalpha                   # azimut : indice bas
        i1 = (i0 + 1) % nalpha                            #          indice haut (boucle 345->0)
        wa = fa - np.floor(fa)
        fb = p[n] / pas_b
        fb = 0.0 if fb < 0 else (nbeta - 1.0 if fb > nbeta - 1 else fb)   # pente bornee a la grille
        j0 = int(np.floor(fb))
        j1 = j0 + 1 if j0 + 1 < nbeta else nbeta - 1
        wb = fb - j0
        w00 = (1-wa)*(1-wb); w10 = wa*(1-wb); w01 = (1-wa)*wb; w11 = wa*wb

        # --- boucle sur les creneaux, on accumule ---
        for m in range(12):
            direct = 0.0
            for h in range(24):
                if SEL[m, h] <= 0.0:                      # nuit -> pas de direct
                    continue
                if SEL[m, h] <= horizon[n, dmh[m, h]]:    # soleil sous l'horizon -> ombre
                    continue
                # bilineaire du direct sur la tranche (m,h) : 4 coins
                direct += (w00*B[i0,j0,m,h] + w10*B[i1,j0,m,h]
                           + w01*B[i0,j1,m,h] + w11*B[i1,j1,m,h])
            # diffus pre-somme (#2) : bilineaire sur la tranche (m)
            diffus = (w00*D_h[i0,j0,m] + w10*D_h[i1,j0,m]
                      + w01*D_h[i0,j1,m] + w11*D_h[i1,j1,m])
            e_mois[n, m] = NJ[m] / 1000.0 * (direct + diffus)
    return e_mois




def irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
              res, B, D, SAZ, SEL, horizon):
    toit = incline | plat
    assert horizon.shape[0] == toit.sum(), "horizon et masque de toit desynchronises"

    a = aspect[toit].astype(np.float32)
    p = pente[toit].astype(np.float32)

    # prepare les entrees du noyau
    pas_a = float(ALPHAS[1] - ALPHAS[0])           # 15
    pas_b = float(BETAS[1] - BETAS[0])             # 10
    ndir  = horizon.shape[1]
    dmh = (np.round(SAZ / (360 / ndir)).astype(np.int64) % ndir)   # (12,24) direction du soleil
    D_h = D.sum(axis=3).astype(np.float32)                          # (#2) diffus pre-somme

    # streaming -> energie mensuelle par pixel (N,12) en kWh/m2
    e_mois = energiePix(a, p, B.astype(np.float32), D_h, horizon.astype(np.float32),
                     dmh, SEL.astype(np.float32), N_JOURS.astype(np.float32), pas_a, pas_b)

    # --- a partir d'ici, IDENTIQUE a avant ---
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
    for t, mois in enumerate(TRIM, start=1):
        df[f"energie_T{t}"] = e_mois[:, mois].sum(axis=1)
    return df




# def interpBilin(T, a, p):
#     """
#     Interpolation bilineaire de la table T en (orientation, pente), pour N pixels.
#     L'azimut boucle (345° -> 0°) ; la pente est bornee dans la grille [0, derniere pente].
#     Les poids sont forces en float32 pour que tout le calcul reste en float32 (la table l'est
#     deja) : evite de materialiser les gros tableaux (N, 12, 24) en float64 (memoire / 2).
#     --------
#     @param[in] T : table a interpoler (nα, nβ, 12, 24), float32 (direct B ou diffus D, W/m2)
#     @param[in] a : orientation de chaque pixel (deg), shape (N,)
#     @param[in] p : pente de chaque pixel (deg), shape (N,)

#     @return out : profil (mois, heure) interpole par pixel, shape (N, 12, 24), float32
#     """
#     pas_a, pas_b = int(ALPHAS[1] - ALPHAS[0]), int(BETAS[1] - BETAS[0])   

#     fa = a / pas_a
#     i0 = np.floor(fa).astype(int) % len(ALPHAS)
#     i1 = (i0 + 1) % len(ALPHAS)
#     wa = (fa - np.floor(fa)).astype(np.float32)[:, None, None]           

#     fb = np.clip(p / pas_b, 0, len(BETAS) - 1)
#     j0 = np.floor(fb).astype(int)
#     j1 = np.minimum(j0 + 1, len(BETAS) - 1)
#     wb = (fb - j0).astype(np.float32)[:, None, None]                      

#     out = ((1 - wa) * (1 - wb) * T[i0, j0] + wa * (1 - wb) * T[i1, j0]
#            + (1 - wa) * wb * T[i0, j1] + wa * wb * T[i1, j1])
#     return out.astype(np.float32)                            


# def masquerHorizon(B_pix, horizon, SAZ, SEL):
#     """
#     Eteint le direct quand le soleil est sous l'horizon du pixel (ombrage, Buffat Eq.6).
#     Le diffus n'est pas touche.
#     --------
#     @param[in] B_pix   : (N, 12, 24) irradiance directe par pixel et (mois, heure)
#     @param[in] horizon : (N, n_dir) angle d'horizon par pixel et direction (deg)
#     @param[in] SAZ, SEL: (12, 24) azimut et elevation moyens du soleil (deg)

#     @return B_pix modifie sur place (direct = 0 a l'ombre)
#     """
#     n_dir = horizon.shape[1]
#     d = np.round(SAZ / (360 / n_dir)).astype(int) % n_dir   # (12,24) direction du soleil
#     horizon_soleil = horizon[:, d]                          # (N, 12, 24)
#     B_pix[SEL[None, :, :] <= horizon_soleil] = 0.0
#     return B_pix


# def irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
#               res, B, D, SAZ, SEL, horizon):
#     """
#     Energie annuelle (et par trimestre) de chaque pixel de toit, ombrage compris.
#     Pour chaque pixel : profil (mois,heure) interpole (bilineaire) en (orientation,pente)
#     -> extinction du direct a l'ombre -> integration sur l'annee -> x surface reelle.
#     --------
#     @param[in] masque_bat            : 2D int — index gdf + 1 du batiment (0 = hors toit)
#     @param[in] pente, aspect         : 2D float (deg)
#     @param[in] incline, incline_or, plat : 2D bool — masques de selection
#     @param[in] res                   : taille du pixel (m)
#     @param[in] B, D                  : tables (n_alphas, n_betas, 12, 24) direct / diffus (W/m2)
#     @param[in] SAZ, SEL              : (12, 24) position moyenne du soleil (deg)
#     @param[in] horizon               : (N, n_dir) horizon par pixel, MEME ordre que (incline|plat)

#     @return df : DataFrame, 1 ligne par pixel de toit, colonnes
#                  id, energie, energie_T1..T4 (kWh), surf (m2), pente (deg), secteur,
#                  incline, incline_or (bool)
#     """

#     toit = incline | plat
#     assert horizon.shape[0] == toit.sum(), "horizon et masque de toit desynchronises"

#     p = pente[toit]
#     a = aspect[toit]

#     # interpolation bilineaire (orientation, pente) -> profil (mois, heure) par pixel
#     B_pix = masquerHorizon(interpBilin(B, a, p), horizon, SAZ, SEL)
#     D_pix = interpBilin(D, a, p)

#     surf   = res**2 / np.cos(np.radians(p))                
#     e_mois = ((B_pix + D_pix) * N_JOURS[None, :, None]).sum(axis=2) / 1000.0   # (N,12) kWh/m2
#     e_mois = e_mois * surf[:, None]                         # (N,12) kWh

#     df = pd.DataFrame({
#         "id":         masque_bat[toit] - 1,                 # index du batiment dans gdf
#         "energie":    e_mois.sum(axis=1),                   # kWh/an, tout le toit
#         "surf":       surf,
#         "pente":      p,
#         "secteur":    np.round(a / 45).astype(int) % 8,
#         "incline":    incline[toit],
#         "incline_or": incline_or[toit],
#     })
#     for t, mois in enumerate(TRIM, start=1):
#         df[f"energie_T{t}"] = e_mois[:, mois].sum(axis=1)
#     return df

