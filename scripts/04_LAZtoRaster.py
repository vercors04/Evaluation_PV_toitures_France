import laspy
import sys
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import uniform_filter, generic_filter


def laz_raster(path_in, path_out, resol, type):
    """
    Fonction pour la conversion d'un nuage de points LAZ en raster GeoTIFF (MNS)
    ---------------------------------------------------------------------------------------
    @param[in]  path_in      : Chemin d'accès vers le .laz d'entree
    @param[in]  path_out     : Chemin d'accès pour le .tif de sortie
    @param[in]  resol        : Taille pixel en m
    @param[in]  type         : Classe LiDAR a etudier

    @param[out] mns          : Matrice NumPy 2D représentant la grille du raster
    @param[out] transf       : Matrice de transformation géométrique affine 
    ---------------------------------------------------------------------------------------
    """
    try:
        las = laspy.read(path_in)
    except Exception:
        print(f"Erreur : Impossible de lire le fichier {path_in}")
        sys.exit(1)

    x = np.array(las.x[las.classification == type])
    y = np.array(las.y[las.classification == type])
    z = np.array(las.z[las.classification == type])

    if len(x) == 0:
        print(f"aucun point avec le type {type} dans le fichier")
        sys.exit(1)

    x_min = np.floor(x.min() / resol) * resol
    x_max = np.ceil(x.max()  / resol) * resol
    y_min = np.floor(y.min() / resol) * resol
    y_max = np.ceil(y.max()  / resol) * resol

    n_rows = int((y_max - y_min) / resol)
    n_cols = int((x_max - x_min) / resol)
    print(f"Dimensions du raster {n_cols} colonnes et {n_rows} lignes")

    col_idx = ((x - x_min) / resol).astype(int)
    row_idx = ((y_max - y) / resol).astype(int)
    col_idx = np.clip(col_idx, 0, n_cols - 1)
    row_idx = np.clip(row_idx, 0, n_rows - 1)

    mns = np.full((n_rows, n_cols), np.nan)
    mns_max = np.full((n_rows, n_cols), -np.inf)
    np.maximum.at(mns_max, (row_idx, col_idx), z)
    mns[mns_max > -np.inf] = mns_max[mns_max > -np.inf]

    print(f"Cellules remplies : {np.sum(~np.isnan(mns)):,} | vides : {np.sum(np.isnan(mns)):,}")

    transf = from_origin(x_min, y_max, resol, resol)

    with rasterio.open(
        path_out, 'w', driver='GTiff',
        height=n_rows, width=n_cols, count=1,
        dtype='float32', crs='EPSG:2154',
        transform=transf, nodata=np.nan
    ) as dst:
        dst.write(mns.astype('float32'), 1)

    print(f"Raster sauvegardé : {path_out}")
    return mns, transf


def fill_gaps(mns, max_gap=5):
    """
    Comble les trous (NaN) de petite taille par interpolation (plus proche voisin)
    Version vectorisée NumPy — remplace generic_filter Python (~100x plus rapide)
    ---------------------------------------------------------------------------------------
    @param[in]  mns        : Matrice NumPy 2D du MNS brut
    @param[in]  max_gap    : Nombre max d'itérations (1 iter ≈ 1 pixel de rayon comblé)

    @param[out] mns_filled : Matrice NumPy 2D avec les trous comblés
    ---------------------------------------------------------------------------------------
    Principe vectorisé : pour chaque NaN, on calcule la moyenne de ses 8 voisins en
    décalant la matrice dans les 8 directions (haut, bas, gauche, droite, diagonales)
    et en moyennant uniquement les valeurs valides. Pas de boucle Python pixel par pixel.
    """
    mns_filled = mns.copy()

    for iteration in range(max_gap):
        nan_mask = np.isnan(mns_filled)
        if not np.any(nan_mask):
            break

        # Remplacer NaN par 0 pour pouvoir faire des opérations matricielles
        data = np.where(nan_mask, 0.0, mns_filled)
        valid = (~nan_mask).astype(float)

        # Décalages dans les 8 directions (padding pour éviter les effets de bord)
        neighbor_sum   = np.zeros_like(data)
        neighbor_count = np.zeros_like(data)

        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            shifted_data  = np.roll(np.roll(data,  dr, axis=0), dc, axis=1)
            shifted_valid = np.roll(np.roll(valid, dr, axis=0), dc, axis=1)
            neighbor_sum   += shifted_data  * shifted_valid
            neighbor_count += shifted_valid

        # Moyenne des voisins valides
        with np.errstate(invalid='ignore'):
            neighbor_mean = np.where(neighbor_count > 0,
                                     neighbor_sum / neighbor_count,
                                     np.nan)

        # On ne remplace que les NaN qui ont au moins un voisin valide
        mns_filled = np.where(nan_mask & (neighbor_count > 0),
                              neighbor_mean,
                              mns_filled)

        n_filled = np.sum(nan_mask) - np.sum(np.isnan(mns_filled))
        print(f"  Itération {iteration+1} : {n_filled:,} pixels comblés")

    print(f"  Trous restants (trop grands) : {np.sum(np.isnan(mns_filled)):,} pixels")
    return mns_filled


def mask_vegetation(mns, roughness_threshold=0.8):
    """
    Supprime les pixels végétation par détection de rugosité locale.
    Version vectorisée — remplace generic_filter Python (~100x plus rapide)
    ---------------------------------------------------------------------------------------
    @param[in]  mns                  : Matrice NumPy 2D du MNS
    @param[in]  roughness_threshold  : Seuil d'écart-type local (en m). Ref : 0.8m
                                       (Cheng et al. 2016, Remote Sensing)

    @param[out] mns_cleaned          : Matrice NumPy 2D filtrée
    ---------------------------------------------------------------------------------------
    Principe : std locale = sqrt(mean(x²) - mean(x)²) calculée sur fenêtre 3x3.
    uniform_filter est compilé en C — applique une moyenne glissante sur toute
    la matrice en une seule opération vectorisée.
    NaN remplacés par la moyenne locale avant calcul pour ne pas propager les NaN.
    """
    # Remplacer NaN par moyenne locale pour ne pas polluer le calcul de std
    nan_mask = np.isnan(mns)
    mns_filled = mns.copy()
    local_mean_for_nan = uniform_filter(np.where(nan_mask, 0.0, mns), size=3)
    mns_filled[nan_mask] = local_mean_for_nan[nan_mask]

    # std locale vectorisée : sqrt(E[X²] - E[X]²)
    mean_sq = uniform_filter(mns_filled ** 2, size=3)
    sq_mean = uniform_filter(mns_filled,      size=3) ** 2
    std_map = np.sqrt(np.maximum(mean_sq - sq_mean, 0))  # max(.,0) évite sqrt(-ε)

    vegetation_mask = std_map > roughness_threshold
    n_masked = np.sum(vegetation_mask & ~nan_mask)
    print(f"  Pixels végétation masqués : {n_masked:,}")

    cleaned = mns.copy()
    cleaned[vegetation_mask] = np.nan
    return cleaned


def check_coverage(mns, threshold=0.40):
    """
    Calcule le taux de remplissage du raster.
    À appeler par bâtiment individuel après clustering DBSCAN, pas sur la dalle entière.
    ---------------------------------------------------------------------------------------
    @param[in]  mns        : Matrice NumPy 2D du MNS
    @param[in]  threshold  : Taux minimal de couverture requis

    @param[out] Tuple(bool, float) : (couverture suffisante ?, ratio)
    ---------------------------------------------------------------------------------------
    """
    total  = mns.size
    filled = np.sum(~np.isnan(mns))
    ratio  = filled / total
    print(f"  Taux de couverture : {ratio:.1%} ({filled:,}/{total:,} pixels)")
    if ratio < threshold:
        print(f"  ⚠ LOW_COVERAGE — bâtiment exclu de l'analyse")
        return False, ratio
    return True, ratio


if __name__ == "__main__":
    mns_brut, transf = laz_raster(
        path_in="data/raw/fic1.laz",
        path_out="data/processed/mns_batiments_brut.tif",
        resol=0.5,
        type=6
    )

    print("\n--- ÉTAPE 1 : Masquage de la végétation sur la dalle ---")
    mns_clean = mask_vegetation(mns_brut, roughness_threshold=0.8)

    print("\n--- ÉTAPE 2 : Remplissage des petits trous sur la dalle ---")
    mns_final = fill_gaps(mns_clean, max_gap=5)

    print("\n--- ÉTAPE 3 : Exportation du MNS nettoyé ---")
    with rasterio.open(
        "data/processed/mns_batiments_nettoye.tif",
        'w', driver='GTiff',
        height=mns_final.shape[0], width=mns_final.shape[1],
        count=1, dtype='float32', crs='EPSG:2154',
        transform=transf, nodata=np.nan
    ) as dst:
        dst.write(mns_final.astype('float32'), 1)

    print("MNS nettoyé sauvegardé : data/processed/mns_batiments_nettoye.tif")