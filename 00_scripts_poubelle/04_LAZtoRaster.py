import laspy
import sys
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import uniform_filter, binary_erosion

def laz_raster(path_in, path_out, resol, classe):
    """
    Convertit un nuage de points LAZ en raster GeoTIFF (MNS brut).
    ---------------------------------------------------------------------------------------
    @param[in]  path_in  : Chemin vers le .laz
    @param[in]  path_out : Chemin du .tif de sortie
    @param[in]  resol    : Taille pixel en m
    @param[in]  classe   : Classe LiDAR à rasteriser (6 = bâtiment)
    @param[out] mns      : Matrice NumPy 2D du MNS
    @param[out] transf   : Transformation affine géographique
    ---------------------------------------------------------------------------------------
    """
    try:
        las = laspy.read(path_in)
    except Exception:
        print(f"Erreur : Impossible de lire {path_in}")
        sys.exit(1)

    x = np.array(las.x[las.classification == classe])
    y = np.array(las.y[las.classification == classe])
    z = np.array(las.z[las.classification == classe])

    if len(x) == 0:
        print(f"Aucun point de classe {classe}")
        sys.exit(1)

    x_min = np.floor(x.min() / resol) * resol
    x_max = np.ceil(x.max()  / resol) * resol
    y_min = np.floor(y.min() / resol) * resol
    y_max = np.ceil(y.max()  / resol) * resol

    n_rows = int((y_max - y_min) / resol)
    n_cols = int((x_max - x_min) / resol)
    print(f"Grille : {n_cols} colonnes × {n_rows} lignes")

    col_idx = np.clip(((x - x_min) / resol).astype(int), 0, n_cols - 1)
    row_idx = np.clip(((y_max - y) / resol).astype(int), 0, n_rows - 1)

    mns_max = np.full((n_rows, n_cols), -np.inf)
    np.maximum.at(mns_max, (row_idx, col_idx), z)

    mns = np.where(mns_max > -np.inf, mns_max, np.nan).astype('float32')
    print(f"Pixels remplis : {np.sum(~np.isnan(mns)):,} | vides : {np.sum(np.isnan(mns)):,}")

    transf = from_origin(x_min, y_max, resol, resol)
    _save_tif(mns, path_out, n_rows, n_cols, transf)
    return mns, transf


def mask_vegetation(mns, roughness_threshold=0.8):
    """
    Masque les pixels de végétation par rugosité locale (écart-type fenêtre 3x3).
    Ref : seuil 0.8m — Cheng et al. 2016, Remote Sensing.
    ---------------------------------------------------------------------------------------
    @param[in]  mns                 : MNS NumPy 2D
    @param[in]  roughness_threshold : Seuil écart-type en m
    @param[out] mns_cleaned         : MNS filtré
    ---------------------------------------------------------------------------------------
    """
    nan_mask = np.isnan(mns)
    # Remplacer NaN par moyenne locale pour ne pas polluer le calcul
    mns_tmp = np.where(nan_mask, uniform_filter(np.where(nan_mask, 0.0, mns), size=3), mns)

    # std locale = sqrt(E[X²] - E[X]²)
    std_map = np.sqrt(np.maximum(
        uniform_filter(mns_tmp**2, size=3) - uniform_filter(mns_tmp, size=3)**2, 0
    ))

    veg_mask = std_map > roughness_threshold
    print(f"  Pixels végétation masqués : {np.sum(veg_mask & ~nan_mask):,}")

    cleaned = mns.copy()
    cleaned[veg_mask] = np.nan
    return cleaned


def fill_gaps(mns, max_gap=5):
    """
    Comble uniquement les trous INTERNES (NaN entourés de pixels valides).
    Ne déborde pas en dehors des bâtiments.
    ---------------------------------------------------------------------------------------
    @param[in]  mns      : MNS NumPy 2D
    @param[in]  max_gap  : Nb max d'itérations (1 iter ≈ 1 pixel de rayon)
    @param[out] mns_filled : MNS avec trous internes comblés
    ---------------------------------------------------------------------------------------
    Principe : à chaque itération, on identifie les NaN internes via binary_erosion
    du masque des pixels valides — seuls les NaN entourés de voisins valides sont comblés.
    """
    mns_filled = mns.copy()

    for iteration in range(max_gap):
        nan_mask = np.isnan(mns_filled)
        if not np.any(nan_mask):
            break

        # Pixels valides
        valid_mask = ~nan_mask

        # Éroder le masque valide : ne garde que les pixels valides
        # dont TOUS les voisins 3x3 sont aussi valides ou NaN interne
        # Un NaN est "interne" s'il est entouré de pixels valides
        # On détecte ça en dilatant le masque valide et en cherchant
        # les NaN qui touchent des pixels valides
        neighbor_sum   = np.zeros_like(mns_filled)
        neighbor_count = np.zeros_like(mns_filled)
        data  = np.where(nan_mask, 0.0, mns_filled)
        valid = valid_mask.astype(float)

        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            neighbor_sum   += np.roll(np.roll(data,  dr, axis=0), dc, axis=1) * \
                              np.roll(np.roll(valid, dr, axis=0), dc, axis=1)
            neighbor_count += np.roll(np.roll(valid, dr, axis=0), dc, axis=1)

        # Un NaN est interne s'il a AU MOINS 4 voisins valides sur 8
        # (évite de combler les bords où il n'y a que 1-2 voisins)
        internal_nan = nan_mask & (neighbor_count >= 4)

        if not np.any(internal_nan):
            break

        with np.errstate(invalid='ignore'):
            mean_neighbors = np.where(neighbor_count > 0,
                                      neighbor_sum / neighbor_count, np.nan)

        mns_filled = np.where(internal_nan, mean_neighbors, mns_filled)

        n_filled = np.sum(nan_mask) - np.sum(np.isnan(mns_filled))
        print(f"  Itération {iteration+1} : {n_filled:,} pixels comblés")

    print(f"  Trous restants : {np.sum(np.isnan(mns_filled)):,} pixels")
    return mns_filled


def _save_tif(mns, path_out, n_rows, n_cols, transf):
    """Sauvegarde un tableau numpy en GeoTIFF Lambert 93."""
    with rasterio.open(
        path_out, 'w', driver='GTiff',
        height=n_rows, width=n_cols, count=1,
        dtype='float32', crs='EPSG:2154',
        transform=transf, nodata=np.nan
    ) as dst:
        dst.write(mns.astype('float32'), 1)
    print(f"  Sauvegardé : {path_out}")


if __name__ == "__main__":

    # --- MNS brut ---
    print("=== Rasterisation ===")
    mns_brut, transf = laz_raster(
        path_in="data/raw/fic1.laz",
        path_out="data/processed/mns_brut.tif",
        resol=0.5,
        classe=6
    )

    # --- Nettoyage ---
    print("\n=== Masquage végétation ===")
    mns_clean = mask_vegetation(mns_brut, roughness_threshold=0.8)

    print("\n=== Remplissage trous internes ===")
    mns_final = fill_gaps(mns_clean, max_gap=5)

    # --- MNS nettoyé ---
    print("\n=== Export MNS nettoyé ===")
    _save_tif(mns_final, "data/processed/mns_nettoye.tif",
              mns_final.shape[0], mns_final.shape[1], transf)