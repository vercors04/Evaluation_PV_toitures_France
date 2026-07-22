import json, os, sys
import numpy as np

if getattr(sys, "frozen", False):
    BASE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "roofTool") # dossier inscriptible (%LOCALAPPDATA%/roofTool), l'exe pouvant etre en lecture seule
    BASE_DATA = sys._MEIPASS                         # ressources embarquees (lecture seule)
else:
    BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BASE_DATA = BASE

SETTINGS = os.path.join(BASE, "settings.json")       # reglages persistes, sous BASE


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
    "surf_seuil_m2":     ["surf_seuil_m2"],
    "pente_moy_incl":    ["pente_moy_incl"],
    "surfaces_orient":   [f"surf_incl_{s}_m2" for s in SECTEURS],
    "irr_an_kwh":        ["irr_an_kwh"],
    "puissance_kwc":     ["puissance_kwc"],
    "prod_an_kwh":       ["prod_an_kwh"],
    "irr_an_kwh_orp":    ["irr_an_kwh_orp"],
    "puissance_kwc_orp": ["puissance_kwc_orp"],
    "prod_an_kwh_orp":   ["prod_an_kwh_orp"],
    "irr_seuil_kwh":     ["irr_seuil_kwh"],
    "puissance_kwc_seuil": ["puissance_kwc_seuil"],
    "prod_seuil_kwh":    ["prod_seuil_kwh"],
    "production_trim":   [f"prod_T{t}_kwh_orp" for t in range(1, 5)],
}

# libelle et unite d'affichage de chaque colonne de sortie
# ("Wh"/"Wc" : les valeurs des gpkg sont en kWh / kWc)
COLONNES_SORTIE = {
    "hauteur_pts":       ("Hauteur du toit", "m"),
    "nb_pixels":         ("Nombre de pixels de toit", ""),
    "surf_tot_m2":       ("Surface totale", "m2"),
    "surf_plate_m2":     ("Surface plate", "m2"),
    "surf_incl_m2":      ("Surface inclinée, toutes orientations", "m2"),
    "surf_incl_or_m2":   ("Surface inclinée orientée (azimut choisi)", "m2"),
    "surf_seuil_m2":     ("Surface au-dessus du seuil d'irradiance", "m2"),
    **{f"surf_incl_{s}_m2": (f"Surface inclinée {s}", "m2") for s in SECTEURS},
    "pente_moy_incl":    ("Pente moyenne des pans inclinés", "deg"),
    "irr_an_kwh":        ("Irradiation reçue / an, toute la toiture", "Wh"),
    "irr_an_kwh_orp":    ("Irradiation reçue / an, base installable", "Wh"),
    "irr_seuil_kwh":     ("Irradiation reçue / an, au-dessus du seuil", "Wh"),
    "prod_an_kwh":       ("Production PV / an, toute la toiture", "Wh"),
    "prod_an_kwh_orp":   ("Production PV / an, base installable", "Wh"),
    "prod_seuil_kwh":    ("Production PV / an, au-dessus du seuil", "Wh"),
    "puissance_kwc":     ("Puissance installable, toute la toiture", "Wc"),
    "puissance_kwc_orp": ("Puissance installable, base installable", "Wc"),
    "puissance_kwc_seuil": ("Puissance installable, au-dessus du seuil", "Wc"),
    "prod_T1_kwh_orp":   ("Production T1 (jan-mars)", "Wh"),
    "prod_T2_kwh_orp":   ("Production T2 (avr-juin)", "Wh"),
    "prod_T3_kwh_orp":   ("Production T3 (juil-sept)", "Wh"),
    "prod_T4_kwh_orp":   ("Production T4 (oct-déc)", "Wh"),
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

ETATS = ['En service', 'En construction', 'En ruines', 'Detruit']

DIVISEURS_360 = [6, 8, 9, 10, 12, 15, 18, 20, 24, 30, 36, 40, 45, 60, 72, 90]   

# ============================================================
#  Reglages modifiables 
# ============================================================
DEFAULTS = {
    # tri des toitures 
    "SURF_MIN": 5, "HAUT_MIN": 2, "HAUT_MAX": 35,
    # WFS
    "N_ESSAIS_WFS": 8, "PAUSE_WFS": 2, "N_THREADS": 8, "COUNT": 5000,
    #region/france
    "N_ESSAIS_DEPARTEMENT": 2, "PAUSE_DEPARTEMENT": 30,
    # parallelisme et telechargement des dalles
    "N_COEURS": 5, "N_ESSAIS": 8, "PAUSE_DL": 5,
    # selection des toits
    "BUFFER": 0.8, "MNH_MIN": 1.5, "PENTE_PLAT": 10, "PENTE_MAX": 45,
    "AZ_MIN": 90, "AZ_MAX": 270,
    # horizon (ombrage)
    "N_DIRECTIONS": 36, "DIST_MAX_M": 100, "CAP": 75.0,
    # modele PV
    "ALBEDO": 0.20, "RENDEMENT_MODULE": 0.20, "PERFORMANCE_RATIO": 0.76, "TAUX_COUVERTURE": 1.0,
    "SEUIL_IRRADIANCE": 1000,
    # filtre batiments BD TOPO
    "ETAT": ["En service"], "CONSTRUCTION_LEGERE": False,
    "NATURE_OK": ['Indifférenciée', 'Industriel, agricole ou commercial'],
    "USAGE_OK":  ['Résidentiel', 'Commercial et services', 'Indifférencié', 'Industriel', 'Agricole'],
    "ATTRS_BATI": ["nature", "usage_1", "hauteur", "nombre_d_etages"],
    # groupes de colonnes conservees en sortie
    "SORTIE_GARDEES": list(GROUPES_SORTIE),
}

def snapshot():
    """Retourne les reglages courants (valeurs des cles de DEFAULTS), pour tracabilite."""
    return {cle: globals()[cle] for cle in DEFAULTS}


def derive():
    """Recalcule les reglages derives des valeurs courantes. Appelee apres chaque chargement."""
    global FILTRES_BATI
    FILTRES_BATI = {
        "etat_de_l_objet": ETAT,
        "nature":          NATURE_OK,
        "usage_1":         USAGE_OK,
    }
    if not CONSTRUCTION_LEGERE:
        FILTRES_BATI["construction_legere"] = False


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
