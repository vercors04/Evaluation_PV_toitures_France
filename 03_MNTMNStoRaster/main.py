import laspy
import numpy as np

las = laspy.read("data/raw/LHD_FXX_0475_6594_PTS_LAMB93_IGN69.copc.laz")
mask = las.classification == 6
x = np.array(las.x[mask])
y = np.array(las.y[mask])
z = np.array(las.z[mask])

print(f"Nb points classe 6 : {len(x)}")
print(f"Z median : {np.median(z):.1f}")
print(f"MAD : {np.median(np.abs(z - np.median(z))) * 1.4826:.1f}")

z_med = np.median(z)
mad = np.median(np.abs(z - z_med)) * 1.4826
ok = z <= z_med + 5 * mad
print(f"Points après filtre MAD : {np.sum(ok)}")