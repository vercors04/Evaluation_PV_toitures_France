import math

import numpy as np
from numba import njit, prange


@njit(parallel=True, cache=True)
def compHZ(mns, masque_toiture, res, n_directions, dist_min_m, dist_max_m, cap, pas_div):
    """
    Angle d'horizon par pixel de toit dans n_directions directions, par lancer de rayons.
    --------
    @param[in] mns            : 2D float, MNS elargi de la portee d'ombrage (NaN hors donnees)
    @param[in] masque_toiture : 2D bool de meme forme, pixels de toit
    @param[in] res            : taille du pixel (m)
    @param[in] n_directions   : nombre de directions azimutales
    @param[in] dist_min_m     : distance de depart (m)
    @param[in] dist_max_m     : portee (m)
    @param[in] cap            : pente max prise en compte (deg)
    @param[in] pas_div        : croissance du pas, k += 1 + k/pas_div ; 0 = pas exact

    @return (N_pixels_toit, n_directions) float32, angle d'horizon (deg), ordre
            np.where(masque_toiture), directions boussole (0=N, 90=E)
    """
    H, W = mns.shape
    max_dist_px = int(dist_max_m / res)
    min_dist_px = max(1, int(dist_min_m / res))
    step = 360 // n_directions
    tan_cap = np.tan(np.radians(cap))
    zmax = np.nanmax(mns)

    ks = np.empty(max(max_dist_px, 1), np.int64)
    m, k = 0, min_dist_px
    while k <= max_dist_px:
        ks[m] = k
        m += 1
        k += 1 + (k // pas_div if pas_div > 0 else 0)
    ks = ks[:m]

    off_l = np.empty((n_directions, m), np.int64)
    off_c = np.empty((n_directions, m), np.int64)
    dist  = np.empty((n_directions, m), np.float64)
    inv_d = np.empty((n_directions, m), np.float64)
    for d in range(n_directions):
        phi = np.deg2rad(d * step)
        dl, dc = -np.cos(phi), np.sin(phi)
        for s in range(m):
            a = np.int64(round(dl * ks[s]))
            b = np.int64(round(dc * ks[s]))
            off_l[d, s] = a
            off_c[d, s] = b
            dist[d, s]  = np.sqrt(np.float64(a * a + b * b)) * res
            inv_d[d, s] = 1.0 / dist[d, s]

    ligne, col = np.where(masque_toiture)
    N = len(ligne)
    horizon = np.empty((N, n_directions), np.float32)

    for d in prange(n_directions):
        for p in range(N):
            i0 = ligne[p]
            j0 = col[p]
            z0 = mns[i0, j0]
            tan_max = -1e30
            for s in range(m):
                lk = i0 + off_l[d, s]
                ck = j0 + off_c[d, s]
                if lk < 0 or lk >= H or ck < 0 or ck >= W:
                    break
                v = mns[lk, ck]
                if v == v:
                    t = (v - z0) * inv_d[d, s]
                    if t > tan_max:
                        tan_max = t
                        if tan_max > tan_cap:
                            break
                if zmax - z0 <= tan_max * dist[d, s]:
                    break
            horizon[p, d] = np.degrees(np.arctan(tan_max))
    return horizon


@njit(cache=True, inline="always")
def _primitive(cb, sb, cd, e0):
    """
    Integrale de max(0, cos incidence) cos(e) de, de e0 a pi/2, dans un azimut.
    --------
    @param[in] cb, sb : cosinus et sinus de la pente du plan
    @param[in] cd     : cosinus de l'ecart azimutal entre la direction et le plan
    @param[in] e0     : borne basse (rad)

    @return valeur de la primitive
    """
    ce = math.cos(e0)
    return (cb * ce * ce / 2.0
            + sb * cd * ((math.pi / 2.0 - e0) / 2.0 - math.sin(2.0 * e0) / 4.0))


@njit(parallel=True, cache=True)
def facteursCiel(horizon, pente, aspect, bande_deg, t_rangee, w_rangee):
    """
    Facteurs de ciel isotrope et de bande d'horizon vus par le plan, masques par l'horizon et
    par la rangee de devant (moyenne sur la hauteur du module).
    --------
    @param[in] horizon   : angle d'horizon par pixel et direction (N, n_dir), deg
    @param[in] pente     : pente du plan (deg), shape (N,)
    @param[in] aspect    : azimut du plan (deg, 0=N, 90=E), shape (N,)
    @param[in] bande_deg : hauteur de la bande d'horizon (deg)
    @param[in] t_rangee  : tangentes du masque de la rangee de devant par point de quadrature
                           (K,) ; zeros(1) sans rangee
    @param[in] w_rangee  : poids de quadrature (K,), de somme 1

    @return f_ciel, f_hz : facteurs par pixel, shape (N,) float32 ; 1 si degage
    """
    N, ndir = horizon.shape
    K = t_rangee.shape[0]
    t_max = 0.0
    for k in range(K):
        if t_rangee[k] > t_max:
            t_max = t_rangee[k]
    f_ciel = np.empty(N, np.float32)
    f_hz   = np.empty(N, np.float32)
    dphi = 2.0 * math.pi / ndir
    eb = math.radians(bande_deg)
    for n in prange(N):
        b  = math.radians(pente[n])
        al = math.radians(aspect[n])
        cb = math.cos(b)
        sb = math.sin(b)
        num = 0.0
        num_b = 0.0
        den_b = 0.0
        for d in range(ndir):
            cd = math.cos(d * dphi - al)
            hz = horizon[n, d]
            if hz < 0.0:
                hz = 0.0
            e0 = math.radians(hz)
            ez = 0.0
            if cd < 0.0:
                ez = math.atan(-sb * cd / cb) if cb > 0.0 else math.pi / 2.0
                if ez > e0:
                    e0 = ez
            haut = _primitive(cb, sb, cd, eb)
            den_b += _primitive(cb, sb, cd, ez if ez < eb else eb) - haut
            if cd > 0.0 and t_max > 0.0:
                for k in range(K):
                    er = math.atan(t_rangee[k] * cd)
                    ek = er if er > e0 else e0
                    num_b += w_rangee[k] * (_primitive(cb, sb, cd, ek if ek < eb else eb)
                                            - haut)
                    if ek < math.pi / 2.0:
                        num += w_rangee[k] * dphi * _primitive(cb, sb, cd, ek)
                continue
            num_b += _primitive(cb, sb, cd, e0 if e0 < eb else eb) - haut
            if e0 >= math.pi / 2.0:
                continue
            num += dphi * _primitive(cb, sb, cd, e0)
        f_ciel[n] = num / (math.pi * (1.0 + cb) / 2.0)
        r = num_b / den_b if den_b > 1e-12 else 0.0
        f_hz[n]   = 0.0 if r < 0.0 else (1.0 if r > 1.0 else r)
    return f_ciel, f_hz
