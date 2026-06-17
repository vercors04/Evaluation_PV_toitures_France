import re

from pyproj import Transformer


def nomCoord(mns_name):
    """
    Coordonnees du coin nord-ouest de la tuile (convention IGN), en km Lambert 93.
    --------
    @param[in] mns_name : nom du fichier MNS IGN (ex: LHD_FXX_0495_6611_MNS_...tif)

    @return x_km, y_km : coin nord-ouest de la tuile (km Lambert 93)
    """
    p = mns_name.replace(".tif", "").split("_")
    return int(p[2]), int(p[3])


def centreWGS84(x_km, y_km):
    """
    Centre de la tuile 1 km x 1 km, converti de Lambert 93 a WGS84.
    --------
    @param[in] x_km, y_km : coin nord-ouest de la tuile (km Lambert 93)

    @return lat, lon : centre de la tuile (deg WGS84)
    """
    xc, yc = x_km * 1000 + 500, y_km * 1000 - 500       # -500 : le nom IGN donne le coin NORD-ouest
    tr = Transformer.from_crs(2154, 4326, always_xy=True)
    lon, lat = tr.transform(xc, yc)
    return lat, lon


def tileBounds(mns_name):
    """
    Emprise de la tuile depuis le nom du fichier MNS IGN.
    --------
    @param[in] mns_name : nom du fichier MNS IGN (0495_6611 -> x=495000, y=6611000, coin NO)

    @return (x_min, y_min, x_max, y_max) en Lambert 93 (tuile 1 km x 1 km)
    """
    match = re.search(r'_(\d{4})_(\d{4})_', mns_name)
    if not match:
        raise ValueError(f"Nom de fichier incorrect : {mns_name}")

    x_km, y_km = int(match.group(1)), int(match.group(2))
    x_min, y_max = x_km * 1000, y_km * 1000
    return (x_min, y_max - 1000, x_min + 1000, y_max)
