import geopandas as gpd

GPKG = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
gdf = gpd.read_file(GPKG, layer="batiment", rows=2000)
print("usage_1 :", gdf["usage_1"].value_counts())
print("etat_de_l_objet :", gdf["etat_de_l_objet"].value_counts())