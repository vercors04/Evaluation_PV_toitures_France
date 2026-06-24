"""
src/debug/comparaison.py

Aide a choisir les parametres des cellules meteo. Trois parties :

  1. TAILLE -> ERREUR : sur 3 sites (montagne, littoral, plaine), de combien
                        l'irradiance varie selon la taille de cellule.
  2. TEMPS            : combien de temps pour couvrir une region selon la taille.
  3. MOYENNAGE        : sur 2 scenarios (fort / faible ombrage), ecart d'irradiance
                        entre "transposer puis moyenner (mois, heure)" et "heure par
                        heure", + temps de calcul aval des deux.

Chaque partie ecrit : un resume console + un CSV + un PNG (dans statistiques/meteo/).

Lancer dans l'env conda 'stage-lidar', depuis la racine du projet :
    python -m src.debug.comparaison             # les 3 parties
    python -m src.debug.comparaison taille       # une seule
    python -m src.debug.comparaison temps
    python -m src.debug.comparaison moyennage
"""
import os
import sys
import time
import itertools

import numpy as np
import pandas as pd
import pvlib
import matplotlib
matplotlib.use("Agg")               # pas d'affichage, on sauvegarde des PNG
import matplotlib.pyplot as plt

from src.irradiance.meteo.grille_fct import telecharger, transpAgr

# ----------------------------------------------------------------------------
# Reglages
# ----------------------------------------------------------------------------
SORTIE = "statistiques/meteo"        # dossier des CSV + PNG
CACHE  = "data/tables/test"          # telechargements PVGIS mis en cache (pickle)

# --- partie 1 : taille -> erreur ---  (centre de chaque fenetre de test)
SITES = {
    "montagne": (45.20,  5.85),      # Alpes (Grenoble)
    "littoral": (48.20, -4.30),      # Bretagne (Finistere)
    "plaine":   (48.15,  1.70),      # Beauce
}
N_COTE  = 5                          # grille N_COTE x N_COTE points par site
PAS_FIN = 0.05                       # espacement des points (deg) = plus petite cellule testee

# --- partie 2 : temps ---
LAT_TEMPS, LON_TEMPS = 46.50, 0.30   # point ou l'on mesure le cout d'1 cellule
AIRE_REGION_KM2 = 84000              # ~ Nouvelle-Aquitaine
TAILLES = [0.05, 0.10, 0.20, 0.40]   # tailles de cellule a chiffrer (deg)

# --- section moyennage ---
LAT_MOY, LON_MOY = 46.56, 0.33       # point ou l'on teste le moyennage
NJ = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])   # jours par mois
# (libelle, pente deg, azimut deg [180=sud], hauteur d'horizon/obstacle en deg)
SCENARIOS_MOY = [
    ("fort ombrage",   30, 180, 25),   # horizon ferme (vallee)
    ("faible ombrage", 30, 180,  5),   # horizon degage
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def charger_brut(lat, lon):
    """Series horaires PVGIS pour un point, avec cache disque (evite de re-telecharger)."""
    os.makedirs(CACHE, exist_ok=True)
    chemin = os.path.join(CACHE, f"brut_{lat:.2f}_{lon:.2f}.pkl")
    if os.path.exists(chemin):
        return pd.read_pickle(chemin)
    df = telecharger(lat, lon)
    df.to_pickle(chemin)
    return df


def ghi_annuel(lat, lon):
    """Irradiation horizontale annuelle moyenne d'un point (kWh/m2/an)."""
    df = charger_brut(lat, lon)
    ghi = (df["poa_direct"] + df["poa_sky_diffuse"]).clip(lower=0)
    return ghi.sum() / df.index.year.nunique() / 1000.0


def enregistrer(nom_csv, df, nom_png):
    """Sauve le CSV (lisible Excel FR) et annonce les fichiers ecrits."""
    os.makedirs(SORTIE, exist_ok=True)
    df.to_csv(os.path.join(SORTIE, nom_csv), index=False,
              sep=";", decimal=",", encoding="utf-8-sig")
    print(f"  -> {os.path.join(SORTIE, nom_csv)}")
    print(f"  -> {os.path.join(SORTIE, nom_png)}\n")


# ----------------------------------------------------------------------------
# Partie 1 : taille -> erreur
# ----------------------------------------------------------------------------
def erreur_site(lat0, lon0):
    """Pour un site : ecart moyen d'irradiance (%) entre points distants d'AU PLUS
    chaque taille de cellule (cumulatif -> bien echantillonne et monotone).
    @return (tailles_deg, ecarts_pct)."""
    moitie = (N_COTE - 1) / 2
    pts, E = [], []
    for i in range(N_COTE):
        for j in range(N_COTE):
            la = round(lat0 + (i - moitie) * PAS_FIN, 3)
            lo = round(lon0 + (j - moitie) * PAS_FIN, 3)
            pts.append((la, lo))
            E.append(ghi_annuel(la, lo))
    pts, E = np.array(pts), np.array(E)
    moy = E.mean()

    dist, ecart = [], []
    for i, j in itertools.combinations(range(len(pts)), 2):
        dist.append(np.hypot(*(pts[i] - pts[j])))
        ecart.append(abs(E[i] - E[j]))
    dist, ecart = np.array(dist), np.array(ecart)

    tailles = np.arange(PAS_FIN, dist.max() + PAS_FIN, PAS_FIN)
    pct = [100 * ecart[dist <= s + 1e-9].mean() / moy for s in tailles]
    return np.round(tailles, 2), np.round(pct, 2)


def effet_taille():
    """Compare l'erreur due a la taille de cellule sur les 3 sites."""
    print("=== Taille de cellule -> erreur ===")
    res = pd.DataFrame()
    for nom, (lat, lon) in SITES.items():
        tailles, pct = erreur_site(lat, lon)
        res["taille_deg"] = tailles
        res[nom] = pct
        print(f"  {nom:9s} : " + "  ".join(f"{t:.2f}={p:.1f}%" for t, p in zip(tailles, pct)))

    plt.figure(figsize=(6, 4))
    for nom in SITES:
        plt.plot(res.taille_deg, res[nom], "o-", label=nom)
    plt.xlabel("Taille de cellule (deg)")
    plt.ylabel("Ecart moyen d'irradiance (%)")
    plt.title("Erreur selon la taille de cellule")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(SORTIE, "taille.png"), dpi=120)
    plt.close()

    enregistrer("taille.csv", res, "taille.png")


# ----------------------------------------------------------------------------
# Partie 2 : temps de calcul  (sous-partie : taille)
# ----------------------------------------------------------------------------
def effet_temps():
    """Mesure le cout d'1 cellule (telechargement + transposition) et extrapole a une region."""
    print("=== Temps de calcul -> selon la taille ===")
    t0 = time.time(); df = telecharger(LAT_TEMPS, LON_TEMPS);  t_dl = time.time() - t0
    t0 = time.time(); transpAgr(df["poa_direct"], df["poa_sky_diffuse"], LAT_TEMPS, LON_TEMPS)
    t_calc = time.time() - t0
    t_cell = t_dl + t_calc
    print(f"  cout d'1 cellule : {t_cell:.0f}s (telech {t_dl:.0f}s + calcul {t_calc:.0f}s)")

    cos_lat = np.cos(np.radians(LAT_TEMPS))
    lignes = []
    for s in TAILLES:
        aire_cell = (s * 111) * (s * 111 * cos_lat)          # km2 (approx)
        n = int(np.ceil(AIRE_REGION_KM2 / aire_cell))
        lignes.append((s, round(s * 111, 1), n, round(n * t_cell / 60, 1)))
    res = pd.DataFrame(lignes, columns=["taille_deg", "taille_km", "n_cellules", "minutes_total"])
    print(f"  region de {AIRE_REGION_KM2} km2 :")
    print(res.to_string(index=False))

    plt.figure(figsize=(6, 4))
    plt.plot(res.taille_deg, res.minutes_total, "o-")
    plt.xlabel("Taille de cellule (deg)")
    plt.ylabel(f"Temps estime (min) pour {AIRE_REGION_KM2} km2")
    plt.title("Temps de calcul selon la taille de cellule")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(SORTIE, "temps.png"), dpi=120)
    plt.close()

    enregistrer("temps.csv", res, "temps.png")


# ----------------------------------------------------------------------------
# Section : moyennage  (transposer puis moyenner vs heure par heure)
# ----------------------------------------------------------------------------
def _temps_par_pixel(fn):
    """Temps moyen d'un appel a fn (s), mesure en boucle jusqu'a >= 0.2 s
    (robuste : evite les 0.000 s sur les operations tres rapides)."""
    n, t0 = 0, time.time()
    while time.time() - t0 < 0.2:
        fn(); n += 1
    return (time.time() - t0) / n


def effet_moyennage():
    """Sur 2 scenarios (fort / faible ombrage), compare :
       - HORAIRE : annee TYPIQUE horaire (~8760 pas, moyenne par mois/jour/heure),
                   ombrage applique a chaque heure ;
       - MOYENNE (notre methode) : profil (mois, heure) (288 pas), ombrage sur la moyenne.
    Sort le graphe d'ecart + le temps de calcul aval par pixel (console / CSV)."""
    print("=== Moyennage : ecart et temps (moyenne vs horaire) ===")
    df = charger_brut(LAT_MOY, LON_MOY)
    t   = df.index
    dhi = df["poa_sky_diffuse"]
    ghi = (df["poa_direct"] + dhi).clip(lower=0)
    sp  = pvlib.solarposition.get_solarposition(t, LAT_MOY, LON_MOY)
    dni = pvlib.irradiance.dni(ghi, dhi, sp["apparent_zenith"]).fillna(0)
    extra   = pvlib.irradiance.get_extra_radiation(t)
    airmass = pvlib.atmosphere.get_relative_airmass(sp["apparent_zenith"])
    el = sp["apparent_elevation"].values
    garder = ~((t.month == 2) & (t.day == 29))            # annee typique = 365 jours
    mo, jr, hr = t.month.to_numpy()[garder], t.day.to_numpy()[garder], t.hour.to_numpy()[garder]

    lignes = []
    for nom, pente, azim, obst in SCENARIOS_MOY:
        poa = pvlib.irradiance.get_total_irradiance(
            pente, azim, sp["apparent_zenith"], sp["azimuth"],
            dni=dni, ghi=ghi, dhi=dhi, dni_extra=extra, airmass=airmass,
            albedo=0.2, model="perez")
        direct = poa["poa_direct"].fillna(0).values
        diffus = (poa["poa_sky_diffuse"] + poa["poa_ground_diffuse"]).fillna(0).values

        # HORAIRE : annee TYPIQUE horaire (moyenne par mois/jour/heure), ombrage a chaque heure
        an = (pd.DataFrame({"mo": mo, "d": jr, "h": hr,
                            "dir": direct[garder], "dif": diffus[garder], "el": el[garder]})
                .groupby(["mo", "d", "h"]).mean())
        dir_a, dif_a, el_a = an.dir.values, an.dif.values, an.el.values
        def horaire():
            return (np.where(el_a < obst, 0, dir_a) + dif_a).sum() / 1000

        # MOYENNE : profil (mois, heure) construit 1 fois, puis ombrage sur la moyenne
        prof = (pd.DataFrame({"m": t.month, "h": t.hour,
                              "dir": direct, "dif": diffus, "el": el})
                  .groupby(["m", "h"]).mean())
        nj = NJ[prof.index.get_level_values("m") - 1]
        dir_m, dif_m, el_m = prof.dir.values, prof.dif.values, prof.el.values
        def moyenne():
            return ((np.where(el_m < obst, 0, dir_m) + dif_m) * nj).sum() / 1000

        E_h, E_m = horaire(), moyenne()
        ecart = 100 * (E_m - E_h) / E_h
        # temps de calcul aval, par pixel (table moyenne supposee deja construite)
        t_h = _temps_par_pixel(horaire) * 1e6        # micro-secondes / pixel
        t_m = _temps_par_pixel(moyenne) * 1e6
        print(f"  {nom:14s} horaire={E_h:6.1f}  moyenne={E_m:6.1f} kWh/m2/an  ({ecart:+.2f}%)"
              f"  | par pixel : horaire {t_h:.0f} us, moyenne {t_m:.1f} us (x{t_h/t_m:.0f})")
        lignes.append((nom, round(E_h, 1), round(E_m, 1), round(ecart, 2),
                       round(t_h, 1), round(t_m, 2), round(t_h / t_m)))

    res = pd.DataFrame(lignes, columns=["scenario", "horaire_kwh", "moyenne_kwh",
                                        "ecart_pct", "t_horaire_us", "t_moyenne_us",
                                        "acceleration"])

    # --- graphe 1 : ecart sur l'irradiance (signe conserve) ---
    plt.figure(figsize=(6, 4))
    plt.bar(res.scenario, res.ecart_pct, color="#378ADD")
    plt.axhline(0, color="k", lw=0.8)
    for i, e in enumerate(res.ecart_pct):
        plt.text(i, e, f"{e:+.2f}%", ha="center", va="top" if e < 0 else "bottom")
    plt.ylabel("Ecart moyenne - horaire (%)")
    plt.title("Erreur d'irradiance due au moyennage")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(SORTIE, "moyennage_ecart.png"), dpi=120)
    plt.close()

    os.makedirs(SORTIE, exist_ok=True)
    res.to_csv(os.path.join(SORTIE, "moyennage.csv"), index=False,
               sep=";", decimal=",", encoding="utf-8-sig")
    print(f"  -> {os.path.join(SORTIE, 'moyennage.csv')}")
    print(f"  -> {os.path.join(SORTIE, 'moyennage_ecart.png')}\n")


# ----------------------------------------------------------------------------
TESTS = {"taille": effet_taille, "temps": effet_temps, "moyennage": effet_moyennage}

if __name__ == "__main__":
    for nom in (sys.argv[1:] or TESTS):
        TESTS[nom]()
