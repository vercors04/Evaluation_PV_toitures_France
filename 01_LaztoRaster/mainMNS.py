import os
import sys
from LAZtoRaster import *
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

    print("\nQue voulez-vous générer ?")
    print("  1 — MNS brut")
    print("  2 — MNS nettoyé  (végétation masquée + trous comblés)")
    choix = input("Votre choix (1/2) : ").strip()

    if choix == '1':
        path_out = os.path.join(OUT_DIR, f"{base}_brut.tif")
        laz_raster(LAZ_PATH, path_out, resol=0.5, classe=6)

    elif choix == '2':
        path_out = os.path.join(OUT_DIR, f"{base}_nettoye.tif")

        mns_brut, transf = laz_raster(LAZ_PATH, path_out, resol=0.5, classe=6)
        mns_clean = mask_vegetation(mns_brut)
        mns_final = fill_gaps(mns_clean)

        with rasterio.open(path_out, 'w', driver='GTiff',
                   height=mns_final.shape[0], width=mns_final.shape[1], count=1,
                   dtype='float32', crs='EPSG:2154',
                   transform=transf, nodata=np.nan) as dst:
            dst.write(mns_final, 1)
    

    else:
        print("Choix invalide.")
        sys.exit(1)


if __name__ == "__main__":
    main()
