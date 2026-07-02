import json, os, sys
import numpy as np

if getattr(sys, "frozen", False):
    BASE      = os.path.dirname(sys.executable)     # dossier de l'exe
    BASE_DATA = sys._MEIPASS                         # ressources embarquees (lecture seule)
else:
    BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BASE_DATA = BASE

SETTINGS = os.path.join(BASE, "settings.json")       # reglages persistes, a cote de l'exe


# ============================================================
#  Constantes fixes
# ============================================================

# dossiers d'entree / sortie
OUT_DIR_RAW       = os.path.join(BASE, "data", "raw")                   # dalles MNS/MNT (transit)
DIR_GEOJSON       = os.path.join(BASE, "data", "processed", "geojson")  # contours de zone (.geojson)
OUT_DIR_PROCESSED = os.path.join(BASE, "data", "processed", "gpkg")     # resultats (.gpkg)
DOSSIER           = os.path.join(BASE_DATA, "data", "tables")           # tables meteo (.npz)

# services distants
WFS = "https://data.geopf.fr/wfs/ows"                # WFS IGN (batiments, dalles)
URL = "https://re.jrc.ec.europa.eu/api/v5_3/"        # PVGIS 5.3 (SARAH-3, 2005-2023)

# grille meteo
PAS   = 0.10                                          # pas de la grille meteo (deg) = taille de cellule
PAUSE = 0.2                                           # pause entre requetes PVGIS (s)

# grilles d'angles et calendrier (modele PV)
ALPHAS  = np.arange(0, 360, 15)                       # orientations testees (deg, 0=N, 90=E)
BETAS   = np.arange(0, 71, 10)                        # pentes testees (deg)
N_JOURS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])  # jours par mois
TRIM    = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]              # mois (index 0-11) par trimestre
SECTEURS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]              # 8 secteurs d'orientation

# colonnes de sortie regroupees par theme 
GROUPES_SORTIE = {
    "hauteur":           ["hauteur_pts"],
    "nb_pixels":         ["nb_pixels"],
    "surf_tot_m2":       ["surf_tot_m2"],
    "surf_plate_m2":     ["surf_plate_m2"],
    "surf_incl_m2":      ["surf_incl_m2"],
    "surf_incl_or_m2":   ["surf_incl_or_m2"],
    "pente_moy_incl":    ["pente_moy_incl"],
    "surfaces_orient":   [f"surf_incl_{s}_m2" for s in SECTEURS],
    "irr_an_kwh":        ["irr_an_kwh"],
    "prod_an_kwh":       ["prod_an_kwh"],
    "irr_an_kwh_orp":    ["irr_an_kwh_orp"],
    "puissance_kwc_orp": ["puissance_kwc_orp"],
    "prod_an_kwh_orp":   ["prod_an_kwh_orp"],
    "production_trim":   [f"prod_T{t}_kwh_orp" for t in range(1, 5)],
}

# catalogues de choix proposes par l'interface (toutes les options possibles)
ATTRS_BDTOPO = ['nature', 'usage_1', 'usage_2', 'construction_legere',
                'etat_de_l_objet', 'nombre_de_logements', 'nombre_d_etages',
                'materiaux_des_murs', 'materiaux_de_la_toiture', 'hauteur',
                'altitude_minimale_sol', 'altitude_minimale_toit', 'altitude_maximale_sol',
                'altitude_maximale_toit', 'date_creation', 'date_modification']
NATURES  = ['Indifférenciée', 'Industriel, agricole ou commercial',
            'Religieux', 'Sportif', 'Château', 'Serre', 'Silo']
USAGE_1  = ['Agricole', 'Annexe', 'Commercial et services', 'Indifférencié',
            'Industriel', 'Religieux', 'Résidentiel', 'Sportif']
ECHELLES = ['Adresse', 'Commune ou ville', 'Département', 'Région', 'France']


# ============================================================
#  Reglages modifiables 
# ============================================================
DEFAULTS = {
    # tri des toitures 
    "SURF_MIN": 5, "HAUT_MIN": 2, "HAUT_MAX": 35,
    # WFS
    "N_ESSAIS_WFS": 8, "PAUSE_WFS": 2, "N_THREADS": 8, "COUNT": 5000,
    # parallelisme et telechargement des dalles
    "N_COEURS": 5, "N_ESSAIS": 8, "PAUSE_DL": 5,
    # selection des toits
    "BUFFER": 1.2, "MNH_MIN": 1.5, "PENTE_PLAT": 10, "PENTE_MAX": 45,
    "AZ_MIN": 90, "AZ_MAX": 270,
    # horizon (ombrage)
    "N_DIRECTIONS": 36, "DIST_MAX_M": 100, "CAP": 75.0,
    # modele PV
    "ALBEDO": 0.20, "RENDEMENT_MODULE": 0.20, "PERFORMANCE_RATIO": 0.78, "TAUX_COUVERTURE": 1.0,
    # filtre batiments BD TOPO
    "ETAT": "En service", "CONSTRUCTION_LEGERE": False,
    "NATURE_OK": ['Indifférenciée', 'Industriel, agricole ou commercial'],
    "USAGE_OK":  ['Résidentiel', 'Commercial et services', 'Indifférencié', 'Industriel', 'Agricole'],
    "ATTRS_BATI": ["nature", "usage_1", "hauteur", "nombre_d_etages"],
    # groupes de colonnes conservees en sortie
    "SORTIE_GARDEES": list(GROUPES_SORTIE),
}


def derive():
    """Recalcule les reglages derives des valeurs courantes. Appelee apres chaque chargement."""
    global FILTRES_BATI
    FILTRES_BATI = {                               
        "etat_de_l_objet":     ETAT,
        "construction_legere": CONSTRUCTION_LEGERE,
        "nature":              NATURE_OK,
        "usage_1":             USAGE_OK,
    }


def load():
    """Charge les reglages (defauts surcharges par settings.json) comme variables du module."""
    valeurs = dict(DEFAULTS)
    if os.path.exists(SETTINGS):
        with open(SETTINGS, encoding="utf-8") as f:
            valeurs.update(json.load(f))
    globals().update(valeurs)
    derive()


def save(reglages):
    """
    Fusionne des reglages dans settings.json puis recharge le module.
    --------
    @param[in] reglages : dict {NOM: valeur} (ex: {"SURF_MIN": 8}) fusionne avec l'existant

    @return None : settings.json est mis a jour et les variables du module rechargees
    """
    actuel = {}
    if os.path.exists(SETTINGS):
        with open(SETTINGS, encoding="utf-8") as f:
            actuel = json.load(f)
    actuel.update(reglages)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(actuel, f, ensure_ascii=False, indent=2)
    load()


load()   
