#==============VISUALISATION=================
import geopandas as gpd
import pandas as pd
import laspy
import numpy as np
import os
import rasterio
import geopandas as gpd
from shapely.geometry import MultiPoint

def sauvRast(mns_path, buildings, raster_out):
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


def sauvPansGPKG(tous_pans, path_out, crs=2154):


    lignes = []
    for pan in tous_pans:
        pts = pan["points"]
        # enveloppe convexe 2D des points du pan
        geom = MultiPoint(pts[:, :2]).convex_hull

        # lignes.append({
        #     "bat_id": pan["bat_id"],
        #     "pente":  pan["pente"],
        #     "azimut": pan["azimut"],
        #     "n_pts":  len(pts),
        #     "geometry": geom
        # })
        lignes.append({
            "bat_id":             pan["bat_id"],
            "pente":              pan["pente"],
            "azimut":             pan["azimut"],
            "n_pts":              len(pts),
            "surf_m2":            pan.get("surf_m2"),
            "puissance_kwc":      pan.get("puissance_kwc"),
            "irradiation_kwh_m2": pan.get("irradiation_kwh_m2"),
            "production_kwh_an":  pan.get("production_kwh_an"),
            "geometry":           geom
        })

    gdf = gpd.GeoDataFrame(lignes, crs=crs)
    gdf.to_file(path_out, driver="GPKG")

def sauvLAZ(nuages, path_out):
    import pyproj

    xyz_all = np.vstack(nuages)
    ids = np.concatenate([
        np.full(len(pts), i, dtype=np.int32)
        for i, pts in enumerate(nuages)
    ])

    header = laspy.LasHeader(point_format=0, version="1.2")
    header.offsets = np.array([
        xyz_all[:,0].min(),
        xyz_all[:,1].min(),
        xyz_all[:,2].min()
    ])
    header.scales = np.array([0.001, 0.001, 0.001])
    header.add_crs(pyproj.CRS.from_epsg(2154))
    header.add_extra_dim(laspy.ExtraBytesParams(name="bat_id", type=np.int32))

    las = laspy.LasData(header=header)
    las.x = xyz_all[:, 0]
    las.y = xyz_all[:, 1]
    las.z = xyz_all[:, 2]
    las.bat_id = ids

    las.write(path_out)
    print(f"LAZ écrit : {path_out} ({len(xyz_all)} points, {len(nuages)} bâtiments)")


def sauvIsolBatGPKG(nuages, path_out, crs=2154):


    os.makedirs(os.path.dirname(path_out), exist_ok=True)

    xyz_all = np.vstack(nuages)
    ids = np.concatenate([
        np.full(len(pts), i, dtype=np.int32)
        for i, pts in enumerate(nuages)
    ])

    df = pd.DataFrame({
        "bat_id": ids,
        "x": xyz_all[:, 0],
        "y": xyz_all[:, 1],
        "z": xyz_all[:, 2],
    })

    geometry = gpd.points_from_xy(df["x"], df["y"])
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
    gdf.to_file(path_out, driver="GPKG")


