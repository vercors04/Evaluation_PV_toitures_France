import os
import queue, threading, multiprocessing
from tkinter import ttk, messagebox
from executable.tool_item_exe import (boiteDefilante, champ, case, champ2, fenetre, boite, menuCoches,
                                       onglets, radioBoutons, onglet, listeDeroulante,
                                       barreProgression, zoneLogs, bouton, bulleAide,
                                       comboSuggestions)
from src import config
from src.pipeline import runPipeline, runPipelineDecoupe
from executable.tool_fct_exe import afficherBilan, listesFichiers, statsRapide
from executable.carte_interactive import genererCarte, ouvrirCarte, viderCache
from executable.carte_dessin import (genererCarte as genererCarteDessin,
                                     ouvrirCarteDessin, lireTrace, listeTraces, SEUIL_GRAVE,
                                     viderCache as viderCacheDessin)

if __name__ == "__main__":
    multiprocessing.freeze_support()

    os.makedirs(config.DIR_GEOJSON, exist_ok=True)
    os.makedirs(config.OUT_DIR_PROCESSED, exist_ok=True)
    os.makedirs(config.OUT_DIR_RAW, exist_ok=True)

    fen1 = fenetre("roofTool", 1000, 500)
    fen1.iconbitmap(os.path.join(config.BASE_DATA, "data/assets", "logo_soleil.ico"))

    q = queue.Queue()

    nb = onglets(fen1)
    nb.grid(row=0, column=0, sticky="nsew")

    o1 = onglet(nb, "Calcul")
    o1.columnconfigure(0, weight=1)
    o1.columnconfigure(1, weight=1)
    o1.rowconfigure(0, weight=1)

    bpg = boite(o1, "paramètres globaux")
    bpg.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    surf_min   = champ(bpg, "Surface min (m2)", config.SURF_MIN)
    haut_min   = champ(bpg, "Hauteur min (m)", config.HAUT_MIN, aide="point le plus haut du toit")
    haut_max   = champ(bpg, "Hauteur max (m)", config.HAUT_MAX, aide="point le plus haut du toit")
    az_min     = champ(bpg, "Azimut min", config.AZ_MIN,
                       aide="degrés, 0 = Nord, 90 = Est. Arc parcouru en sens horaire jusqu'au max.")
    az_max     = champ(bpg, "Azimut max", config.AZ_MAX, aide="degrés, 0 = Nord, 90 = Est.")
    pente_plat = champ(bpg, "Pente plat (deg)", config.PENTE_PLAT, aide="en dessous, le toit est plat")
    pente_max  = champ(bpg, "Pente max (deg)", config.PENTE_MAX, aide="70 au plus")
    seuil_irradiance = champ(bpg, "Seuil irradiance", config.SEUIL_IRRADIANCE,
                             aide="kWh/m²/an reçus, ombrage compris, pour les sorties « seuil »")

    const_leg = case(bpg, "Inclure les constructions légères", config.CONSTRUCTION_LEGERE)

    attrs   = menuCoches(bpg, "Attributs BD TOPO", config.ATTRS_BDTOPO, config.ATTRS_BATI,
                         aide="attributs copiés dans le gpkg, souvent incomplets")
    etat    = menuCoches(bpg, "État", config.ETATS, config.ETAT)
    nature  = menuCoches(bpg, "Natures gardées", config.NATURES, config.NATURE_OK)
    usage_1 = menuCoches(bpg, "Usages gardés", config.USAGE_1, config.USAGE_OK,
                         aide="beaucoup de bâtiments sont notés « Indifférencié »")

    protections  = menuCoches(bpg, "Protections", list(config.PROTECTIONS), config.PROTECTIONS_OK,
                              aide="zones où un refus reste possible (L111-17). Une colonne par "
                                   "couche cochée ; marqué ne veut pas dire interdit.")
    prot_exclure = case(bpg, "Supprimer les bâtiments protégés", config.PROTECTIONS_EXCLURE,
                        aide="retire du gpkg les bâtiments marqués au lieu de les signaler")

    sortie = menuCoches(bpg, "Colonnes de sortie", list(config.GROUPES_SORTIE), config.SORTIE_GARDEES,
                        aide="colonnes écrites dans le gpkg ; toutes sont calculées")

    cg = ttk.Frame(o1)
    cg.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    bcz = boite(cg, "choix de la zone")
    bcz.pack(fill="x")

    champs = {}

    def rebuild():
        for w in sous.winfo_children():
            w.destroy()
        champs.clear()
        choix = zone.get()

        if choix == "Adresse":
            champs["zone"] = comboSuggestions(
                sous, choix, config.GEOCODAGE, lambda t: {"q": t, "limit": 10},
                lambda r: [f["properties"]["label"] for f in r.get("features", [])], 3, largeur=50)
        elif choix == "Commune ou ville":
            champs["zone"] = comboSuggestions(
                sous, choix, config.GEO_API + "/communes",
                lambda t: {"nom": t, "limit": 10, "fields": "nom,codeDepartement"},
                lambda r: [f'{c["nom"]} ({c["codeDepartement"]})' for c in r
                           if c["codeDepartement"] < "97"], 3)
        elif choix == "Département":
            champs["zone"] = comboSuggestions(
                sous, choix, config.GEO_API + "/departements", lambda t: {"nom": t, "limit": 10},
                lambda r: [f'{c["nom"]} ({c["code"]})' for c in r if c["code"] < "97"], 2)
        elif choix == "Région":
            champs["zone"] = comboSuggestions(
                sous, choix, config.GEO_API + "/regions", lambda t: {"nom": t, "limit": 10},
                lambda r: [c["nom"] for c in r if int(c["code"]) > 10], 2)
        elif choix == "Zone tracée":
            ttk.Label(sous, text="Zone tracée").pack(anchor="w", pady=5)
            champ_zone = ttk.Combobox(sous, width=30, state="readonly",
                                      values=listeTraces())
            champ_zone.pack(anchor="w", pady=5)
            if champ_zone["values"]:
                champ_zone.current(len(champ_zone["values"]) - 1)
            else:
                ttk.Label(sous, text="Aucune zone tracée : voir l'onglet « Carte de traçage ».",
                          foreground="#8A4B08").pack(anchor="w")
            champs["zone"] = champ_zone

    zone = radioBoutons(bcz, "Échelle", config.ECHELLES, "Commune ou ville", on_change=rebuild,
                        aide="Région et France : un fichier par département ; ceux déjà calculés "
                             "sont sautés (supprimer le fichier pour refaire).")
    sous = ttk.Frame(bcz); sous.pack(fill="x")
    rebuild()

    def recolte():
        reglages = {nom: int(w.get())   for nom, w in {**w_entiers, **w_listes}.items()}
        reglages.update({nom: w.get()        for nom, w in w_textes.items()})
        reglages.update({nom: float(w.get()) for nom, w in w_flottants.items()})
        reglages.update({nom: var.get()      for nom, var in w_cases.items()})
        reglages.update({nom: [o for o, v in d.items() if v.get()] for nom, d in w_menus.items()})
        return reglages

    def lireZone():
        choix = zone.get()

        if choix == "France":
            return "nationale", "France", None

        texte = champs["zone"].get().strip()
        if not texte:
            raise ValueError("Choisissez une zone.")

        if choix == "Adresse":
            return "adresse", texte, None

        if choix == "Région":
            return "region", texte, None

        if choix == "Commune ou ville":
            if "(" not in texte:
                raise ValueError("Sélectionnez une suggestion dans la liste (nom + code).")
            nom, code = texte.rsplit("(", 1)
            return "commune", nom.strip(), code.rstrip(")").strip()

        if choix == "Département":
            if "(" not in texte:
                raise ValueError("Sélectionnez une suggestion dans la liste (nom + code).")
            return "departement", texte.rsplit("(", 1)[0].strip(), None

        if choix == "Zone tracée":
            return "polygone", texte, None

        raise ValueError(f"Échelle inconnue : {choix}")

    bl = boite(cg, "lancement")
    bl.pack(fill="both", expand=True, pady=(10, 0))

    btn_lancer = ttk.Button(bl, text="Lancer", command=lambda: lancer())
    btn_lancer.pack(anchor="w", pady=5)

    barre = barreProgression(bl)
    barre.pack(fill="x", pady=5)

    logs = zoneLogs(bl, hauteur=8)
    logs.pack(fill="both", expand=True, pady=5)
    logs.configure(state="disabled")

    def ecrireLog(texte):
        logs.configure(state="normal")
        logs.insert("end", texte)
        logs.see("end")
        logs.configure(state="disabled")

    def viderLogs():
        logs.configure(state="normal")
        logs.delete("1.0", "end")
        logs.configure(state="disabled")

    def lancer():
        try:
            reglages = recolte()
            echelle, nom_zone, code_dep = lireZone()
        except ValueError as e:
            ecrireLog(f"[ERREUR] {e}\n")
            return

        config.save(reglages)

        btn_lancer.configure(state="disabled")
        barre["value"] = 0
        viderLogs()

        threading.Thread(target=lancerPipeline, args=(echelle, nom_zone, code_dep), daemon=True).start()

    def lancerPipeline(echelle, nom_zone, code_dep):
        def onLog(msg):
            q.put(("log", msg))

        def onProgress(i, total):
            q.put(("progress", i, total))

        try:
            if echelle in ("nationale", "region"):
                bilan = runPipelineDecoupe(echelle, nom_zone, on_progress=onProgress, on_log=onLog)
            else:
                bilan = runPipeline(echelle, nom_zone, code_dep, on_progress=onProgress, on_log=onLog)
            q.put(("done", bilan))
        except Exception as e:
            q.put(("error", str(e)))

    def verifierQueue():
        try:
            while True:
                item = q.get_nowait()

                if item[0] == "log":
                    ecrireLog(item[1] + "\n")

                elif item[0] == "progress":
                    i, total = item[1], item[2]
                    barre["value"] = i * 100 // total

                elif item[0] == "done":
                    btn_lancer.configure(state="normal")
                    barre["value"] = 0
                    for ligne in afficherBilan(item[1]):
                        ecrireLog(ligne + "\n")
                    rafraichirPA()
                    rafraichirIF()

                elif item[0] == "error":
                    btn_lancer.configure(state="normal")
                    barre["value"] = 0
                    ecrireLog(f"[ERREUR] {item[1]}\n")

        except queue.Empty:
            pass

        fen1.after(100, verifierQueue)

    verifierQueue()

    o2 = onglet(nb, "Paramètres avancés")
    o2.columnconfigure(0, weight=1)
    o2.columnconfigure(1, weight=1)
    o2.rowconfigure(0, weight=1)
    bpa_ext, bpa = boiteDefilante(o2, "paramètres avancés")
    bpa_ext.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def groupe(titre):
        """
        Boite de reglages empilee dans la colonne defilante.
        --------
        @param[in] titre : titre de la boite

        @return LabelFrame
        """
        b = boite(bpa, titre)
        b.pack(fill="x", padx=8, pady=(4, 6))
        return b

    def placements(mere):
        """
        Ordre et placement des enfants d'une boite, pour les cacher puis les remontrer a
        leur place.
        --------
        @param[in] mere : boite dont tous les enfants sont crees

        @return liste de (widget, options de pack)
        """
        liste = []
        for w in mere.winfo_children():
            if w.winfo_manager() == "pack":
                info = w.pack_info()
                info.pop("in", None)
            else:
                info = {"fill": "x", "padx": 8, "pady": (2, 6)}
            liste.append((w, info))
        return liste

    def montrer(liste, caches):
        """
        Replace les enfants d'une boite dans leur ordre, sauf ceux a cacher.
        --------
        @param[in] liste  : sortie de placements
        @param[in] caches : widgets a cacher
        """
        for w, _ in liste:
            w.pack_forget()
        for w, info in liste:
            if w not in caches:
                w.pack(**info)

    g_pv = groupe("Modèle photovoltaïque")
    rendement_module   = champ2(g_pv, "Rendement du module PV", config.RENDEMENT_MODULE,
                                aide="aux conditions standard. 0,20 = 20 %.")
    pr_hors_temp       = champ2(g_pv, "Performance ratio (hors température)", config.PR_HORS_TEMP,
                                aide="câblage, onduleur, salissures, désadaptation, indisponibilités.")
    gamma_module       = champ2(g_pv, "Coefficient de température (/°C)", config.GAMMA_MODULE,
                                aide="perte par degré au-dessus de 25 °C. -0,0035 = -0,35 %/°C.")
    albedo             = champ2(g_pv, "Albédo (réflectivité du sol)", config.ALBEDO,
                                aide="figé dans les tables météo : les reconstruire après changement.")
    pose               = listeDeroulante(g_pv, "Type de pose (pans inclinés)", list(config.POSES),
                                config.POSE,
                                aide="préremplit U0 et U1. Surimposé : rails sur la couverture ; intégré : "
                                     "remplace la couverture ; libre : châssis ventilé.")

    g_faiman = boite(g_pv, "Coefficients thermiques de Faiman")
    u0_faiman          = champ2(g_faiman, "U0 (W/m²/K)", config.U0_FAIMAN,
                                aide="échange module/air à vent nul. Plus bas = plus chaud.")
    u1_faiman          = champ2(g_faiman, "U1 (W·s/m³/K)", config.U1_FAIMAN,
                                aide="part de l'échange due au vent.")

    g_plat = groupe("Toits plats")
    plat_pose          = listeDeroulante(g_plat, "Pose des modules", config.POSES_PLAT + ["mixte"],
                                config.PLAT_POSE,
                                aide="à plat : sur la membrane ; sud : rangées espacées ; est-ouest : paires "
                                     "dos à dos ; mixte : pose choisie par bâtiment.")

    g_mixte = boite(g_plat, "Répartition")
    mixte_critere      = listeDeroulante(g_mixte, "Critère", config.CRITERES_MIXTE,
                                config.MIXTE_CRITERE,
                                aide="surface : surface plate du bâtiment. usage, nature : "
                                     "attributs BD TOPO.")
    mixte_seuil        = champ2(g_mixte, "Seuil de surface plate (m²)", config.MIXTE_SEUIL_M2)
    mixte_usages       = menuCoches(g_mixte, "Usages retenus", config.USAGE_1, config.MIXTE_USAGES)
    ligne_usages       = g_mixte.winfo_children()[-1]
    mixte_natures      = menuCoches(g_mixte, "Natures retenues", config.NATURES,
                                config.MIXTE_NATURES)
    ligne_natures      = g_mixte.winfo_children()[-1]
    mixte_si           = listeDeroulante(g_mixte, "Pose si le critère est rempli",
                                config.POSES_PLAT, config.MIXTE_SI,
                                aide="surface : au-dessus du seuil. usage, nature : valeurs "
                                     "retenues.")
    mixte_sinon        = listeDeroulante(g_mixte, "Pose sinon", config.POSES_PLAT,
                                config.MIXTE_SINON)

    g_sud = boite(g_plat, "Rangées sud")
    sud_pente          = champ2(g_sud, "Pente (deg)", config.SUD_PENTE,
                                aide="10 à 15 sur lestage, 20 à 35 sur structure.")
    sud_azimut         = champ2(g_sud, "Azimut (deg)", config.SUD_AZIMUT,
                                aide="0 = Nord, 180 = Sud.")
    sud_espacement     = listeDeroulante(g_sud, "Espacement", config.ESPACEMENTS_SUD,
                                config.SUD_ESPACEMENT,
                                aide="aucune ombre à midi au solstice d'hiver, selon la latitude.")
    sud_gcr            = champ2(g_sud, "Taux d'occupation au sol", config.SUD_GCR,
                                aide="surface de modules / surface du champ. 0,5 à 0,7.")

    g_eo = boite(g_plat, "Est-ouest")
    eo_pente           = champ2(g_eo, "Pente (deg)", config.EO_PENTE, aide="5 à 15.")
    eo_gcr             = champ2(g_eo, "Taux d'occupation au sol", config.EO_GCR,
                                aide="surface de modules / surface du champ, deux faces. "
                                     "0,8 à 0,95.")

    g_couv = groupe("Surface équipable")
    couv_incl          = champ2(g_couv, "Couverture des pans inclinés", config.COUVERTURE_INCL,
                                aide="part équipée : reculs, cheminées, calepinage.")
    emprise_plat       = champ2(g_couv, "Emprise du champ sur les toits plats", config.EMPRISE_PLAT,
                                aide="part du toit plat sous le champ : reculs, accès, édicules.")
    recul_m            = champ2(g_couv, "Recul géométrique (m)", config.RECUL_M,
                                aide="écarte les pixels proches d'un bord ou d'un obstacle. 0 = désactivé ; "
                                     "sinon, baisser les taux ci-dessus.")

    g_geom = groupe("Détection de la géométrie")
    buffer      = champ2(g_geom, "Tampon autour des bâtiments (m)", config.BUFFER,
                                aide="marge autour des emprises BD TOPO.")
    mnh_min     = champ2(g_geom, "Hauteur min au-dessus du sol (m)", config.MNH_MIN,
                                aide="en dessous, le pixel n'est pas du toit.")
    res_mnt_m   = champ2(g_geom, "Pas du MNT téléchargé (m)", config.RES_MNT_M,
                                aide="sert à la hauteur au-dessus du sol. 0,5 en relief marqué.")
    methode_pente = listeDeroulante(g_geom, "Méthode pente/orientation", ["plan", "differences"],
                                config.METHODE_PENTE,
                                aide="« plan » : moindres carrés, moins bruité. « differences » : méthode du "
                                     "rapport.")

    g_plan = boite(g_geom, "Ajustement de plan")
    rayon_plan  = champ2(g_plan, "Demi-fenêtre d'ajustement (px)", config.RAYON_PLAN,
                                aide="1 = 3x3, 2 = 5x5. Au-delà, les arêtes sont lissées.")
    residu_max  = champ2(g_plan, "Écart max au plan ajusté (m)", config.RESIDU_MAX_M,
                                aide="au-delà, le pixel est écarté (mur, rive). 0 = désactivé.")
    residu_pan  = champ2(g_plan, "Seuil de réajustement sur demi-fenêtre (m)", config.RESIDU_PAN_M,
                                aide="au-delà, pente réestimée sur la demi-fenêtre la plus plane. 0 = désactivé.")

    g_omb = groupe("Ombrage proche")
    n_directions = listeDeroulante(g_omb, "Nombre de directions azimutales",
                                config.DIVISEURS_360, config.N_DIRECTIONS,
                                aide="36 = une direction tous les 10 degrés.")
    dist_max_m   = champ2(g_omb, "Rayon de recherche (m)", config.DIST_MAX_M,
                                aide="portée sur le MNS fin ; la dalle est téléchargée élargie d'autant.")
    cap          = champ2(g_omb, "Plafond solaire (deg)", config.CAP,
                                aide="au-delà, l'obstacle est ignoré.")
    pas_rayon_div = champ2(g_omb, "Croissance du pas du rayon", config.PAS_RAYON_DIV,
                                aide="0 = exact. n : pas += 1 + pas/n, plus rapide, moins exact.")

    g_loin = groupe("Ombrage lointain (relief)")
    dist_loin_m     = champ2(g_loin, "Portée (m)", config.DIST_LOIN_M,
                                aide="portée sur le MNT de relief. 0 = désactivé.")
    res_loin_m      = champ2(g_loin, "Pas du MNT de relief (m)", config.RES_LOIN_M,
                                aide="plus fin = plus lourd, mais crédible plus près.")
    dist_min_loin_m = champ2(g_loin, "Distance de confiance (m)", config.DIST_MIN_LOIN_M,
                                aide="en deçà, le relief n'ombre pas. Environ 20 fois le pas du MNT de relief.")

    g_res = groupe("Réseau, téléchargement et parallélisme")
    n_coeurs      = champ2(g_res, "Nombre de cœurs (parallélisme)", config.N_COEURS,
                                aide="dalles traitées en parallèle.")
    n_threads     = champ2(g_res, "Nombre de threads (requêtes WFS)", config.N_THREADS)
    count         = champ2(g_res, "Taille des paquets WFS", config.COUNT,
                                aide="entités par requête WFS.")
    n_essais_wfs  = champ2(g_res, "Essais WFS", config.N_ESSAIS_WFS,
                                aide="essais si la requête échoue.")
    pause_wfs     = champ2(g_res, "Pause entre essais WFS (s)", config.PAUSE_WFS)
    n_essais      = champ2(g_res, "Essais téléchargement de dalle", config.N_ESSAIS)
    pause_dl      = champ2(g_res, "Pause entre essais de dalle (s)", config.PAUSE_DL)
    n_essais_dep  = champ2(g_res, "Essais par département", config.N_ESSAIS_DEPARTEMENT)
    pause_dep     = champ2(g_res, "Pause entre essais de département (s)", config.PAUSE_DEPARTEMENT)

    places = {b: placements(b) for b in (g_pv, g_geom, g_plat, g_mixte, g_sud)}

    def majVisibilite(*_):
        choix = plat_pose.get()
        poses = {mixte_si.get(), mixte_sinon.get()} if choix == "mixte" else {choix}
        montrer(places[g_pv], set() if pose.get() == "personnalise" else {g_faiman})
        montrer(places[g_geom], set() if methode_pente.get() == "plan" else {g_plan})
        montrer(places[g_plat], {b for b, vu in ((g_mixte, choix == "mixte"),
                                                 (g_sud, "sud" in poses),
                                                 (g_eo, "est-ouest" in poses)) if not vu})
        critere = mixte_critere.get()
        montrer(places[g_mixte], {w for w, vu in ((mixte_seuil.master, critere == "surface"),
                                                  (ligne_usages, critere == "usage"),
                                                  (ligne_natures, critere == "nature")) if not vu})
        montrer(places[g_sud], set() if sud_espacement.get() == config.ESPACEMENTS_SUD[1]
                               else {sud_gcr.master})

    for liste in (pose, methode_pente, plat_pose, mixte_critere, mixte_si, mixte_sinon,
                  sud_espacement):
        liste.bind("<<ComboboxSelected>>", majVisibilite)
    majVisibilite()

    w_entiers = {
        "SURF_MIN": surf_min, "HAUT_MIN": haut_min, "HAUT_MAX": haut_max,
        "AZ_MIN": az_min, "AZ_MAX": az_max, "PENTE_PLAT": pente_plat, "PENTE_MAX": pente_max,
        "N_ESSAIS_WFS": n_essais_wfs, "N_COEURS": n_coeurs, "N_THREADS": n_threads,
        "COUNT": count, "N_ESSAIS": n_essais, "DIST_MAX_M": dist_max_m,
        "N_ESSAIS_DEPARTEMENT": n_essais_dep, "RAYON_PLAN": rayon_plan,
        "DIST_LOIN_M": dist_loin_m, "RES_LOIN_M": res_loin_m,
        "DIST_MIN_LOIN_M": dist_min_loin_m, "PAS_RAYON_DIV": pas_rayon_div,
    }
    w_flottants = {
        "BUFFER": buffer, "MNH_MIN": mnh_min, "CAP": cap, "PAUSE_WFS": pause_wfs, "PAUSE_DL": pause_dl,
        "RENDEMENT_MODULE": rendement_module, "PR_HORS_TEMP": pr_hors_temp,
        "GAMMA_MODULE": gamma_module, "COUVERTURE_INCL": couv_incl,
        "EMPRISE_PLAT": emprise_plat, "RECUL_M": recul_m,
        "U0_FAIMAN": u0_faiman, "U1_FAIMAN": u1_faiman,
        "ALBEDO": albedo, "PAUSE_DEPARTEMENT": pause_dep,
        "RESIDU_MAX_M": residu_max, "SEUIL_IRRADIANCE": seuil_irradiance,
        "RES_MNT_M": res_mnt_m, "RESIDU_PAN_M": residu_pan,
        "SUD_PENTE": sud_pente, "SUD_AZIMUT": sud_azimut, "SUD_GCR": sud_gcr,
        "EO_PENTE": eo_pente, "EO_GCR": eo_gcr, "MIXTE_SEUIL_M2": mixte_seuil,
    }
    w_listes = {"N_DIRECTIONS": n_directions}
    w_textes = {"POSE": pose, "METHODE_PENTE": methode_pente, "PLAT_POSE": plat_pose,
                "SUD_ESPACEMENT": sud_espacement, "MIXTE_CRITERE": mixte_critere,
                "MIXTE_SI": mixte_si, "MIXTE_SINON": mixte_sinon}
    w_cases  = {"CONSTRUCTION_LEGERE": const_leg, "PROTECTIONS_EXCLURE": prot_exclure}
    w_menus  = {"ATTRS_BATI": attrs, "NATURE_OK": nature, "USAGE_OK": usage_1,
                "SORTIE_GARDEES": sortie, "ETAT": etat, "MIXTE_USAGES": mixte_usages,
                "MIXTE_NATURES": mixte_natures, "PROTECTIONS_OK": protections}

    def reinitialiser():
        for nom, w in {**w_entiers, **w_flottants}.items():
            w.delete(0, "end"); w.insert(0, str(config.DEFAULTS[nom]))
        for nom, w in {**w_listes, **w_textes}.items():
            w.set(config.DEFAULTS[nom])
        for nom, var in w_cases.items():
            var.set(config.DEFAULTS[nom])
        for nom, d in w_menus.items():
            for opt, var in d.items():
                var.set(opt in config.DEFAULTS[nom])
        majVisibilite()

    def enregistrer():
        try:
            reglages = recolte()
        except ValueError as e:
            messagebox.showerror("Paramètres", f"Valeur invalide dans un champ : {e}")
            return
        config.save(reglages)
        messagebox.showinfo("Paramètres", "Paramètres enregistrés")

    ligne_btns = ttk.Frame(bpa); ligne_btns.pack(pady=8)
    ttk.Button(ligne_btns, text="Réinitialiser les paramètres par défaut",
               command=lambda: reinitialiser()).pack(side="left", padx=3)

    ttk.Button(ligne_btns, text="Enregistrer les paramètres",
               command=lambda: enregistrer()).pack(side="left", padx=3)
    bulleAide(ligne_btns, "enregistre les réglages sans lancer de calcul.")

    bfg = boite(o2, "fichiers générés")
    bfg.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    rafraichirPA = listesFichiers(bfg, config.DIR_GEOJSON, config.OUT_DIR_PROCESSED)

    o3 = onglet(nb, "Carte des résultats")
    o3.columnconfigure(0, weight=1)
    o3.rowconfigure(0, weight=1)

    bvc = boite(o3, "carte interactive")
    bvc.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ttk.Label(bvc, text="Carte des résultats calculés, mise à jour à chaque affichage.").pack(pady=(30, 5))
    btn_carte = bouton(bvc, "Afficher la carte", lambda: lancerCarte(),
                       aide="les gpkg affichés doivent partager les mêmes paramètres.")

    bouton(bvc, "Vider le cache", lambda: lancerViderCache(),
           aide="statistiques mises en cache ; à vider après une mise à jour de data/contours.")

    etat_carte = ttk.Label(bvc, text="")
    etat_carte.pack(pady=5)

    logs_carte = zoneLogs(bvc, hauteur=6)
    logs_carte.pack(fill="both", expand=True, pady=5)
    logs_carte.configure(state="disabled")

    def ecrireLogCarte(texte):
        logs_carte.configure(state="normal")
        logs_carte.insert("end", texte + "\n")
        logs_carte.see("end")
        logs_carte.configure(state="disabled")

    def viderLogsCarte():
        logs_carte.configure(state="normal")
        logs_carte.delete("1.0", "end")
        logs_carte.configure(state="disabled")

    def lancerViderCache():
        viderCache()
        etat_carte.configure(text="Cache vidé : tout sera recalculé au prochain affichage.")

    def lancerCarte():
        btn_carte.configure(state="disabled")
        etat_carte.configure(text="Préparation de la carte (jusqu'à 30 min pour toute la France).")
        viderLogsCarte()
        threading.Thread(target=travailCarte, daemon=True).start()

    def travailCarte():
        def onLog(msg):
            logs_carte.after(0, ecrireLogCarte, msg)
        try:
            chemin = genererCarte(on_log=onLog)
            multiprocessing.Process(target=ouvrirCarte, args=(chemin,), daemon=True).start()
            msg = "Carte ouverte."
        except Exception as e:
            msg = f"[ERREUR] {e}"
        etat_carte.after(0, lambda: (etat_carte.configure(text=msg),
                                     btn_carte.configure(state="normal")))

    o3b = onglet(nb, "Carte de traçage")
    o3b.columnconfigure(0, weight=1)
    o3b.rowconfigure(0, weight=1)

    btz = boite(o3b, "zone tracée à la main")
    btz.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ttk.Label(btz, justify="left", text=
              "Dessiner l'emprise plutôt que choisir un contour administratif.\n"
              "Une zone validée se lance depuis l'onglet principal, échelle « Zone tracée »."
              ).pack(pady=(25, 5))

    btn_dessin = bouton(btz, "Ouvrir la carte de traçage", lambda: lancerDessin(),
                        aide="taille annoncée avant validation. Un calcul interrompu reprend "
                             "aux dalles manquantes.")

    bouton(btz, "Vider le cache", lambda: lancerViderCacheDessin(),
           aide="cache des résultats, pour ne pas relire les gpkg à chaque affichage.")

    etat_dessin = ttk.Label(btz, text="", justify="left")
    etat_dessin.pack(pady=5)

    logs_dessin = zoneLogs(btz, hauteur=6)
    logs_dessin.pack(fill="both", expand=True, pady=5)
    logs_dessin.configure(state="disabled")

    def ecrireLogDessin(texte):
        logs_dessin.configure(state="normal")
        logs_dessin.insert("end", texte + "\n")
        logs_dessin.see("end")
        logs_dessin.configure(state="disabled")

    def lancerViderCacheDessin():
        viderCacheDessin()
        etat_dessin.configure(text="Cache vidé : la carte sera reconstruite au prochain affichage.")

    def lancerDessin():
        btn_dessin.configure(state="disabled")
        etat_dessin.configure(text="Préparation de la carte...")
        logs_dessin.configure(state="normal"); logs_dessin.delete("1.0", "end")
        logs_dessin.configure(state="disabled")
        threading.Thread(target=travailDessin, daemon=True).start()

    def travailDessin():
        def onLog(msg):
            logs_dessin.after(0, ecrireLogDessin, msg)
        try:
            chemin = genererCarteDessin(on_log=onLog)
            p = multiprocessing.Process(target=ouvrirCarteDessin, args=(chemin,), daemon=True)
            p.start()
            p.join()
            trace = lireTrace()
            if trace:
                gros = " — pensez à la découper" if trace["n_dalles"] >= SEUIL_GRAVE else ""
                msg = (f"Zone « {trace['nom']} » enregistrée : "
                       f"{trace['surface_km2']:.2f} km², {trace['n_dalles']} dalles{gros}.\n"
                       f"Choisissez l'échelle « Zone tracée » dans l'onglet principal.")
                logs_dessin.after(0, rebuild)
            else:
                msg = "Fenêtre fermée sans validation : aucune zone enregistrée."
        except Exception as e:
            msg = f"[ERREUR] {e}"
        etat_dessin.after(0, lambda: (etat_dessin.configure(text=msg),
                                      btn_dessin.configure(state="normal")))

    o4 = onglet(nb, "Info fichiers")
    o4.columnconfigure(0, weight=1, uniform="col")
    o4.columnconfigure(1, weight=1, uniform="col")
    o4.columnconfigure(2, weight=1, uniform="col")
    o4.rowconfigure(0, weight=1, uniform="row")
    o4.rowconfigure(1, weight=1, uniform="row")
    bad = boite(o4, "gpkg calculés")
    bad.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)

    bas = boite(o4, "statistiques")
    bas.grid(row=0, column=1, rowspan=2, columnspan=2, sticky="nsew", padx=10, pady=10)

    rafraichirIF = statsRapide(bad, config.OUT_DIR_PROCESSED, bas)

    o5 = onglet(nb, "À propos")
    o5.columnconfigure(0, weight=1)
    o5.rowconfigure(0, weight=1)

    bap = boite(o5, "à propos")
    bap.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    apropos = zoneLogs(bap, hauteur=25)
    apropos.pack(fill="both", expand=True)
    apropos.configure(font=("Consolas", 10))

    with open(os.path.join(config.BASE_DATA, "a_propos.md"), encoding="utf-8") as f:
        apropos.insert("1.0", f.read())
    apropos.configure(state="disabled")

    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    fen1.mainloop()
