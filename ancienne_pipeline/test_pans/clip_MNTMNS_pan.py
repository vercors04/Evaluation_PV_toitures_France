import numpy as np
import rasterio
from rasterio.features import rasterize


def clip_MNSMNT_pans(mns_path, mnt_path, gdf, buffer=0.7, mnh_min=2, debug=False):
    """
    masques pixels toiture depuis MNS, MNT et BD TOPO.
    --------
    @param[in]  mns_path : chemin vers MNS IGN
    @param[in]  mnt_path : chemin vers MNT IGN
    @param[in]  gdf      : GeoDataFrame BD TOPO filtrée
    @param[in]  buffer   : tampon en m autour des géométries BD
    @param[in]  mnh_min   : seuil MNH pour filtrer pixels non-toiture
    @param[in]  debug    : si True, exporte rasters intermédiaires

    @param[out] meta           : dict           — métadonnées rasterio pour exports ultérieurs
    @param[out] pts_ok         : np.ndarray 1D  — masque booléen des points retenus
    @param[out] masque_bat     : np.ndarray 2D  — index GDF bâtiment si toit, 0 sinon
    @param[out] mns            : np.ndarray 2D  — MNS original masqué aux emprises bâtiments
    @param[out] transform      : affine         — transformation affine du raster (pour passer des coordonnées spatiales aux indices de matrice)
    """

    # --- chargement ---
    with rasterio.open(mns_path) as src: #gere automatiquement la liberation de la memoire
        mns        = src.read(1).astype(np.float32) #read(1) : on garde que la premiere bande du raster (ici on a que 1 bande)
        transform  = src.transform #transformation affine pour passer des coordonnées spatiales aux indices de matrice
        meta       = src.meta.copy() #métadonnées du raster (dimensions, résolution, système de référence, etc.)
        nodata     = src.nodata #valeur utilisée pour les pixels sans données (ex: hors dalle, ou pixels invalides)
        resolution = src.res[0] #resol du raster, un tuple pour x et pour y 

    with rasterio.open(mnt_path) as src:
        mnt = src.read(1).astype(np.float32)

    if nodata is not None:
        mns[mns == nodata] = np.nan #remplace les pixels sans données par NaN pour eviter valeurs aberantes
        mnt[mnt == nodata] = np.nan

    # --- MNH + rasterisation ---
    mnh = mns - mnt

    geometries = gdf.geometry.buffer(buffer)
    masque_bat = rasterize( #rasterize prends une liste de paire, forme et valeur
        zip(geometries, gdf.index), #en gros on garde que la colonne des geometrie, y met un buffer 
        out_shape=mns.shape,
        transform=transform,
        fill=0,
        dtype="int32"
    )

    # --- MNS masqué ---
    pts_ok = (
        (masque_bat > 0) &
        (mnh >= mnh_min) &
        np.isfinite(mns) &
        np.isfinite(mnt)
    )

    if debug:
        import os
        debug_dir = os.path.dirname("data/processed/DIDIER/")
        meta_float = {**meta, "dtype": "float32", "nodata": -9999}

        # MNS découpé aux emprises bâtiments (avec buffer et filtre MNH)
        mns_debug = np.where(pts_ok, mns, np.nan).astype(np.float32)
        mns_debug_out = np.where(np.isnan(mns_debug), -9999, mns_debug).astype(np.float32)
        
        with rasterio.open(os.path.join(debug_dir, "debug_mns_toits.tif"), "w", **meta_float) as dst:
            dst.write(mns_debug_out, 1)

    return pts_ok, masque_bat, mns, transform, meta
