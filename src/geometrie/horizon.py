"""
src/geometrie/horizon.py
Calcul des angles d'horizon par raycast numpy.
"""

import os
import numpy as np
import rasterio


def compHZ(mns_path, masque_toiture, out_dir,
                    n_directions=36, max_distance_m=500.0):
    """
    Calcule les angles d'horizon dans n_directions directions depuis le MNS.
    Pour chaque pixel de toiture et chaque direction, avance pas à pas
    et garde l'angle d'élévation maximum rencontré (= angle d'horizon).
    --------
    @param[in]  mns_path        : chemin vers le GeoTIFF MNS IGN (float32, Lambert 93)
    @param[in]  masque_toiture  : np.ndarray 2D bool — True sur les pixels de toiture
    @param[in]  out_dir         : dossier de sortie pour les GeoTIFF produits
    @param[in]  n_directions    : nombre de directions azimutales
    @param[in]  max_distance_m  : rayon de recherche en mètres

    @param[out] horizon : np.ndarray (N_pixels_toiture, n_directions) — angle d'horizon
                          en degrés, dans l'ordre de np.where(masque_toiture) (lignes C).
                          La colonne d correspond a l'azimut d * (360/n_directions).
                          Convention boussole : 000=Nord, 090=Est, 180=Sud, 270=Ouest.

    Ecrit aussi, en effet de bord, un GeoTIFF par direction (horizon_000.tif ...
    horizon_350.tif, nodata=-9999) pour visualisation dans QGIS.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Lecture fic
    with rasterio.open(mns_path) as src:
        mns  = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        res  = src.res[0]         

    nodata = meta.get("nodata")
    if nodata is not None:
        mns[mns == nodata] = np.nan

    meta.update(dtype="float32", count=1, nodata=-9999.0, compress="lzw")

    H, W        = mns.shape
    max_dist_px = int(max_distance_m / res)  #conersion m en pixel
    step        = 360 // n_directions         

    x, y = np.where(masque_toiture) #x et y de chaque pixel
    z0 = mns[x, y]   # altitude de chaque pixel toit

    horizon = np.full((len(x), n_directions), -9999.0, np.float32)  # (N pixels, n_directions), en degres

    for d, phi_deg in enumerate(range(0, 360, step)):

        phi_rad = np.deg2rad(phi_deg)

        # 0deg = nord 90 deg = est
        dx = -np.cos(phi_rad)   # nord = lignes qui diminuent
        dy =  np.sin(phi_rad)   # est  = colonnes qui augmentent

       
        theta = np.full(len(x), -np.pi / 2, dtype=np.float32) #angle d'horizon courant pour chaque pixel de toiture, initialisé à -90° 

        # on avance dans la direction phi
        for k in range(1, max_dist_px + 1):

            # Coordonnées du voisin à distance k
            x_k = np.clip(np.round(x + k * dx).astype(int), 0, H-1)
            y_k = np.clip(np.round(y + k * dy).astype(int), 0, W-1)

            # Angle 
            dz    = mns[x_k, y_k] - z0
            angle = np.arctan2(dz, k * res)

            
            theta = np.fmax(theta, angle) #on garde le max (fmax ignore les NaN du MNS)

        horizon[:, d] = np.degrees(theta)        # garde l'horizon en memoire (pour la phase tuile)

        # raster de sortie pour la direction phi, en degres (visualisation QGIS)
        out = np.full((H, W), -9999.0, dtype=np.float32)
        out[x, y] = np.degrees(theta)

        out_tif = os.path.join(out_dir, f"horizon_{phi_deg:03d}.tif")
        with rasterio.open(out_tif, "w", **meta) as dst:
            dst.write(out, 1)

        print(f"  horizon {phi_deg:3d} deg")

    return horizon