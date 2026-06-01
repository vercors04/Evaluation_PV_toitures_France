import os
import sys
import numpy as np
import rasterio
import pandas as pd
from ClipMNS      import *
from ExtractBDtopo import *
from Ransac       import *

THRESHOLD   = 0.15
MIN_RATIO   = 0.15
MAX_PENTE   = 70.0
MIN_SURFACE = 5.0


def sauv_raster(mns_path, buildings, raster_out):
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


def _analyser_pans(buildings):
    """Lance le RANSAC sur une liste de bâtiments et retourne un DataFrame."""
    resultats = []
    for b in buildings:

        points = MNSToPointCloud(b['mns'], b['transf'])
        if points is None or len(points) < 10:
            continue

        points = RemoveNoise(points)
        if len(points) < 10:
            continue

        planes = DetectMultiPlanes(points, min_ratio=MIN_RATIO, threshold=THRESHOLD)

        for w, pts in planes:
            pente, azimut = PlaneToAngles(w)
            surface = len(pts) * 0.25
            if pente > MAX_PENTE or surface < MIN_SURFACE:
                continue
            resultats.append({
                'cleabs'     : b['cleabs'],
                'usage'      : b['usage'],
                'pente'      : pente,
                'azimut'     : azimut,
                'surface'    : round(surface, 1),
                'orientation': AzimutToOrientation(azimut)
            })
    return pd.DataFrame(resultats)



def main():
    
    # MNS_NAME  = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"#DIDIER
    # MNS_PATH  = f"data/raw/DIDIER/{MNS_NAME}" #DIDIER
    # OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
    
    MNS_NAME  = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"#INRAE
    MNS_PATH  = f"data/raw/INRAE/{MNS_NAME}" #INRAE
    OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE
    
    
    GPKG_FILE = "BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
    GPKG_PATH = f"data/raw/{GPKG_FILE}"

    if not os.path.exists(MNS_PATH):
        print(f"Erreur : fichier introuvable → {MNS_NAME}")
        sys.exit(1)

    base_name         = os.path.splitext(MNS_NAME)[0]
    raster_out = os.path.join(OUT_DIR, f"{base_name}_batiments.tif")


    tile_bounds = TileBounds(MNS_NAME)
    gdf         = LoadBuild(GPKG_PATH, tile_bounds)
    buildings   = clipMNS(MNS_PATH, gdf)

    sauv_raster(MNS_PATH, buildings, raster_out)

    print("\n=== Analyse RANSAC — tuile entière ===")
    df = _analyser_pans(buildings)

    if df.empty:
        print("Aucun pan détecté.")
        return

    print(f"\nTotal pans détectés : {len(df)}")
    print(f"Pente moyenne       : {df['pente'].mean():.1f}°")
    print(f"Surface totale      : {df['surface'].sum():.0f} m²")
    print("\nRépartition par orientation (surface en m²) :")
    print(df.groupby('orientation')['surface'].sum().round(0))
    print("\nRépartition par orientation (nombre de pans) :")
    print(df['orientation'].value_counts())

    


if __name__ == "__main__":
    main()
