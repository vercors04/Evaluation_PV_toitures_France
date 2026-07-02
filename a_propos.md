=================
DONNEES UTILISEES
=================

BD TOPO (IGN)
    Emprises des bâtiments et contours administratifs (communes, départements,
    régions). 
    Source : WFS IGN Géoplateforme (https://data.geopf.fr/wfs/ows), couches
    BDTOPO_V3:batiment, BDTOPO_V3:commune, BDTOPO_V3:departement,
    BDTOPO_V3:region.

MNS / MNT LiDAR HD (IGN)
    Modèle Numérique de Surface et Modèle Numérique de Terrain, fournis par
    dalles de 1km x 1km. 
    Source : WFS IGN Géoplateforme (https://data.geopf.fr/wfs/ows), couches
    IGNF_MNS-LIDAR-HD:dalle et IGNF_MNT-LIDAR-HD:dalle.

PVGIS - SARAH-3 (Commission Européenne, Centre commun de recherche)
    Données d'irradiation solaire (période 2005-2023)
    Source : https://re.jrc.ec.europa.eu/api/v5_3/

geocodage
autocompletion



==================================
FONCTIONEMENT GENERAL DU PROGRAMME
==================================


---------
GEOMETRIE
---------


-----
METEO
-----









===========================================
VARIABLES DE SORTIE (1 ligne par bâtiment)
===========================================

cleabs, nature, usage_1, hauteur, nombre_d_etages
    Attributs BD TOPO du bâtiment

hauteur_pts
    Hauteur du bâtiment (p95 du MNH LiDAR) — emprise du toit

nb_pixels
    Nombre de pixels de toit — toute la toiture

surf_tot_m2
    Surface de toit exploitable (plat + incliné)

surf_plate_m2
    Surface plate

surf_incl_m2
    Surface inclinée, toutes orientations

surf_incl_or_m2
    Surface inclinée orientée (azimut choisis)

pente_moy_incl
    Pente moyenne des pans inclinés (toutes orientations)

surf_incl_N_m2 ... surf_incl_NO_m2
    Surface inclinée par orientation (8 secteurs)

irr_an_kwh
    Irradiation reçue par an — toute la toiture

prod_an_kwh
    Production PV par an — toute la toiture

irr_an_kwh_orp
    Irradiation reçue par an — plat + orienté

puissance_kwc_orp
    Puissance crête installable — plat + orienté

prod_an_kwh_orp
    Production PV par an — plat + orienté

prod_T1_kwh_orp ... prod_T4_kwh_orp
    Production PV par trimestre — plat + orienté

---------------------
CONVENTION DE NOMMAGE
---------------------


sans suffixe   = toute la toiture (ex. irr_an_kwh, prod_an_kwh)
_incl          = incliné, toutes orientations (ex. surf_incl_m2, surf_incl_N_m2, pente_moy_incl)
_or            = incliné orienté seul, sans le plat (ex. surf_incl_or_m2)
_orp           = orienté + plat = base de production (ex. irr_an_kwh_orp, puissance_kwc_orp, prod_an_kwh_orp, prod_T*_kwh_orp)