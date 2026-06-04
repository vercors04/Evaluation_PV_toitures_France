#premiere version pour valider les ordres de gradeurs
import requests
from pyproj import Transformer

def pvgisPan(lat, lon, pente, azimut,
              puissance_kwc=1.0, pertes=14, an=2020):
    """
    Calcule le productible annuel d'un pan via l'API PVGIS.
    ---------------------------------------------------------------
    @param[in]  lat        : latitude du pan (degrés décimaux)
    @param[in]  lon        : longitude du pan (degrés décimaux)
    @param[in]  pente      : inclinaison du pan (degrés, 0=plat)
    @param[in]  azimut     : orientation IGN (0=N,90=E,180=S,270=O)
                             converti en convention PVGIS (0=S,-90=E,90=O)
    @param[in]  puissance_kwc : puissance crête installée (kWc)
    @param[in]  pertes     : pertes système en % (câbles, onduleur...)
    @param[in]  an         : année de référence météo
    @param[out] dict       : {irradiation_kwh_m2, production_kwh, ok}
    ---------------------------------------------------------------
    """
    # convention d'azimut diff avec pvgis
    azimut_pvgis = azimut - 180
    if azimut_pvgis > 180:
        azimut_pvgis -= 360

    url = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
    params = {
        "lat":        lat,
        "lon":        lon,
        "peakpower":  puissance_kwc,
        "loss":       pertes,
        "angle":      pente,
        "aspect":     azimut_pvgis,
        "outputformat": "json",
        "raddatabase":  "PVGIS-SARAH2",
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        prod  = data["outputs"]["totals"]["fixed"]["E_y"]   # kWh/an/kWc
        irrad = data["outputs"]["totals"]["fixed"]["H(i)_y"] # kWh/m²/an
        return {"irradiation_kwh_m2": irrad, "production_kwh": prod, "ok": True}
    except Exception as e:
        return {"irradiation_kwh_m2": None, "production_kwh": None, "ok": False}


def pvgisTousPans(pans, crs_source=2154):
    """
    Calcule le productible PVGIS pour tous les pans.
    Convertit les coordonnées Lambert 93 → WGS84.
    Ajoute irradiation_kwh_m2 et production_kwh à chaque pan.
    """
    transformer = Transformer.from_crs(crs_source, 4326, always_xy=True)

    for i, pan in enumerate(pans):
        # centroïde du pan en Lambert 93
        cx = pan["points"][:, 0].mean()
        cy = pan["points"][:, 1].mean()

        # conversion en WGS84
        lon, lat = transformer.transform(cx, cy)

        result = pvgisPan(lat, lon, pan["pente"], pan["azimut"])
        pan["lat"]               = round(lat, 6)
        pan["lon"]               = round(lon, 6)
        pan["irradiation_kwh_m2"] = result["irradiation_kwh_m2"]
        pan["production_kwh"]    = result["production_kwh"]

        if i % 50 == 0:
            print(f"  {i}/{len(pans)} pans traités...")

    ok = sum(1 for p in pans if p["production_kwh"] is not None)
    print(f"PVGIS : {ok}/{len(pans)} pans avec résultat")
    return pans