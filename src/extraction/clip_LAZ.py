import laspy
import numpy as np
import open3d as o3d


def clipLAZ(laz_path, min_cluster=20, eps=0.5, min_pts=30, classe=6):
    """r
    Extrait les batiments d'un .laz 
    ---------------------------------------------------------------------------------------
    @param[in]  laz_path : Chemin du fichier .laz
    @param[in]  min_cluster : Nombre minimum de points pour former un cluster
    @param[in]  eps : Distance maximale entre les points pour les considérer comme voisins
    @param[in]  min_pts : Nombre minimum de points dans un cluster pour le conserver
    @param[in]  classe   : Classe LiDAR à rasteriser (6 = bâtiment)
    @param[out] nuages : liste de nuages de points contenant que les points de la classe spécifiée
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
    num = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_cluster)) #donne un num a chaque point selon le cluster auquel il appartient, -1 si bruit

    nuages = []
    # regroupe les pts par clust
    for n in np.unique(num[num >= 0]):
        pts = xyz[num == n]
        if len(pts) >= min_pts:
            nuages.append(pts)

    print(f"Bâtiments détectés : {len(nuages)}")

    return nuages



