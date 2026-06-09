import os
import sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # accès au package src/
from ancienne_pipeline.src.detection.selec_Pans import *
from ancienne_pipeline.src.extraction.clip_LAZ import *
from ancienne_pipeline.src.detection.Ransac import *
from ancienne_pipeline.src.io.util import *
from ancienne_pipeline.src.ombrage.pvgis import *
import time



LAZ_NAME ="LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz"#INRAE
LAZ_PATH = f"data/raw/INRAE/{LAZ_NAME}" #INRAE
OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE
MNS_NAME = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"  # INRAE
MNS_PATH = f"data/raw/INRAE/{MNS_NAME}"                       # INRAE

# LAZ_NAME ="LHD_FXX_0495_6611_PTS_LAMB93_IGN69.copc.laz"#DIDIER
# LAZ_PATH = f"data/raw/DIDIER/{LAZ_NAME}" #DIDIER
# OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
# MNS_NAME = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"   # DIDIER (non utilisé ici)

GPKG_PATH = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"

def main():
    t0 = time.time()
    if not os.path.exists(LAZ_PATH):
        print(f"Erreur : fichier introuvable → {LAZ_NAME}")
        sys.exit(1)

    base    = LAZ_NAME.replace(".copc.laz", "")
    nuages = clipLAZ(LAZ_PATH, eps=0.9, min_pts=20, min_cluster=50, classe=6)
    print(f"clipLAZ : {time.time()-t0:.1f}s")


    path_gpkg = os.path.join(OUT_DIR, f"{base}_clust.gpkg")
    path_laz = os.path.join(OUT_DIR, f"{base}_clust.laz")

    sauvIsolBatGPKG(nuages, path_gpkg) #graph qui montre les clusters isolés sur la dalle (voir la séparation des batiments)
    sauvLAZ(nuages, path_laz) #graph qui montre les nuages de points sur la dalle
    
    
    #PANS ransac
    print("=====RANSAC=====")
    pans_r = ransacTot(nuages)
    print(f"ransac : {time.time()-t0:.1f}s")

    path_pans = os.path.join(OUT_DIR, f"{base}_LAZpans_ransac.gpkg")
    sauvPansGPKG(pans_r, path_pans) #graph qui montre les pans détectés par ransac (voir la séparation des pans)
    print(f"nombre de batiments {len(nuages)}")
    print(f"Pans détectés : {len(pans_r)}")
    print(f"Creation fichiers : {time.time()-t0:.1f}s")
    


    pans_ok  = selecPans(pans_r)
    print(f"selec : {time.time()-t0:.1f}s")




    # PVGIS
    path_pans_pvg = os.path.join(OUT_DIR, f"{base}_LAZpans_pvgis.gpkg")
    pans_pvg = pvgisTousPans(pans_ok)  #graph qui montre les pans sélectionnés pour PVGIS (voir la séparation des pans sélectionnés pour PVGIS)
    print(f"pvgis : {time.time()-t0:.1f}s")

    sauvPansGPKG(pans_pvg, path_pans_pvg)



    # STATS
    pentes  = [p["pente"]  for p in pans_pvg]
    azimuts = [p["azimut"] for p in pans_pvg]
    prods   = [p["production_kwh_an"] for p in pans_pvg if p["production_kwh_an"]]

    print(f"\n===== STATS =====")
    print(f"Pans analysés        : {len(pans_pvg)}")
    print(f"Pente moyenne        : {np.mean(pentes):.1f}°")
    print(f"Pente min/max        : {np.min(pentes):.1f}° / {np.max(pentes):.1f}°")

    print(f"\nRépartition azimut :")
    print(f"  Nord  (315-45°)  : {sum(1 for a in azimuts if a >= 315 or a < 45)} pans")
    print(f"  Est   (45-135°)  : {sum(1 for a in azimuts if 45 <= a < 135)} pans")
    print(f"  Sud   (135-225°) : {sum(1 for a in azimuts if 135 <= a < 225)} pans")
    print(f"  Ouest (225-315°) : {sum(1 for a in azimuts if 225 <= a < 315)} pans")

    print(f"\nProduction totale    : {sum(prods):,.0f} kWh/an")
    print(f"Production moyenne   : {np.mean(prods):,.0f} kWh/an par pan")
    print(f"Production max       : {np.max(prods):,.0f} kWh/an")


if __name__ == "__main__":
    main()