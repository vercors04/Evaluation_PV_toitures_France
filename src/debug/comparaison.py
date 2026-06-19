"""
src/debug/comparaison.py
Compare, le plus simplement possible, l'impact de 2 choix de modelisation :
  1. la TAILLE des cellules meteo   -> variation spatiale de l'irradiance
  2. le MOYENNAGE mensuel vs horaire -> impact sur l'ombrage
Lancer depuis la racine : python -m src.debug.comparaison
"""
import glob
import numpy as np
import pandas as pd
import pvlib

from src.irradiance.meteo.irr_fct import telecharger

NJ = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])   # jours par mois


def effet_taille_cellule():
    """1. De combien l'irradiance varie-t-elle d'une cellule a l'autre ?"""
    print("=== 1. Taille de cellule (variation spatiale) ===")
    E = []
    for f in sorted(glob.glob("data/tables/*.npz")):
        d = np.load(f)                               # irradiation horizontale annuelle (kWh/m2/an)
        E.append(((d["B"][0, 0] + d["D"][0, 0]) * NJ[:, None]).sum() / 1000)
    E = np.array(E)
    print(f"{len(E)} cellules : min={E.min():.0f}  max={E.max():.0f}  moy={E.mean():.0f} kWh/m2/an")
    print(f"ecart max = {100 * (E.max() - E.min()) / E.mean():.1f}%"
          "  -> une grosse cellule perd cet ecart (petit en plaine)\n")


def effet_moyennage(lat=46.56, lon=0.33, obstacle=25):
    """2. Ombrage : moyenner le mois change-t-il le resultat vs heure par heure ?"""
    print("=== 2. Moyennage mensuel vs horaire (ombrage) ===")
    df = telecharger(lat, lon)                        # series horaires PVGIS
    t   = df.index
    dhi = df["poa_sky_diffuse"]
    ghi = (df["poa_direct"] + dhi).clip(lower=0)
    sp  = pvlib.solarposition.get_solarposition(t, lat, lon)
    dni = pvlib.irradiance.dni(ghi, dhi, sp["apparent_zenith"]).fillna(0)
    direct = pvlib.irradiance.get_total_irradiance(   # direct sur un toit sud 30 deg
        30, 180, sp["apparent_zenith"], sp["azimuth"], dni=dni, ghi=ghi, dhi=dhi,
        dni_extra=pvlib.irradiance.get_extra_radiation(t), albedo=0.2, model="perez"
    )["poa_direct"].fillna(0).values
    az = sp["azimuth"].values
    el = sp["apparent_elevation"].values
    ny = t.year.nunique()

    # obstacle a l'est : a l'ombre si le soleil est a l'est (az 60-120) ET bas (el < obstacle)
    a_lombre = (az >= 60) & (az <= 120) & (el < obstacle)

    # VERITE : on ombrage heure par heure
    E_horaire = np.where(a_lombre, 0, direct).sum() / 1000 / ny

    # MENSUEL : on moyenne direct + position du soleil par (mois, heure), PUIS on ombrage
    g = pd.DataFrame({"m": t.month, "h": t.hour, "dir": direct, "az": az, "el": el}
                     ).groupby(["m", "h"]).mean()
    ombre_moy = (g["az"] >= 60) & (g["az"] <= 120) & (g["el"] < obstacle)
    nj = np.array([NJ[m - 1] for m in g.index.get_level_values("m")])
    E_mensuel = (np.where(ombre_moy, 0, g["dir"]) * nj).sum() / 1000

    print(f"toit sud 30 deg, obstacle {obstacle} deg a l'est : direct annuel")
    print(f"  horaire (verite) : {E_horaire:.1f} kWh/m2/an")
    print(f"  mensuel          : {E_mensuel:.1f} kWh/m2/an"
          f"  (ecart {100 * (E_mensuel - E_horaire) / E_horaire:+.1f}%)")
    print("  -> ~identique : moyenner le mois ne coute presque rien\n")


if __name__ == "__main__":
    effet_taille_cellule()
    effet_moyennage()
