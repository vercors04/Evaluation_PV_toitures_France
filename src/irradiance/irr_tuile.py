"""
src/irradiance/irr_tuile.py
Helper pour travailler sur UNE dalle (tests) : a partir du nom du fichier MNS IGN,
retrouve ses coordonnees et le centre en WGS84 (pour charger la bonne cellule
meteo). N'est PAS utilise par la pipeline finale (qui boucle sur les dalles).
"""
from pyproj import Transformer


def nomCoord(MNS_name):
    """
    Coordonnees du coin nord-ouest de la tuile (convention IGN), en km Lambert 93.
    --------
    @param[in] MNS_name : nom du fichier MNS IGN (ex: LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif)

    @return x_km, y_km : coin nord-ouest de la tuile, en km Lambert 93
    """
    base = MNS_name.replace(".tif", "")
    p = base.split("_")
    return int(p[2]), int(p[3])


def centreWGS84(x_km, y_km):
    """
    Centre de la tuile 1 km x 1 km, converti de Lambert 93 a WGS84.
    --------
    @param[in] x_km, y_km : coin nord-ouest de la tuile, en km Lambert 93 (convention IGN)

    @return lat, lon : coordonnees du centre de la tuile, en degres WGS84
    """
    xc, yc = x_km * 1000 + 500, y_km * 1000 - 500   # -500 : le nom IGN donne le coin NORD-ouest
    tr = Transformer.from_crs(2154, 4326, always_xy=True)
    lon, lat = tr.transform(xc, yc)
    return lat, lon
