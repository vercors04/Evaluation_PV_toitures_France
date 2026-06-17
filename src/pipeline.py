import os
import time

from src.tuile.raster import chargerDalle
from src.tuile.bd_topo import loadBuild
from src.tuile.donnees_dalle import tileBounds, nomCoord, centreWGS84
from src.geometrie.extract_geom import extractGeom, makeMasques
from src.geometrie.horizon import compHZ
from src.irradiance.meteo.irr_fct import chargerTable
from src.irradiance.irr_calcul import irrPixels
from src.util.agregation import agregerBatiment
from src.debug import debug_pipeline as debug


def traiterDalle(mns_path, mnt_path, gpkg_bdtopo, out_gpkg, debug_dir=None):
    """
    Traite une dalle : BD TOPO -> geometrie -> masques -> horizon -> irradiance
    -> agregation par batiment -> ecriture du GeoPackage.
    --------
    @param[in] mns_path, mnt_path : chemins des rasters MNS / MNT IGN
    @param[in] gpkg_bdtopo        : chemin du GeoPackage BD TOPO
    @param[in] out_gpkg           : chemin du GeoPackage de sortie
    @param[in] debug_dir          : si fourni, exporte les rasters de debug

    @return out : GeoDataFrame ecrit (1 ligne par batiment)
    """
    mns_name = os.path.basename(mns_path)

    # ------ ouverture BDTPOPO ------
    t0 = time.time()
    gdf = loadBuild(gpkg_bdtopo, tileBounds(mns_name))
    print(f"BD TOPO    : {time.time()-t0:.1f}s")



    # ------ Lecture des raster, chargements des masques et donnees ------
    t0 = time.time()
    mns, mnt, meta = chargerDalle(mns_path, mnt_path)
    pente, aspect, masque_bat, mnh = extractGeom(mns, mnt, gdf, meta)
    incline_or, incline, plat = makeMasques(pente, aspect, masque_bat)
    toiture = incline | plat
    print(f"Geometrie  : {time.time()-t0:.1f}s")



    # ------ horizon ------
    t0 = time.time()
    horizon = compHZ(mns, toiture, meta["resolution"])
    print(f"Horizon    : {time.time()-t0:.1f}s")



    # ------ irradiance par pixel ------
    t0 = time.time()
    lat, lon = centreWGS84(*nomCoord(mns_name))
    B, D, SAZ, SEL = chargerTable(lat, lon)
    df  = irrPixels(masque_bat, pente, aspect, incline, incline_or, plat,
                    meta["resolution"], B, D, SAZ, SEL, horizon)
    


    # ------ agregation par bat + ecriture ------
    out = agregerBatiment(df, gdf)
    out.to_file(out_gpkg, driver="GPKG")
    print(f"Irradiance : {time.time()-t0:.1f}s  ->  {out_gpkg}")




    # ------ debug pour visualisation ------
    if debug_dir is not None:
        debug.exportRasters({
            "pente": pente, "aspect": aspect, "mnh": mnh,
            "incline":    incline.astype("int32"),
            "incline_or": incline_or.astype("int32"),
            "plat":       plat.astype("int32"),
        }, meta, debug_dir)
        debug.exportHorizon(horizon, toiture, meta, os.path.join(debug_dir, "horizon"))

    return out
