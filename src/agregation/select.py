import pandas as pd

def hBat(mnh, masque_bat, q=0.95):
    """Hauteur par batiment = quantile q du MNH sur l'emprise (m)."""
    ok = masque_bat > 0
    h = pd.DataFrame({"id": masque_bat[ok] - 1, "mnh": mnh[ok]})
    return h.groupby("id").mnh.quantile(q)       