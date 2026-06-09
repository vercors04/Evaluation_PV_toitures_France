import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.ops import unary_union
from ancienne_pipeline.src.extraction.ExtractBDtopo import *


def clipMNSBDTOPO(mns_path, gdf):
    """
    Découpe le MNS IGN par l'emprise de chaque bâtiment avec BD topo bati.
    ---------------------------------------------------------------------------------------
    @param[in]  mns_path : Chemin vers le fichier MNS IGN
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
                    'usage'  : row['nature'],
                    'hauteur': row['hauteur'],
                    'mns'    : mns_clip,
                    'transf' : transf
                })

            except Exception as e:
                print(f"  Erreur bâtiment {row['cleabs']} : {e}")
                continue

    print(f"Bâtiments extraits : {len(buildings)}/{len(gdf)}")
    return buildings