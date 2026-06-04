import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import uniform_filter
import rasterio



def lazToMNS(laz_name, path_out, resol, classe):
    """
    LAZ vers raster GeoTIFF 
    ---------------------------------------------------------------------------------------
    @param[in]  laz_name : Nom du fichier .laz
    @param[in]  path_out : Chemin du .tif de sortie
    @param[in]  resol    : Taille pixel en m
    @param[in]  classe   : Classe LiDAR à rasteriser (6 = bâtiment)
    @param[out] mns      : Matrice NumPy 2D du MNS
    @param[out] transf   : Transformation affine géographique
    ---------------------------------------------------------------------------------------
    """
    las = laspy.read(laz_name)

    mask = las.classification == classe
    x, y, z = np.array(las.x[mask]), np.array(las.y[mask]), np.array(las.z[mask])

    # supression valeur abérrante
    z_med = np.median(z)
    mad   = np.median(np.abs(z - z_med)) * 1.4826
    ok    = z <= z_med + 5 * mad
    x, y, z = x[ok], y[ok], z[ok]

    # Grille
    x_min  = np.floor(x.min() / resol) * resol
    y_max  = np.ceil(y.max()  / resol) * resol
    n_cols = int((np.ceil(x.max() / resol) * resol - x_min) / resol)
    n_rows = int((y_max - np.floor(y.min() / resol) * resol) / resol)

    col = np.clip(((x - x_min) / resol).astype(int), 0, n_cols - 1)
    row = np.clip(((y_max - y) / resol).astype(int), 0, n_rows - 1)

    # Z max par pixel
    mns_max = np.full((n_rows, n_cols), -np.inf, dtype='float32')
    np.maximum.at(mns_max, (row, col), z)
    mns = np.where(mns_max > -np.inf, mns_max, np.nan).astype('float32')

    transf = from_origin(x_min, y_max, resol, resol)

    with rasterio.open(path_out, 'w', driver='GTiff',
                       height=n_rows, width=n_cols, count=1,
                       dtype='float32', crs='EPSG:2154',
                       transform=transf, nodata=np.nan) as dst:
        dst.write(mns, 1)

    return mns, transf


def maskVegetation(mns, seuil=0.8):
    """
    Met à NaN les pixels de végétation ou autre détécté par rugosité locale.
    ---------------------------------------------------------------------------------------
    @param[in]  mns   : MNS NumPy 2D
    @param[in]  seuil : Seuil écart-type en m (défaut 0.8)
    @param[out] out   : MNS filtré (végétation → NaN)
    ---------------------------------------------------------------------------------------
    """
    tmp = np.where(np.isnan(mns), 0.0, mns)
    std = np.sqrt(np.maximum(
        uniform_filter(tmp**2, size=3) - uniform_filter(tmp, size=3)**2, 0
    ))
    out = mns.copy()
    out[std > seuil] = np.nan
    return out


def fillGaps(mns, iterations=5):
    """
    Comble les trous INTERNES du raster (NaN entourés de voisins valides).
    Chaque itération remplace les NaN ayant ≥4 voisins valides par leur moyenne.
    ---------------------------------------------------------------------------------------
    @param[in]  mns        : MNS NumPy 2D
    @param[in]  iterations : Nb max d'itérations
    @param[out] out        : MNS avec trous internes comblés
    ---------------------------------------------------------------------------------------
    """
    out = mns.copy()

    for _ in range(iterations):
        nan_mask = np.isnan(out)
        if not nan_mask.any():
            break

        data  = np.where(nan_mask, 0.0, out)
        valid = (~nan_mask).astype(float)
        s, n  = np.zeros_like(out), np.zeros_like(out)

        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            s += np.roll(np.roll(data,  dr, 0), dc, 1) * np.roll(np.roll(valid, dr, 0), dc, 1)
            n += np.roll(np.roll(valid, dr, 0), dc, 1)

        internes = nan_mask & (n >= 4)
        out = np.where(internes, s / np.where(n > 0, n, 1), out)

    return out