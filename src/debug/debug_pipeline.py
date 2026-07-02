import os

import numpy as np

from src.tuile.raster import ecrireGeotiff


def exportRasters(arrays, meta, out_dir):
    """
    Exporte un GeoTIFF par entree, pour visualisation (QGIS).
    --------
    @param[in] arrays  : dict {nom: tableau 2D}
    @param[in] meta    : profil rasterio de la dalle
    @param[in] out_dir : dossier de sortie
    """
    os.makedirs(out_dir, exist_ok=True)
    for nom, arr in arrays.items():
        ecrireGeotiff(arr, meta, os.path.join(out_dir, f"{nom}.tif"))


def exportHorizon(horizon, masque_toiture, meta, out_dir, nodata=-9999.0):
    """
    Eclate la table horizon (N, n_dir) en un GeoTIFF par direction.
    --------
    @param[in] horizon        : (N, n_dir) angle d'horizon par pixel (sortie compHZ)
    @param[in] masque_toiture : 2D bool, pixels de toit (meme ordre que horizon)
    @param[in] meta           : profil rasterio de la dalle
    @param[in] out_dir        : dossier de sortie
    """
    os.makedirs(out_dir, exist_ok=True)
    H, W = masque_toiture.shape
    ligne, col = np.where(masque_toiture)        # memes pixels / ordre que compHZ
    step = 360 // horizon.shape[1]
    for d in range(horizon.shape[1]):
        grid = np.full((H, W), nodata, np.float32)
        grid[ligne, col] = horizon[:, d]         # on re-disperse la colonne d sur la grille
        ecrireGeotiff(grid, meta, os.path.join(out_dir, f"horizon_{d * step:03d}.tif"))
