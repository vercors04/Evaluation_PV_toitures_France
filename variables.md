# Variables de la pipeline

## Paramètres d'entrée ajustables

| Paramètre            | Valeur  | Rôle / pourquoi le faire varier             |
| -------------------- | ------- | ------------------------------------------- |
| Azimut orienté       | 90–270° | Pans exploitables ; élargir pour E/O, SE/SO |
| Pente inclinée       | 10–45°  | Bornes des toits inclinés retenus           |
| Seuil plat / incliné | 10°     | Sépare plat et incliné                      |
| `ALBEDO`             | 0,20    | Réflectivité du sol (diffus réfléchi)       |
| `RENDEMENT_MODULE`   | 0,20    | Rendement du panneau                        |
| `PERFORMANCE_RATIO`  | 0,78    | Pertes système (onduleur, température…)     |
| `TAUX_COUVERTURE`    | 1,0     | Part du toit couverte de panneaux           |

**Fixés / optimisés (ne pas faire varier)** : buffer = 1,2 m ; `mnh_min` = 1,5 m ; `max_distance_m` = 100 m ; nb de directions d'horizon = 36 ; pas des grilles d'orientation (15°) et de pente (10°).

## Variables de sortie (1 ligne par bâtiment)

| Colonne                                                     | Signification                                 | Base spatiale         |
| ----------------------------------------------------------- | --------------------------------------------- | --------------------- |
| `cleabs`, `nature`, `usage_1`, `hauteur`, `nombre_d_etages` | Attributs BD TOPO du bâtiment                 | —                     |
| `hauteur_pts`                                               | Hauteur du bâtiment (p95 du MNH LiDAR)        | Emprise du toit       |
| `nb_pixels`                                                 | Nombre de pixels de toit                      | Toute la toiture      |
| `surf_tot_m2`                                               | Surface de toit exploitable                   | Plat + incliné        |
| `surf_plate_m2`                                             | Surface plate                                 | Plat                  |
| `surf_incl_m2`                                              | Surface inclinée                              | Incliné (toutes dir.) |
| `surf_incl_or_m2`                                           | Surface inclinée orientée                     | Incliné azimut choisis|
| `pente_moy_incl`                                            | Pente moyenne des pans inclinés               | Incliné (toutes dir.) |
| `surf_incl_N_m2` … `surf_incl_NO_m2`                        | Surface inclinée par orientation (8 secteurs) | Incliné (toutes dir.) |
| `irr_an_kwh`                                                | Irradiation reçue / an                        | Toute la toiture      |
| `prod_an_kwh`                                               | Production PV / an                            | Toute la toiture      |
| `irr_an_kwh_orp`                                            | Irradiation reçue / an                        | Plat + orienté        |
| `puissance_kwc_orp`                                         | Puissance crête installable                   | Plat + orienté        |
| `prod_an_kwh_orp`                                           | Production PV / an                            | Plat + orienté        |
| `prod_T1_kwh_orp` … `prod_T4_kwh_orp`                       | Production PV par trimestre                   | Plat + orienté        |


## Convention de nommage

- **sans suffixe** = toute la toiture (ex. `irr_an_kwh`, `prod_an_kwh`)
- **`_incl`** = incliné, toutes orientations (ex. `surf_incl_m2`, `surf_incl_N_m2`, `pente_moy_incl`)
- **`_or`** = incliné orienté seul, sans le plat (ex. `surf_incl_or_m2`)
- **`_orp`** = orienté + plat = base de production (ex. `irr_an_kwh_orp`, `puissance_kwc_orp`, `prod_an_kwh_orp`, `prod_T*_kwh_orp`)