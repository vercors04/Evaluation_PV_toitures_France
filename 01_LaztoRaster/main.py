import os
import sys
from LAZ_bati import *


LAZ_NAME ="LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz"#INRAE
LAZ_PATH = f"data/raw/INRAE/{LAZ_NAME}" #INRAE
OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE

#LAZ_NAME ="LHD_FXX_0495_6611_PTS_LAMB93_IGN69.copc.laz"#DIDIER
#LAZ_PATH = f"data/raw/DIDIER/{LAZ_NAME}" #DIDIER
#OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER

def main():
    if not os.path.exists(LAZ_PATH):
        print(f"Erreur : fichier introuvable → {LAZ_NAME}")
        sys.exit(1)

    base    = os.path.splitext(os.path.basename(LAZ_PATH))[0]
    nuages = laz_bati(LAZ_PATH, min_cluster=20, eps=1.0, min_pts=30, classe=6)


    path_gpkg = os.path.join(OUT_DIR, f"{base}_clust.gpkg")
    path_laz  = os.path.join(OUT_DIR, f"{base}_clust.laz")
    sauv_gpkg(nuages, path_gpkg)
    sauv_laz(nuages, path_laz)

    
if __name__ == "__main__":
    main()