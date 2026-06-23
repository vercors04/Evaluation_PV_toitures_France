import numpy as np
from numba import njit, prange
from src.config import N_DIRECTIONS, DIST_MAX_M


@njit(parallel=True, cache=True)
def compHZ(mns, masque_toiture, res, n_directions=N_DIRECTIONS, max_distance_m=DIST_MAX_M):
    """
    Angle d'horizon par pixel de toit, dans n_directions directions (raycast, compile numba).
    Pour chaque pixel/direction : avance pas a pas et garde la pente max (un seul arctan a la fin).
    --------
    @param[in] mns            : 2D float de la dalle (NaN hors donnees)
    @param[in] masque_toiture : 2D bool — True sur les pixels de toit
    @param[in] res            : taille du pixel (m)
    @param[in] n_directions   : nombre de directions azimutales
    @param[in] max_distance_m : rayon de recherche (m)

    @return horizon : (N_pixels_toit, n_directions) angle d'horizon (deg), ordre np.where(masque_toiture) ;
                      convention boussole 000=N, 090=E, 180=S, 270=O
    """
    H, W = mns.shape
    max_dist_px = int(max_distance_m / res)
    step = 360 // n_directions

    ligne, col = np.where(masque_toiture)
    N = len(ligne)
    horizon = np.full((N, n_directions), -9999.0, np.float32)

    for d in prange(n_directions):
        phi = np.deg2rad(d * step)
        d_ligne = -np.cos(phi)
        d_col   = np.sin(phi)
        for p in range(N):
            z0 = mns[ligne[p], col[p]]
            tan_max = -1e30
            for k in range(1, max_dist_px + 1):
                lk = min(max(int(round(ligne[p] + k * d_ligne)), 0), H - 1)
                ck = min(max(int(round(col[p]  + k * d_col)),   0), W - 1)
                v = mns[lk, ck]
                if v == v:                       # pas NaN
                    t = (v - z0) / (k * res)
                    if t > tan_max:
                        tan_max = t
            horizon[p, d] = np.degrees(np.arctan(tan_max))
    return horizon