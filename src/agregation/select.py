import pandas as pd
from src.config import SURF_MIN, HAUT_MIN, HAUT_MAX


def hBat(mnh, masque_bat, q=0.95):
    """
    Hauteur par batiment : quantile q du MNH sur l'emprise (m).
    --------
    @param[in] mnh        : 2D float, hauteur au-dessus du sol (m)
    @param[in] masque_bat : 2D int, index gdf + 1 du batiment (0 hors batiment)
    @param[in] q          : quantile (0.95 = p95, robuste aux cheminees et au bruit)

    @return Series indexee par id (= index gdf) : hauteur du batiment (m)
    """
    ok = masque_bat > 0
    h = pd.DataFrame({"id": masque_bat[ok] - 1, "mnh": mnh[ok]})
    return h.groupby("id").mnh.quantile(q)       


def filtrer(gdf, surf_min=SURF_MIN, haut_min=HAUT_MIN, haut_max=HAUT_MAX):
    """
    Garde les batiments assez grands et dans une plage de hauteur plausible.
    --------
    @param[in] gdf                : GeoDataFrame de sortie (1 ligne par batiment)
    @param[in] surf_min           : surface totale minimale (m2)
    @param[in] haut_min, haut_max : bornes de hauteur mesuree (m)

    @return GeoDataFrame filtre
    """
    return gdf[(gdf.surf_tot_m2 >= surf_min) & (gdf.hauteur_pts >= haut_min) & (gdf.hauteur_pts <= haut_max)].copy()

