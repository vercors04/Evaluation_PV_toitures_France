import numpy as np
from numba import njit, prange
from src.config import N_DIRECTIONS, DIST_MAX_M


@njit(parallel=True, cache=True)
def compHZ(mns, masque_toiture, res, n_directions=N_DIRECTIONS, max_distance_m=DIST_MAX_M):
    H, W = mns.shape
    max_dist_px = int(max_distance_m / res)
    step = 360 // n_directions

    x, y = np.where(masque_toiture)
    N = len(x)
    horizon = np.full((N, n_directions), -9999.0, np.float32)

    for d in prange(n_directions):
        phi = np.deg2rad(d * step)
        dx = -np.cos(phi)
        dy = np.sin(phi)
        for p in range(N):
            z0 = mns[x[p], y[p]]
            tan_max = -1e30
            for k in range(1, max_dist_px + 1):
                xk = min(max(int(round(x[p] + k * dx)), 0), H - 1)
                yk = min(max(int(round(y[p] + k * dy)), 0), W - 1)
                v = mns[xk, yk]
                if v == v:                       # pas NaN
                    t = (v - z0) / (k * res)
                    if t > tan_max:
                        tan_max = t
            horizon[p, d] = np.degrees(np.arctan(tan_max))
    return horizon