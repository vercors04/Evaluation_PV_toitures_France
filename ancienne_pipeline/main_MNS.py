import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # accès au package src/
from ancienne_pipeline.src.extraction.clip_MNSBDTOPO import *
from ancienne_pipeline.src.extraction.clip_MNSBDTOPO_autre import *
from ancienne_pipeline.src.detection.Ransac          import *
from ancienne_pipeline.src.io.util                   import *

MNS_NAME  = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"#DIDIER
MNS_PATH  = f"data/raw/DIDIER/{MNS_NAME}" #DIDIER
OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
    
# MNS_NAME  = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"#INRAE
# MNS_PATH  = f"data/raw/INRAE/{MNS_NAME}" #INRAE
# OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE
    
    
GPKG_FILE = "BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
GPKG_PATH = f"data/raw/{GPKG_FILE}"

def main():
        
    t0 = time.time()

    if not os.path.exists(MNS_PATH):
        print(f"Erreur : fichier introuvable → {MNS_NAME}")
        sys.exit(1)

    base    = MNS_NAME.replace(".tif", "")
    path_mns_0Buffer = os.path.join(OUT_DIR, f"{base}_MNS_sansBuffer.tif")
    path_mns_1Buffer = os.path.join(OUT_DIR, f"{base}_MNS_avecBuffer.tif")

    tile_bounds = tileBounds(MNS_NAME)
    gdf         = loadBuild(GPKG_PATH, tile_bounds)


    # MNS sans buffer
    buildings_0b   = clipMNSBDTOPO(MNS_PATH, gdf)
    print(f"clipMNSBDTOPO 0b: {time.time()-t0:.1f}s")

    sauvRast(MNS_PATH, buildings_0b, path_mns_0Buffer) #graph qui montre les batiments détectés sur la dalle (voir la séparation des batiments)
    print(f"Creation fichiers : {time.time()-t0:.1f}s")

    # MNS AVEC GRAPH
    buildings_1b = clipMNSBDTOPO_gpkg(MNS_PATH, gdf, debug_gpkg="data/processed/DIDIER/debug_clip_geoms.gpkg")
    sauvRast(MNS_PATH, buildings_1b, path_mns_1Buffer)
    print(f"clipMNSBDTOPO 1b + gpkg: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
