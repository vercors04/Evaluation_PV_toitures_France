import re
import geopandas as gpd

def TileBounds(mns_name):
    """
    Extrait l'emprise (bounds) d'une tuile depuis le nom du fichier MNS IGN.
    ---------------------------------------------------------------------------------------
    @param[in]  mns_name : Nom du fichier MNS IGN   LHD_FXX_0475_6594_MNS_O_0M50_LAMB93_IGN69.tif

    @param[out] tuple        : (x_min, y_min, x_max, y_max) en Lambert 93
    ---------------------------------------------------------------------------------------
    Convention IGN : 0475_6594 → x=475000, y=6594000 (coin nord-ouest)
    Tuile = 1km x 1km
    """
    #objet match qui recherche des occurences de caractères, fonctionne un peu comme un tableau
    match = re.search(r'_(\d{4})_(\d{4})_', mns_name) 
    if not match:
        raise ValueError(f"Nom de fichier incorrect : {mns_name}")

    x_km = int(match.group(1))  
    y_km = int(match.group(2))  

    x_min = x_km * 1000        
    x_max = x_min + 1000        
    y_max = y_km * 1000         
    y_min = y_max - 1000        

    print(f"Coord de la tuile : X=[{x_min}, {x_max}] Y=[{y_min}, {y_max}]")

    
    return (x_min, y_min, x_max, y_max)


def LoadBuild(gpkg_name, tile_bounds):
    """
    Charge et filtre les bâtiments exploitables depuis la BD TOPO.
    ---------------------------------------------------------------------------------------
    @param[in]  gpkg_name    : Nom du fichier .gpkg
    @param[in]  tile_bounds  : Tuple (x_min, y_min, x_max, y_max) en Lambert 93
                               None = charge tout le département.
    @param[out] gdf          : GeoDataFrame filtré (bâtiments exploitables)
    ---------------------------------------------------------------------------------------
    """
    USAGES_GARDES = [
    'Indifférenciée',
    'Industriel, agricole ou commercial',
    'Eglise',
    'Chapelle',
    'Monument',
    'Château',
    ]

    if tile_bounds is not None:
        gdf = gpd.read_file(f"data/raw/{gpkg_name}", layer='batiment', bbox=tile_bounds) #on lit que le carré qui nous interesse
    else:
        gdf = gpd.read_file(f"data/raw/{gpkg_name}", layer='batiment')

    total = len(gdf)

    gdf = gdf[
        (gdf['nature'].isin(USAGES_GARDES)) &
        (gdf['etat_de_l_objet'] == 'En service')
    ].copy()

    #on garde que les colonnes utiles
    gdf = gdf[['cleabs', 'nature', 'hauteur', 'nombre_d_etages', 'geometry']]

    print(f"Bâtiments totaux    : {total:,}")
    print(f"Bâtiments conservés : {len(gdf):,}")
    print(f"Bâtiments exclus    : {total - len(gdf):,}")

    return gdf

