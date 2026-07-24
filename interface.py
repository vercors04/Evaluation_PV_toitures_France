import os
import queue, threading, requests, multiprocessing
from tkinter import ttk, messagebox
from executable.tool_item_exe import (boiteDefilante, champ, case, champ2, fenetre, boite, menuCoches,
                                       onglets, radioBoutons, onglet, listeDeroulante,
                                       barreProgression, zoneLogs, bouton, bulleAide)
from src import config
from src.pipeline import runPipeline, runPipelineDecoupe
from executable.tool_fct_exe import afficherBilan, listesFichiers, statsRapide
from executable.carte_interactive import genererCarte, ouvrirCarte, viderCache

if __name__ == "__main__":
    multiprocessing.freeze_support()

    os.makedirs(config.DIR_GEOJSON, exist_ok=True)
    os.makedirs(config.OUT_DIR_PROCESSED, exist_ok=True)
    os.makedirs(config.OUT_DIR_RAW, exist_ok=True)

    fen1=fenetre("roofTool", 1000, 500)
    fen1.iconbitmap(os.path.join(config.BASE_DATA, "data/assets", "logo_soleil.ico"))

    q = queue.Queue()

    #======onglet 1======
    nb = onglets(fen1)
    nb.grid(row=0, column=0, sticky="nsew")

    #-------------parametres globaux-------------
    o1 = onglet(nb, "main")
    o1.columnconfigure(0, weight=1)
    o1.columnconfigure(1, weight=1)
    o1.rowconfigure(0, weight=1)

    bpg = boite(o1, "paramètres globaux") # boite parametres globaux
    bpg.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    surf_min   = champ(bpg, "Surface min (m2)", config.SURF_MIN)
    haut_min   = champ(bpg, "Hauteur min (m)", config.HAUT_MIN, aide = "hauteur minimale du point le plus haut du toit")
    haut_max   = champ(bpg, "Hauteur max (m)", config.HAUT_MAX, aide="hauteur maximale du point le plus haut du toit")
    az_min     = champ(bpg, "Azimut min", config.AZ_MIN, aide= "degrés, 0=Nord, 90=Est")
    az_max     = champ(bpg, "Azimut max", config.AZ_MAX, aide="degrés, 0=Nord, 90=Est")
    pente_plat = champ(bpg, "Pente plat (deg)", config.PENTE_PLAT, aide="seuil de la pente du toit pour le considérer comme plat")
    pente_max  = champ(bpg, "Pente max (deg)", config.PENTE_MAX, aide="pente maximale du toit, max 70")
    seuil_irradiance = champ(bpg, "Seuil irradiance", config.SEUIL_IRRADIANCE, aide="kWh/m2/an — un pixel compte dans les sorties « seuil » si son irradiance reçue par m2 (ombrage compris) dépasse cette valeur")

    const_leg   = case(bpg, "Inclure constructions legeres", False)

    attrs       = menuCoches(bpg, "Attributs BD TOPO",
                                config.ATTRS_BDTOPO,
                                ["nature", "usage_1", "nombre_d_etages"], aide="attributs de la BD TOPO. Les colonnes sont souvent partiellement vide et/ou avec des données éronées. Il est conseillé de ne pas inclure les colonnes 'hauteur' et 'nombre_d_etages' dans le filtrage des toits, mais de les utiliser uniquement pour l'analyse des toits retenus.")

    etat = menuCoches(bpg, "Etat", config.ETATS, config.ETAT)
    nature = menuCoches(bpg, "Natures gardees", config.NATURES,
                               config.NATURE_OK)
    usage_1 = menuCoches(bpg, "Usages gardees", config.USAGE_1,
                                config.USAGE_OK, aide = "beaucoup de batiments sont notés comme indifférenciés, bien qu'ils puissent être d'un usage particulier.")

    sortie = menuCoches(bpg, "Colonnes de sortie", list(config.GROUPES_SORTIE), config.SORTIE_GARDEES, aide="colonnes gardées. Dans tout les cas les valeurs sont calculées, certaines peuvent être juste supprimées de la sortie finale.")


    #-------------choix zone-------------
    cg = ttk.Frame(o1) #colonne gauche
    cg.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    bcz = boite(cg, "choix de la zone") #boite choix zone
    bcz.pack(fill="x")
    
    champs = {}  


    #on reconstruit les champs de saisie de la zone selon l'echelle choisie

    def rebuild():                                  
        for w in sous.winfo_children():             
            w.destroy()
        champs.clear()
        choix = zone.get()

        if choix == "Adresse":
            ttk.Label(sous, text=choix).pack(anchor="w", pady=5)
            champ_zone = ttk.Combobox(sous, width=50) 
            champ_zone.pack(anchor="w", pady=5)
            
            def suggestion(event=None):
                txt = champ_zone.get()
                if len(txt) < 3:                    
                    return
                
                try:
                    r = requests.get("https://data.geopf.fr/geocodage/search",
                    params={"q": txt, "limit": 10},
                    timeout=2).json()
                    
                    champ_zone["values"] = [f["properties"]["label"] for f in r.get("features", [])]
                except requests.RequestException:
                    pass

            def premier(event=None):
                vals = champ_zone["values"]
                if vals:
                    champ_zone.set(vals[0])

            champ_zone.bind("<KeyRelease>", suggestion)
            champ_zone.bind("<Return>", premier)
            champs["zone"] = champ_zone


        elif choix == "Commune ou ville":
            ttk.Label(sous, text=choix).pack(anchor="w", pady=5)
            champ_zone = ttk.Combobox(sous, width=30)
            champ_zone.pack(anchor="w", pady=5)
            def suggestion(event=None):
                txt = champ_zone.get()
                if len(txt) < 3:                     
                    return
                
                try:
                    r = requests.get("https://geo.api.gouv.fr/communes",
                                    params={"nom": txt, "limit": 10, "fields": "nom,codeDepartement"}).json()
                    champ_zone["values"] = [f'{c["nom"]} ({c["codeDepartement"]})' for c in r]
                except requests.RequestException:
                    pass

            def premier(event=None):
                vals = champ_zone["values"]
                if vals:
                    champ_zone.set(vals[0])

            champ_zone.bind("<KeyRelease>", suggestion)
            champ_zone.bind("<Return>", premier)
            champs["zone"] = champ_zone



        elif choix == "Département":
            ttk.Label(sous, text=choix).pack(anchor="w", pady=5)
            champ_zone = ttk.Combobox(sous, width=30)
            champ_zone.pack(anchor="w", pady=5)

            def suggestion(event=None):
                txt = champ_zone.get()
                if len(txt) < 2: 
                    champ_zone["values"] = []
                    return
                
                url = "https://geo.api.gouv.fr/departements"
                try :
                    r = requests.get(url, params={"nom": txt, "limit": 10}).json()
                    champ_zone["values"] = [f'{c["nom"]} ({c["code"]})' for c in r]
                except requests.RequestException:
                    pass

            def premier(event=None):
                vals = champ_zone["values"]
                if vals:
                    champ_zone.set(vals[0])

            champ_zone.bind("<KeyRelease>", suggestion)
            champ_zone.bind("<Return>", premier)
            champs["zone"] = champ_zone



        elif choix == "Région":
            ttk.Label(sous, text=choix).pack(anchor="w", pady=5)
            champ_zone = ttk.Combobox(sous, width=30)
            champ_zone.pack(anchor="w", pady=5)

            def suggestion(event=None):
                txt = champ_zone.get()
                if len(txt) < 2: 
                    champ_zone["values"] = []
                    return
                
                url = "https://geo.api.gouv.fr/regions"
                
                try :
                    r = requests.get(url, params={"nom": txt, "limit": 10}).json()
                    champ_zone["values"] = [f'{c["nom"]}' for c in r]

                except requests.RequestException:
                    pass

            def premier(event=None):
                vals = champ_zone["values"]
                if vals:
                    champ_zone.set(vals[0])

            champ_zone.bind("<KeyRelease>", suggestion)
            champ_zone.bind("<Return>", premier)
            champs["zone"] = champ_zone

    zone = radioBoutons(bcz, "Echelle", config.ECHELLES, "Commune ou ville", on_change=rebuild,
                        aide="Région et France : calcul departement par departement (un fichier par "
                             "departement). Ne refait pas les departements déjà fait, " 
                             "il faut les supprimer manuellement pour les refaire.")
    sous = ttk.Frame(bcz); sous.pack(fill="x")    
    rebuild()

   

    #-------------lancement pipeline-------------
    def recolte():
        reglages = {nom: int(w.get())   for nom, w in {**w_entiers, **w_listes}.items()}
        reglages.update({nom: float(w.get()) for nom, w in w_flottants.items()})
        reglages.update({nom: var.get()      for nom, var in w_cases.items()})
        reglages.update({nom: [o for o, v in d.items() if v.get()] for nom, d in w_menus.items()})
        return reglages

    # on lit l'echelle et le champ de zone choisis pour renvoyer (echelle, nom_zone, code_dep)
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
            nom, code = texte.rsplit("(", 1)
            return "departement", nom.strip(), None
        
        raise ValueError(f"Problème echelle pas connue : {choix}") # garde-fou, echelle inconnue


    bl = boite(cg, "lancement") #boite lancement
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
            if echelle in ("nationale", "region"):  # condition a supprimer si region/france se calculent en un seul run
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



    #======onglet 2======
    o2 = onglet(nb, "Paramètres avancés")
    o2.columnconfigure(0, weight=1)
    o2.columnconfigure(1, weight=1)
    o2.rowconfigure(0, weight=1)
    bpa_ext, bpa = boiteDefilante(o2, "paramètres avancés") # boite parametres precis
    bpa_ext.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)


    n_essais_wfs   = champ2(bpa, "nombres d'essais wfs", config.N_ESSAIS_WFS, aide = "nombres d'essais pour la requête WFS si elle échoue")
    pause_wfs   = champ2(bpa, "Pause entre les essais (s)", config.PAUSE_WFS, aide = "pause entre les essais pour la requête WFS")
    n_coeurs    = champ2(bpa, "Nombre de coeurs (parallelisme)", config.N_COEURS, aide = "nombre de coeurs à utiliser pour le parallélisme")
    n_threads   = champ2(bpa, "Nombre de threads (requetes WFS)", config.N_THREADS, aide = "nombre de threads pour les requêtes WFS")
    count       = champ2(bpa, "Taille des paquets WFS (count)", config.COUNT, aide = "nombre de batiment récupéré par requête WFS")
    n_essais    = champ2(bpa, "Nombre d'essais telechargement dalles", config.N_ESSAIS, aide = "nombre d'essais pour le téléchargement des dalles si elles échouent")
    pause_dl    = champ2(bpa, "Pause entre essais telechargement dalles (s)", config.PAUSE_DL, aide = "pause entre les essais pour le téléchargement des dalles")
    n_essais_dep  = champ2(bpa, "Nombre d'essais telechargement departement", config.N_ESSAIS_DEPARTEMENT, aide = "nombre d'essais pour le traitement des départements si ça échouent")
    pause_dep    = champ2(bpa, "Pause entre essais telechargement departement (s)", config.PAUSE_DEPARTEMENT, aide = "pause entre les essais pour les départements")

    buffer      = champ2(bpa, "Tampon autour des batiments (m)", config.BUFFER, aide = "marge autour des emprises BD TOPO pour capturer tout les pixels de toit")
    mnh_min     = champ2(bpa, "Hauteur min au-dessus du sol (m)", config.MNH_MIN, aide = "hauteur minimale au dessus du sol pour qu'un pixel soit considéré comme faisant partit du toit")

    n_directions = listeDeroulante(bpa, "Nombre de directions azimutales", config.DIVISEURS_360, config.N_DIRECTIONS, aide = "nombre de directions azimutales pour le calcul de l'ombrage")
    dist_max_m   = champ2(bpa, "Rayon de recherche d'ombrage (m)", config.DIST_MAX_M, aide = "distance maximale pour le calcul de l'ombrage. Les batiments plus loin ne sont pas considérés comme ombrageant le toit.")
    cap          = champ2(bpa, "Plafond solaire (deg)", config.CAP, aide = "angle a partir duquel un obstacle est ignoré car trop haut pour bloquer le soleil")

    rendement_module   = champ2(bpa, "Rendement du module PV", config.RENDEMENT_MODULE)
    performance_ratio  = champ2(bpa, "Performance ratio (pertes systeme)", config.PERFORMANCE_RATIO)
    taux_couverture    = champ2(bpa, "Taux de couverture du toit", config.TAUX_COUVERTURE)
    albedo = champ2(bpa, "Albédo (réflectivité du sol)", config.ALBEDO)


    w_entiers = {
        "SURF_MIN": surf_min, "HAUT_MIN": haut_min, "HAUT_MAX": haut_max,
        "AZ_MIN": az_min, "AZ_MAX": az_max, "PENTE_PLAT": pente_plat, "PENTE_MAX": pente_max,
        "N_ESSAIS_WFS": n_essais_wfs, "N_COEURS": n_coeurs, "N_THREADS": n_threads,
        "COUNT": count, "N_ESSAIS": n_essais, "DIST_MAX_M": dist_max_m,
        "N_ESSAIS_DEPARTEMENT": n_essais_dep,
    }
    w_flottants = {
        "BUFFER": buffer, "MNH_MIN": mnh_min, "CAP": cap, "PAUSE_WFS": pause_wfs, "PAUSE_DL": pause_dl,
        "RENDEMENT_MODULE": rendement_module, "PERFORMANCE_RATIO": performance_ratio,
        "TAUX_COUVERTURE": taux_couverture, "ALBEDO": albedo, "PAUSE_DEPARTEMENT": pause_dep,
        "SEUIL_IRRADIANCE": seuil_irradiance,
    }
    w_listes = {"N_DIRECTIONS": n_directions}
    w_cases  = {"CONSTRUCTION_LEGERE": const_leg}
    w_menus  = {"ATTRS_BATI": attrs, "NATURE_OK": nature, "USAGE_OK": usage_1,
                "SORTIE_GARDEES": sortie, "ETAT": etat}

    def reinitialiser():
        for nom, w in {**w_entiers, **w_flottants}.items():
            w.delete(0, "end"); w.insert(0, str(config.DEFAULTS[nom]))
        for nom, w in w_listes.items():
            w.set(config.DEFAULTS[nom])
        for nom, var in w_cases.items():
            var.set(config.DEFAULTS[nom])
        for nom, d in w_menus.items():
            for opt, var in d.items():
                var.set(opt in config.DEFAULTS[nom])

    def enregistrer():
        try:
            reglages = recolte()
        except ValueError as e:
            messagebox.showerror("Paramètres", f"Valeur invalide dans un champ : {e}")
            return
        config.save(reglages)
        messagebox.showinfo("Paramètres", "Paramètres enregistrés dans settings.json.")

    ligne_btns = ttk.Frame(bpa); ligne_btns.pack(pady=8)
    ttk.Button(ligne_btns, text="Réinitialiser les paramètres par défaut",
               command=lambda: reinitialiser()).pack(side="left", padx=3)
    
    ttk.Button(ligne_btns, text="Enregistrer les paramètres",
               command=lambda: enregistrer()).pack(side="left", padx=3)
    bulleAide(ligne_btns, "Valider les réglages si ils sont modifiés sans lancer aucune tache par la suite")

    bfg = boite(o2, "fichiers générés")  # boite fichiers generes
    bfg.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    rafraichirPA = listesFichiers(bfg, config.DIR_GEOJSON, config.OUT_DIR_PROCESSED)

    #======onglet 3======
    o3 = onglet(nb, "Visualisation sur carte")
    o3.columnconfigure(0, weight=1)
    o3.rowconfigure(0, weight=1)

    bvc = boite(o3, "carte interactive")  # boite visualisation carte
    bvc.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    ttk.Label(bvc, text="Génère la carte à partir des résultats calculés puis l'ouvre dans une fenêtre dédiée.\n"
                        "Recliquer après un nouveau calcul pour la mettre à jour.").pack(pady=(30, 5))
    btn_carte = bouton(bvc, "Afficher la carte", lambda: lancerCarte(), 
                       aide = "assurez vous que les gpkg calculés utilisent les mêmes "
                                      "paramètres (azimut min/max, ...)")

    bouton(bvc, "Vider le cache", lambda: lancerViderCache(),
           aide="Les statistiques de la carte sont mises en cache pour ne pas relire "
                "les gpkg à chaque affichage. À vider uniquement si les contours "
                "(data/contours) ont été mis à jour (ou pour libérer du stockage)")

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
        etat_carte.configure(text="Préparation de la carte en cours, peut durer jusqu'à 20-30mn pour la France metropolitaine entière")
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


    #======onglet 4======
    o4 = onglet(nb, "Info fichiers")
    o4.columnconfigure(0, weight=1, uniform="col")
    o4.columnconfigure(1, weight=1, uniform="col")
    o4.columnconfigure(2, weight=1, uniform="col")
    o4.rowconfigure(0, weight=1, uniform="row")
    o4.rowconfigure(1, weight=1, uniform="row")
    bad = boite(o4, "gpkg calculés") #boite affichage dossier
    bad.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)

    bas = boite(o4, "statistiques") #boite affichage statistiques
    bas.grid(row=0, column=1, rowspan=2, columnspan=2, sticky="nsew", padx=10, pady=10)


    
    rafraichirIF = statsRapide (bad, config.OUT_DIR_PROCESSED, bas)


    #======onglet 5======
    o5 = onglet(nb, "À propos")
    o5.columnconfigure(0, weight=1)
    o5.rowconfigure(0, weight=1)

    bap = boite(o5, "à propos")  # boite a propos
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


    