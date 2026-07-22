import numpy as np
import rasterio


def chargerDalle(mns_path, mnt_path):
    """
    Lit le MNS et le MNT d'une dalle, met le nodata de chacun a NaN.
    --------
    @param[in] mns_path, mnt_path : chemins des GeoTIFF MNS / MNT IGN

    @return mns, mnt : tableaux 2D float32 (NaN hors donnees)
    @return meta     : profil rasterio du MNS (cle "resolution" = taille pixel en m)
    """
    with rasterio.open(mns_path) as src:
        mns  = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        meta["resolution"] = src.res[0]
        nodata = src.nodata
    with rasterio.open(mnt_path) as src:
        mnt = src.read(1).astype(np.float32)
        nodata_mnt = src.nodata

    if nodata is not None:
        mns[mns == nodata] = np.nan
    if nodata_mnt is not None:
        mnt[mnt == nodata_mnt] = np.nan
        
    return mns, mnt, meta


def ecrireGeotiff(arr, meta, path, nodata=-9999.0):
    """
    Ecrit un tableau 2D en GeoTIFF mono-bande (float32 si flottant, int32 sinon).
    --------
    @param[in] arr    : tableau 2D a ecrire
    @param[in] meta   : profil rasterio de la dalle (cle "resolution" toleree)
    @param[in] path   : chemin de sortie
    @param[in] nodata : valeur nodata pour les flottants (NaN remplace par nodata)

    @return None : ecrit le GeoTIFF a path
    """
    if np.issubdtype(arr.dtype, np.floating):
        dtype = "float32"
        arr = np.where(np.isnan(arr), nodata, arr).astype(dtype)
    else:
        dtype, nodata = "int32", 0
        arr = arr.astype(dtype)

    profil = {**meta, "count": 1, "dtype": dtype, "nodata": nodata, "compress": "lzw"}
    profil.pop("resolution", None)        # pas un champ rasterio valide
    with rasterio.open(path, "w", **profil) as dst:
        dst.write(arr, 1)
