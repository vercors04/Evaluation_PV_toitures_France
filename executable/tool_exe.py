import tkinter as tk
from tkinter import ttk, scrolledtext
import math

ATTRS_BDTOPO = ['nature', 'usage_1', 'usage_2', 'construction_legere',       
    'etat_de_l_objet', 'nombre_de_logements', 'nombre_d_etages',           
    'materiaux_des_murs', 'materiaux_de_la_toiture', 'hauteur',                   
    'altitude_minimale_sol', 'altitude_minimale_toit', 'altitude_maximale_sol',
    'altitude_maximale_toit', 'date_creation', 'date_modification',
]

NATURES = ['Indifférenciée', 'Industriel, agricole ou commercial',
           'Religieux', 'Sportif', 'Château', 'Serre', 'Silo']  

USAGE_1 = ['Agricole', 'Annexe', 'Commercial et services', 
           'Indifférencié', 'Industriel', 'Religieux', 
           'Résidentiel', 'Sportif']

ECHELLES = ['Adresse', 'Commune ou ville', 'Departement', 'Region', 'France']

SECTEURS          = ["N","NE","E","SE","S","SO","O","NO"]          
GROUPES_SORTIE = {
    "hauteur":         ["hauteur_pts"],
    "nb_pixels":        ["nb_pixels"],
    "surf_tot_m2":      ["surf_tot_m2"],
    "surf_plate_m2":    ["surf_plate_m2"],
    "surf_incl_m2":     ["surf_incl_m2"],
    "surf_incl_or_m2":  ["surf_incl_or_m2"],
    "pente_moy_incl":   ["pente_moy_incl"],
    "surfaces_orient": [f"surf_incl_{s}_m2" for s in SECTEURS],
    "irr_an_kwh":      ["irr_an_kwh"],
    "prod_an_kwh":      ["prod_an_kwh"],
    "irr_an_kwh_orp":   ["irr_an_kwh_orp"],
    "puissance_kwc_orp": ["puissance_kwc_orp"],
    "prod_an_kwh_orp":  ["prod_an_kwh_orp"],
    "production_trim": [f"prod_T{t}_kwh_orp" for t in range(1, 5)],
}
    




def fenetre(titre="", largeur=600, hauteur=400):
    """
    Cree la fenetre principale.
    --------
    @param[in] titre   : titre affiche en haut de la fenetre
    @param[in] largeur : largeur en pixels
    @param[in] hauteur : hauteur en pixels

    @return Tk : la fenetre (a configurer puis a lancer avec .mainloop())
    """
    fen = tk.Tk()
    fen.title(titre)
    fen.geometry(f"{largeur}x{hauteur}")
    fen.columnconfigure(0, weight=1) 
    fen.rowconfigure(0, weight=1)   
    return fen


def boite(parent, titre):
    """
    Cree une boite (cadre avec titre) pour regrouper des widgets.
    --------
    @param[in] parent : la fenetre (ou une autre boite) ou la mettre
    @param[in] titre  : texte affiche en haut de la boite

    @return LabelFrame : a placer avec .grid(...), et a remplir avec des champs
    """
    return ttk.LabelFrame(parent, text=titre)


def bouton(parent, texte, action):
    """
    Cree un bouton qui lance une fonction au clic.
    --------
    @param[in] parent : conteneur
    @param[in] texte  : texte affiche sur le bouton
    @param[in] action : fonction appelee au clic (sans argument)

    @return Button : a placer avec .grid(...)
    """
    return ttk.Button(parent, text=texte, command=action)


def barre_progression(parent):
    """
    Cree une barre de progression (0 a 100).
    --------
    @param[in] parent : conteneur

    @return Progressbar : a placer avec .grid(...) ; mettre a jour avec  barre["value"] = 0..100
    """
    return ttk.Progressbar(parent, maximum=100)


def zone_logs(parent, hauteur=10):
    """
    Cree une zone de texte deroulante pour afficher des messages.
    --------
    @param[in] parent  : conteneur
    @param[in] hauteur : nombre de lignes visibles

    @return ScrolledText : a placer avec .grid(...) ;
                           ajouter une ligne avec  .insert("end", txt + "\\n")  puis  .see("end")
    """
    return scrolledtext.ScrolledText(parent, height=hauteur)



def champ(parent, libelle, defaut):
    """
    Une ligne 'libelle : [case texte]', rangee automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger ce champ
    @param[in] libelle : texte a gauche
    @param[in] defaut  : valeur pre-remplie

    @return Entry : lire avec .get() (renvoie du texte, a convertir en int/float)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=18).pack(side="left")
    e = ttk.Entry(ligne); e.insert(0, str(defaut)); e.pack(side="left", fill="x", expand=True)
    return e


def case(parent, libelle, defaut):
    """
    Une case a cocher (oui/non), rangee automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger la case
    @param[in] libelle : texte a cote de la case
    @param[in] defaut  : True/False coche au depart

    @return BooleanVar : lire avec .get() -> True/False
    """
    var = tk.BooleanVar(value=defaut)
    ttk.Checkbutton(parent, text=libelle, variable=var).pack(anchor="w", pady=2)
    return var


def menu(parent, libelle, options, defaut):
    """
    Un menu deroulant (un seul choix), range automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger le menu
    @param[in] libelle : texte a gauche
    @param[in] options : liste des choix possibles
    @param[in] defaut  : choix affiche au depart

    @return Combobox : lire avec .get()
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=18).pack(side="left")
    combo = ttk.Combobox(ligne, values=options, state="readonly"); combo.set(defaut)
    combo.pack(side="left", fill="x", expand=True)
    return combo




def menu_coches(parent, libelle, options, defaut):
    """
    Un bouton qui ouvre un panneau de cases a cocher (compact, une seule fenetre a la fois).
    Au-dela de 5 options, elles sont reparties en colonnes cote a cote.
    --------
    @param[in] parent  : la boite ou ranger
    @param[in] libelle : texte a gauche
    @param[in] options : liste des choix possibles
    @param[in] defaut  : liste des choix coches au depart

    @return dict {option: BooleanVar} : lire avec  [o for o, v in d.items() if v.get()]
    """
    variables = {opt: tk.BooleanVar(value=(opt in defaut)) for opt in options}

    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=18).pack(side="left")
    btn = ttk.Button(ligne); btn.pack(side="left")
    etat = {"pop": None}                              

    def maj_texte():
        n = sum(v.get() for v in variables.values())
        btn.configure(text=f"{n} sélectionné(s)  ▾")

    def ouvrir():
        if etat["pop"] is not None and etat["pop"].winfo_exists():
            etat["pop"].lift()
            return

        pop = tk.Toplevel(btn); etat["pop"] = pop
        pop.title(libelle)
        pop.transient(btn.winfo_toplevel())
        pop.geometry(f"+{btn.winfo_rootx()}+{btn.winfo_rooty() + btn.winfo_height()}")

        opts    = list(variables.items())
        ncols   = math.ceil(len(opts) / 5)             
        par_col = math.ceil(len(opts) / ncols)        
        for idx, (opt, v) in enumerate(opts):
            ttk.Checkbutton(pop, text=opt, variable=v, command=maj_texte).grid(
                row=idx % par_col, column=idx // par_col, sticky="w", padx=10, pady=2)

        ttk.Button(pop, text="OK", command=pop.destroy).grid(
            row=par_col, column=0, columnspan=ncols, pady=6)

    btn.configure(command=ouvrir)
    maj_texte()
    return variables