import os
import sys
from LAZtoRaster import *
import importlib.util

# Load Ransac.py from sibling directory '02_MNStoPans' (directory name starts with a digit,
# so import as a module by file path)
ransac_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '02_MNStoPans', 'Ransac.py'))
Ransac = None
if os.path.exists(ransac_path):
    spec = importlib.util.spec_from_file_location('Ransac', ransac_path)
    ransac_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ransac_mod)
    Ransac = ransac_mod
else:
    # keep compatibility: try standard import if package name is available
    try:
        from Ransac import *  # type: ignore
    except Exception:
        pass

#LAZ_NAME ="LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz"#INRAE
LAZ_NAME ="LHD_FXX_0495_6611_PTS_LAMB93_IGN69.copc.laz"#DIDIER

#LAZ_PATH = f"data/raw/INRAE/{LAZ_NAME}" #INRAE
LAZ_PATH = f"data/raw/DIDIER/{LAZ_NAME}" #DIDIER

OUT_DIR = os.path.normpath("data/processed/DIDIER") #DIDIER
#OUT_DIR = os.path.normpath("data/processed/INRAE") #INRAE

def main():
    if not os.path.exists(LAZ_PATH):
        print(f"Erreur : fichier introuvable → {LAZ_NAME}")
        sys.exit(1)

    base    = os.path.splitext(os.path.basename(LAZ_PATH))[0]

   
if __name__ == "__main__":
    main()
