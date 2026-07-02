import queue, threading, requests, multiprocessing
from tkinter import ttk
from executable.tool_item_exe import (champ, case, champ2, fenetre, boite, menu_coches,
                                       onglets, radioBoutons, onglet,
                                       barre_progression, zone_logs)
from src import config
from src.pipeline import runPipeline
from executable.tool_fct_exe import afficherBilan


if __name__ == "__main__":
    multiprocessing.freeze_support()   
    fen1=fenetre("roofTool", 1000, 500)
    q = queue.Queue()

    #======onglet 1======
    nb = onglets(fen1)
    nb.grid(row=0, column=0, sticky="nsew")

    #-------------parametres globaux-------------
    o1 = onglet(nb, "main")
    o1.columnconfigure(0, weight=1)
    o1.columnconfigure(1, weight=1)
    o1.rowconfigure(0, weight=1)

    bpg = boite(o1, "paramètres globaux") #boite paramatres globaux
    bpg.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    surf_min   = champ(bpg, "Surface min (m2)", config.SURF_MIN)
    haut_min   = champ(bpg, "Hauteur min (m)", config.HAUT_MIN)
    haut_max   = champ(bpg, "Hauteur max (m)", config.HAUT_MAX)
    az_min     = champ(bpg, "Azimut min", config.AZ_MIN)
    az_max     = champ(bpg, "Azimut max", config.AZ_MAX)
    pente_plat = champ(bpg, "Pente plat (deg)", config.PENTE_PLAT)
    pente_max  = champ(bpg, "Pente max (deg)", config.PENTE_MAX)

    const_leg   = case(bpg, "Inclure constructions legeres", False)

    attrs       = menu_coches(bpg, "Attributs BD TOPO",
                                config.ATTRS_BDTOPO,
                                ["nature", "usage_1", "nombre_d_etages"])

    etat = menu_coches (bpg, "Etat", ["En service", "En construction", "En ruines", "Detruit"], "En service")
    nature = menu_coches(bpg, "Natures gardees", config.NATURES,
                                ['Indifférenciée', 'Industriel, agricole ou commercial'])
    usage_1 = menu_coches(bpg, "Usages gardees", config.USAGE_1,
                                ['Résidentiel', 'Commercial et services', 'Indifférencié', 'Industriel', 'Agricole'])

    sortie = menu_coches(bpg, "Colonnes de sortie", list(config.GROUPES_SORTIE), list(config.GROUPES_SORTIE))


    #-------------choix zone-------------
    cg = ttk.Frame(o1) #colonne gauche
    cg.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    bcz = boite(cg, "choix de la zone") #boite choix zone
    bcz.pack(fill="x")
    
    champs = {}  


    #on récupère les champs de sortie suivant le choix de l'utilisateur 

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
                    r = requests.get("https://api-adresse.data.gouv.fr/search/",
                                    params={"q": txt, "limit": 10}, 
                                    timeout=2).json()
                    
                    champ_zone["values"] = [f["properties"]["label"] for f in r.get("features", [])]
                except:
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
                except:
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
                except:
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

                except:
                    pass

            def premier(event=None):
                vals = champ_zone["values"]
                if vals:
                    champ_zone.set(vals[0])

            champ_zone.bind("<KeyRelease>", suggestion)
            champ_zone.bind("<Return>", premier)
            champs["zone"] = champ_zone

    zone = radioBoutons(bcz, "Echelle", config.ECHELLES, "Commune ou ville", on_change=rebuild)  # 3.
    sous = ttk.Frame(bcz); sous.pack(fill="x")    
    rebuild()

   

    #-------------lancement pipeline-------------
    #on lit les widgets de reglage pour créer un dict qui servira à config
    def recolte():
        entiers = {
            "SURF_MIN": surf_min, "HAUT_MIN": haut_min, "HAUT_MAX": haut_max,
            "AZ_MIN": az_min, "AZ_MAX": az_max, "PENTE_PLAT": pente_plat, "PENTE_MAX": pente_max,
            "N_ESSAIS_WFS": n_essais_wfs, "PAUSE_WFS": pause_wfs, "N_COEURS": n_coeurs,
            "N_THREADS": n_threads, "COUNT": count, "N_ESSAIS": n_essais, "PAUSE_DL": pause_dl,
            "N_DIRECTIONS": n_directions, "DIST_MAX_M": dist_max_m,
        }
        flottants = {
            "BUFFER": buffer, "MNH_MIN": mnh_min, "CAP": cap,
            "RENDEMENT_MODULE": rendement_module, "PERFORMANCE_RATIO": performance_ratio,
            "TAUX_COUVERTURE": taux_couverture,
        }
        cases = {"CONSTRUCTION_LEGERE": const_leg}
        menus = {
            "ATTRS_BATI": attrs, "NATURE_OK": nature,
            "USAGE_OK": usage_1, "SORTIE_GARDEES": sortie, "ETAT": etat,
        }

        reglages = {nom: int(w.get()) for nom, w in entiers.items()}
        reglages.update({nom: float(w.get()) for nom, w in flottants.items()})
        reglages.update({nom: var.get() for nom, var in cases.items()})
        reglages.update({nom: [o for o, v in d.items() if v.get()] for nom, d in menus.items()})
        return reglages

    #on lit l'echelle et le champs de zone choisi par l'utilisateur pour renvoyer (echelle, nom_zone, code_dep)
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


    bl = boite(cg, "lancement") #boite lancement
    bl.pack(fill="both", expand=True, pady=(10, 0))

    btn_lancer = ttk.Button(bl, text="Lancer", command=lambda: lancer())
    btn_lancer.pack(anchor="w", pady=5)

    barre = barre_progression(bl)
    barre.pack(fill="x", pady=5)

    logs = zone_logs(bl, hauteur=8)
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
        def on_log(msg):
            q.put(("log", msg))

        def on_progress(i, total):
            q.put(("progress", i, total))

        try:
            bilan = runPipeline(echelle, nom_zone, code_dep, on_progress=on_progress, on_log=on_log)
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

                elif item[0] == "error":
                    btn_lancer.configure(state="normal")
                    barre["value"] = 0
                    ecrireLog(f"[ERREUR] {item[1]}\n")

        except queue.Empty:
            pass

        fen1.after(100, verifierQueue)

    verifierQueue()



    #======onglet 2======
    o2 = onglet(nb, "Paramètres précis")
    o2.columnconfigure(0, weight=1)
    o2.columnconfigure(1, weight=1)
    o2.rowconfigure(0, weight=1)
    bpp = boite(o2, "paramètres précis") #boite parametre precis
    bpp.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)


    n_essais_wfs   = champ2(bpp, "nombres d'essais wfs", config.N_ESSAIS_WFS)
    pause_wfs   = champ2(bpp, "Pause entre les essais (s)", config.PAUSE_WFS)
    n_coeurs    = champ2(bpp, "Nombre de coeurs (parallelisme)", config.N_COEURS)
    n_threads   = champ2(bpp, "Nombre de threads (requetes WFS)", config.N_THREADS)
    count       = champ2(bpp, "Taille des paquets WFS (count)", config.COUNT)
    n_essais    = champ2(bpp, "Nombre d'essais telechargement dalles", config.N_ESSAIS)
    pause_dl    = champ2(bpp, "Pause entre essais telechargement (s)", config.PAUSE_DL)

    buffer      = champ2(bpp, "Tampon autour des batiments (m)", config.BUFFER)
    mnh_min     = champ2(bpp, "Hauteur min au-dessus du sol (m)", config.MNH_MIN)

    n_directions = champ2(bpp, "Nombre de directions azimutales", config.N_DIRECTIONS)
    dist_max_m   = champ2(bpp, "Rayon de recherche d'ombrage (m)", config.DIST_MAX_M)
    cap          = champ2(bpp, "Plafond solaire (deg)", config.CAP)

    rendement_module   = champ2(bpp, "Rendement du module PV", config.RENDEMENT_MODULE)
    performance_ratio  = champ2(bpp, "Performance ratio (pertes systeme)", config.PERFORMANCE_RATIO)
    taux_couverture    = champ2(bpp, "Taux de couverture du toit", config.TAUX_COUVERTURE)



    #======onglet 3======
    o3 = onglet(nb, "Visualisation sur carte")
 
    
    #======onglet 5======
    o5 = onglet(nb, "Statistiques rapides")



    #======onglet 4======
    o4 = onglet(nb, "À propos")
    bne = boite(o4, "à propos")
    bne.grid(row=0, column=1, sticky="ne", padx=10, pady=10)


    
   


    fen1.mainloop()                  


    