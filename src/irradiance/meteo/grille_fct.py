import os

import numpy as np
import pvlib
from src import config




def transpAgr(bhi, dhi, lat, lon):
    """
    Transpose chaque pas de temps (Perez) puis moyenne par (mois, heure).
    --------
    @param[in] bhi, dhi : Series (W/m2, plan horizontal) indexees par un DatetimeIndex UTC
    @param[in] lat, lon : centre de la cellule (deg WGS84)

    @return B, D     : tableaux (n_alphas, n_betas, 12, 24), direct et diffus (W/m2)
    @return SAZ, SEL : tableaux (12, 24), azimut et elevation apparente moyens du soleil (deg)
    """
    times = bhi.index
    ghi = (bhi + dhi).clip(lower=0)

    sp = pvlib.solarposition.get_solarposition(times, lat, lon)            # zenith, azimut, elevation par heure
    dni = pvlib.irradiance.dni(ghi, dhi, sp["apparent_zenith"]).fillna(0)  # reconstruction du DNI
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    airmass = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"])
    cles = [times.month, times.hour]

    B = np.zeros((len(config.ALPHAS), len(config.BETAS), 12, 24), np.float32)
    D = np.zeros_like(B)
    for i, a in enumerate(config.ALPHAS):
        for j, b in enumerate(config.BETAS):
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=b, surface_azimuth=a,
                solar_zenith=sp["apparent_zenith"], solar_azimuth=sp["azimuth"],
                dni=dni, ghi=ghi, dhi=dhi,
                dni_extra=dni_extra, airmass=airmass, albedo=config.ALBEDO, model="perez")
            direct = poa["poa_direct"].fillna(0)
            diffus = (poa["poa_sky_diffuse"] + poa["poa_ground_diffuse"]).fillna(0)
            B[i, j] = profMH(direct, cles)
            D[i, j] = profMH(diffus, cles)

    # position moyenne du soleil par (mois, heure) ; moyenner l'azimut est sans risque :
    # en France le soleil ne passe jamais par le nord (0/360) de jour
    SAZ = profMH(sp["azimuth"], cles)
    SEL = profMH(sp["apparent_elevation"], cles)
    return B, D, SAZ, SEL


def profMH(serie, cles):
    """
    Moyenne par (mois, heure UTC), tableau (12, 24), bins absents a 0.
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


def telecharger(lat, lon):
    """
    Telecharge les series horaires PVGIS (SARAH-3, 2005-2023) au point demande.
    --------
    @param[in] lat, lon : coordonnees du point (centre de la cellule), en degres WGS84

    @return df : DataFrame des series horaires PVGIS (composantes directe/diffuse, plan horizontal)
    """
    out = pvlib.iotools.get_pvgis_hourly(
        lat, lon, start=2005, end=2023,
        raddatabase="PVGIS-SARAH3",
        components=True, surface_tilt=0, surface_azimuth=0,
        usehorizon=False,
        url=config.URL, map_variables=True,
        timeout=120)                     # defaut 30s 
    df = out[0]
    return df


def cheminTable(lat, lon):
    """
    Chemin du fichier table d'une cellule.
    --------
    @param[in] lat, lon : centre de cellule, multiples de PAS (degres WGS84)

    @return chemin du .npz (ex: data/tables/lat_46/table_46.55_0.35.npz)
    """
    sous = f"lat_{int(lat)}"                                                                 # sous-dossier par bande de latitude
    return os.path.join(config.DOSSIER, sous, f"table_{lat + 0.0:.2f}_{lon + 0.0:.2f}.npz")  # + 0.0 : evite "-0.00"


_cache = {}

def chargerTable(lat, lon):
    """
    Charge (avec cache) la table de la cellule contenant un point quelconque.
    Point d'entree de la pipeline tuile : centreWGS84(...) puis chargerTable(...).
    --------
    @param[in] lat, lon : coordonnees quelconques (deg WGS84)

    @return B, D     : tableaux (n_alphas, n_betas, 12, 24) en W/m2
    @return SAZ, SEL : tableaux (12, 24), azimut et elevation du soleil (deg)
    """
    la = round(round(lat / config.PAS) * config.PAS, 2)
    lo = round(round(lon / config.PAS) * config.PAS, 2)

    if (la, lo) not in _cache:
        chemin = cheminTable(la, lo)
        if not os.path.exists(chemin):
            raise FileNotFoundError(
                f"Table meteo absente pour la cellule ({la}, {lo}) -> {chemin}. "
                f"Construis-la d'abord avec main_meteo.")
        d = np.load(chemin)

        _cache[(la, lo)] = (d["B"].astype(np.float32), d["D"].astype(np.float32),
                            d["SAZ"], d["SEL"])      # disque en float16 -> calcul en float32

    return _cache[(la, lo)]
