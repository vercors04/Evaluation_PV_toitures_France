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
    dalles de 1km x 1km, en Lambert 93.
    Source : WFS IGN Géoplateforme (https://data.geopf.fr/wfs/ows), couche
    IGNF_LIDAR-HD_METADONNEE:metadata ; dalles lues en WMS.

PVGIS - SARAH-3 (Commission Européenne, Centre commun de recherche)
    Séries horaires d'irradiation, de température de l'air et de vent
    (2005-2023).
    Source : https://re.jrc.ec.europa.eu/api/v5_3/

Géocodage et suggestions de zone
    Adresses : API Géocodage IGN Géoplateforme (https://data.geopf.fr/geocodage).
    Communes, départements, régions : https://geo.api.gouv.fr.

Protections (Géoportail de l'urbanisme, INPN)
    Zones où un refus d'installation reste possible (article L111-17 du code de
    l'urbanisme) : monuments historiques, abords de monuments, sites patrimoniaux
    remarquables, sites classés ou inscrits, cœurs de parcs nationaux.
    Source : WFS IGN Géoplateforme (https://data.geopf.fr/wfs/ows), couches
    wfs_sup:generateur_sup_s, wfs_sup:assiette_sup_s (types ac1, ac2, ac4) et
    patrinat_pn2:pn.


===================================
FONCTIONNEMENT GENERAL DU PROGRAMME
===================================

---------
GEOMETRIE
---------

Pour chaque dalle, les bâtiments BD TOPO sont rasterisés puis croisés avec le
MNS et le MNT :

    - pente et orientation de chaque pixel de toit, par ajustement d'un plan
      sur le MNS (ou différences finies) ; les pixels trop éloignés du plan
      (murs, rives) sont écartés
    - classement des pixels en plat / incliné / incliné orienté (seuils de
      pente et arc d'azimut réglables)
    - ligne d'horizon par pixel : ombrage proche par lancer de rayons sur le
      MNS élargi, ombrage lointain sur un MNT grossier de la zone (relief)
    - hauteur du bâtiment (percentile du MNH)

-----
METEO
-----

Indépendamment de la géométrie, le territoire est découpé en cellules de
0,10°. Pour chaque cellule :

    - récupération d'une série horaire d'irradiance (PVGIS - SARAH-3,
      2005-2023)
    - transposition sur 192 plans (24 orientations x 8 pentes), modèle de
      Perez pour le diffus incliné
    - moyennage par créneau (mois, heure), stocké dans une table réutilisée
      par tous les pixels de la cellule (interpolation bilinéaire)

Chaque table porte aussi huit profils (mois, heure) résumant les VRAIES heures
avant moyennage : moments d'ordre 2 du direct et du diffus, température et vent
pondérés par l'irradiance. L'échauffement d'un module suit le carré de
l'irradiance, que le moyennage détruit ; ces profils permettent de le
reconstruire pour n'importe quel plan. Deux coefficients de Perez pondérés
complètent la table, pour l'ombrage du diffus.

Là où l'irradiance varie à l'intérieur d'une cellule (relief, littoral), la
cellule se découpe en quatre sous-cellules de 0,05°, la maille de SARAH-3. Une
sous-cellule est construite si son irradiation annuelle s'écarte de plus de 1 %
de celle de sa cellule ; elle remplace alors la cellule pour les dalles qu'elle
contient. Mesure et construction : python -m src.irradiance.meteo.raffiner

-----------------
PHOTOVOLTAIQUE
-----------------

L'irradiance par pixel de toit est obtenue en combinant sa géométrie, son
horizon et la table météo de sa cellule ; l'horizon masque le direct et le
diffus (facteurs de vue du ciel). La conversion en puissance et en production
tient compte :

    - de la température de cellule (modèle de Faiman + dérating linéaire),
      dont les coefficients dépendent du type de pose : surimposé, intégré
      ou libre sur les pans inclinés, fixés par la pose sur les toits plats
    - de la surface équipable : taux de couverture des pans inclinés (reculs,
      obstacles, calepinage) ; sur toit plat, emprise du champ multipliée par
      sa densité (1 à plat, taux d'occupation au sol en rangées) ; en option,
      recul géométrique mesuré sur le masque de toiture
    - de la pose sur toit plat : à plat, rangées sud, est-ouest dos à dos,
      ou mixte selon la surface plate, l'usage ou la nature du bâtiment. L'irradiance
      productive est celle du plan des modules, diminuée de l'ombrage entre
      rangées (direct et bas du ciel)
    - d'un performance ratio résiduel, qui ne couvre plus que ce qui n'est
      pas modélisé (câblage, onduleur, salissures, désadaptation)

------
CALCUL
------

Les dalles d'une zone se calculent en parallèle. Chaque dalle finie est écrite
dans data/processed/en_cours/<zone>/ ; un calcul interrompu reprend aux dalles
manquantes, tant que la zone et les réglages du calcul n'ont pas changé. Le
dossier est supprimé une fois le gpkg écrit.

----------
EXECUTABLE
----------

Construction de l'exécutable : pyinstaller main.spec


===========================================
VARIABLES DE SORTIE (1 ligne par bâtiment)
===========================================

cleabs, nature, usage_1, hauteur, nombre_d_etages
    Attributs BD TOPO du bâtiment

pose_plat
    Pose des modules sur la partie plate du toit : à plat, sud ou est-ouest
    (vide sans toit plat)

prot_monument, prot_abords, prot_spr, prot_site, prot_coeur_parc
    Vrai si le point intérieur du bâtiment tombe dans la zone correspondante.
    Une colonne par protection cochée ; aucune si aucune ne l'est. Un bâtiment
    marqué n'est pas interdit : l'autorité compétente peut imposer des conditions
    plutôt que refuser. L'option "Supprimer les bâtiments protégés" les retire du
    fichier au lieu de les signaler.

hauteur_p95_m
    Hauteur du bâtiment (p95 du MNH LiDAR) — emprise du toit

nb_pixels
    Nombre de pixels de toit — toute la toiture

surf_m2
    Surface de toit exploitable (plat + incliné)

surf_m2_plat
    Surface plate

surf_m2_incl
    Surface inclinée, toutes orientations

surf_m2_or
    Surface inclinée orientée (arc d'azimut choisi)

surf_m2_seuil
    Surface de toit au-dessus du seuil d'irradiance

surf_m2_mod
    Surface de modules installables : surface retenue x taux de couverture
    (pans inclinés), ou x emprise du champ x densité de la pose (toits plats).
    C'est elle qui porte la puissance et la production, pas surf_m2.

pente_moy_deg_incl
    Pente moyenne des pans inclinés (toutes orientations)

surf_m2_incl_N ... surf_m2_incl_NO
    Surface inclinée par orientation (8 secteurs)

ciel_moy
    Part du ciel vue par le toit, en moyenne sur ses pixels (0 à 1, 1 = dégagé) ;
    horizon des bâtiments et du relief compris

irr_an_kwh
    Irradiation reçue par an — toute la toiture

irr_an_kwh_orp
    Irradiation reçue par an — plat + orienté

irr_an_kwh_seuil
    Irradiation reçue par an — au-dessus du seuil

puissance_kwc
    Puissance crête installable — toute la toiture

puissance_kwc_orp
    Puissance crête installable — plat + orienté

puissance_kwc_seuil
    Puissance crête installable — au-dessus du seuil

prod_an_kwh
    Production PV par an — toute la toiture

prod_an_kwh_orp
    Production PV par an — plat + orienté

prod_an_kwh_seuil
    Production PV par an — au-dessus du seuil

prod_T1_kwh_orp ... prod_T4_kwh_orp
    Production PV par trimestre — plat + orienté

---------------------
CONVENTION DE NOMMAGE
---------------------

Toute colonne de résultat suit le même schéma :

    <grandeur>[_<qualificateur>]_<unité>[_<périmètre>]

grandeur        surf, irr, prod, puissance, pente, hauteur, ciel, nb_pixels
qualificateur   temporel (an, T1..T4) ou statistique (moy, p95) ; absent si sans objet
unité           m2, kwh, kwc, deg, m ; absente pour un comptage (nb_pixels) ou un rapport (ciel_moy)
périmètre       TOUJOURS en dernier ; absent = toute la toiture

Valeurs du périmètre :

(aucun)   toute la toiture         ex. surf_m2, irr_an_kwh, prod_an_kwh, puissance_kwc
_plat     pans plats seuls         ex. surf_m2_plat
_incl     incliné, toutes orient.  ex. surf_m2_incl, pente_moy_deg_incl
_incl_X   incliné, secteur X       ex. surf_m2_incl_N ... surf_m2_incl_NO (8 secteurs)
_or       incliné orienté seul     ex. surf_m2_or
_orp      orienté + plat           ex. irr_an_kwh_orp, puissance_kwc_orp, prod_T1_kwh_orp
          = base de production
_seuil    au-dessus du seuil       ex. surf_m2_seuil, irr_an_kwh_seuil, prod_an_kwh_seuil
          d'irradiance
_mod      couvert de modules       ex. surf_m2_mod
