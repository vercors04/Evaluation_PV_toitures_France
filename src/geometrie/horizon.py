import numpy as np

from src.config import N_DIRECTIONS, DIST_MAX_M


def compHZ(mns, masque_toiture, res, n_directions=N_DIRECTIONS, max_distance_m=DIST_MAX_M):
    """
    Angle d'horizon par pixel de toit, dans n_directions directions (raycast).
    Pour chaque pixel et direction, avance pas a pas et garde l'angle d'elevation max.
    --------
    @param[in] mns            : 2D float de la dalle (NaN hors donnees)
    @param[in] masque_toiture : 2D bool — True sur les pixels de toit
    @param[in] res            : taille du pixel (m)
    @param[in] n_directions   : nombre de directions azimutales
    @param[in] max_distance_m : rayon de recherche (m)

    @return horizon : (N_pixels_toit, n_directions) angle d'horizon (deg), dans l'ordre
                      de np.where(masque_toiture). Colonne d -> azimut d*(360/n_directions),
                      convention boussole 000=N, 090=E, 180=S, 270=O.
    """
    H, W        = mns.shape
    max_dist_px = int(max_distance_m / res)
    step        = 360 // n_directions

    x, y = np.where(masque_toiture)
    z0   = mns[x, y]
    horizon = np.full((len(x), n_directions), -9999.0, np.float32)

    for d, phi_deg in enumerate(range(0, 360, step)):
        phi = np.deg2rad(phi_deg)
        dx, dy = -np.cos(phi), np.sin(phi)          # 0=N (lignes -), 90=E (colonnes +)

        theta = np.full(len(x), -np.pi / 2, np.float32)
        for k in range(1, max_dist_px + 1):
            xk = np.clip(np.round(x + k * dx).astype(int), 0, H - 1)
            yk = np.clip(np.round(y + k * dy).astype(int), 0, W - 1)
            angle = np.arctan2(mns[xk, yk] - z0, k * res)
            theta = np.fmax(theta, angle)            # fmax ignore les NaN (hors donnees)
        horizon[:, d] = np.degrees(theta)

    return horizon
