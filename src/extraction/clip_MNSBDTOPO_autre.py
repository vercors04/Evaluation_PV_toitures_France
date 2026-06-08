import numpy as np
import rasterio
import geopandas as gpd
from rasterio.mask import mask as rasterio_mask
from shapely.ops import unary_union
from src.extraction.ExtractBDtopo import *



def clipMNSBDTOPO_gpkg(mns_path, gdf, debug_gpkg=None):
    buildings  = []
    clip_geoms = []
    clip_ids   = []
    sindex     = gdf.sindex

    with rasterio.open(mns_path) as src:
        for _, row in gdf.iterrows():
            try:
                geom_buf    = row.geometry.buffer(0.7)
                voisins_idx = list(sindex.intersection(geom_buf.bounds))
                voisins_geoms = [gdf.iloc[i].geometry for i in voisins_idx
                                 if gdf.iloc[i]['cleabs'] != row['cleabs']]
                geom_clip = geom_buf.difference(unary_union(voisins_geoms)) if voisins_geoms else geom_buf

                clip_geoms.append(geom_clip)
                clip_ids.append(row['cleabs'])

                mns_clip, transf = rasterio_mask(
                    src, [geom_clip], crop=True, nodata=np.nan, filled=True
                )
                mns_clip = mns_clip[0].astype('float32')
                mns_clip[mns_clip == src.nodata] = np.nan

                z_min = np.nanmin(mns_clip)
                mns_clip[mns_clip < z_min + 1.35] = np.nan

                n_valid = np.sum(~np.isnan(mns_clip))
                if n_valid == 0:
                    continue

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

    if debug_gpkg:
        gdf_clip = gpd.GeoDataFrame({'cleabs': clip_ids, 'geometry': clip_geoms}, crs=2154)
        gdf_clip.to_file(debug_gpkg, driver="GPKG")
        print(f"Debug clip geoms : {debug_gpkg}")

    print(f"Bâtiments extraits : {len(buildings)}/{len(gdf)}")
    return buildings