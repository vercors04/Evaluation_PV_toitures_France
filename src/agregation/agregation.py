import pandas as pd
import geopandas as gpd

from src import config


def agregerBatiment(df, gdf, hauteur):
    """
    Agrege les pixels par batiment, applique le modele PV, joint a la BD TOPO.
    Production / puissance sur base "orientee" = plat + incline dans la fenetre d'azimut.
    Surfaces descriptives (surf_incl_m2, secteurs, pente_moy_incl) : toutes orientations.
    --------
    @param[in] df      : sortie de irrPixels (1 ligne par pixel)
    @param[in] gdf     : GeoDataFrame des batiments (index 0..n-1 = df.id)
    @param[in] hauteur : Series hauteur par batiment (index = df.id), issue du MNH

    @return out : GeoDataFrame, 1 ligne par batiment ayant >= 1 pixel de toit
    """
    pv = config.TAUX_COUVERTURE * config.RENDEMENT_MODULE * config.PERFORMANCE_RATIO  # conversion des kWh recus en kWh produits

    inc     = df[df.incline]                       # incline, toutes orientations
    inc_or  = df[df.incline_or]                    # incline dans la fenetre d'azimut
    plat    = df[~df.incline]                      # plat
    oriente = df[df.incline_or | ~df.incline]      # plat + oriente (base de production)
    seuil   = df[df.energie / df.surf >= config.SEUIL_IRRADIANCE]

    res = pd.DataFrame({
        "irr_an_kwh":          df.groupby("id").energie.sum(),         # toute la toiture
        "irr_an_kwh_orp":      oriente.groupby("id").energie.sum(),    # plat + oriente
        "irr_seuil_kwh":       seuil.groupby("id").energie.sum(),
        "surf_incl_m2":        inc.groupby("id").surf.sum(),
        "surf_incl_or_m2":     inc_or.groupby("id").surf.sum(),
        "surf_plate_m2":       plat.groupby("id").surf.sum(),
        "surf_seuil_m2":       seuil.groupby("id").surf.sum(),
        "pente_moy_incl":           inc.groupby("id").pente.mean(),
        "nb_pixels":           df.groupby("id").size(),
    })
    for s, nom in enumerate(config.SECTEURS):      # surface inclinee par orientation
        res[f"surf_incl_{nom}_m2"] = inc[inc.secteur == s].groupby("id").surf.sum()
    for t in range(1, 5):                          # production par trimestre (orientee)
        res[f"prod_T{t}_kwh_orp"] = oriente.groupby("id")[f"energie_T{t}"].sum() * pv


    res["hauteur_pts"] = hauteur   # hauteur issue du MNH, pas de la BD TOPO

    res = res.fillna(0.0)                           # batiment sans pixel d'une categorie : 0 plutot que NaN

    kwc = config.TAUX_COUVERTURE * config.RENDEMENT_MODULE
    res["surf_tot_m2"]         = res.surf_incl_m2 + res.surf_plate_m2
    res["puissance_kwc"]       = res.surf_tot_m2 * kwc
    res["puissance_kwc_orp"]   = (res.surf_incl_or_m2 + res.surf_plate_m2) * kwc
    res["puissance_kwc_seuil"] = res.surf_seuil_m2 * kwc
    res["prod_an_kwh"]         = res.irr_an_kwh    * pv
    res["prod_an_kwh_orp"]     = res.irr_an_kwh_orp * pv
    res["prod_seuil_kwh"]      = res.irr_seuil_kwh * pv

    out = gdf.join(res, how="inner")               # garde les batiments avec >= 1 pixel de toit
    ordre = (["cleabs", *config.ATTRS_BATI, "hauteur_pts",
              "nb_pixels", "surf_tot_m2", "surf_plate_m2",
              "surf_incl_m2", "surf_incl_or_m2", "surf_seuil_m2", "pente_moy_incl"]
             + [f"surf_incl_{s}_m2" for s in config.SECTEURS]
             + ["irr_an_kwh", "puissance_kwc", "prod_an_kwh",
                "irr_an_kwh_orp", "puissance_kwc_orp", "prod_an_kwh_orp",
                "irr_seuil_kwh", "puissance_kwc_seuil", "prod_seuil_kwh"]
             + [f"prod_T{t}_kwh_orp" for t in range(1, 5)]
             + ["geometry"])
    return out[ordre]


def mergeCleabs(gdf):
    """
    Recolle les morceaux d'un meme batiment a cheval sur plusieurs dalles (meme cleabs) :
    somme les grandeurs additives, moyenne ponderee de la pente, garde la hauteur max.
    --------
    @param[in] gdf : sortie de agregerBatiment (plusieurs lignes possibles par cleabs)

    @return GeoDataFrame : 1 ligne par cleabs (morceaux recolles)
    """
    gdf = gdf.copy()
    gdf["_pente_pond"] = gdf.pente_moy_incl * gdf.surf_incl_m2    # pour la moyenne ponderee (par surface inclinee)
    agg = {c: "sum" for c in gdf.columns                          # surfaces, energies, prod, puissance, nb_pixels
           if c.startswith(("surf_", "irr_", "prod_", "puissance_")) or c in ("nb_pixels", "_pente_pond")}
    agg.update({a: "first" for a in config.ATTRS_BATI})   # attributs BD TOPO recopies
    agg.update(hauteur_pts="max", geometry="first")
    out = gdf.groupby("cleabs", as_index=False).agg(agg)
    out["pente_moy_incl"] = (out._pente_pond / out.surf_incl_m2).fillna(0.0)  # pente moyenne ponderee par surface
    out = out.drop(columns="_pente_pond")
    return gpd.GeoDataFrame(out, geometry="geometry", crs=gdf.crs)