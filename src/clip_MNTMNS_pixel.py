import numpy as np
import rasterio
from rasterio.features import rasterize


def clip_MNSMNT_pixels(mns_path, mnt_path, gdf, buffer=1.2, mnh_min=1.5, debug=False):
    """
    masques pixels toiture depuis MNS, MNT et BD TOPO.
    --------
    @param[in]  mns_path : chemin vers MNS IGN
    @param[in]  mnt_path : chemin vers MNT IGN
    @param[in]  gdf      : GeoDataFrame BD TOPO filtrée
    @param[in]  buffer   : tampon en m autour des géométries BD
    @param[in]  mnh_min   : seuil MNH pour filtrer pixels non-toiture
    @param[in]  debug    : si True, exporte rasters intermédiaires

    @param[out] masque_incline : np.ndarray 2D  — index GDF bâtiment si toit incliné (10-60°), 0 sinon
    @param[out] masque_plat    : np.ndarray 2D  — index GDF bâtiment si toit plat (<10°),      0 sinon
    @param[out] pente          : np.ndarray 2D  — pente en degrés
    @param[out] aspect         : np.ndarray 2D  — aspect en degrés convention boussole
    @param[out] meta           : dict           — métadonnées rasterio pour exports ultérieurs
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


    # --- gradient → pente + aspect ---
    dz_dy, dz_dx = np.gradient(mns, resolution)
    pente  = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))
    aspect = np.degrees(np.arctan2(-dz_dx, dz_dy)) % 360

    pente [~pts_ok] = np.nan
    aspect[~pts_ok] = np.nan

    # --- masques finaux ---
    masque_incline = np.where(
        pts_ok &
        (pente >= 10) & (pente <= 45) &
        (aspect >= 90) & (aspect <= 270),
        masque_bat, 0
    ).astype("int32")

    masque_plat = np.where(
        pts_ok &
        (pente < 10),
        masque_bat, 0
    ).astype("int32")
    
    # --- debug ---
    if debug:
        import os
        debug_dir  = os.path.dirname("data/processed/DIDIER/")
        meta_float = {**meta, "dtype": "float32", "nodata": -9999}
        meta_int   = {**meta, "dtype": "int32",   "nodata": 0}

        for nom, arr, m in [
            ("debug_mnh_masque",     np.where(pts_ok, mnh, np.nan),            meta_float),
            ("debug_pente_filtree", np.where((pente <= 45) & pts_ok, pente, np.nan), meta_float),
            ("debug_aspect",         aspect,         meta_float),
            ("debug_masque_incline", masque_incline, meta_int),
            ("debug_masque_plat",    masque_plat,    meta_int),
        ]:
            arr_out = np.where(np.isnan(arr), m["nodata"], arr).astype(m["dtype"])
            with rasterio.open(os.path.join(debug_dir, f"{nom}.tif"), "w", **m) as dst:
                dst.write(arr_out, 1)

    return masque_incline, masque_plat, pente, aspect, meta