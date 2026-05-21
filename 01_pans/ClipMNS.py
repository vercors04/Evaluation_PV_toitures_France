import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
import geopandas as gpd
import re
from ExtractBDtopo import *


def clipMNS(mns_path, gdf):
    """
    Découpe le MNS IGN par l'emprise de chaque bâtiment avec BD topo bati.
    ---------------------------------------------------------------------------------------
    @param[in]  mns_path : Chemin vers le MNS IGN .tif complet
    @param[in]  gdf      : BD TOPO filtrée

    @param[out] buildings : Liste de dicts, un par bâtiment :
                            {
                              'cleabs'  : identifiant unique,
                              'usage'   : type de bâtiment,
                              'hauteur' : hauteur en m,
                              'mns'     : matrice numpy 2D (pixels du toit),
                              'transf'  : transformation affine de la vignette
                            }
    ---------------------------------------------------------------------------------------
    """
    buildings = [] #liste contenant un dictionnaire pour chaque batiment
                   #chaque dictionnaire contient les infos du batiment (usage, hauteur, ...)

    with rasterio.open(mns_path) as src:
        for _, row in gdf.iterrows(): #pour tout les batiments dans le BDTopo bat
            try:

                mns_clip, transf = rasterio_mask(
                    src, #dalle initiale
                    [row.geometry], #pose masque contours batiment
                    crop=True, #réduit la matrice au rectangle entourant le batiment
                    nodata=np.nan, #pixel hors de ces rectangle -> NaN
                    filled=True
                )
                mns_clip = mns_clip[0].astype('float32')  # on supr donnees inutile pour garder que la matrice 2D
                mns_clip[mns_clip == src.nodata] = np.nan

                n_valid = np.sum(~np.isnan(mns_clip)) #si batiment avec aucun pixel valide on ignore
                if n_valid == 0:
                    continue

                #stockage dans le dictionnaire 
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
    mns_filename = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"
    tile_bounds  = TileBounds(mns_filename) #bords du domaine

    gdf = LoadBuild("data/raw/vienne.gpkg", tile_bounds) #batiments dans cette zone

    buildings = clipMNS( #decoupe le MNS
        f"data/raw/{mns_filename}",
        gdf
    )

    #reccolement de la grande dalle
    with rasterio.open(f"data/raw/{mns_filename}") as src:
        mns_batiments = np.full((src.height, src.width), np.nan, dtype='float32')
        transf_global = src.transform
        for b in buildings:
            row_off, col_off = rasterio.transform.rowcol(
                transf_global,
                b['transf'].c,  
                b['transf'].f    
            )
            h, w = b['mns'].shape
            mns_batiments[row_off:row_off+h, col_off:col_off+w] = np.where(
                ~np.isnan(b['mns']),
                b['mns'],
                mns_batiments[row_off:row_off+h, col_off:col_off+w]
            )

     
        with rasterio.open(
            "data/processed/mns_didier_ign_nettoye.tif",
            'w', driver='GTiff',
            height=src.height, width=src.width,
            count=1, dtype='float32',
            crs='EPSG:2154', transform=transf_global,
            nodata=np.nan
        ) as dst:
            dst.write(mns_batiments, 1)

    print("Sauvegardé : data/processed/mns_ign_nettoye2.tif")