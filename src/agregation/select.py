import pandas as pd
from src import config


def hBat(mnh, masque_haut, q=0.95):
    """
    Hauteur par batiment : quantile q du MNH sur ses pixels.
    --------
    @param[in] mnh         : 2D float, hauteur au-dessus du sol (m)
    @param[in] masque_haut : 2D int, index gdf + 1 (0 hors batiment), avant critere de pente
    @param[in] q           : quantile (0.95 = p95)

    @return Series indexee par id (= index gdf) : hauteur (m)
    """
    ok = masque_haut > 0
    h = pd.DataFrame({"id": masque_haut[ok] - 1, "mnh": mnh[ok]})
    return h.groupby("id").mnh.quantile(q)


def filtrer(gdf):
    """
    Garde les batiments assez grands et dans une plage de hauteur plausible.
    Seuils : config.SURF_MIN, config.HAUT_MIN, config.HAUT_MAX.
    --------
    @param[in] gdf : GeoDataFrame de sortie (1 ligne par batiment)

    @return GeoDataFrame filtre
    """
    return gdf[(gdf.surf_m2 >= config.SURF_MIN)
               & (gdf.hauteur_p95_m >= config.HAUT_MIN)
               & (gdf.hauteur_p95_m <= config.HAUT_MAX)].copy()
