import numpy as np
from numba import njit, prange
from src.config import N_DIRECTIONS, DIST_MAX_M, CAP


@njit(parallel=True, cache=True)
def compHZ(mns, masque_toiture, res, n_directions=N_DIRECTIONS, max_distance_m=DIST_MAX_M):
    """
    Angle d'horizon par pixel de toit, dans n_directions directions (raycast, compile numba).
    Pour chaque pixel/direction : avance le long du rayon et garde la pente max (un seul arctan a la fin).
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
    tan_cap = np.tan(np.radians(CAP))


    zmax = -1e30
    for i in range(H):
        for j in range(W):
            v = mns[i, j]
            if v == v and v > zmax:
                zmax = v

    ks = np.empty(max_dist_px, np.int64)
    m, k = 0, 1
    while k <= max_dist_px:
        ks[m] = k
        m += 1
        k += 1 + k // 10                
    ks = ks[:m]
    dist_m = ks * res



    off_l = np.empty((n_directions, m), np.int64)
    off_c = np.empty((n_directions, m), np.int64)
    for d in range(n_directions):
        phi = np.deg2rad(d * step)
        dl, dc = -np.cos(phi), np.sin(phi)
        for s in range(m):
            off_l[d, s] = np.int64(round(dl * ks[s]))
            off_c[d, s] = np.int64(round(dc * ks[s]))

    ligne, col = np.where(masque_toiture)
    N = len(ligne)
    horizon = np.full((N, n_directions), -9999.0, np.float32)



    for d in prange(n_directions):    

        for p in range(N):
            z0 = mns[ligne[p], col[p]]
            tan_max = -1e30

            for s in range(m):
                lk = ligne[p] + off_l[d, s]
                ck = col[p]  + off_c[d, s]
                if lk < 0 or lk >= H or ck < 0 or ck >= W:
                    break                                
                v = mns[lk, ck]
                if v == v:                                # pas NaN
                    t = (v - z0) / dist_m[s]
                    if t > tan_max:
                        tan_max = t
                        if tan_max > tan_cap:             
                            break
                if zmax - z0 <= tan_max * dist_m[s]:     
                    break
            horizon[p, d] = np.degrees(np.arctan(tan_max))
    return horizon
