import os
import sys
from ClipMNS      import *
from Ransac       import *
from util         import *



def main():
    
    MNS_NAME  = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"#DIDIER
    MNS_PATH  = f"data/raw/DIDIER/{MNS_NAME}" #DIDIER
    OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
    
    # MNS_NAME  = "LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif"#INRAE
    # MNS_PATH  = f"data/raw/INRAE/{MNS_NAME}" #INRAE
    # OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE
    
    
    GPKG_FILE = "BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
    GPKG_PATH = f"data/raw/{GPKG_FILE}"

    if not os.path.exists(MNS_PATH):
        print(f"Erreur : fichier introuvable → {MNS_NAME}")
        sys.exit(1)

    base    = MNS_NAME.replace(".tif", "")
    path_mns = os.path.join(OUT_DIR, f"{base}_batiments.tif")

    # MNS
    tile_bounds = TileBounds(MNS_NAME)
    gdf         = LoadBuild(GPKG_PATH, tile_bounds)
    buildings   = clipMNS(MNS_PATH, gdf)
    sauv_rast(MNS_PATH, buildings, path_mns)

    #PANS
    path_pans = os.path.join(OUT_DIR, f"{base}_MNSpans.gpkg")
    nuages = []
    for b in buildings:
        xyz = MNSToPointCloud(b['mns'], b['transf'])
        if xyz is not None and len(xyz) > 30:
            nuages.append(xyz)

    pans = ransac_tot(nuages)
    sauv_pans_gpkg(pans, path_pans)

    print(f"Pans détectés : {len(pans)}")
    print(f"nombre de batiments (avec > 30 points) : {len(nuages)}")
    print("fichier gpk batiments + pans ok et fichier LAZ batiments ok")

if __name__ == "__main__":
    main()
