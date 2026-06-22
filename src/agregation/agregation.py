import pandas as pd
import geopandas as gpd

from src.config import SECTEURS, TAUX_COUVERTURE, RENDEMENT_MODULE, PERFORMANCE_RATIO

PV = TAUX_COUVERTURE * RENDEMENT_MODULE * PERFORMANCE_RATIO   # kWh recus -> kWh produits


def agregerBatiment(df, gdf, hauteur):
    """
    Agrege les pixels par batiment, applique le modele PV, joint a la BD TOPO.
    Production / puissance : base "orientee" = plat + incline sud (pans nord exclus).
    Surfaces descriptives (surf_incl_m2, secteurs, pente_moy_incl) : toutes orientations.
    --------
    @param[in] df  : sortie de irrPixels (1 ligne par pixel)
    @param[in] gdf : GeoDataFrame des batiments (index 0..n-1 = df.id)

    @return out : GeoDataFrame, 1 ligne par batiment ayant >= 1 pixel de toit
    """
    inc     = df[df.incline]                       # incline, toutes orientations
    inc_or  = df[df.incline_or]                    # incline oriente sud
    plat    = df[~df.incline]                      # plat
    oriente = df[df.incline_or | ~df.incline]      # plat + sud (base de production)

    res = pd.DataFrame({
        "irr_an_kwh":          df.groupby("id").energie.sum(),         # toute la toiture
        "irr_an_kwh_orp":      oriente.groupby("id").energie.sum(),    # plat + sud
        "surf_incl_m2":        inc.groupby("id").surf.sum(),
        "surf_incl_or_m2":     inc_or.groupby("id").surf.sum(),
        "surf_plate_m2":       plat.groupby("id").surf.sum(),
        "pente_moy_incl":           inc.groupby("id").pente.mean(),
        "nb_pixels":           df.groupby("id").size(),
    })
    for s, nom in enumerate(SECTEURS):             # surface inclinee par orientation
        res[f"surf_incl_{nom}_m2"] = inc[inc.secteur == s].groupby("id").surf.sum()
    for t in range(1, 5):                          # production par trimestre (orientee)
        res[f"prod_T{t}_kwh_orp"] = oriente.groupby("id")[f"energie_T{t}"].sum() * PV


    res["hauteur_pts"] = hauteur #hauteur a partir du mnh pas bdtopo

    res = res.fillna(0.0)                           # mettre des 0 au lieu de NaN

    res["surf_tot_m2"]      = res.surf_incl_m2 + res.surf_plate_m2
    res["puissance_kwc_orp"] = (res.surf_incl_or_m2 + res.surf_plate_m2) * TAUX_COUVERTURE * RENDEMENT_MODULE
    res["prod_an_kwh"]      = res.irr_an_kwh         * PV       # toute la toiture
    res["prod_an_kwh_orp"]   = res.irr_an_kwh_orp * PV          # plat + sud

    out = gdf.join(res, how="inner")               # garde les batiments avec >= 1 pixel de toit
    ordre = [
        "cleabs", "nature", "usage_1", "hauteur", "nombre_d_etages",
        "hauteur_pts",
        "nb_pixels", "surf_tot_m2", "surf_plate_m2",
        "surf_incl_m2", "surf_incl_or_m2", "pente_moy_incl",
        "surf_incl_N_m2", "surf_incl_NE_m2", "surf_incl_E_m2", "surf_incl_SE_m2",
        "surf_incl_S_m2", "surf_incl_SO_m2", "surf_incl_O_m2", "surf_incl_NO_m2",
        "irr_an_kwh", "prod_an_kwh",
        "irr_an_kwh_orp", "puissance_kwc_orp", "prod_an_kwh_orp",
        "prod_T1_kwh_orp", "prod_T2_kwh_orp", "prod_T3_kwh_orp", "prod_T4_kwh_orp",
        "geometry",
    ]
    return out[ordre]



def merger_cleabs(gdf):
    """Un batiment a cheval sur 2 dalles apparait 2x -> on garde le plus gros morceau."""
    return (gdf.sort_values("nb_pixels", ascending=False)
               .drop_duplicates("cleabs")
               .reset_index(drop=True))


def mergeCleabs(gdf):
    """
    Recolle les morceaux d'un meme batiment a cheval sur 2 dalles (meme cleabs) :
    somme les grandeurs additives, moyenne la pente, garde la hauteur max.
    --------
    @param[in] gdf : sortie de agregerBatiment (peut avoir plusieurs lignes par cleabs)

    @return GeoDataFrame : 1 ligne par cleabs (morceaux recolles)
    """
    agg = {c: "sum" for c in gdf.columns                          # surfaces, energies, prod, puissance, nb_pixels
           if c.startswith(("surf_", "irr_", "prod_", "puissance_")) or c == "nb_pixels"}
    agg.update(pente_moy_incl="mean", hauteur_pts="max",         # pente moyenne, hauteur la plus haute
               nature="first", usage_1="first", hauteur="first", # attributs BD TOPO (identiques)
               nombre_d_etages="first", geometry="first")
    out = gdf.groupby("cleabs", as_index=False).agg(agg)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=gdf.crs)