import os

import numpy as np
import pandas as pd
import pyogrio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config

GPKG   = os.path.join(config.OUT_DIR_PROCESSED, "Savoie.gpkg")
CSV    = os.path.join(os.path.dirname(__file__), "batiments.csv")
SORTIE = os.path.join(config.BASE, "statistiques", "comparaison_savoie")


def medIqr(x):
    """
    Mediane et quartiles d'une serie.
    --------
    @param[in] x : Series

    @return mediane, q1, q3
    """
    return np.nanmedian(x), np.nanpercentile(x, 25), np.nanpercentile(x, 75)


def charger():
    """
    Sorties roofTool (Savoie.gpkg) et cadastre solaire Cythelia (batiments.csv), joints sur
    cleabs = id_bdtopo.
    --------
    @return DataFrame des batiments communs
    """
    rt = pyogrio.read_dataframe(GPKG, read_geometry=False, columns=[
        "cleabs", "surf_m2", "surf_m2_plat", "pente_moy_deg_incl", "irr_an_kwh",
        "prod_an_kwh", "prod_an_kwh_orp", "puissance_kwc"])
    cy = pd.read_csv(CSV, sep=";", decimal=".", encoding="latin-1", dtype={"id_bdtopo": str},
                     usecols=["id_bdtopo", "surface_2D", "surface_3D", "inclin_pro", "orient_pro",
                              "irrad_moy", "MAX_PROD", "MAX_PUISS"])
    df = rt.merge(cy, left_on="cleabs", right_on="id_bdtopo", how="inner")
    print(f"roofTool : {len(rt):,} bat | Cythelia : {len(cy):,} bat | communs : {len(df):,} "
          f"({100*len(df)/len(rt):.0f}% de roofTool, {100*len(df)/len(cy):.0f}% de Cythelia)")
    return df


def partieGeometrie(df):
    """
    Surface de toiture : surf_m2 contre surface_3D, par tranche de pente Cythelia.
    --------
    @param[in] df : batiments communs (voir charger)

    @return Series des ecarts relatifs (%)
    """
    print("\n" + "=" * 60 + "\n1. GEOMETRIE : surf_m2 vs surface_3D (aire de toit)\n" + "=" * 60)
    rd = 100 * (df.surf_m2 - df.surface_3D) / df.surface_3D
    m, q1, q3 = medIqr(rd)
    print(f"ecart relatif roofTool/Cythelia : mediane {m:+.1f}%  (IQR {q1:+.1f} .. {q3:+.1f})")
    print(f"surface totale (communs) : roofTool {df.surf_m2.sum()/1e6:.2f} vs "
          f"Cythelia {df.surface_3D.sum()/1e6:.2f} Mm2  -> {100*df.surf_m2.sum()/df.surface_3D.sum():.0f}%")
    analytique = df.surface_2D / np.cos(np.radians(df.inclin_pro.clip(0, 89)))
    print(f"Cythelia surface_3D = emprise_2D / cos(inclin_pro) ? r={df.surface_3D.corr(analytique):.4f}")
    bins = pd.cut(df.inclin_pro, [0, 20, 30, 40, 47, 90])
    tend = rd.groupby(bins, observed=True).median()
    print("ecart median (%) par tranche d'inclin_pro (Cythelia) :")
    for tr, v in tend.items():
        print(f"   {str(tr):12s} : {v:+.1f}%")

    lab = ["moins de 15", "15 à 25", "25 à 35", "35 à 45", "45 à 55", "plus de 55"]
    cats = pd.cut(df.inclin_pro, [0, 15, 25, 35, 45, 55, 90], labels=lab)
    grp = rd.groupby(cats, observed=False)
    med = grp.median().reindex(lab); q1 = grp.quantile(.25).reindex(lab); q3 = grp.quantile(.75).reindex(lab)
    x = np.arange(len(lab))
    accord = 100 * df.surf_m2.sum() / df.surface_3D.sum()
    plt.figure(figsize=(8, 5))
    plt.fill_between(x, q1, q3, alpha=0.20, color="#2a9d8f", label="moitié centrale des bâtiments (Q1 à Q3)")
    plt.plot(x, med, "o-", color="#1d6f66", lw=2.2, label="écart médian")
    plt.axhline(0, color="black", lw=1.2)
    plt.xticks(x, lab); plt.xlabel("Pente du toit estimée par Cythelia (degrés)")
    plt.ylabel("Écart de surface de toiture\nroofTool moins Cythelia, en % de Cythelia")
    plt.text(0.02, 0.03, f"Surfaces totalisées sur la Savoie : accord à {abs(accord-100):.1f} %",
             transform=plt.gca().transAxes, fontsize=9, style="italic",
             bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    plt.legend(loc="upper right"); plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout(); sauver("1_geometrie.png")
    return rd


def partieIrradiance(df):
    """
    Irradiance recue par m2 de toit contre irrad_moy.
    --------
    @param[in] df : batiments communs

    @return rd, i_rt, i_cy : ecarts relatifs (%), irradiations totales roofTool et Cythelia (kWh)
    """
    print("\n" + "=" * 60 + "\n2. IRRADIANCE : irr recue par m2 vs irrad_moy (kWh/m2/an)\n" + "=" * 60)
    inten = df.irr_an_kwh / df.surf_m2
    rd = 100 * (inten - df.irrad_moy) / df.irrad_moy
    m, q1, q3 = medIqr(rd)
    print(f"intensite roofTool : mediane {inten.median():.0f} | Cythelia : {df.irrad_moy.median():.0f} kWh/m2/an")
    print(f"ecart relatif : mediane {m:+.1f}%  (IQR {q1:+.1f} .. {q3:+.1f})")
    i_rt = df.irr_an_kwh.sum()
    i_cy = (df.irrad_moy * df.surface_3D).sum()
    print(f"irradiation totale recue (communs) : roofTool {i_rt/1e9:.2f} vs Cythelia {i_cy/1e9:.2f} GWh "
          f"-> {100*i_rt/i_cy:.0f}%")

    part_haute = 100 * (rd > 45).mean()
    plt.figure(figsize=(8, 5))
    plt.hist(rd, bins=70, range=(-25, 45), color="#4a90d9", alpha=0.85, edgecolor="white", linewidth=0.3)
    plt.axvline(0, color="black", lw=1.2, label="irradiances égales")
    plt.axvline(m, color="#c0392b", lw=2, ls="--", label=f"écart médian = {m:+.1f} %")
    plt.xlim(-25, 45)
    plt.text(0.98, 0.55, f"{part_haute:.0f} % des bâtiments\nau-delà de +45 % (hors cadre)",
             transform=plt.gca().transAxes, ha="right", fontsize=9, style="italic",
             bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    plt.ylabel("Nombre de bâtiments")
    plt.legend(); plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout(); sauver("2_irradiance.png")
    return rd, i_rt, i_cy


def partieProduction(df):
    """
    Production installable et decomposition ensoleillement x conversion, batiments a MAX_PROD
    non nul.
    --------
    @param[in] df : batiments communs

    @return None
    """
    print("\n" + "=" * 60 + "\n3. PRODUCTION : notre modele vs le leur, et croisement\n" + "=" * 60)
    d = df[df.MAX_PROD.notna() & (df.surface_3D > 0) & (df.irrad_moy > 0)].copy()
    p_rt = d.prod_an_kwh_orp.sum()
    p_cy = d.MAX_PROD.sum()
    print(f"batiments avec MAX_PROD non nul : {len(d):,}")
    print(f"production installable : roofTool {p_rt/1e9:.2f} vs Cythelia {p_cy/1e9:.2f} GWh -> {100*p_rt/p_cy:.0f}%")
    i_rt = d.irr_an_kwh.sum()
    i_cy = (d.irrad_moy * d.surface_3D).sum()
    c_rt = d.prod_an_kwh.sum() / i_rt
    c_cy = p_cy / i_cy
    print("\ndecomposition (par rapport a l'irradiation recue) :")
    print(f"  ensoleillement recu : roofTool {i_rt/1e9:.1f} vs Cythelia {i_cy/1e9:.1f} GWh -> {100*i_rt/i_cy:.0f}%")
    print(f"  conversion prod/irr : roofTool {c_rt:.3f} vs Cythelia {c_cy:.3f} -> x{c_rt/c_cy:.2f}")
    print("\ncroisement (a ensoleillement recu identique, on echange les conversions) :")
    print(f"  NOTRE ensoleillement x LEUR conversion : {i_rt*c_cy/1e9:.2f} GWh")
    print(f"  LEUR ensoleillement x NOTRE conversion : {i_cy*c_rt/1e9:.2f} GWh")

    groupes = ["Ensoleillement reçu\npar les toitures", "Conversion de la lumière\nreçue en électricité"]
    val_cy = [100, 100]
    val_rt = [100 * i_rt / i_cy, 100 * c_rt / c_cy]
    x = np.arange(len(groupes)); w = 0.36
    plt.figure(figsize=(8, 5))
    b1 = plt.bar(x - w/2, val_cy, w, color="#e76f51", label="Cythelia (référence, base 100)")
    b2 = plt.bar(x + w/2, val_rt, w, color="#2a9d8f", label="roofTool")
    for bars in (b1, b2):
        for r in bars:
            plt.text(r.get_x() + r.get_width()/2, r.get_height(), f"{r.get_height():.0f}",
                     ha="center", va="bottom", fontsize=10)
    plt.axhline(100, color="black", lw=0.8)
    plt.xticks(x, groupes); plt.ylabel("Indice comparé à Cythelia (base 100)")
    plt.text(0.98, 0.03, f"roofTool : couverture {config.COUVERTURE_INCL:.2f} des pans inclinés\n"
             "Cythelia : 70 à 90 % du toit + pertes",
             transform=plt.gca().transAxes, ha="right", fontsize=9, style="italic",
             bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    plt.legend(loc="upper left"); plt.grid(True, axis="y", alpha=0.3); plt.ylim(0, 200)
    plt.tight_layout(); sauver("3_production.png")


def partiePente(df):
    """
    Pente moyenne (roofTool) contre pente modale (Cythelia), toits presque sans plat.
    --------
    @param[in] df : batiments communs

    @return None
    """
    print("\n" + "=" * 60 + "\n4. PENTE : pente_moy_deg_incl (nous) vs inclin_pro (eux)\n" + "=" * 60)
    part_plate = df.surf_m2_plat / df.surf_m2
    pur = df[(part_plate < 0.02) & (df.pente_moy_deg_incl > 0)]
    print(f"toits quasi purement inclines (plat < 2%) : {len(pur):,} / {len(df):,}")
    print(f"  mediane pente : roofTool {pur.pente_moy_deg_incl.median():.1f}° | Cythelia {pur.inclin_pro.median():.1f}°")
    print(f"  Cythelia >= 47° (plateau artefact) : {100*(pur.inclin_pro >= 47).mean():.0f}% des toits purs")
    fiable = pur[pur.inclin_pro < 45]
    print(f"  hors plateau (inclin_pro < 45°, {len(fiable):,} toits) : "
          f"roofTool {fiable.pente_moy_deg_incl.median():.1f}° vs Cythelia {fiable.inclin_pro.median():.1f}°, "
          f"correlation r={fiable.pente_moy_deg_incl.corr(fiable.inclin_pro):.2f}")

    plt.figure(figsize=(8, 5))
    b = np.arange(0, 62, 2)
    plt.hist(pur.inclin_pro, bins=b, alpha=0.55, color="#e76f51", label="Cythelia (inclin_pro, mode)")
    plt.hist(pur.pente_moy_deg_incl, bins=b, alpha=0.55, color="#2a9d8f", label="roofTool (pente_moy_deg_incl, moyenne)")
    plt.axvline(47.5, color="#c0392b", ls="--", lw=1.5, label="plafond Cythelia ~47,5° (artefact)")
    plt.xlabel("Pente du toit (degrés)"); plt.ylabel("Nombre de toits (purement inclinés)")
    plt.legend(); plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout(); sauver("4_pente.png")


def partieMotifs(df, rd_surf):
    """
    Dispersion des ecarts de surface selon la taille du toit, queue d'ecarts extremes, exemples.
    --------
    @param[in] df      : batiments communs
    @param[in] rd_surf : ecarts relatifs de surface (%), voir partieGeometrie

    @return None
    """
    print("\n" + "=" * 60 + "\n5. MOTIFS : tendances de surface\n" + "=" * 60)
    bins = pd.cut(df.surface_3D, [0, 50, 100, 200, 500, 1e6],
                  labels=["<50", "50-100", "100-200", "200-500", ">500"])
    disp = rd_surf.abs().groupby(bins, observed=True).median()
    print("ecart de surface |%| median par taille de toit (m2) :")
    for tr, v in disp.items():
        print(f"   {tr:8s} : {v:.1f}%")
    gross = (rd_surf.abs() > 100).mean() * 100
    print(f"\nqueue d'ecarts extremes (|ecart surface|>100%) : {gross:.1f}% des batiments")
    print("\nexemples (2 tres proches, 2 tres divergents en surface) :")
    df2 = df.assign(rd=rd_surf).dropna(subset=["rd"])
    proches = df2.reindex(df2.rd.abs().nsmallest(2).index)
    loin    = df2.reindex(df2.rd.abs().nlargest(2).index)
    for titre, sous in [("proches", proches), ("divergents", loin)]:
        print(f"  -- {titre} --")
        for _, r in sous.iterrows():
            print(f"     {r.cleabs}  surf {r.surf_m2:6.0f}/{r.surface_3D:6.0f}  "
                  f"pente {r.pente_moy_deg_incl:4.1f}/{r.inclin_pro:4.1f}  ecart {r.rd:+.0f}%")


def sauver(nom):
    """
    Enregistre la figure courante dans SORTIE.
    --------
    @param[in] nom : nom du fichier

    @return None
    """
    os.makedirs(SORTIE, exist_ok=True)
    chemin = os.path.join(SORTIE, nom)
    plt.savefig(chemin, dpi=120); plt.close()
    print(f"   -> {chemin}")


def main():
    """
    Comparaison methode contre methode de la Savoie : geometrie, irradiance, production, pente,
    motifs.
    --------
    @return None
    """
    df = charger()
    rd_surf = partieGeometrie(df)
    partieIrradiance(df)
    partieProduction(df)
    partiePente(df)
    partieMotifs(df, rd_surf)
    print("\n" + "=" * 60 + "\nComparaison methode contre methode, pas une validation.\n" + "=" * 60)


if __name__ == "__main__":
    main()
