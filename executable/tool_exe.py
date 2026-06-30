import tkinter as tk
from tkinter import ttk, scrolledtext


NATURES = ['Indifférenciée', 'Industriel, agricole ou commercial',
           'Religieux', 'Sportif', 'Château', 'Serre', 'Silo']  

USAGE_1 = ['Agricole', 'Annexe', 'Commercial et services', 
           'Indifférencié', 'Industriel', 'Religieux', 
           'Résidentiel', 'Sportif']

ECHELLES = ['Adresse', 'Commune ou ville', 'Departement', 'Region', 'France']

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
    Un bouton qui ouvre un panneau de cases a cocher (compact). Le bouton affiche le nombre coche.
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

    def maj_texte():                                   # met a jour le compteur sur le bouton
        n = sum(v.get() for v in variables.values())
        btn.configure(text=f"{n} sélectionné(s)  ▾")

    def ouvrir():                                      # ouvre le panneau au clic
        pop = tk.Toplevel(btn)
        pop.title(libelle)
        pop.transient(btn.winfo_toplevel())            # reste au-dessus de la fenetre
        pop.geometry(f"+{btn.winfo_rootx()}+{btn.winfo_rooty() + btn.winfo_height()}")  # juste sous le bouton
        for opt, v in variables.items():
            ttk.Checkbutton(pop, text=opt, variable=v, command=maj_texte).pack(anchor="w", padx=10, pady=2)
        ttk.Button(pop, text="OK", command=pop.destroy).pack(pady=6)

    btn.configure(command=ouvrir)
    maj_texte()                                        # affiche le compte de depart
    return variables