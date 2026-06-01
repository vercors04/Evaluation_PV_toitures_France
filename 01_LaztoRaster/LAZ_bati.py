import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import uniform_filter
import rasterio


def laz_bati(laz_path, path_out, min_pts, classe):
    """r
    LAZ vers raster GeoTIFF 
    ---------------------------------------------------------------------------------------
    @param[in]  laz_path : Chemin du fichier .laz
    @param[in]  path_out : Chemin du .tif de sortie
    @param[in]  resol    : Taille pixel en m
    @param[in]  classe   : Classe LiDAR à rasteriser (6 = bâtiment)
    @param[out] laz_bati : fichier LAZ contenant que les points de la classe spécifiée
    ---------------------------------------------------------------------------------------
    """
    las = laspy.read(laz_path)
    xyz = np.column_stack([
        np.array(las.x[las.classification == classe]),
        np.array(las.y[las.classification == classe]),
        np.array(las.z[las.classification == classe])
    ])

    print(f"Points classe 6 : {len(xyz)}")

    return las