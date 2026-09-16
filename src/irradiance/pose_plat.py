import numpy as np
import pandas as pd
from shapely.geometry import box

from src import config

N_QUAD = 4
CODES = {nom: i for i, nom in enumerate(config.POSES_PLAT)}
LIBELLES = {i: nom for nom, i in CODES.items()}
A_PLAT, SUD, EST_OUEST = CODES["à plat"], CODES["sud"], CODES["est-ouest"]
R_AUCUNE, R_SUD, R_EST, R_OUEST = 0, 1, 2, 3


def gcrSud(lat):
    """
    Taux d'occupation au sol des rangees sud : sans ombre a midi au solstice d'hiver, ou
    valeur saisie ; borne a des rangees jointives.
    --------
    @param[in] lat : latitude du centre de la dalle (deg)

    @return gcr
    """
    b = np.radians(config.SUD_PENTE)
    if config.SUD_ESPACEMENT == config.ESPACEMENTS_SUD[1]:
        g = float(config.SUD_GCR)
    else:
        h = np.radians(max(90.0 - abs(lat) - 23.44, 5.0))
        g = 1.0 / (np.cos(b) + np.sin(b) / np.tan(h))
    return float(np.clip(g, 0.05, 0.999 / np.cos(b)))


def densiteEstOuest():
    """
    Surface de modules par surface du champ en est-ouest, bornee a des paires jointives.
    --------
    @return densite
    """
    b = np.radians(config.EO_PENTE)
    return float(np.clip(config.EO_GCR, 0.05, 0.999 / np.cos(b)))


def quadrature(pente, gcr):
    """
    Masque de la rangee de devant aux points de Gauss de la hauteur du module.
    --------
    @param[in] pente : inclinaison des modules (deg)
    @param[in] gcr   : taux d'occupation au sol de la rangee

    @return t, w : tangentes du masque et poids, (N_QUAD,)
    """
    b = np.radians(pente)
    x, w = np.polynomial.legendre.leggauss(N_QUAD)
    u = (x + 1.0) / 2.0
    t = u * np.sin(b) / (1.0 / gcr - u * np.cos(b))
    return t, w / 2.0


def ombre(SAZ, SEL, azimut, pente, gcr):
    """
    Fraction du module ombree par la rangee de devant, par creneau (rangees infinies).
    --------
    @param[in] SAZ, SEL : azimut et elevation du soleil par (mois, heure), deg
    @param[in] azimut   : azimut vers lequel les modules font face (deg)
    @param[in] pente    : inclinaison des modules (deg)
    @param[in] gcr      : taux d'occupation au sol de la rangee

    @return (12, 24) float32 dans [0, 1]
    """
    h   = np.radians(SEL)
    rel = np.radians(SAZ - azimut)
    b   = np.radians(pente)
    devant = (SEL > 0.0) & (np.cos(rel) > 1e-9)
    hp = np.arctan2(np.sin(h), np.cos(h) * np.cos(rel))
    with np.errstate(divide="ignore", invalid="ignore"):
        f = 1.0 - np.sin(hp) / (gcr * np.sin(hp + b))
    return np.where(devant, np.clip(f, 0.0, 1.0), 0.0).astype(np.float32)


def geometrie(lat, SAZ, SEL):
    """
    Geometrie des poses de la dalle. Une face est-ouest est une rangee de taux moitie
    de la densite de la paire.
    --------
    @param[in] lat      : latitude du centre de la dalle (deg)
    @param[in] SAZ, SEL : position du soleil par (mois, heure), deg

    @return dict : "sud" et "eo" (densite, t, w), "f_sh" (4, 12, 24) par type de rangee
    """
    g_sud = gcrSud(lat)
    d_eo = densiteEstOuest()
    f_sh = np.zeros((4, 12, 24), np.float32)
    f_sh[R_SUD] = ombre(SAZ, SEL, config.SUD_AZIMUT, config.SUD_PENTE, g_sud)
    f_sh[R_EST] = ombre(SAZ, SEL, 90.0, config.EO_PENTE, d_eo / 2.0)
    f_sh[R_OUEST] = ombre(SAZ, SEL, 270.0, config.EO_PENTE, d_eo / 2.0)
    t_s, w_s = quadrature(config.SUD_PENTE, g_sud)
    t_e, w_e = quadrature(config.EO_PENTE, d_eo / 2.0)
    return {"sud": {"densite": g_sud, "t": t_s, "w": w_s},
            "eo":  {"densite": d_eo, "t": t_e, "w": w_e},
            "f_sh": f_sh}


def description(lats):
    """
    Poses et coefficients thermiques appliques, pour les metadonnees du resultat.
    --------
    @param[in] lats : latitudes des centres des dalles traitees (deg)

    @return dict serialisable en JSON
    """
    faiman = {nom: {"classe": c, "U0": config.POSES[c][0], "U1": config.POSES[c][1]}
              for nom, c in config.THERMIQUE_PLAT.items()}
    gcr = [gcrSud(lat) for lat in lats]
    return {
        "pans_inclines": {"classe": config.POSE, "U0": config.U0_FAIMAN, "U1": config.U1_FAIMAN},
        "toits_plats": config.PLAT_POSE,
        "a_plat": {**faiman["à plat"], "densite": 1.0},
        "sud": {**faiman["sud"], "pente": config.SUD_PENTE,
                "azimut": config.SUD_AZIMUT, "espacement": config.SUD_ESPACEMENT,
                "gcr_min": min(gcr) if gcr else None, "gcr_max": max(gcr) if gcr else None},
        "est_ouest": {**faiman["est-ouest"], "pente": config.EO_PENTE,
                      "azimuts": [90.0, 270.0], "densite": densiteEstOuest()},
        "emprise_plat": config.EMPRISE_PLAT,
        "bande_horizon_deg": config.BANDE_HORIZON_DEG,
    }


def posesBatiments(masque_bat, plat, pente, res, gdf, bornes):
    """
    Pose du toit plat de chaque batiment en mode mixte ; surface plate d'un batiment coupe par
    la dalle ramenee a son emprise entiere.
    --------
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 hors toit)
    @param[in] plat       : 2D bool, pixels plats retenus
    @param[in] pente      : 2D float (deg)
    @param[in] res        : taille du pixel (m)
    @param[in] gdf        : batiments de la dalle (geometrie entiere, usage_1, nature)
    @param[in] bornes     : emprise de la dalle (xmin, ymin, xmax, ymax), Lambert 93

    @return Series int8 des codes de pose, indexee par batiment ; None hors mode mixte
    """
    if config.PLAT_POSE != "mixte":
        return None
    if config.MIXTE_CRITERE in ("usage", "nature"):
        colonne, valeurs = (("usage_1", config.MIXTE_USAGES) if config.MIXTE_CRITERE == "usage"
                            else ("nature", config.MIXTE_NATURES))
        if colonne in gdf.columns:
            rempli = gdf[colonne].isin(valeurs)
        else:
            rempli = pd.Series(False, index=gdf.index)
    else:
        ok = plat & (masque_bat > 0)
        surf = (pd.Series(res**2 / np.cos(np.radians(pente[ok])))
                .groupby(masque_bat[ok] - 1).sum())
        b = gdf.geometry.loc[surf.index].bounds
        t = config.BUFFER
        coupe = ((b.minx - t < bornes[0]) | (b.miny - t < bornes[1])
                 | (b.maxx + t > bornes[2]) | (b.maxy + t > bornes[3]))
        if coupe.any():
            ids = coupe.index[coupe]
            emprise = gdf.geometry.loc[ids].buffer(t)
            dedans = emprise.intersection(box(*bornes)).area
            surf.loc[ids] *= (emprise.area / dedans.where(dedans > 0)).fillna(1.0)
        rempli = (surf >= config.MIXTE_SEUIL_M2).reindex(gdf.index, fill_value=False)
    return pd.Series(np.where(rempli, CODES[config.MIXTE_SI], CODES[config.MIXTE_SINON]),
                     index=gdf.index, dtype=np.int8)
