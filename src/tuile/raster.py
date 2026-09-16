import numpy as np
import rasterio
from affine import Affine


def chargerDalle(mns_path, mnt_path):
    """
    Lit le MNS, recoupe a la dalle s'il a une marge, et le MNT, ramene au pas du MNS (plus
    proche voisin) ; nodata a NaN.
    --------
    @param[in] mns_path, mnt_path : chemins des GeoTIFF MNS / MNT

    @return mns, mnt  : 2D float32 de la dalle, au pas du MNS (NaN hors donnees)
    @return meta      : profil rasterio de la dalle (cle "resolution" = taille pixel en m)
    @return mns_large : MNS avec sa marge (mns si sans marge)
    """
    with rasterio.open(mns_path) as src:
        mns_large = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        res  = src.res[0]
        meta["resolution"] = res
        t_mns  = src.transform
        nodata = src.nodata
    with rasterio.open(mnt_path) as src:
        mnt   = src.read(1).astype(np.float32)
        t_mnt = src.transform
        nodata_mnt = src.nodata

    if nodata is not None:
        mns_large[mns_large == nodata] = np.nan
    if nodata_mnt is not None:
        mnt[mnt == nodata_mnt] = np.nan

    m  = int(round((t_mnt.c - t_mns.c) / res))
    mv = int(round((t_mns.f - t_mnt.f) / res))
    if m < 0 or m != mv:
        raise ValueError(f"MNS et MNT mal cales : marge {m} x {mv} pixels")

    h, w = mns_large.shape[0] - 2 * m, mns_large.shape[1] - 2 * m
    if mnt.shape != (h, w):
        mnt = mnt[np.ix_(np.arange(h) * mnt.shape[0] // h,
                         np.arange(w) * mnt.shape[1] // w)]
    if m == 0:
        return mns_large, mnt, meta, mns_large

    mns = np.ascontiguousarray(mns_large[m:-m, m:-m])
    meta["height"], meta["width"] = mns.shape
    meta["transform"] = t_mns * Affine.translation(m, m)
    return mns, mnt, meta, mns_large
