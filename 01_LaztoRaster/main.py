import os
import sys
from LAZ_bati import *
from Ransac import *
from crea_fic import *


# LAZ_NAME ="LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz"#INRAE
# LAZ_PATH = f"data/raw/INRAE/{LAZ_NAME}" #INRAE
# OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE

LAZ_NAME ="LHD_FXX_0495_6611_PTS_LAMB93_IGN69.copc.laz"#DIDIER
LAZ_PATH = f"data/raw/DIDIER/{LAZ_NAME}" #DIDIER
OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER

def main():
    if not os.path.exists(LAZ_PATH):
        print(f"Erreur : fichier introuvable → {LAZ_NAME}")
        sys.exit(1)

    base    = LAZ_NAME.replace(".copc.laz", "")
    nuages = laz_bati(LAZ_PATH, min_cluster=20, eps=0.9, min_pts=60, classe=6)


    path_gpkg = os.path.join(OUT_DIR, f"{base}_clust.gpkg")
    path_laz = os.path.join(OUT_DIR, f"{base}_clust.laz")

    sauv_gpkg(nuages, path_gpkg)
    sauv_laz(nuages, path_laz)
    
    pans = ransac_tot(nuages)



    path_pans = os.path.join(OUT_DIR, f"{base}_pans.gpkg")
    sauv_pans_gpkg(pans, path_pans)

if __name__ == "__main__":
    main()