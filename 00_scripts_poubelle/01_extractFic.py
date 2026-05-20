import laspy #librairie qui lit les fichiers LAS/LAZ
import numpy as np

las = laspy.read("data/raw/fic1.laz") #las contient tt les pts

# Infos générales
print(f"Nombre de points : {len(las.points):_}")
print(f"Classes présentes : {np.unique(las.classification)}") #las.classification tableau contenant tt les labels des pts

#bords du domaine
print(f"\nX : {las.x.min():.1f} → {las.x.max():.1f}")
print(f"Y : {las.y.min():.1f} → {las.y.max():.1f}")
print(f"Z : {las.z.min():.1f} → {las.z.max():.1f}")

print("\nPoints par classe :")
for c in np.unique(las.classification):
    n = np.sum(las.classification == c)
    print(f"  Classe {c} : {n} points")
   
   
"""
===============================================================================
ASPRS LAS/LAZ CLASSIFICATION CODES REFERENCE
===============================================================================
 0 : Never Classified  - Unprocessed points by any classification algorithm
 1 : Unassigned        - Processed but not assigned to a specific class
 2 : Ground            - Bare earth surface points (essential for DTM/MNT)
 3 : Low Vegetation    - Grass, crops, and vegetation under 0.5 meters
 4 : Medium Vegetation - Shrubs and vegetation between 0.5 and 2 meters
 5 : High Vegetation   - Trees and vegetation above 2 meters
 6 : Building          - Roof surfaces and building structures (Target class)
 7 : Low Point (Noise) - Low outliers, typical errors or ground clutter
 8 : Reserved          - Model Key-point in older specs (reserved in LAS 1.4)
 9 : Water             - Water surfaces (lakes, rivers, ponds)
10 : Rail              - Railway tracks
11 : Road Surface      - Paved road surfaces
12 : Reserved          - Overlap points in older specs (reserved in LAS 1.4)
13 : Wire – Guard      - Shield wires on power lines
14 : Wire – Conductor  - Phase/conductor wires carrying electricity
15 : Transmission Tower- Power line towers and poles
16 : Wire Connector    - Insulators and connectors on power infrastructure
17 : Bridge Deck       - Bridge surfaces
18 : High Noise        - High outliers (atmospheric interference, birds, etc.)
===============================================================================
"""