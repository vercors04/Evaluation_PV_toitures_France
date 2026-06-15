"""
src/irradiance/irr_calcul.py
Passage de la lookup table (cellule meteo) a l'irradiance et a la production PV
par batiment, pour une dalle. C'est le coeur de calcul reutilise par la pipeline
complete (boucle sur toutes les dalles).
"""
import numpy as np
import pandas as pd

from src.irradiance.irr_fct import chargerTable, ALPHAS, BETAS, N_JOURS


SECTEURS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]   # 8 secteurs de 45 deg, 0 = Nord

# --- modele PV simple ---
# Un seul parametre de rendement ; la "surface par kWc" classique en decoule :
# m2/kWc = 1 / (RENDEMENT_MODULE * TAUX_COUVERTURE)  (~5 a couverture 1, ~6 a 0.83).
RENDEMENT_MODULE  = 0.20    # rendement du panneau (-)  ->  ~5 m2 de panneau par kWc
PERFORMANCE_RATIO = 0.78    # pertes systeme : onduleur, temperature, salissures, cablage (-)
TAUX_COUVERTURE   = 1.0     # part de la toiture exploitable couverte de panneaux (-)


def masquerHorizon(B_pix, horizon, SAZ, SEL):
    """
    Eteint le rayonnement direct quand le soleil est sous l'horizon du pixel
    (regle d'ombrage de Buffat, Eq 6). Le diffus n'est pas touche.
    --------
    @param[in] B_pix   : (N, 12, 24) irradiance directe par pixel et par (mois, heure)
    @param[in] horizon : (N, n_dir) angle d'horizon par pixel et direction, en degres
    @param[in] SAZ, SEL: (12, 24) azimut et elevation moyens du soleil, en degres

    @return B_pix masque (modifie sur place : direct = 0 a l'ombre)
    """
    n_dir = horizon.shape[1]
    d = np.round(SAZ / (360 / n_dir)).astype(int) % n_dir   # (12,24) direction la plus proche du soleil
    horizon_soleil = horizon[:, d]                           # (N, 12, 24) horizon dans la direction du soleil
    B_pix[SEL[None, :, :] <= horizon_soleil] = 0.0           # soleil sous l'horizon -> a l'ombre
    return B_pix


def irrPixels(masque_incline, masque_plat, pente, aspect, B, D, SAZ, SEL, horizon, alphas, betas):
    """
    Irradiation annuelle et surface reelle de chaque pixel de toiture, ombrage compris.
    Pour chaque pixel : on lit le profil (mois, heure) de la case (orientation, pente)
    la plus proche, on eteint le direct a l'ombre, on integre sur l'annee, et on
    multiplie par la surface reelle du pixel.
    --------
    @param[in] masque_incline, masque_plat : 2D int — index gdf + 1 du batiment, 0 sinon
    @param[in] pente, aspect : 2D float — par pixel, en degres
    @param[in] B, D          : tables (n_alphas, n_betas, 12, 24) direct et diffus, W/m2
    @param[in] SAZ, SEL      : (12, 24) position moyenne du soleil, en degres
    @param[in] horizon       : (N, n_dir) angle d'horizon par pixel (sortie de compHZ),
                               dans le MEME ordre que np.where(masque_toiture)
    @param[in] alphas, betas : axes des tables (degres) -> donnent le pas de la grille

    @return df : DataFrame, 1 ligne par pixel de toit, colonnes
                 id (index gdf), energie (kWh/an), surf (m2), pente (deg), secteur, incline
    """
    pas_a = alphas[1] - alphas[0]      # 15 deg
    pas_b = betas[1] - betas[0]        # 10 deg

    masque_bat = np.where(masque_incline > 0, masque_incline, masque_plat)
    toit = masque_bat > 0
    assert horizon.shape[0] == toit.sum(), "horizon et masque de toiture desynchronises"

    p = pente[toit]
    a = aspect[toit]

    # case (orientation, pente) la plus proche dans les tables -> profil par pixel
    i = np.round(a / pas_a).astype(int) % len(alphas)
    j = np.clip(np.round(p / pas_b).astype(int), 0, len(betas) - 1)
    B_pix = B[i, j]                                 # (N, 12, 24) direct
    D_pix = D[i, j]                                 # (N, 12, 24) diffus + reflechi

    B_pix = masquerHorizon(B_pix, horizon, SAZ, SEL)

    # integration -> kWh/m2/an (variante de totAb, par pixel)
    e_m2 = ((B_pix + D_pix) * N_JOURS[None, :, None]).sum(axis=(1, 2)) / 1000.0
    surf = 0.25 / np.cos(np.radians(p))             # 0.25 m2 projetes / cos(pente)

    return pd.DataFrame({
        "id":      masque_bat[toit] - 1,            # index du batiment dans gdf
        "energie": e_m2 * surf,                     # kWh/an
        "surf":    surf,
        "pente":   p,
        "secteur": np.round(a / 45).astype(int) % 8,
        "incline": masque_incline[toit] > 0,
    })


def agregerBatiment(df, gdf):
    """
    Somme les pixels par batiment, applique le modele PV, et joint le resultat aux batiments.
    --------
    @param[in] df  : sortie de irrPixels (1 ligne par pixel)
    @param[in] gdf : GeoDataFrame des batiments (index 0..n-1 = df.id)

    @return out : GeoDataFrame, 1 ligne par batiment ayant >= 1 pixel de toit
    """
    inc = df[df.incline]

    res = pd.DataFrame({
        "irr_an_kwh":       df.groupby("id").energie.sum(),
        "surf_inclinee_m2": inc.groupby("id").surf.sum(),
        "surf_plate_m2":    df[~df.incline].groupby("id").surf.sum(),
        "pente_moy":        inc.groupby("id").pente.mean(),
        "nb_pixels":        df.groupby("id").size(),
    })
    for s, nom in enumerate(SECTEURS):              # surface inclinee par orientation
        res[f"surf_{nom}_m2"] = inc[inc.secteur == s].groupby("id").surf.sum()

    res = res.fillna(0.0)
    res["surf_tot_m2"]   = res.surf_inclinee_m2 + res.surf_plate_m2
    res["irr_an_kwh_m2"] = res.irr_an_kwh / res.surf_tot_m2

    # modele PV simple : puissance et production decoulent du meme rendement
    res["puissance_kwc"] = res.surf_tot_m2 * TAUX_COUVERTURE * RENDEMENT_MODULE
    res["prod_an_kwh"]   = res.irr_an_kwh  * TAUX_COUVERTURE * RENDEMENT_MODULE * PERFORMANCE_RATIO

    return gdf.join(res, how="inner")               # garde les batiments avec >= 1 pixel de toit


def irradianceTuile(masque_incline, masque_plat, pente, aspect, gdf, horizon, lat, lon, out_path):
    """
    Calcul complet pour une dalle : lookup table -> irradiance par pixel (avec
    ombrage) -> agregation + production PV par batiment -> ecriture du GeoPackage.
    --------
    @param[in] masque_incline, masque_plat, pente, aspect : sorties du clip MNS/MNT
    @param[in] gdf      : GeoDataFrame des batiments de la dalle
    @param[in] horizon  : (N, n_dir) angles d'horizon par pixel (sortie de compHZ)
    @param[in] lat, lon : centre de la dalle, en degres WGS84 (-> cellule meteo)
    @param[in] out_path : chemin du .gpkg a ecrire

    @return out : GeoDataFrame ecrit
    """
    B, D, SAZ, SEL = chargerTable(lat, lon)
    df  = irrPixels(masque_incline, masque_plat, pente, aspect,
                    B, D, SAZ, SEL, horizon, ALPHAS, BETAS)
    out = agregerBatiment(df, gdf)
    out.to_file(out_path, driver="GPKG")
    return out
