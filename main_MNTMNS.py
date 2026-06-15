import os
import sys
import time
import numpy as np
from src.geometrie.clip_MNTMNS_pixel import clip_MNSMNT_pixels
from src.geometrie.ExtractBDtopo import tileBounds, loadBuild
from src.geometrie.horizon import compHZ
from src.irradiance.irr_tuile import nomCoord, centreWGS84
from src.irradiance.irr_calcul import irradianceTuile

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

    # chargement BDTOPO
    t0 = time.time()

    print("--- BDTopo ---")
    tile_bounds = tileBounds(MNS_NAME)
    gdf         = loadBuild(GPKG_PATH, tile_bounds)
    print(f"chargement BD TOPO : {time.time()-t0:.1f}s")
    print()

    # masquage MNS/MNT pixel par pixel
    t0 = time.time()
    print("--- Clip MNS/MNT pixels ---")
    masque_incline, masque_plat, pente, aspect, meta = clip_MNSMNT_pixels(
        MNS_PATH, MNT_PATH, gdf, debug_dir=OUT_DIR
    )
    print(f"clip pixels : {time.time()-t0:.1f}s")
    print()
    


    # calcul des angles d'horizon (raycast numpy, src/geometrie/horizon.py)
    t0 = time.time()

    print("--- Horizons ---")
    horizon_dir    = os.path.join(OUT_DIR, "horizon")
    masque_toiture = (masque_incline > 0) | (masque_plat > 0)
    horizon = compHZ(
        mns_path       = MNS_PATH,
        masque_toiture = masque_toiture,
        out_dir        = horizon_dir,
        n_directions=36, max_distance_m=100.0
    )

    print(f"Calcul d'horizon terminé : {time.time()-t0:.1f}s")
    print()


    # irradiance (avec ombrage) + geopackage de sortie
    print("--- Irradiance + GeoPackage ---")
    t0 = time.time()

    lat, lon = centreWGS84(*nomCoord(MNS_NAME))
    out_gpkg = os.path.join(OUT_DIR, MNS_NAME.replace(".tif", "_irradiance.gpkg"))
    irradianceTuile(masque_incline, masque_plat, pente, aspect, gdf, horizon, lat, lon, out_gpkg)

    print(f"GeoPackage écrit : {out_gpkg}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()



