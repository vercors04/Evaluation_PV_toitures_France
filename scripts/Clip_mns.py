import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
import geopandas as gpd
import re
from ExtractBDtopo import *


def clip_mns_by_buildings(mns_path, gdf):
    """
    Découpe le MNS IGN par l'emprise de chaque bâtiment.
    ---------------------------------------------------------------------------------------
    @param[in]  mns_path : Chemin vers le MNS IGN .tif
    @param[in]  gdf      : GeoDataFrame des bâtiments (BD TOPO filtrée)

    @param[out] buildings : Liste de dicts, un par bâtiment :
                            {
                              'cleabs'  : identifiant unique,
                              'usage'   : type de bâtiment,
                              'hauteur' : hauteur en m,
                              'mns'     : matrice numpy 2D (pixels du toit),
                              'transf'  : transformation affine de la vignette
                            }
    ---------------------------------------------------------------------------------------
    rasterio_mask() découpe un raster selon un polygone — les pixels hors polygone
    deviennent nodata (NaN). On récupère une petite matrice centrée sur le bâtiment.
    """
    buildings = []

    with rasterio.open(mns_path) as src:
        for _, row in gdf.iterrows():
            try:
                # Découpe le raster selon le polygone du bâtiment
                # crop=True : réduit la matrice à l'emprise minimale du polygone
                mns_clip, transf = rasterio_mask(
                    src,
                    [row.geometry],
                    crop=True,
                    nodata=np.nan,
                    filled=True
                )
                mns_clip = mns_clip[0].astype('float32')  # bande 1 → 2D
                mns_clip[mns_clip == src.nodata] = np.nan

                # Ignorer les bâtiments sans aucun pixel valide
                n_valid = np.sum(~np.isnan(mns_clip))
                if n_valid == 0:
                    continue

                buildings.append({
                    'cleabs' : row['cleabs'],
                    'usage'  : row['usage_1'],
                    'hauteur': row['hauteur'],
                    'mns'    : mns_clip,
                    'transf' : transf
                })

            except Exception as e:
                print(f"  Erreur bâtiment {row['cleabs']} : {e}")
                continue

    print(f"Bâtiments extraits : {len(buildings)}/{len(gdf)}")
    return buildings


if __name__ == "__main__":
    mns_filename = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"
    tile_bounds  = parse_tile_bounds(mns_filename)

    gdf = load_buildings("data/raw/vienne.gpkg", tile_bounds)

    buildings = clip_mns_by_buildings(
        f"data/raw/{mns_filename}",
        gdf
    )

    # Afficher quelques stats sur les vignettes extraites
    for b in buildings[:5]:
        h, w = b['mns'].shape
        n_valid = np.sum(~np.isnan(b['mns']))
        total   = b['mns'].size
        print(f"{b['cleabs']} | {b['usage']:25s} | "
              f"{w*0.5:.0f}m x {h*0.5:.0f}m | "
              f"couverture {n_valid/total:.0%}")
        
    with rasterio.open(f"data/raw/{mns_filename}") as src:
        mns_batiments = np.full((src.height, src.width), np.nan, dtype='float32')
        transf_global = src.transform

        # Recoller chaque vignette dans le raster global
        for b in buildings:
            # Convertir les coordonnées de la vignette en indices dans le raster global
            row_off, col_off = rasterio.transform.rowcol(
                transf_global,
                b['transf'].c,   # x coin haut-gauche de la vignette
                b['transf'].f    # y coin haut-gauche de la vignette
            )
            h, w = b['mns'].shape
            mns_batiments[row_off:row_off+h, col_off:col_off+w] = np.where(
                ~np.isnan(b['mns']),
                b['mns'],
                mns_batiments[row_off:row_off+h, col_off:col_off+w]
            )

        # Sauvegarder
        with rasterio.open(
            "data/processed/mns_ign_nettoye.tif",
            'w', driver='GTiff',
            height=src.height, width=src.width,
            count=1, dtype='float32',
            crs='EPSG:2154', transform=transf_global,
            nodata=np.nan
        ) as dst:
            dst.write(mns_batiments, 1)

    print("Sauvegardé : data/processed/mns_ign_nettoye.tif")