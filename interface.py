import queue, threading, requests, multiprocessing
from tkinter import ttk
from executable.tool_item_exe import  champ, case, champ2, fenetre, boite, menu_coches, onglets, radioBoutons, onglet
from src import config



if __name__ == "__main__":
    multiprocessing.freeze_support()   
    fen1=fenetre("roofTool", 800, 500)
    q = queue.Queue()

    #======onglet 1======
    nb = onglets(fen1)
    nb.grid(row=0, column=0, sticky="nsew")

    #-------------parametres globaux-------------
    o1 = onglet(nb, "main")
    bne = boite(o1, "paramètres globaux")
    bne.grid(row=0, column=1, sticky="ne", padx=10, pady=10)

    surf_min   = champ(bne, "Surface min (m2)", config.SURF_MIN)
    haut_min   = champ(bne, "Hauteur min (m)", config.HAUT_MIN)
    haut_max   = champ(bne, "Hauteur max (m)", config.HAUT_MAX)
    az_min     = champ(bne, "Azimut min", config.AZ_MIN)
    az_max     = champ(bne, "Azimut max", config.AZ_MAX)
    pente_plat = champ(bne, "Pente plat (deg)", config.PENTE_PLAT)
    pente_max  = champ(bne, "Pente max (deg)", config.PENTE_MAX)

    const_leg   = case(bne, "Inclure constructions legeres", False)

    attrs       = menu_coches(bne, "Attributs BD TOPO",
                                config.ATTRS_BDTOPO,
                                ["nature", "usage_1", "nombre_d_etages"])

    etat = menu_coches (bne, "Etat", ["En service", "En construction", "En ruines", "Detruit"], "En service")
    nature = menu_coches(bne, "Natures gardees", config.NATURES,
                                ['Indifférenciée', 'Industriel, agricole ou commercial'])
    usage_1 = menu_coches(bne, "Usages gardees", config.USAGE_1,
                                ['Résidentiel', 'Commercial et services', 'Indifférencié', 'Industriel', 'Agricole'])

    sortie = menu_coches(bne, "Colonnes de sortie", list(config.GROUPES_SORTIE), list(config.GROUPES_SORTIE))


    #-------------choix zone-------------
    bnw = boite(o1, "choix de la zone")
    bnw.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
    
    champs = {}  

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

    zone = radioBoutons(bnw, "Echelle", config.ECHELLES, "Commune ou ville", on_change=rebuild)  # 3.
    sous = ttk.Frame(bnw); sous.pack(fill="x")    
    rebuild()

   



    #-------------lancement pipeline-------------
    


    #======onglet 2======
    o2 = onglet(nb, "Paramètres précis")
    bnw = boite(o2, "paramètres précis")
    bnw.grid(row=0, column=1, sticky="nw", padx=10, pady=10)


    n_essais_wfs   = champ2(bnw, "nombres d'essais wfs", config.N_ESSAIS_WFS)
    pause_wfs   = champ2(bnw, "Pause entre les essais (s)", config.PAUSE_WFS)
    n_coeurs    = champ2(bnw, "Nombre de coeurs (parallelisme)", config.N_COEURS)
    n_threads   = champ2(bnw, "Nombre de threads (requetes WFS)", config.N_THREADS)
    count       = champ2(bnw, "Taille des paquets WFS (count)", config.COUNT)
    n_essais    = champ2(bnw, "Nombre d'essais telechargement dalles", config.N_ESSAIS)
    pause_dl    = champ2(bnw, "Pause entre essais telechargement (s)", config.PAUSE_DL)

    buffer      = champ2(bnw, "Tampon autour des batiments (m)", config.BUFFER)
    mnh_min     = champ2(bnw, "Hauteur min au-dessus du sol (m)", config.MNH_MIN)

    n_directions = champ2(bnw, "Nombre de directions azimutales", config.N_DIRECTIONS)
    dist_max_m   = champ2(bnw, "Rayon de recherche d'ombrage (m)", config.DIST_MAX_M)
    cap          = champ2(bnw, "Plafond solaire (deg)", config.CAP)
    
    rendement_module   = champ2(bnw, "Rendement du module PV", config.RENDEMENT_MODULE)
    performance_ratio  = champ2(bnw, "Performance ratio (pertes systeme)", config.PERFORMANCE_RATIO)
    taux_couverture    = champ2(bnw, "Taux de couverture du toit", config.TAUX_COUVERTURE)



    #======onglet 3======
    o3 = onglet(nb, "Visualisation sur carte")
    bne = boite(o3, "visualisation sur carte")
    surf_min   = champ(bne, "Surface min (m2)", 5)
    haut_min   = champ(bne, "Hauteur min (m)", 2)
    

    #======onglet 2======
    o4 = onglet(nb, "À propos")
    bne = boite(o4, "à propos")
    bne.grid(row=0, column=1, sticky="ne", padx=10, pady=10)
    surf_min   = champ(bne, "Surface min (m2)", 5)
    haut_min   = champ(bne, "Hauteur min (m)", 2)


    fen1.mainloop()                  


    