import os
import sys
import numpy as np
import rasterio
import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import Point

_HERE     = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, '..', 'data')
GPKG_FILE = os.path.join(_DATA_DIR, 'raw', 'vienne.gpkg')
_OUT_DIR  = os.path.join(_DATA_DIR, 'processed')

sys.path.insert(0, _HERE)
from ClipMNS      import clipMNS
from ExtractBDtopo import TileBounds, LoadBuild
from Ransac       import (MNSToPointCloud, RemoveNoise, DetectMultiPlanes,
                          PlaneToAngles, AzimutToOrientation)

THRESHOLD   = 0.15
MIN_RATIO   = 0.15
MAX_PENTE   = 70.0
MIN_SURFACE = 5.0


def _sauvegarder_raster_batiments(mns_path, buildings, path_out):
    """Reconstitue la dalle MNS avec uniquement les bâtiments et la sauvegarde."""
    with rasterio.open(mns_path) as src:
        mns_bat    = np.full((src.height, src.width), np.nan, dtype='float32')
        transf_ref = src.transform

        for b in buildings:
            row_off, col_off = rasterio.transform.rowcol(
                transf_ref, b['transf'].c, b['transf'].f)
            h, w = b['mns'].shape
            mns_bat[row_off:row_off+h, col_off:col_off+w] = np.where(
                ~np.isnan(b['mns']),
                b['mns'],
                mns_bat[row_off:row_off+h, col_off:col_off+w]
            )

        with rasterio.open(
            path_out, 'w', driver='GTiff',
            height=src.height, width=src.width, count=1,
            dtype='float32', crs='EPSG:2154',
            transform=transf_ref, nodata=np.nan
        ) as dst:
            dst.write(mns_bat, 1)

    print(f"Raster bâtiments sauvegardé : {path_out}")


def _analyser_pans(buildings):
    """Lance le RANSAC sur une liste de bâtiments et retourne un DataFrame."""
    resultats = []
    for b in buildings:
        points = MNSToPointCloud(b['mns'], b['transf'])
        if points is None or len(points) < 10:
            continue
        points = RemoveNoise(points)
        if len(points) < 10:
            continue
        planes = DetectMultiPlanes(points, min_ratio=MIN_RATIO, threshold=THRESHOLD)
        for w, pts in planes:
            pente, azimut = PlaneToAngles(w)
            surface = len(pts) * 0.25
            if pente > MAX_PENTE or surface < MIN_SURFACE:
                continue
            resultats.append({
                'cleabs'     : b['cleabs'],
                'usage'      : b['usage'],
                'pente'      : pente,
                'azimut'     : azimut,
                'surface'    : round(surface, 1),
                'orientation': AzimutToOrientation(azimut)
            })
    return pd.DataFrame(resultats)


def _geocode_adresse(adresse):
    """Géocode une adresse française, retourne (x, y) en Lambert 93."""
    r    = requests.get("https://api-adresse.data.gouv.fr/search/",
                        params={"q": adresse, "limit": 1})
    feat = r.json()["features"][0]
    lon, lat = feat["geometry"]["coordinates"]
    t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    return t.transform(lon, lat)


def main():
    mns_path = input("Chemin vers le fichier MNS IGN (.tif) : ").strip()
    if not os.path.exists(mns_path):
        print(f"Erreur : fichier introuvable → {mns_path}")
        sys.exit(1)

    mns_filename = os.path.basename(mns_path)
    base         = os.path.splitext(mns_filename)[0]
    out_dir      = os.path.normpath(_OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    print("\nQue voulez-vous faire ?")
    print("  1 — Raster bâtiments + détail des pans  (tuile entière, terminal)")
    print("  2 — Raster bâtiments + détail d'un bâtiment  (par adresse)")
    choix = input("Votre choix (1/2) : ").strip()

    # ── Étapes communes ──────────────────────────────────────────────────────
    tile_bounds = TileBounds(mns_filename)
    gdf         = LoadBuild(GPKG_FILE, tile_bounds)
    buildings   = clipMNS(mns_path, gdf)

    raster_out = os.path.join(out_dir, f"{base}_batiments.tif")
    _sauvegarder_raster_batiments(mns_path, buildings, raster_out)

    # ── Option 1 : tuile entière ─────────────────────────────────────────────
    if choix == '1':
        print("\n=== Analyse RANSAC — tuile entière ===")
        df = _analyser_pans(buildings)

        if df.empty:
            print("Aucun pan détecté.")
            return

        print(f"\nTotal pans détectés : {len(df)}")
        print(f"Pente moyenne       : {df['pente'].mean():.1f}°")
        print(f"Surface totale      : {df['surface'].sum():.0f} m²")
        print("\nRépartition par orientation (surface en m²) :")
        print(df.groupby('orientation')['surface'].sum().round(0))
        print("\nRépartition par orientation (nombre de pans) :")
        print(df['orientation'].value_counts())

    # ── Option 2 : bâtiment par adresse ─────────────────────────────────────
    elif choix == '2':
        adresse = input("\nAdresse du bâtiment : ").strip()
        x, y    = _geocode_adresse(adresse)
        point   = Point(x, y)

        gdf_tmp           = gdf.copy()
        gdf_tmp['dist']   = gdf_tmp.geometry.distance(point)
        candidats         = gdf_tmp[gdf_tmp['dist'] < 50]

        if candidats.empty:
            print("Aucun bâtiment trouvé à moins de 50 m de cette adresse.")
            sys.exit(1)

        bat    = candidats.loc[candidats.geometry.area.idxmax()]
        cleabs = bat['cleabs']
        print(f"\nBâtiment trouvé : {cleabs}")
        print(f"Usage : {bat['usage_1']} | Hauteur : {bat['hauteur']} m")

        bat_buildings = [b for b in buildings if b['cleabs'] == cleabs]
        if not bat_buildings:
            print("Bâtiment introuvable dans les données extraites.")
            sys.exit(1)

        df = _analyser_pans(bat_buildings)
        print(f"\n=== Pans du bâtiment {cleabs} ===")
        if df.empty:
            print("Aucun pan détecté.")
        else:
            for _, r in df.iterrows():
                print(f"  Pan : pente={r['pente']:.1f}°  azimut={r['azimut']:.1f}°  "
                      f"orientation={r['orientation']}  surface={r['surface']:.1f} m²")

    else:
        print("Choix invalide.")
        sys.exit(1)


if __name__ == "__main__":
    main()
