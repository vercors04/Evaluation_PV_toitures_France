# roofTool

Potentiel photovoltaïque des toitures de France métropolitaine, par bâtiment, à partir du LiDAR HD IGN (MNS, MNT), de la BD TOPO et de PVGIS (SARAH-3).

- Environnement : `conda env create -f environment.yml` (env `stage-lidar`)
- Interface : `python interface.py`
- Exécutable Windows : `pyinstaller main.spec` (dossier `dist/roofTool`)
- Tables météo : `python -m src.irradiance.meteo.main_meteo` (cellules), `python -m src.irradiance.meteo.raffiner` (sous-cellules)
- Comparaison au cadastre solaire de la Savoie : `python -m src.debug.comparaisons.comparaison_cythelia_savoie`
- Documentation : `00_rapport/` (rapport de stage, figé), `01_RoofTool_1.1.0/changements.pdf` (écarts depuis le rapport), `a_propos.md` (données, fonctionnement, colonnes de sortie)
