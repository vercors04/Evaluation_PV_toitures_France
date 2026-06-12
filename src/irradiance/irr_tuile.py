import pvlib
from pyproj import Transformer

URL = "https://re.jrc.ec.europa.eu/api/v5_3/"   # PVGIS 5.3 (SARAH-3, 2005-2023)

def nomCoord(MNS_name):
    """
    Retourne les coordonnees du coin bas-gauche de la tuile, en km Lambert 93.
    --------
    @param[in] 

    @return 
    """
    base = MNS_name.replace(".tif", "")
    p = base.split("_")
    x_str = p[2]
    y_str = p[3]
    return int(x_str), int(y_str)



def centreWGS84(x_km, y_km):
    """
    Centre de la tuile 1 km x 1 km, converti de Lambert 93 a WGS84.
    --------
    @param[in] x_km, y_km : coordonnees du coin bas-gauche de la tuile, en km Lambert 93

    @return lat, lon : coordonnees du centre de la tuile, en degees WGS84
    """
    xc, yc = x_km * 1000 + 500, y_km * 1000 + 500
    tr = Transformer.from_crs(2154, 4326, always_xy=True)
    lon, lat = tr.transform(xc, yc)
    return lat, lon


