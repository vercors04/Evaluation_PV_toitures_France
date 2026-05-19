import numpy as np
import rasterio
import geopandas as gpd
import laspy
import pvlib
import pandas as pd

print("numpy :", np.__version__)
print("rasterio :", rasterio.__version__)
print("geopandas :", gpd.__version__)
print("laspy :", laspy.__version__)
print("pvlib :", pvlib.__version__)

# Test pvlib — position du soleil à Bordeaux
from pvlib.location import Location
bordeaux = Location(latitude=44.84, longitude=-0.58, tz='Europe/Paris')
now = pd.Timestamp.now(tz='Europe/Paris')
pos = bordeaux.get_solarposition(now)
print(f"\nSoleil à Bordeaux maintenant :")
print(f"  Élévation : {pos['elevation'].values[0]:.1f}°")
print(f"  Azimut    : {pos['azimuth'].values[0]:.1f}°")
print("\nEnvironnement prêt.")