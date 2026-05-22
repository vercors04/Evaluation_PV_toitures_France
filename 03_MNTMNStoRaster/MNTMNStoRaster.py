import os
import sys
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter, binary_opening, binary_closing, label


def charger_dalle(mns_path):
    """
    Charge la dalle MNS et son MNT associé (même tuile IGN).
    Le chemin du MNT est dérivé automatiquement en remplaçant 'MNS' par 'MNT'.
    ---------------------------------------------------------------------------------------
    @param[in]  mns_path : Chemin vers le fichier MNS IGN (.tif)
    @param[out] mns      : Matrice NumPy 2D du MNS (élévations absolues)
    @param[out] mnt      : Matrice NumPy 2D du MNT (terrain nu)
    @param[out] meta     : Métadonnées rasterio (transform, crs, shape…)
    ---------------------------------------------------------------------------------------
    """
    mnt_path = mns_path.replace('MNS', 'MNT')

    if not os.path.exists(mnt_path):
        print(f"Erreur : MNT introuvable → {mnt_path}")
        sys.exit(1)

    with rasterio.open(mns_path) as src:
        mns = src.read(1).astype('float32')
        if src.nodata is not None:
            mns[mns == src.nodata] = np.nan
        meta = src.meta.copy()
        meta.update(dtype='float32', count=1, nodata=np.nan)

    with rasterio.open(mnt_path) as src:
        mnt = src.read(1).astype('float32')
        if src.nodata is not None:
            mnt[mnt == src.nodata] = np.nan

    print(f"MNS : {os.path.basename(mns_path)}")
    print(f"MNT : {os.path.basename(mnt_path)}")
    return mns, mnt, meta


def calculer_ndsm(mns, mnt):
    """
    Calcule le nDSM : hauteur de chaque pixel au-dessus du sol (MNS − MNT).
    ---------------------------------------------------------------------------------------
    @param[in]  mns  : MNS brut
    @param[in]  mnt  : MNT terrain nu
    @param[out] ndsm : Matrice 2D des hauteurs relatives (m)
    ---------------------------------------------------------------------------------------
    """
    ndsm = mns - mnt
    ndsm[np.isnan(mns) | np.isnan(mnt)] = np.nan
    print(f"nDSM calculé — pixels valides : {np.sum(~np.isnan(ndsm)):,}")
    return ndsm


def rugosité_locale(mns, taille=3):
    """
    Calcule l'écart-type local du MNS dans une fenêtre glissante.
    Végétation = surface rugueuse (std élevé).
    Bâtiments  = surface lisse   (std faible).
    ---------------------------------------------------------------------------------------
    @param[in]  mns    : MNS NumPy 2D
    @param[in]  taille : Taille de la fenêtre (pixels)
    @param[out] std    : Carte de rugosité 2D (m)
    ---------------------------------------------------------------------------------------
    """
    nan_mask = np.isnan(mns)
    mns_tmp  = np.where(nan_mask, 0.0, mns)

    std_map = np.sqrt(np.maximum(
        uniform_filter(mns_tmp**2, size=taille) -
        uniform_filter(mns_tmp,    size=taille)**2,
        0
    ))
    std_map[nan_mask] = np.nan
    return std_map


def extraire_batiments(mns, ndsm, h_min=2.0, h_max=50.0,
                       rugosité_max=0.4, surface_min_m2=10.0, resol=0.5):
    """
    Extrait les bâtiments par combinaison de trois critères :
      1. Hauteur au-dessus du sol (nDSM)  → élimine sol et végétation basse
      2. Rugosité locale du MNS           → élimine la végétation haute
      3. Nettoyage morphologique          → supprime le bruit résiduel
    ---------------------------------------------------------------------------------------
    @param[in]  mns            : MNS brut
    @param[in]  ndsm           : Hauteur au-dessus du sol (m)
    @param[in]  h_min          : Hauteur min pour être un bâtiment (m)
    @param[in]  h_max          : Hauteur max — élimine les outliers (m)
    @param[in]  rugosité_max   : Seuil écart-type — au-delà = végétation (m)
    @param[in]  surface_min_m2 : Surface minimale d'un objet retenu (m²)
    @param[in]  resol          : Résolution du raster (m/pixel)
    @param[out] masque         : Masque booléen 2D (True = bâtiment)
    ---------------------------------------------------------------------------------------
    """
    # 1. Filtre hauteur
    masque = (ndsm >= h_min) & (ndsm <= h_max)
    print(f"  Filtre hauteur  [{h_min}–{h_max} m]   : {np.sum(masque):,} pixels")

    # 2. Filtre rugosité (lissage = bâtiment, rugosité = végétation)
    rug = rugosité_locale(mns)
    masque_lisse = (rug < rugosité_max) & ~np.isnan(rug)
    masque = masque & masque_lisse
    print(f"  Filtre rugosité [< {rugosité_max} m]      : {np.sum(masque):,} pixels")

    # 3. Opening : supprime les petits îlots de bruit (< noyau 3×3)
    masque = binary_opening(masque, structure=np.ones((3, 3)))

    # 4. Closing : referme les petits trous internes des toitures
    masque = binary_closing(masque, structure=np.ones((5, 5)))

    # 5. Suppression des objets inférieurs à surface_min_m2
    min_pixels   = max(1, int(surface_min_m2 / resol**2))
    labeled, n   = label(masque)
    for i in range(1, n + 1):
        if np.sum(labeled == i) < min_pixels:
            masque[labeled == i] = False

    print(f"  Après nettoyage morphologique : {np.sum(masque):,} pixels")
    return masque


def sauvegarder_raster(mns, masque, path_out, meta):
    """
    Sauvegarde le MNS filtré : pixels hors bâtiment → NaN.
    ---------------------------------------------------------------------------------------
    @param[in]  mns      : MNS brut
    @param[in]  masque   : Masque bâtiments (True = bâtiment)
    @param[in]  path_out : Chemin de sortie (.tif)
    @param[in]  meta     : Métadonnées rasterio
    ---------------------------------------------------------------------------------------
    """
    mns_bat = np.where(masque, mns, np.nan).astype('float32')

    with rasterio.open(path_out, 'w', **meta) as dst:
        dst.write(mns_bat, 1)

    n_bat = np.sum(masque)
    print(f"  {n_bat:,} pixels bâtiments sauvegardés → {path_out}")
    return mns_bat
