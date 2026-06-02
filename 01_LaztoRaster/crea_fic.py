#==============VISUALISATION=================
import geopandas as gpd
import pandas as pd
import laspy
import numpy as np
import os

def sauv_pans_gpkg(tous_pans, path_out, crs=2154):
    import geopandas as gpd
    from shapely.geometry import MultiPoint

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
    print(f"Pans écrits : {path_out} ({len(gdf)} pans)")

def sauv_laz(nuages, path_out):
    os.makedirs(os.path.dirname(path_out), exist_ok=True)

    xyz_all = np.vstack(nuages)
    ids = np.concatenate([
        np.full(len(pts), i, dtype=np.int32)
        for i, pts in enumerate(nuages)
    ])

    header = laspy.LasHeader(point_format=0, version="1.4")
    header.add_extra_dim(laspy.ExtraBytesParams(name="bat_id", type=np.int32))
    las = laspy.LasData(header=header)
    las.x = xyz_all[:, 0]
    las.y = xyz_all[:, 1]
    las.z = xyz_all[:, 2]
    las.bat_id = ids

    las.write(path_out)
    print(f"LAZ écrit : {path_out} ({len(xyz_all)} points, {len(nuages)} bâtiments)")


def sauv_gpkg(nuages, path_out, crs=2154):


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
    print(f"GPKG écrit : {path_out} ({len(gdf)} points, {len(nuages)} bâtiments)")





