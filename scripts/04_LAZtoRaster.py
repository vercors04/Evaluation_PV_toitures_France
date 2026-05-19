import laspy
import sys
import numpy as np
import rasterio  # pour manipuler les donnees spatiale matricielles, permet de cree un geoTIFF
from rasterio.transform import from_origin


def laz_raster(path_in, path_out, resol, type):
    """
    Fonction pour la conversion d'un nuage de points LAZ en raster GeoTIFF (MNS)
    ---------------------------------------------------------------------------------------
    @param[in]  path_in      : Chemin d'accès vers le .laz d'entree
    @param[in]  path_out     : Chemin d'accès pour le .tif de sortie
    @param[in]  resol        : Taille pixel en m
    @param[in]  type         : Classe LiDAR a etudier

    @param[out] mns          : Matrice NumPy 2D représentant la grille du raster
    @param[out] transf       : Matrice de transformation géométrique affine 
    ---------------------------------------------------------------------------------------
    """
    try:
        las = laspy.read(path_in)
    except Exception:
        print(f"Erreur : Impossible de lire le fichier {path_in}")
        sys.exit (1)
    
    if (len(x)==0) :
        print("aucun point avec le type {type} dans le fichier")
        sys.exit (1)

    x = las.x[las.classification == type]
    y = las.y[las.classification == type]
    z = las.z[las.classification == type]

    xmin = las.x.min()
    xmax = las.x.max()
    ymin = las.y.min()
    ymaw = las.y.max()
