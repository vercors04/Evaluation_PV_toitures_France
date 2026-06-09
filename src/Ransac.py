import numpy as np
import open3d as o3d


def ransac1Bat(xyz, seuil=0.1, min_ratio=0.2, n_iter=1000,
                    pente_max=70.0, min_pts_pan=50):
    """
    Détecte les pans de toiture d'un bâtiment par RANSAC séquentiel.
    ---------------------------------------------------------------
    @param[in]  xyz         : array Nx3 points du bâtiment
    @param[in]  seuil       : distance max au plan RANSAC (m)
    @param[in]  min_ratio   : ratio min de points restants pour continuer
    @param[in]  n_iter      : nb itérations RANSAC
    @param[in]  pente_max   : seuil rejet façades (degrés)
    @param[in]  min_pts_pan : nb min de points pour garder un pan
    @param[out] pans        : liste de dicts {points, pente, azimut, normale}
    """
    #xyz = RemoveNoiseStatistical(xyz, nb_neighbors=20, std_ratio=2.0)

    pans_brut = DetectMultiPlanes(xyz, min_ratio=min_ratio,
                                  threshold=seuil, iterations=n_iter)
    pans = []
    for equation, pts_pan in pans_brut:
        if len(pts_pan) < min_pts_pan:
            continue

        a, b, c, d = equation
        n = np.array([a, b, c])
        n = n / np.linalg.norm(n)
        if n[2] < 0:
            n = -n

        pente  = np.degrees(np.arccos(np.clip(n[2], -1, 1)))
        azimut = np.degrees(np.arctan2(n[0], n[1])) % 360

        if pente > pente_max:   # façade → rejetée
            continue

        pans.append({
            "points": pts_pan,
            "pente":  round(pente, 1),
            "azimut": round(azimut, 1),
            "normale": n,
        })
    return pans


def ransacTot(masque_bat, pts_ok, mns, transform, gdf, min_pts=20):
    from shapely.geometry import MultiPoint
    pans_tous = []
    for idx, bat in gdf.iterrows():
        
        mask = (masque_bat == idx) & pts_ok
        if mask.sum() < min_pts:
            continue
        
        xyz = mnsToPointCloud(np.where(mask, mns, np.nan), transform)
        if xyz is None:
            continue
        
        pans = ransac1Bat(xyz, seuil=0.05, n_iter=500, pente_max=60.0, min_pts_pan=min_pts)
        for pan in pans:
            geom_pan = MultiPoint(pan["points"][:, :2]).convex_hull
            # intersection avec emprise bâtiment pour éviter débordements
            geom_pan = geom_pan.intersection(bat.geometry)
            
            if geom_pan.is_empty:
                continue
                
            pans_tous.append({
                "cleabs"  : bat["cleabs"],
                "pente"   : pan["pente"],
                "azimut"  : pan["azimut"],
                "geometry": geom_pan,
            })
    return pans_tous


def mnsToPointCloud(mns, transf):
    """
    Convertit une vignette MNS (raster 2D) en nuage de points 3D.

    """
    rows, cols = np.where(~np.isnan(mns))
    if len(rows) == 0:
        return None
    x = transf.c + cols * transf.a
    y = transf.f + rows * transf.e
    z = mns[rows, cols]
    return np.column_stack([x, y, z])


#===========================================================================================
# fonctions prise du depot github https://github.com/yuecideng/Multiple_Planes_Detection
#===========================================================================================

def DetectMultiPlanes(points, min_ratio=0.05, threshold=0.01, iterations=1000):
    """ Detect multiple planes from given point clouds

    Args:
        points (np.ndarray): 
        min_ratio (float, optional): The minimum left points ratio to end the Detection. Defaults to 0.05.
        threshold (float, optional): RANSAC threshold in (m). Defaults to 0.01.

    Returns:
        [List[tuple(np.ndarray, List)]]: Plane equation and plane point index
    """

    plane_list = []
    N = len(points)
    target = points.copy()
    count = 0

    while count < (1 - min_ratio) * N:
        w, index = PlaneRegression(
            target, threshold=threshold, init_n=3, iter=iterations)
    
        count += len(index)
        plane_list.append((w, target[index]))
        target = np.delete(target, index, axis=0)

    return plane_list





def NumpyToPCD(xyz):
    """ convert numpy ndarray to open3D point cloud 

    Args:
        xyz (ndarray): 

    Returns:
        [open3d.geometry.PointCloud]: 
    """

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)

    return pcd


def PCDToNumpy(pcd):
    """  convert open3D point cloud to numpy ndarray

    Args:
        pcd (open3d.geometry.PointCloud): 

    Returns:
        [ndarray]: 
    """

    return np.asarray(pcd.points)




def RemoveNoiseStatistical(pc, nb_neighbors=20, std_ratio=2.0):
    """ remove point clouds noise using statitical noise removal method

    Args:
        pc (ndarray): N x 3 point clouds
        nb_neighbors (int, optional): Defaults to 20.
        std_ratio (float, optional): Defaults to 2.0.

    Returns:
        [ndarray]: N x 3 point clouds
    """

    pcd = NumpyToPCD(pc)
    cl, ind = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio)

    return PCDToNumpy(cl)




def PlaneRegression(points, threshold=0.01, init_n=3, iter=1000):
    """ plane regression using ransac

    Args:
        points (ndarray): N x3 point clouds
        threshold (float, optional): distance threshold. Defaults to 0.003.
        init_n (int, optional): Number of initial points to be considered inliers in each iteration
        iter (int, optional): number of iteration. Defaults to 1000.

    Returns:
        [ndarray, List]: 4 x 1 plane equation weights, List of plane point index
    """

    pcd = NumpyToPCD(points)

    w, index = pcd.segment_plane(
        threshold, init_n, iter)

    return w, index




