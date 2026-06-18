import pandas as pd
from src.config import SURF_MIN, HAUT_MIN, HAUT_MAX


def hBat(mnh, masque_bat, q=0.95):
    """Hauteur par batiment = quantile q du MNH sur l'emprise (m)."""
    ok = masque_bat > 0
    h = pd.DataFrame({"id": masque_bat[ok] - 1, "mnh": mnh[ok]})
    return h.groupby("id").mnh.quantile(q)       


def filtrer(gdf, surf_min=SURF_MIN, haut_min=HAUT_MIN, haut_max=HAUT_MAX):
    """Garde les batiments assez grands et assez hauts."""
    return gdf[(gdf.surf_tot_m2 >= surf_min) & (gdf.hauteur_pts >= haut_min) & (gdf.hauteur_pts <= haut_max)].copy()

