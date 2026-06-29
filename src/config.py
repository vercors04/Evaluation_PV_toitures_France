import numpy as np
import os

#dossiers de sortie/entree 
OUT_DIR_RAW =  os.path.normpath("data/raw/TEST/dalles")
OUT_DIR_PROCESSED = os.path.normpath("data/processed/TEST")
DIR_GEOJSON = os.path.normpath("data/raw/TEST/geojson")


#tri toitures
SURF_MIN = 5
HAUT_MIN = 2
HAUT_MAX = 35

#WFS
WFS = "https://data.geopf.fr/wfs/ows"
N_COEURS = 5


#batiments
NATURE_OK = ['Indifférenciée', 'Industriel, agricole ou commercial']
FILTRES_BATI = {
    "etat_de_l_objet":     "En service",
    "construction_legere": False,
    "nature":              NATURE_OK,
}
ATTRS_BATI = ["nature", "usage_1", "hauteur", "nombre_d_etages"]
COUNT = 5000
N_THREADS = 8


# construction table meteo
URL     = "https://re.jrc.ec.europa.eu/api/v5_3/"    # PVGIS 5.3 (SARAH-3, 2005-2023)
DOSSIER = "data/tables"                              # un fichier par cellule meteo
PAS     = 0.10                                       # pas de la grille meteo (deg) = taille de cellule
PAUSE   = 0.2                                        # temps entre requete pvgis


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
CAP = 75.0                # plafond solaire

# irradiance / modele PV 
ALBEDO            = 0.20                                           # reflectivite du sol
N_JOURS           = np.array([31,28,31,30,31,30,31,31,30,31,30,31])
RENDEMENT_MODULE  = 0.20                                           # rendement panneau
PERFORMANCE_RATIO = 0.78                                           # pertes systeme
TAUX_COUVERTURE   = 1.0                                            # part de toit couverte
SECTEURS          = ["N","NE","E","SE","S","SO","O","NO"]          
TRIM = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]

