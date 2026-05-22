import os
import sys

_HERE    = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(_HERE, '..', 'data', 'processed')

sys.path.insert(0, _HERE)
from LAZtoRaster import laz_raster, mask_vegetation, fill_gaps, _save_tif


def main():
    laz_path = input("Chemin vers le fichier LAZ : ").strip()
    if not os.path.exists(laz_path):
        print(f"Erreur : fichier introuvable → {laz_path}")
        sys.exit(1)

    base    = os.path.splitext(os.path.basename(laz_path))[0]
    out_dir = os.path.normpath(_OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    print("\nQue voulez-vous générer ?")
    print("  1 — MNS brut")
    print("  2 — MNS nettoyé  (végétation masquée + trous comblés)")
    choix = input("Votre choix (1/2) : ").strip()

    if choix == '1':
        path_out = os.path.join(out_dir, f"{base}_brut.tif")
        print(f"\n=== Rasterisation ===")
        laz_raster(laz_path, path_out, resol=0.5, classe=6)

    elif choix == '2':
        path_out = os.path.join(out_dir, f"{base}_nettoye.tif")
        tmp_path = os.path.join(out_dir, f"{base}_tmp.tif")

        print("\n=== Rasterisation ===")
        mns_brut, transf = laz_raster(laz_path, tmp_path, resol=0.5, classe=6)

        print("\n=== Masquage végétation ===")
        mns_clean = mask_vegetation(mns_brut)

        print("\n=== Remplissage trous internes ===")
        mns_final = fill_gaps(mns_clean)

        print(f"\n=== Export MNS nettoyé ===")
        _save_tif(mns_final, path_out, mns_final.shape[0], mns_final.shape[1], transf)
        os.remove(tmp_path)

    else:
        print("Choix invalide.")
        sys.exit(1)


if __name__ == "__main__":
    main()
