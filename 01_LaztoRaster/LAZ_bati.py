import laspy
import numpy as np
import os
import open3d as o3d


def laz_bati(laz_path, min_cluster=20, eps=1.0, min_pts=30, classe=6):
    """r
    Extrait les batiments d'un .laz 
    ---------------------------------------------------------------------------------------
    @param[in]  laz_path : Chemin du fichier .laz
    @param[in]  min_cluster : Nombre minimum de points pour former un cluster
    @param[in]  eps : Distance maximale entre les points pour les considérer comme voisins
    @param[in]  min_pts : Nombre minimum de points dans un cluster pour le conserver
    @param[in]  classe   : Classe LiDAR à rasteriser (6 = bâtiment)
    @param[out] laz_bati : fichier LAZ contenant que les points de la classe spécifiée
    ---------------------------------------------------------------------------------------
    """
    las = laspy.read(laz_path)
    xyz = np.column_stack([
        np.array(las.x[las.classification == classe]),
        np.array(las.y[las.classification == classe]),
        np.array(las.z[las.classification == classe])
    ])

    print(f"Points classe 6 : {len(xyz)}")

    if len(xyz) < min_cluster:  
        return []
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_cluster))

    nuages = []
    for lab in np.unique(labels[labels >= 0]):
        pts = xyz[labels == lab]
        if len(pts) >= min_pts:
            nuages.append(pts)

    print(f"Bâtiments détectés : {len(nuages)}")

    return nuages



#==============VISUALISATION=================


def sauv_laz(nuages, path_out):
    """
    Sauvegarde tous les nuages en un seul .laz.
    ----------------------------------------------------------
    @param[in]  nuages    : Liste d'arrays Nx3
    @param[in]  path_out  : Chemin complet du fichier de sortie (.laz)
    """
    xyz_all = np.vstack(nuages)
    ids = np.concatenate([
        np.full(len(xyz), i, dtype=np.int32)
        for i, xyz in enumerate(nuages)
    ])

    header = laspy.LasHeader(point_format=0, version="1.4")
    header.add_extra_dim(laspy.ExtraBytesParams(name="bat_id", type=np.int32))
    las = laspy.LasData(header=header)
    las.x = xyz_all[:, 0]
    las.y = xyz_all[:, 1]
    las.z = xyz_all[:, 2]
    las.bat_id = ids

    las.write(path_out)


