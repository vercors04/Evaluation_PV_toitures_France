def selecPans(pans, pente_min=10, pente_max=60,
                               az_exclu_min=270, az_exclu_max=90):
    """
    Garde uniquement les pans orientés favorablement pour le PV.
    ---------------------------------------------------------------
    @param[in]  pente_min     : pente minimale (degrés)
    @param[in]  pente_max     : pente maximale (degrés)
    @param[in]  az_exclu_min  : début zone azimut exclu (270° = ouest-nord)
    @param[in]  az_exclu_max  : fin zone azimut exclu (90° = est-nord)
    @param[out] pans_ok       : liste filtrée
    """
    pans_ok = []
    for pan in pans:
        if not (pente_min <= pan["pente"] <= pente_max):
            continue
        az = pan["azimut"]
        if az >= az_exclu_min or az <= az_exclu_max:
            continue
        pans_ok.append(pan)

    print(f"Pans exploitables : {len(pans_ok)}/{len(pans)} "
          f"({100*len(pans_ok)/len(pans):.0f}%)")
    return pans_ok