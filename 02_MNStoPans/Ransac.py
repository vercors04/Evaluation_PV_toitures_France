import numpy as np
import open3d as o3d
from ClipMNS import *
from ExtractBDtopo import *


# fonctions inspirees du depot github https://github.com/yuecideng/Multiple_Planes_Detection


def NumpyToPCD(xyz):
    """
    Convertit un array numpy en PointCloud open3d.
    Ref : yuecideng/Multiple_Planes_Detection — NumpyToPCD()
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    return pcd


def RemoveNoise(points, nb_neighbors=20, std_ratio=2.0):
    """
    Supprime les points aberrants par filtre statistique.
    Ref : yuecideng/Multiple_Planes_Detection — RemoveNoiseStatistical()
    """
    pcd = NumpyToPCD(points)
    cl, _ = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    return np.asarray(cl.points)


def PlaneRegression(points, threshold=0.15, init_n=3, iterations=1000):
    """
    RANSAC pour détecter le plan dominant dans un nuage de points.
    Ref : yuecideng/Multiple_Planes_Detection — PlaneRegression()
    ---------------------------------------------------------------------------------------
    @param[in]  points     : N x3 point clouds
    @param[in]  threshold  : distance threshold.
    @param[in]  init_n     : Number of initial points to be considered inliers in each iteration
    @param[in]  iterations : number of iteration.

    @param[out] w          : Equation du plan (a,b,c,d) tq ax+by+cz+d=0
    @param[out] index      : Indices des inliers
    ---------------------------------------------------------------------------------------
    """
    pcd = NumpyToPCD(points)
    w, index = pcd.segment_plane(threshold, init_n, iterations)
    return w, index


def DetectMultiPlanes(points, min_ratio=0.05, threshold=0.15, iterations=1000):
    """
    Détecte plusieurs plans séquentiellement (RANSAC itératif).
    Ref : yuecideng/Multiple_Planes_Detection — DetectMultiPlanes()
    ---------------------------------------------------------------------------------------
    @param[in]  points     : Array (N,3) nuage de points du bâtiment
    @param[in]  min_ratio  : The minimum left points ratio to end the Detection.
    @param[in]  threshold  : RANSAC threshold in (m).
    @param[in]  iterations : Nb d'itérations par plan

    @param[out] plane_list : Plane equation and plane point index
    ---------------------------------------------------------------------------------------
    """
    plane_list = []
    N = len(points)
    remaining = points.copy()
    count = 0

    while count < (1 - min_ratio) * N:
        if len(remaining) < 10:
            break
        w, index = PlaneRegression(remaining, threshold, iterations=iterations)
        count += len(index)
        plane_list.append((w, remaining[index]))
        remaining = np.delete(remaining, index, axis=0)

    return plane_list


def MNSToPointCloud(mns, transf):
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


def PlaneToAngles(w):
    """
    Calcule pente et azimut depuis l'équation du plan ax+by+cz+d=0.
    ---------------------------------------------------------------------------------------
    @param[in]  w      : tuple (a,b,c,d)
    @param[out] pente  : inclinaison en degrés (0°=plat, 90°=vertical)
    @param[out] azimut : orientation en degrés (0°=Nord, 90°=Est, 180°=Sud, 270°=Ouest)
    ---------------------------------------------------------------------------------------
    """
    a, b, c, _ = w
    normal = np.array([a, b, c])
    normal = normal / np.linalg.norm(normal)

    if normal[2] < 0:
        normal = -normal

    pente  = np.degrees(np.arccos(np.clip(normal[2], -1, 1)))
    azimut = np.degrees(np.arctan2(normal[0], normal[1])) % 360

    return round(pente, 1), round(azimut, 1)



def AzimutToOrientation(az):
    if az <= 22.5 or az > 337.5:   return 'Nord'
    elif az <= 67.5:                return 'Nord-Est'
    elif az <= 112.5:               return 'Est'
    elif az <= 157.5:               return 'Sud-Est'
    elif az <= 202.5:               return 'Sud'
    elif az <= 247.5:               return 'Sud-Ouest'
    elif az <= 292.5:               return 'Ouest'
    else:                           return 'Nord-Ouest'


if __name__ == "__main__":
    import pandas as pd

    MNS_FILE  = "LHD_FXX_0495_6611_MNS_O_0M50_LAMB93_IGN69.tif"
    GPKG_FILE = "data/raw/vienne.gpkg"
    THRESHOLD = 0.15
    MIN_RATIO = 0.15
    MAX_PENTE = 70.0
    MIN_SURFACE = 5.0

    tile_bounds = TileBounds(MNS_FILE)
    gdf         = LoadBuild(GPKG_FILE, tile_bounds)
    buildings   = clipMNS(f"data/raw/{MNS_FILE}", gdf)
    buildings = [b for b in buildings if b['cleabs'] == 'BATIMENT0000000273342486']

    resultats = []

    for b in buildings:
        points = MNSToPointCloud(b['mns'], b['transf'])
        if points is None or len(points) < 10:
            continue

        points = RemoveNoise(points, nb_neighbors=20, std_ratio=2.0)
        if len(points) < 10:
            continue

        planes = DetectMultiPlanes(points, min_ratio=MIN_RATIO,
                                   threshold=THRESHOLD, iterations=1000)
        
        for w, pts in planes:
            pente, azimut = PlaneToAngles(w)
            surface = len(pts) * 0.25
            print(f"  Pan : pente={pente:.1f}°  azimut={azimut:.1f}°  surface={surface:.1f} m²")

            if pente > MAX_PENTE or surface < MIN_SURFACE:
                continue

            

            resultats.append({
                'cleabs' : b['cleabs'],
                'usage'  : b['usage'],
                'pente'  : pente,
                'azimut' : azimut,
                'surface': round(surface, 1)
            })

        n_pans = sum(1 for r in resultats if r['cleabs'] == b['cleabs'])
        print(f"{b['cleabs']} → {n_pans} pan(s)")

    df = pd.DataFrame(resultats)
    print(f"\nTotal pans détectés : {len(df)}")
    print(f"Pente moyenne       : {df['pente'].mean():.1f}°")
    print(f"Surface totale      : {df['surface'].sum():.0f} m²")



    df['orientation'] = df['azimut'].apply(AzimutToOrientation)
    print("\nRépartition par orientation (surface en m²) :")
    print(df.groupby('orientation')['surface'].sum().round(0))
    print("\nRépartition par orientation (nombre de pans) :")
    print(df['orientation'].value_counts())