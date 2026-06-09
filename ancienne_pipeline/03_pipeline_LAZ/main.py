import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # accès au package src/
from ancienne_pipeline.src.extraction.clip_LAZ import *
from ancienne_pipeline.src.detection.Ransac import *
from ancienne_pipeline.src.io.util import *
from ancienne_pipeline.src.detection.region_g import *


# LAZ_NAME ="LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz"#INRAE
# LAZ_PATH = f"data/raw/INRAE/{LAZ_NAME}" #INRAE
# OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE

LAZ_NAME ="LHD_FXX_0495_6611_PTS_LAMB93_IGN69.copc.laz"#DIDIER
LAZ_PATH = f"data/raw/DIDIER/{LAZ_NAME}" #DIDIER
OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER

GPKG_PATH = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"

def main():
    if not os.path.exists(LAZ_PATH):
        print(f"Erreur : fichier introuvable → {LAZ_NAME}")
        sys.exit(1)

    base    = LAZ_NAME.replace(".copc.laz", "")
    nuages = clipLAZ(LAZ_PATH, eps=0.9, min_pts=20, min_cluster=50, classe=6)


    path_gpkg = os.path.join(OUT_DIR, f"{base}_clust.gpkg")
    path_laz = os.path.join(OUT_DIR, f"{base}_clust.laz")

    sauvIsolBatGPKG(nuages, path_gpkg)
    sauvLAZ(nuages, path_laz)
    
    


    #PANS ransac
    pans_r = ransacTot(nuages)
    path_pans = os.path.join(OUT_DIR, f"{base}_LAZpans_ransac.gpkg")
    sauvPansGPKG(pans_r, path_pans)

    print("=====RANSAC=====")
    print(f"Pans détectés : {len(pans_r)}")
    print(f"nombre de batiments {len(nuages)}")
    print("fichier gpk batiments + pans ok et fichier LAZ batiments ok")



    #pans region growing
    # pans_g = rg_tot(nuages)
    # path_pans = os.path.join(OUT_DIR, f"{base}_LAZpans_region_growing.gpkg")
    # sauvPansGPKG(pans_g, path_pans)

    # print("=====REGION GROWING=====")
    # print(f"Pans détectés : {len(pans_g)}")
    # print(f"nombre de batiments {len(nuages)}")
    # print("fichier gpk batiments + pans ok et fichier LAZ batiments ok")

if __name__ == "__main__":
    main()