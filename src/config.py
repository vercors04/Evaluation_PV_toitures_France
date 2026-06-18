import numpy as np
import os

#tri toitures
SURF_MIN = 5
HAUT_MIN = 2
HAUT_MAX = 35


#dossiers de sortie/entree 
OUT_DIR_RAW =  os.path.normpath("data/raw/TEST/dalles")
OUT_DIR_PROCESSED = os.path.normpath("data/processed/TEST")
GPKG_BDTOPO = "data/raw/BDT_3-5_GPKG_LAMB93_D086-ED2026-03-15.gpkg"
DIR_GEOJSON = os.path.normpath("data/raw/TEST/geojson")

# construction table meteo
URL     = "https://re.jrc.ec.europa.eu/api/v5_3/"    # PVGIS 5.3 (SARAH-3, 2005-2023)
DOSSIER = "data/tables"                              # un fichier par cellule meteo
PAS     = 0.05                                       # pas de la grille meteo (deg)
PAUSE   = 1.0                                        # temps entre requete pvgis
LAT_MIN, LAT_MAX = 46.30, 46.60                      # emprise des cellules a construire
LON_MIN, LON_MAX = 0.05,  0.40 

# grille table meteo
ALPHAS = np.arange(0, 360, 15)    # orientations testees (deg, 0=N, 90=E)
BETAS  = np.arange(0, 71, 10)     # pentes testees (deg)

# select toitures
BUFFER     = 1.2          # tampon autour des batiments BD TOPO (m)
MNH_MIN    = 1.5          # hauteur min au-dessus du sol pour etre un toit (m)
PENTE_PLAT = 10           # seuil plat / incline (deg)
PENTE_MAX  = 45           # pente max exploitable (deg)
AZ_MIN, AZ_MAX = 90, 270  # fenetre d'azimut "oriente" (deg)

# horizon
N_DIRECTIONS = 36         # directions azimutales
DIST_MAX_M   = 100        # rayon de recherche d'ombrage (m)

# irradiance / modele PV 
ALBEDO            = 0.20                                           # reflectivite du sol
N_JOURS           = np.array([31,28,31,30,31,30,31,31,30,31,30,31])
RENDEMENT_MODULE  = 0.20                                           # rendement panneau
PERFORMANCE_RATIO = 0.78                                           # pertes systeme
TAUX_COUVERTURE   = 1.0                                            # part de toit couverte
SECTEURS          = ["N","NE","E","SE","S","SO","O","NO"]          

__all__ = [
    "URL", "DOSSIER", "PAS", "PAUSE", "LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX",
    "ALPHAS", "BETAS",
    "BUFFER", "MNH_MIN", "PENTE_PLAT", "PENTE_MAX", "AZ_MIN", "AZ_MAX",
    "N_DIRECTIONS", "DIST_MAX_M",
    "ALBEDO", "N_JOURS", "RENDEMENT_MODULE", "PERFORMANCE_RATIO",
    "TAUX_COUVERTURE", "SECTEURS",
]
