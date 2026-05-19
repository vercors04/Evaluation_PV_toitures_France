import laspy
import numpy as np
from sklearn.cluster import DBSCAN #DBscan regroupe les points par densité, pour isoler les batiments

las = laspy.read("data/raw/fic1.laz")

x = las.x[las.classification==6]
y = las.y[las.classification==6]
z = las.z[las.classification==6]



# eps = distance max entre deux points pour être dans le même cluster (en mètres)
# min_samples = nombre minimum de points pour former un cluster
db = DBSCAN(eps=0.8, min_samples=10).fit(np.column_stack([x, y]))
labels = db.labels_ #batiment 1 avec le label 0, etc etc. Le bruit avec le label -1. 

nb_build = len(np.unique(labels)) - (1 if -1 in labels else 0)
print(f"Bâtiments détectés : {nb_build}")
print(f"Points bruit : {np.sum(labels == -1):_}")

for label in np.unique(labels):
    if label == -1:
        continue
    n = np.sum(labels == label)
    if n > 500:  
        print(f"  Bâtiment {label} : {n} points")