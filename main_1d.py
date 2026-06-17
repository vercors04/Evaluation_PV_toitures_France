import os
import sys

from src.pipeline import traiterDalle

# --- dalle a traiter ---
MNS_NAME = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"   # DIDIER
MNT_NAME = "LHD_FXX_0495_6611_MNT_O_0M50_LAMB93_IGN69.tif"
MNS_PATH = f"data/raw/DIDIER/{MNS_NAME}"
MNT_PATH = f"data/raw/DIDIER/{MNT_NAME}"
OUT_DIR  = os.path.normpath("data/processed/DIDIER")

GPKG_BDTOPO = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"


def main():
    for p in (MNS_PATH, MNT_PATH):
        if not os.path.exists(p):
            sys.exit(f"Fichier introuvable : {p}")

    os.makedirs(OUT_DIR, exist_ok=True)
    out_gpkg = os.path.join(OUT_DIR, MNS_NAME.replace(".tif", "_irradiance.gpkg"))
    traiterDalle(MNS_PATH, MNT_PATH, MNS_NAME, GPKG_BDTOPO, out_gpkg, debug_dir=OUT_DIR)


if __name__ == "__main__":
    main()
