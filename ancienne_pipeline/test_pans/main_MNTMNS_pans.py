import os
import sys
import time
import geopandas as gpd
from src.clip_MNTMNS_pixel import clip_MNSMNT_pixels
from ancienne_pipeline.test_pans.clip_MNTMNS_pan import clip_MNSMNT_pans
from src.ExtractBDtopo import tileBounds, loadBuild
from ancienne_pipeline.test_pans.Ransac import *

MNT_NAME  = "LHD_FXX_0495_6611_MNT_O_0M50_LAMB93_IGN69.tif"#DIDIER
MNS_NAME  = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"#DIDIER
MNS_PATH  = f"data/raw/DIDIER/{MNS_NAME}" #DIDIER
MNT_PATH = f"data/raw/DIDIER/{MNT_NAME}" #DIDIER
OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
    
# MNT_NAME  = "LHD_FXX_0475_6594_MNT_O_0M50_LAMB93_IGN69.tif"#INRAE
# MNS_NAME  = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"#INRAE
# MNS_PATH  = f"data/raw/INRAE/{MNS_NAME}" #INRAE
# MNT_PATH = f"data/raw/INRAE/{MNT_NAME}" #INRAE
# OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE

GPKG_FILE = "BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
GPKG_PATH = f"data/raw/{GPKG_FILE}"

def main():

    if not os.path.exists(MNS_PATH):
        print(f"Erreur : fichier introuvable → {MNS_NAME}")
        sys.exit(1)

    if not os.path.exists(MNT_PATH):
        print(f"Erreur : fichier introuvable → {MNT_NAME}")
        sys.exit(1)

    base    = MNS_NAME.replace(".tif", "")
    path_mns = os.path.join(OUT_DIR, f"{base}_MNTMNSbatiments.tif")
    
    t0 = time.time()
    # chargement BDTOPO
    tile_bounds = tileBounds(MNS_NAME)
    gdf         = loadBuild(GPKG_PATH, tile_bounds)
    print(f"chargement BD TOPO : {time.time()-t0:.1f}s")

    t0 = time.time()
    # masquage MNS/MNT pixel par pixel
    masque_incline, masque_plat, pente, aspect, meta = clip_MNSMNT_pixels(
        MNS_PATH, MNT_PATH, gdf, debug=True
    )
    print(f"clip pixels : {time.time()-t0:.1f}s")







if __name__ == "__main__":
    main()



    # t0 = time.time()
    # # masquage MNS/MNT par pans
    # pts_ok, masque_bat, mns, transform, meta = clip_MNSMNT_pans(
    #     MNS_PATH, MNT_PATH, gdf, debug=True
    # )
    # print(f"clip pans : {time.time()-t0:.1f}s")

    
    # t0 = time.time()
    # # RANSAC par bâtiment
    # pans_tous = ransacTot(masque_bat, pts_ok, mns, transform, gdf)

    # gdf_pans  = gpd.GeoDataFrame(pans_tous, crs=gdf.crs)
    # gdf_pans.to_file(os.path.join(OUT_DIR, "pans.gpkg"), driver="GPKG")
    # print(f"RANSAC {len(gdf_pans)} pans : {time.time()-t0:.1f}s")