import requests
import numpy as np
import rasterio
from pyproj import Transformer
from shapely.geometry import MultiPoint


def pvgisTousPans(pans, mns_path, crs_source=2154):
    """
    Calcule le productible PVGIS pour tous les pans avec masque horizon MNS.
    ---------------------------------------------------------------
    @param[in]  pans       : liste de dicts (sortie ransac_tot)
    @param[in]  mns_path   : chemin MNS IGN (.tif)
    @param[in]  crs_source : EPSG source (2154 = Lambert 93)
    @param[out] pans       : liste enrichie
    """
    transformer = Transformer.from_crs(crs_source, 4326, always_xy=True)

    with rasterio.open(mns_path) as src:
        mns = src.read(1).astype("float32")
        tf  = src.transform
        nd  = src.nodata
        if nd is not None:
            mns[mns == nd] = np.nan

    dists = np.arange(10, int(100 / tf.a) + 1) * tf.a  # 5m à 100m

    for i, pan in enumerate(pans):
        pts         = pan["points"]
        cx, cy      = pts[:, 0].mean(), pts[:, 1].mean()
        z_pan       = pts[:, 2].mean()
        surf_reelle = MultiPoint(pts[:, :2]).convex_hull.area \
                      / (np.cos(np.radians(pan["pente"])) or 1)
        lon, lat    = transformer.transform(cx, cy)

        # horizon 36 directions
        horizon = []
        for d in range(36):
            az   = np.radians(d * 10)
            cols = ((cx + np.sin(az) * dists - tf.c) / tf.a).astype(int)
            rows = ((tf.f - (cy + np.cos(az) * dists)) / (-tf.e)).astype(int)
            v    = (cols >= 0) & (cols < mns.shape[1]) & \
                   (rows >= 0) & (rows < mns.shape[0])
            if v.sum() == 0:
                horizon.append(0.0)
                continue
            zv = mns[rows[v], cols[v]]
            ok = ~np.isnan(zv) & (zv > -100)
            elev = float(np.degrees(np.arctan2(
                zv[ok] - z_pan, dists[v][ok])).max()) if ok.sum() else 0.0
            horizon.append(round(min(max(elev, 0.0), 45.0), 2))

        # azimut IGN → PVGIS
        asp = round(pan["azimut"] - 180, 1)
        if asp > 180:  asp -= 360
        if asp < -180: asp += 360

        try:
            r = requests.get(
                "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
                params={
                    "lat": round(lat, 5), "lon": round(lon, 5),
                    "peakpower": 1.0, "loss": 14,
                    "angle": round(pan["pente"], 1), "aspect": asp,
                    "outputformat": "json", "raddatabase": "PVGIS-SARAH3",
                    "mountingplace": "building",
                    "userhorizon": ",".join(f"{h:.2f}" for h in horizon),
                },
                timeout=10
            )
            r.raise_for_status()
            d   = r.json()["outputs"]["totals"]["fixed"]
            kwc = surf_reelle * 0.20
            pan["surf_m2"]            = round(surf_reelle, 1)
            pan["puissance_kwc"]      = round(kwc, 2)
            pan["irradiation_kwh_m2"] = d["H(i)_y"]
            pan["production_kwh_an"]  = round(d["E_y"] * kwc, 0)
        except Exception:
            pan["surf_m2"]            = round(surf_reelle, 1)
            pan["puissance_kwc"]      = round(surf_reelle * 0.20, 2)
            pan["irradiation_kwh_m2"] = None
            pan["production_kwh_an"]  = None

        if i % 50 == 0:
            print(f"  {i}/{len(pans)} pans traités...")

    ok = sum(1 for p in pans if p["production_kwh_an"] is not None)
    print(f"PVGIS : {ok}/{len(pans)} pans calculés")
    return pans