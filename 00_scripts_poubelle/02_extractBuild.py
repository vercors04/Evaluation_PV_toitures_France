import laspy
import numpy as np
import matplotlib.pyplot as plt

las = laspy.read("data/raw/fic1.laz")

x = las.x[las.classification==6]
y = las.y[las.classification==6]
z = las.z[las.classification==6]

print(f"Points bâtiment extraits : {len(x):_}")
print(f"Z min : {z.min():.1f}m  Z max : {z.max():.1f}m")

# Visualisation vue de dessus (X, Y) colorée par hauteur Z
plt.figure(figsize=(13, 10))
plt.scatter(x, y, c=z, cmap='viridis', s=0.1) #couleur =z, viridis pack couleurs s=0.1 points de petite taille
plt.colorbar(label='Altitude (m)')
plt.title("Points bâtiment — vue de dessus")
plt.xlabel("X")
plt.ylabel("Y")
plt.axis('equal') #impose un ratio de 1:1 entre les deux axes
plt.savefig("data/images/buildings_top_view.png", dpi=150)
