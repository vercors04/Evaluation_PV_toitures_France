import numpy as np
import pandas as pd
import pvlib


ALBEDO = 0.2                      # pouvoir réfléchissant d'une suface  - Buffat 2018, Solar Wizard
ALPHAS = np.arange(0, 360, 15)    # grille grossiere d'orientations (24 valeurs)
BETAS = np.arange(0, 51, 10)      # grille grossiere de pentes (5 valeurs)
N_JOURS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

URL = "https://re.jrc.ec.europa.eu/api/v5_3/"   # PVGIS 5.3 (SARAH-3, 2005-2023)


def transpAgr(bhi, dhi, lat, lon):
    """Transpose CHAQUE pas de temps (Perez) puis moyenne par (mois, heure).

    @param[in]  lat, lon : coordonnees du centre de la tuile, en degees WGS84
    @param[in]  bhi, dhi : Series (W/m2, plan horizontal) indexees par un DatetimeIndex UTC.
    
    @return B, D : tableaux (24 alphas x 10 betas) de l'irradiance directe et diffuse
    @return sp   : DataFrame position solaire (azimuth, apparent_elevation) indexe par DatetimeIndex
    """
    times = bhi.index
    ghi = (bhi + dhi).clip(lower=0)

    sp = pvlib.solarposition.get_solarposition(times, lat, lon)

    dni = pvlib.irradiance.dni(ghi, dhi, sp["apparent_zenith"])
    dni = pd.Series(dni, index=times).fillna(0).clip(lower=0)

    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    cles = [times.month, times.hour]

    B = np.zeros((len(ALPHAS), len(BETAS), 12, 24), np.float32)
    D = np.zeros_like(B)
    for i, a in enumerate(ALPHAS):
        for j, b in enumerate(BETAS):
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=b, surface_azimuth=a,
                solar_zenith=sp["apparent_zenith"], solar_azimuth=sp["azimuth"],
                dni=dni, ghi=ghi, dhi=dhi,
                dni_extra=dni_extra, albedo=ALBEDO, model="perez")
            direct = poa["poa_direct"].fillna(0)
            diffus = (poa["poa_sky_diffuse"] + poa["poa_ground_diffuse"]).fillna(0)
            B[i, j] = profMH(direct, cles)
            D[i, j] = profMH(diffus, cles)
    return B, D, sp


def profMH(serie, cles):
    """
    Moyenne par (mois, heure UTC) -> tableau (12, 24). Bins absents = 0.
    --------
    @param[in] serie : Series indexee par un DatetimeIndex UTC
    @param[in] cles  : liste de Series (ex: [times.month, times.hour]) pour grouper la serie

    @return out : tableau (12, 24) de la valeur moyenne par (mois, heure)
    """
    g = serie.groupby(cles).mean()
    out = np.zeros((12, 24), np.float32)
    for (m, h), v in g.items():
        out[int(m) - 1, int(h)] = v
    return out


def totAb(B, D):
    """Irradiation annuelle dans le plan, kWh/m2/an, par (alpha, beta).
    --------
    @param[in] B, D : tableaux (24 alphas x 10 betas) de l'irradiance directe et diffuse, en W/m2, par (mois, heure)
    @return E : tableau (24 alphas x 10 betas) de l'irradiation annuelle dans le plan, en kWh/m2/an
    """
    E = (B + D).astype(np.float64)                       # W/m2 moyens par bin
    return (E * N_JOURS[None, None, :, None]).sum(axis=(2, 3)) / 1000.0



def telecharger(lat, lon):
    """
    Telecharge les series horaires PVGIS pour la cellule de 0,05 deg contenant le pts actuel.
    --------
    @param[in] lat, lon : coordonnees du coin bas-gauche de la tuile, en degees WGS84

    @return df : DataFrame contenant les donnees PVGIS
   """ 
    out = pvlib.iotools.get_pvgis_hourly(
        lat, lon, start=2005, end=2023,
        raddatabase="PVGIS-SARAH3",      
        components=True, surface_tilt=0, surface_azimuth=0,
        usehorizon=False,                # a voir si on prends cet horizon en +
        url=URL, map_variables=True)
    df = out[0]
    return df