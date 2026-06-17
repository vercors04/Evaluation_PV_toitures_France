import geopandas as gpd


def loadBuild(gpkg_path, tile_bounds):
    """
    Charge et filtre les batiments exploitables depuis la BD TOPO.
    --------
    @param[in] gpkg_path   : chemin du GeoPackage BD TOPO
    @param[in] tile_bounds : (x_min, y_min, x_max, y_max) Lambert 93 (None = tout le dep.)

    @return gdf : GeoDataFrame filtre, index 0..n-1, colonnes
                  cleabs, nature, usage_1, hauteur, nombre_d_etages, geometry
    """
    if tile_bounds is not None:
        gdf = gpd.read_file(gpkg_path, layer='batiment', bbox=tile_bounds)   # index spatial : lit juste la tuile
    else:
        gdf = gpd.read_file(gpkg_path, layer='batiment')

    total = len(gdf)
    gdf = gdf[
        (gdf['etat_de_l_objet'] == 'En service') &
        (gdf['construction_legere'] == False)
    ].copy().reset_index(drop=True)

    gdf = gdf[['cleabs', 'nature', 'usage_1', 'hauteur',
               'nombre_d_etages', 'geometry']].copy()

    print(f"Batiments tuile : {total:,}  |  conserves : {len(gdf):,}  |  exclus : {total - len(gdf):,}")
    return gdf
