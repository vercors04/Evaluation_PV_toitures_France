import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import MultiPoint

#pour savuegarder le raster des batiments en un fichier 
def sauv_rast(mns_path, buildings, raster_out):
    with rasterio.open(mns_path) as src:
        mns_bat = np.full((src.height, src.width), np.nan, dtype='float32')
        transf_ref = src.transform # récupération de la transformation locale
        
        for b in buildings:
            # Calcul du décalage 
            row_off, col_off = rasterio.transform.rowcol(transf_ref, b['transf'].c, b['transf'].f)
            h, w = b['mns'].shape
            
            mask = ~np.isnan(b['mns'])
            mns_bat[row_off:row_off+h, col_off:col_off+w][mask] = b['mns'][mask]

        with rasterio.open(
            raster_out, 'w', driver='GTiff',
            height=src.height, width=src.width, count=1,
            dtype='float32', crs=src.crs,
            transform=transf_ref, nodata=np.nan
        ) as dst:
            dst.write(mns_bat, 1)


def sauv_pans_gpkg(tous_pans, path_out, crs=2154):

    lignes = []
    for pan in tous_pans:
        pts = pan["points"]
        # enveloppe convexe 2D des points du pan
        geom = MultiPoint(pts[:, :2]).convex_hull

        lignes.append({
            "bat_id": pan["bat_id"],
            "pente":  pan["pente"],
            "azimut": pan["azimut"],
            "n_pts":  len(pts),
            "geometry": geom
        })

    gdf = gpd.GeoDataFrame(lignes, crs=crs)
    gdf.to_file(path_out, driver="GPKG")