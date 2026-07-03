"""
Carte interactive des resultats calcules (folium), ouverte dans une fenetre native.

Fonctionnement en deux temps, pour ne jamais refaire un calcul deja fait :
  1. majStats() agrege chaque gpkg nouveau ou modifie en statistiques par commune,
     conservees dans data/processed/stats_carte.json (cache incremental) ;
  2. construireCarte() genere le HTML depuis ce cache. Contours embarques :
     regions et departements de metropole, communes des seuls departements
     ayant des donnees (le HTML reste leger).

Trois niveaux (regions, departements, communes) bascules automatiquement selon
le zoom. Chaque entite calculee a une popup de synthese et un bouton ouvrant un
panneau de detail (moyenne / min / max par batiment de chaque colonne de sortie).

Point d'entree interface : genererCarte() puis ouvrirCarte(chemin) dans un process.
viderCache() supprime cache et HTML, a faire si les fichiers de contours changent.
Test direct : python -m executable.carte_interactive
"""
import os
import json

import folium
import pandas as pd
import geopandas as gpd
from folium.plugins import Geocoder

from src import config


DIR_CONTOURS  = os.path.join(config.BASE_DATA, "data", "contours")
FICHIER_STATS = os.path.join(config.BASE, "data", "processed", "stats_carte.json")
FICHIER_CARTE = os.path.join(config.BASE, "data", "processed", "carte.html")

REGIONS = ["auvergne-rhone-alpes", "bourgogne-franche-comte", "bretagne",
           "centre-val-de-loire", "corse", "grand-est", "hauts-de-france",
           "ile-de-france", "normandie", "nouvelle-aquitaine", "occitanie",
           "pays-de-la-loire", "provence-alpes-cote-d-azur"]

ZOOM_DEP = 8            # zoom a partir duquel les departements remplacent les regions
ZOOM_COM = 11           # zoom a partir duquel les communes s'ajoutent
SEUIL_DEP_COMPLET = 0.9  # part des communes avec donnees pour compter un departement entier

# colonnes agregees : libelle affiche et unite ("Wh"/"Wc" : les gpkg sont en kWh / kWc)
COLONNES = {
    "hauteur_pts":       ("Hauteur du toit", "m"),
    "nb_pixels":         ("Nombre de pixels de toit", ""),
    "surf_tot_m2":       ("Surface totale", "m2"),
    "surf_plate_m2":     ("Surface plate", "m2"),
    "surf_incl_m2":      ("Surface inclinée, toutes orientations", "m2"),
    "surf_incl_or_m2":   ("Surface inclinée orientée (azimut choisi)", "m2"),
}
COLONNES.update({f"surf_incl_{s}_m2": (f"Surface inclinée {s}", "m2") for s in config.SECTEURS})
COLONNES.update({
    "pente_moy_incl":    ("Pente moyenne des pans inclinés", "deg"),
    "irr_an_kwh":        ("Irradiation reçue / an, toute la toiture", "Wh"),
    "irr_an_kwh_orp":    ("Irradiation reçue / an, base installable", "Wh"),
    "prod_an_kwh":       ("Production PV / an, toute la toiture", "Wh"),
    "prod_an_kwh_orp":   ("Production PV / an, base installable", "Wh"),
    "puissance_kwc_orp": ("Puissance installable", "Wc"),
    "prod_T1_kwh_orp":   ("Production T1 (jan-mars)", "Wh"),
    "prod_T2_kwh_orp":   ("Production T2 (avr-juin)", "Wh"),
    "prod_T3_kwh_orp":   ("Production T3 (juil-sept)", "Wh"),
    "prod_T4_kwh_orp":   ("Production T4 (oct-déc)", "Wh"),
})


def formater(valeur, unite):
    """
    Formate une valeur avec un prefixe adapte (k, M, G, T, P pour Wh/Wc, km2 pour m2).
    --------
    @param[in] valeur : valeur numerique (NaN tolere)
    @param[in] unite  : "Wh", "Wc", "m2", "m", "deg" ou ""

    @return chaine affichable ("-" si NaN)
    """
    if valeur != valeur:
        return "-"
    if unite in ("Wh", "Wc"):
        for seuil, prefixe in ((1e12, "P"), (1e9, "T"), (1e6, "G"), (1e3, "M")):
            if abs(valeur) >= seuil:
                return f"{valeur / seuil:.2f} {prefixe}{unite}"
        return f"{valeur:.2f} k{unite}"
    if unite == "m2" and abs(valeur) >= 1e6:
        return f"{valeur / 1e6:.2f} km2"
    if unite == "":
        return f"{valeur:,.0f}".replace(",", " ")
    return f"{valeur:,.1f} {unite}".replace(",", " ")


def chargerContours(niveau, regions=REGIONS):
    """
    Concatene les contours des regions metropolitaines pour un niveau donne.
    --------
    @param[in] niveau  : "region", "departement" ou "communes"
    @param[in] regions : sous-ensemble de REGIONS a charger (defaut : toutes)

    @return GeoDataFrame WGS84 (colonnes nom, code si present, region, geometry)
    """
    dossier, prefixe = {"region":      ("region", "region-"),
                        "departement": ("departement", "departements-"),
                        "communes":    ("communes", "communes-")}[niveau]
    morceaux = []
    for reg in regions:
        chemin = os.path.join(DIR_CONTOURS, dossier, f"{prefixe}{reg}.geojson")
        if not os.path.exists(chemin):
            continue
        g = gpd.read_file(chemin)
        g["region"] = reg.replace("-", " ").title()
        morceaux.append(g[[c for c in ("nom", "code", "region", "geometry") if c in g.columns]])
    if not morceaux:
        return gpd.GeoDataFrame(columns=["nom", "code", "region", "geometry"], crs="EPSG:4326")
    return gpd.GeoDataFrame(pd.concat(morceaux, ignore_index=True), crs="EPSG:4326")


def agregerGpkg(chemin, communes):
    """
    Resume un gpkg de resultats par commune : compte, somme, min et max des colonnes.
    --------
    @param[in] chemin   : chemin du .gpkg (1 ligne par batiment)
    @param[in] communes : GeoDataFrame des contours de communes (code, geometry, WGS84)

    @return dict {code_insee: {"n": int, "somme": {...}, "min": {...}, "max": {...}}}
    """
    try:
        import pyogrio                                    # ne lit que les colonnes utiles
        champs = list(pyogrio.read_info(chemin)["fields"])
        gdf = gpd.read_file(chemin, columns=[c for c in COLONNES if c in champs])
    except Exception:
        gdf = gpd.read_file(chemin)
    cols = [c for c in COLONNES if c in gdf.columns]

    pts = gpd.GeoDataFrame(gdf[cols], geometry=gdf.geometry.representative_point(),
                           crs=gdf.crs).to_crs(4326)
    minx, miny, maxx, maxy = pts.total_bounds
    proches = communes.cx[minx:maxx, miny:maxy]           # evite le sjoin France entiere
    joint = gpd.sjoin(pts, proches[["code", "geometry"]], how="inner", predicate="within")

    grp = joint.groupby("code")[cols]
    sommes, minis, maxis = grp.sum(), grp.min(), grp.max()
    tailles = joint.groupby("code").size()

    return {code: {"n": int(tailles[code]),
                   "somme": {c: float(sommes.at[code, c]) for c in cols},
                   "min":   {c: float(minis.at[code, c]) for c in cols},
                   "max":   {c: float(maxis.at[code, c]) for c in cols}}
            for code in tailles.index}


def majStats(on_log=print):
    """
    Met a jour le cache : agrege les gpkg nouveaux ou modifies, retire les disparus.
    --------
    @param[in] on_log : callback (message) pour suivre l'avancement

    @return stats, change : contenu du cache et bool indiquant s'il a change
    """
    stats = {"fichiers": {}}
    if os.path.exists(FICHIER_STATS):
        try:
            with open(FICHIER_STATS, encoding="utf-8") as f:
                stats = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    presents = {}
    if os.path.isdir(config.OUT_DIR_PROCESSED):
        presents = {nom: os.path.getmtime(os.path.join(config.OUT_DIR_PROCESSED, nom))
                    for nom in os.listdir(config.OUT_DIR_PROCESSED) if nom.endswith(".gpkg")}

    change = False
    for nom in list(stats["fichiers"]):                   # fichiers supprimes du dossier
        if nom not in presents:
            del stats["fichiers"][nom]
            change = True

    a_faire = [nom for nom, mtime in presents.items()
               if stats["fichiers"].get(nom, {}).get("mtime") != mtime]
    if a_faire:
        communes = chargerContours("communes")
        for nom in a_faire:
            on_log(f"agregation de {nom}")
            stats["fichiers"][nom] = {
                "mtime": presents[nom],
                "communes": agregerGpkg(os.path.join(config.OUT_DIR_PROCESSED, nom), communes)}
            change = True

    if change:
        os.makedirs(os.path.dirname(FICHIER_STATS), exist_ok=True)
        with open(FICHIER_STATS, "w", encoding="utf-8") as f:
            json.dump(stats, f)
    return stats, change


def fusionnerCommunes(stats):
    """
    Fusionne les stats par commune de tous les fichiers. Si une commune apparait
    dans plusieurs gpkg (ex : ville puis son departement), garde le fichier au
    plus grand nombre de batiments pour ne pas compter deux fois.
    --------
    @param[in] stats : contenu du cache (cle "fichiers")

    @return dict {code_insee: stats de la commune}
    """
    communes = {}
    for fichier in stats["fichiers"].values():
        for code, d in fichier["communes"].items():
            if code not in communes or d["n"] > communes[code]["n"]:
                communes[code] = d
    return communes


def enTableau(communes):
    """Passe le dict des communes en DataFrame plat (colonnes X_s / X_mn / X_mx)."""
    lignes = []
    for code, d in communes.items():
        ligne = {"code": code, "n": d["n"]}
        ligne.update({f"{c}_s": v for c, v in d["somme"].items()})
        ligne.update({f"{c}_mn": v for c, v in d["min"].items()})
        ligne.update({f"{c}_mx": v for c, v in d["max"].items()})
        lignes.append(ligne)
    return pd.DataFrame(lignes) if lignes else pd.DataFrame(columns=["code", "n"])


def agreger(df, cle):
    """Agrege un tableau plat par cle : sommes des X_s et n, min des X_mn, max des X_mx."""
    agg = {"n": "sum"}
    agg.update({c: "sum" for c in df.columns if c.endswith("_s")})
    agg.update({c: "min" for c in df.columns if c.endswith("_mn")})
    agg.update({c: "max" for c in df.columns if c.endswith("_mx")})
    return df.groupby(cle, as_index=False).agg(agg)


def colonne(df, nom):
    """Colonne du DataFrame, ou colonne de NaN si absente."""
    return df[nom] if nom in df.columns else pd.Series(float("nan"), index=df.index)


def valeursDetails(ligne, colonnes):
    """Liste [moyenne, min, max] formatee par entree de COLONNES (None si absente)."""
    vals = []
    for c, (_, unite) in COLONNES.items():
        if f"{c}_s" in colonnes and pd.notna(ligne.get(f"{c}_s")) and ligne["n"] > 0:
            vals.append([formater(ligne[f"{c}_s"] / ligne["n"], unite),
                         formater(ligne[f"{c}_mn"], unite),
                         formater(ligne[f"{c}_mx"], unite)])
        else:
            vals.append(None)
    return vals


def preparer(contours, df, cle_contours, cle_df, prefixe, details, titres):
    """
    Joint les stats aux contours et fabrique les colonnes texte de la popup
    (production, toitures, parts plate / inclinee, bouton de detail).
    Remplit au passage les dicts details et titres pour le panneau lateral.
    --------
    @return GeoDataFrame reduit a (nom, geometry, colonnes de popup)
    """
    g = contours.merge(df, left_on=cle_contours, right_on=cle_df, how="left")

    n     = colonne(g, "n")
    prod  = colonne(g, "prod_an_kwh_s")
    tot   = colonne(g, "surf_tot_m2_s")
    plate = colonne(g, "surf_plate_m2_s")
    pct   = (plate / tot * 100).where(tot > 0)

    g["p_prod"] = prod.map(lambda v: formater(v, "Wh"))
    g["p_toit"] = n.map(lambda v: formater(v, ""))
    g["p_plat"] = pct.map(lambda v: "-" if v != v else f"{v:.1f} %")
    g["p_incl"] = pct.map(lambda v: "-" if v != v else f"{100 - v:.1f} %")

    boutons = []
    for _, ligne in g.iterrows():
        if pd.notna(ligne.get("n")):
            cle = prefixe + str(ligne[cle_contours])
            details[cle] = valeursDetails(ligne, g.columns)
            titres[cle] = str(ligne["nom"])
            boutons.append(f"<button class=\"btn-details\" "
                           f"onclick=\"montrerDetails('{cle}')\">Voir le détail</button>")
        else:
            boutons.append("")
    g["p_btn"] = boutons

    for c in ("p_prod", "p_toit", "p_plat", "p_incl"):
        g[c] = g[c].replace("-", "Non calculé")
    return g[["nom", "geometry", "p_prod", "p_toit", "p_plat", "p_incl", "p_btn"]]


def couche(gdf, alias_nom, couleur, epaisseur, note="", zoom_on_click=False):
    """Couche folium d'un niveau : contours + tooltip + popup de synthese."""
    return folium.GeoJson(
        gdf,
        zoom_on_click=zoom_on_click,
        style_function=lambda x: {"color": couleur, "weight": epaisseur, "fillColor": "#E67E22",
                                  "fillOpacity": 0.18 if x["properties"]["p_btn"] else 0.0},
        highlight_function=lambda x: {"fillColor": "#FBFF00", "fillOpacity": 0.35},
        tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=[alias_nom]),
        popup=folium.GeoJsonPopup(
            fields=["nom", "p_prod", "p_toit", "p_plat", "p_incl", "p_btn"],
            aliases=[alias_nom, f"Production PV / an{note} :", f"Nb de toitures{note} :",
                     "Toits plats :", "Toits inclinés :", ""]))


def construireCarte(stats):
    """
    Genere le HTML de la carte depuis le cache de stats.
    --------
    @param[in] stats : contenu du cache (voir majStats)

    @return chemin du HTML ecrit (FICHIER_CARTE)
    """
    gdf_reg = chargerContours("region")
    gdf_dep = chargerContours("departement").drop_duplicates("code")
    gdf_reg["geometry"] = gdf_reg.geometry.simplify(0.002, preserve_topology=True)
    gdf_dep["geometry"] = gdf_dep.geometry.simplify(0.002, preserve_topology=True)

    # stats par commune depuis le cache ; seules les regions avec donnees sont chargees
    df_com = enTableau(fusionnerCommunes(stats))
    df_com["dep"] = df_com["code"].str[:2]
    dep_region = gdf_dep.set_index("code")["region"]
    regions_avec = {dep_region.get(d) for d in set(df_com["dep"])} - {None}
    gdf_com = chargerContours("communes", [r for r in REGIONS
                                           if r.replace("-", " ").title() in regions_avec])

    # departements montres si quasi complets
    total_par_dep = gdf_com.groupby(gdf_com["code"].str[:2]).size()
    avec_par_dep  = df_com.groupby("dep").size()
    complets = [d for d, nb in avec_par_dep.items()
                if nb >= SEUIL_DEP_COMPLET * total_par_dep.get(d, float("inf"))]

    df_dep = agreger(df_com[df_com["dep"].isin(complets)].drop(columns="code"), "dep")
    df_dep["region"] = df_dep["dep"].map(gdf_dep.set_index("code")["region"])
    df_reg = agreger(df_dep.drop(columns="dep"), "region")

    # seules les communes des departements avec donnees sont gardees, puis simplifiees
    gdf_com = gdf_com[gdf_com["code"].str[:2].isin(set(df_com["dep"]))].copy()
    gdf_com["geometry"] = gdf_com.geometry.simplify(0.001, preserve_topology=True)

    # jointure stats + contours, popups, panneau de detail
    details, titres = {}, {}
    g_reg = preparer(gdf_reg, df_reg, "region", "region", "r", details, titres)
    g_dep = preparer(gdf_dep, df_dep.drop(columns="region"), "code", "dep", "d", details, titres)
    g_com = preparer(gdf_com, df_com, "code", "code", "c", details, titres)

    carte = folium.Map(location=(46.8, 2.3), zoom_start=6, tiles="CartoDB Positron",
                       control_scale=True, prefer_canvas=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Vue satellite", overlay=False, control=True, show=False).add_to(carte)
    Geocoder(position="topright", zoom=13, add_marker=False).add_to(carte)

    fg_reg = folium.FeatureGroup(name="Régions", control=False)
    fg_dep = folium.FeatureGroup(name="Départements", control=False, show=False)
    fg_com = folium.FeatureGroup(name="Communes", control=False, show=False)
    couche(g_reg, "Région :", "#FFFFFF", 2, note=" (dép. complets)", zoom_on_click=True).add_to(fg_reg)
    couche(g_dep, "Département :", "#1A252C", 1.5).add_to(fg_dep)
    if not g_com.empty:
        couche(g_com, "Commune :", "#7F8C8D", 1.2).add_to(fg_com)
    fg_reg.add_to(carte)
    fg_dep.add_to(carte)
    fg_com.add_to(carte)
    folium.LayerControl(position="topleft", collapsed=True).add_to(carte)

    # bascule automatique des niveaux selon le zoom
    niveaux = [f"[{fg_reg.get_name()}, 0, {ZOOM_DEP}]",
               f"[{fg_dep.get_name()}, {ZOOM_DEP}, 99]",
               f"[{fg_com.get_name()}, {ZOOM_COM}, 99]"]
    js_zoom = f"""
    <script>
    document.addEventListener("DOMContentLoaded", function () {{
        var carte = {carte.get_name()};
        var niveaux = [{", ".join(niveaux)}];
        function majNiveaux() {{
            var z = carte.getZoom();
            niveaux.forEach(function (nv) {{
                if (z >= nv[1] && z < nv[2]) {{ if (!carte.hasLayer(nv[0])) carte.addLayer(nv[0]); }}
                else {{ if (carte.hasLayer(nv[0])) carte.removeLayer(nv[0]); }}
            }});
        }}
        carte.on("zoomend", majNiveaux);
        majNiveaux();
    }});
    </script>"""

    # panneau lateral de detail, rempli au clic sur le bouton d'une popup
    libelles = [lib for lib, _ in COLONNES.values()]
    js_details = f"""
    <div id="panneau-details">
        <span id="detail-fermer" onclick="fermerDetails()">&#10005;</span>
        <div id="detail-contenu"></div>
    </div>
    <script>
    var LIBELLES = {json.dumps(libelles, ensure_ascii=False)};
    var TITRES = {json.dumps(titres, ensure_ascii=False)};
    var DETAILS = {json.dumps(details, ensure_ascii=False)};
    function montrerDetails(cle) {{
        var d = DETAILS[cle];
        if (!d) return;
        var html = "<h3>" + TITRES[cle] + "</h3><p class='detail-note'>valeurs par bâtiment</p>";
        html += "<table><tr><th></th><th>moyenne</th><th>min</th><th>max</th></tr>";
        for (var i = 0; i < d.length; i++) {{
            if (!d[i]) continue;
            html += "<tr><th>" + LIBELLES[i] + "</th><td>" + d[i][0] + "</td><td>"
                  + d[i][1] + "</td><td>" + d[i][2] + "</td></tr>";
        }}
        document.getElementById("detail-contenu").innerHTML = html + "</table>";
        document.getElementById("panneau-details").style.display = "block";
    }}
    function fermerDetails() {{
        document.getElementById("panneau-details").style.display = "none";
    }}
    </script>"""

    css = """
    <style>
    .leaflet-popup-content-wrapper { border-radius: 10px; }
    .leaflet-popup-content { margin: 10px 14px; width: 300px !important; }
    .leaflet-popup-content table { width: 100%; border-collapse: collapse;
                                   font-family: Arial, sans-serif; }
    .leaflet-popup-content th, .leaflet-popup-content td { padding: 5px 6px;
        border-bottom: 1px solid #eee; font-size: 12.5px; }
    .leaflet-popup-content th { text-align: left; color: #555; font-weight: 600; }
    .leaflet-popup-content td { text-align: right; font-weight: 700; color: #1A252C; }
    .btn-details { cursor: pointer; border: none; border-radius: 6px; padding: 5px 10px;
                   background: #E67E22; color: white; font-weight: 600; }
    #panneau-details { position: fixed; top: 80px; right: 15px; width: 480px;
        max-height: 75%; overflow-y: auto; display: none; z-index: 9999;
        background: #fff; border-radius: 12px; padding: 15px 20px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.25); font-family: Arial, sans-serif; }
    #panneau-details h3 { margin: 0 0 2px 0; color: #1A252C; }
    #panneau-details .detail-note { margin: 0 0 10px 0; color: #7F8C8D; font-size: 12px; }
    #panneau-details table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
    #panneau-details th, #panneau-details td { padding: 4px 6px;
        border-bottom: 1px solid #eee; text-align: right; }
    #panneau-details th { text-align: left; color: #555; font-weight: 600; }
    #detail-fermer { float: right; cursor: pointer; color: #7F8C8D; font-size: 16px; }
    </style>"""

    titre = """
    <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
                background-color: rgba(255,255,255,0.98); border-radius: 30px;
                z-index: 9999; padding: 10px 25px;
                font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px;
                color: #1A252C; box-shadow: 0 4px 24px rgba(0,0,0,0.15);">
        <span style="color: #E67E22; font-weight: bold; margin-right: 8px;">&#9679;</span>
        Évaluation du Potentiel Photovoltaïque des Toitures en France
    </div>"""

    noms = sorted(nom.replace(".gpkg", "").replace("-", " ") for nom in stats["fichiers"])
    lignes = "".join(f'<li>{nom}</li>' for nom in noms)
    secteurs = f"""
    <div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999;
                background-color: rgba(255,255,255,0.95); padding: 12px 18px;
                border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif; max-height: 260px; overflow-y: auto;">
        <div style="font-size: 13px; font-weight: bold; color: #1A252C;
                    border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 6px;">
            Secteurs traités ({len(noms)})</div>
        <ul style="list-style: none; padding: 0; margin: 0; font-size: 12.5px;
                   color: #2C3E50; line-height: 1.7;">{lignes}</ul>
    </div>"""

    for element in (css, titre, secteurs, js_details, js_zoom):
        carte.get_root().html.add_child(folium.Element(element))

    os.makedirs(os.path.dirname(FICHIER_CARTE), exist_ok=True)
    carte.save(FICHIER_CARTE)
    return FICHIER_CARTE


def genererCarte(on_log=print):
    """
    Met a jour le cache de stats puis regenere le HTML seulement si necessaire.
    --------
    @param[in] on_log : callback (message) pour suivre l'avancement

    @return chemin du HTML de la carte
    """
    stats, change = majStats(on_log)
    if change or not os.path.exists(FICHIER_CARTE):
        on_log("construction de la carte")
        construireCarte(stats)
    return FICHIER_CARTE


def viderCache():
    """
    Supprime le cache de stats et le HTML : tout sera reconstruit au prochain
    affichage (plusieurs minutes). Necessaire apres une mise a jour des fichiers
    de contours (data/contours), sinon les codes INSEE du cache peuvent ne plus
    correspondre aux nouveaux contours.
    """
    for chemin in (FICHIER_STATS, FICHIER_CARTE):
        if os.path.exists(chemin):
            os.remove(chemin)


def ouvrirCarte(chemin):
    """
    Ouvre la carte dans une fenetre native (pywebview / WebView2). A lancer dans
    un process dedie depuis l'interface : la boucle pywebview est bloquante.
    Sans pywebview, repli sur le navigateur par defaut.
    --------
    @param[in] chemin : chemin du HTML a afficher
    """
    try:
        import webview
    except ImportError:
        import webbrowser
        webbrowser.open("file:///" + os.path.abspath(chemin).replace("\\", "/"))
        return
    webview.create_window("Carte des toitures", chemin, width=1200, height=800)
    webview.start()


if __name__ == "__main__":
    ouvrirCarte(genererCarte())
