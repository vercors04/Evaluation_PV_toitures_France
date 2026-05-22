import os
import sys

_HERE    = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(_HERE, '..', 'data', 'processed')

sys.path.insert(0, _HERE)
from MNTMNStoRaster import (charger_dalle, calculer_ndsm,
                             extraire_batiments, sauvegarder_raster)

# ── Paramètres ───────────────────────────────────────────────────────────────
H_MIN          = 2.0    # Hauteur min au-dessus du sol pour être un bâtiment (m)
H_MAX          = 50.0   # Hauteur max — élimine les outliers extrêmes (m)
RUGOSITÉ_MAX   = 0.4    # Seuil rugosité locale : au-delà = végétation (m)
SURFACE_MIN_M2 = 10.0   # Surface minimale d'un objet retenu (m²)
RESOL          = 0.5    # Résolution IGN LiDAR HD (m/pixel)
# ─────────────────────────────────────────────────────────────────────────────


def main():
    mns_path = input("Chemin vers le fichier MNS IGN (.tif) : ").strip()
    if not os.path.exists(mns_path):
        print(f"Erreur : fichier introuvable → {mns_path}")
        sys.exit(1)

    base     = os.path.splitext(os.path.basename(mns_path))[0]
    out_dir  = os.path.normpath(_OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    base_mntmns = base.replace("MNS", "MNTMNS")
    path_out = os.path.join(out_dir, f"{base_mntmns}_batiments.tif")

    print("\n=== Chargement des dalles ===")
    mns, mnt, meta = charger_dalle(mns_path)

    print("\n=== Calcul du nDSM (MNS − MNT) ===")
    ndsm = calculer_ndsm(mns, mnt)

    print("\n=== Extraction des bâtiments ===")
    masque = extraire_batiments(
        mns, ndsm,
        h_min          = H_MIN,
        h_max          = H_MAX,
        rugosité_max   = RUGOSITÉ_MAX,
        surface_min_m2 = SURFACE_MIN_M2,
        resol          = RESOL
    )

    print("\n=== Export ===")
    sauvegarder_raster(mns, masque, path_out, meta)


if __name__ == "__main__":
    main()
