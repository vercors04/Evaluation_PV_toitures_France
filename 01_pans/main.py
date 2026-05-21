import requests

r = requests.get("https://api-adresse.data.gouv.fr/search/",
                 params={"q": "42 Chemin du Sémaphore, Poitiers", "limit": 1})
print(r.json())

from pyproj import Transformer
from shapely.geometry import Point
import geopandas as gpd

# Coordonnées
feat = r.json()["features"][0]
lon, lat = feat["geometry"]["coordinates"]

# Lambert 93
t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
x, y = t.transform(lon, lat)

# Charger la BD TOPO autour du point
gdf = gpd.read_file("data/raw/vienne.gpkg", layer="batiment",
                    bbox=(x-100, y-100, x+100, y+100))

# Trouver le bâtiment
point = Point(x, y)
bat_proches = gdf[gdf.geometry.distance(point) < 50]
bat_principal = bat_proches.loc[bat_proches.geometry.area.idxmax()]
print(bat_principal[["cleabs", "usage_1", "hauteur"]])