import requests
import numpy as np
from pyproj import Transformer
from shapely.geometry import MultiPoint


def pvgisTousPans(pans, crs_source=2154):
    """
    Calcule le productible PVGIS pour tous les pans.
    ---------------------------------------------------------------
    @param[in]  pans       : liste de dicts (sortie ransacTot)
    @param[in]  crs_source : EPSG source (2154 = Lambert 93)
    @param[out] pans       : liste enrichie avec surf_m2, puissance_kwc,
                             irradiation_kwh_m2, production_kwh_an
    """
    transformer = Transformer.from_crs(crs_source, 4326, always_xy=True)

    for i, pan in enumerate(pans):
        pts    = pan["points"]
        cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
        lon, lat = transformer.transform(cx, cy)

        surf_reelle      = MultiPoint(pts[:, :2]).convex_hull.area \
                           / np.cos(np.radians(pan["pente"]))
        kwc              = surf_reelle * 0.20   # 200 Wc/m²

        # azimut IGN (0=N, 180=S) -> PVGIS (0=S, ±180)
        asp = round(pan["azimut"] - 180, 1)
        if asp >  180: asp -= 360
        if asp < -180: asp += 360

        r = requests.get(
            "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
            params={
                "lat":           round(lat, 5),
                "lon":           round(lon, 5),
                "peakpower":     1.0,
                "loss":          14,
                "angle":         round(pan["pente"], 1),
                "aspect":        asp,
                "outputformat":  "json",
                "raddatabase":   "PVGIS-SARAH3",
                "mountingplace": "building",
            },
            timeout=10
        )
        r.raise_for_status()
        d = r.json()["outputs"]["totals"]["fixed"]
        pan["surf_m2"]            = round(surf_reelle, 1)
        pan["puissance_kwc"]      = round(kwc, 2)
        pan["irradiation_kwh_m2"] = d["H(i)_y"]
        pan["production_kwh_an"]  = round(d["E_y"] * kwc, 0)

        if i % 50 == 0:
            print(f"  {i}/{len(pans)} pans traités...")

    ok = sum(1 for p in pans if p["production_kwh_an"] is not None)
    print(f"PVGIS : {ok}/{len(pans)} pans calculés")
    return pans
