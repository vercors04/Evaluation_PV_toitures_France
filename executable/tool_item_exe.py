import tkinter as tk
from tkinter import ttk, scrolledtext
import math


def onglets(parent):
    """Cree un bloc a onglets (Notebook), a placer avec .pack/.grid."""
    return ttk.Notebook(parent)

def onglet(notebook, titre):
    """Cree un onglet (Frame) et l'ajoute au notebook."""
    f = ttk.Frame(notebook)
    notebook.add(f, text=titre)
    return f


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

def radioBoutons(parent, libelle, options, defaut, on_change=None):
    """
    Un groupe de boutons radio (un seul choix a la fois).
    --------
    @param[in] parent    : conteneur ou ranger le groupe
    @param[in] libelle   : titre affiche au-dessus
    @param[in] options   : liste des choix
    @param[in] defaut    : choix selectionne au depart
    @param[in] on_change : fonction appelee a chaque changement de choix (optionnel)

    @return StringVar : lire le choix courant avec .get()
    """
    ttk.Label(parent, text=libelle).pack(anchor="w", pady=(4, 0))
    var = tk.StringVar(value=defaut)
    cb = ttk.Frame(parent)
    cb.pack(anchor="w", fill="x")
    
    for opt in options:
        ttk.Radiobutton(cb, text=opt, value=opt, variable=var,
                        command=on_change).pack(side="left", padx=5)
    return var


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


def champ2(parent, libelle, defaut):
    """
    Une ligne 'libelle : [case texte]', rangee automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger ce champ
    @param[in] libelle : texte a gauche
    @param[in] defaut  : valeur pre-remplie

    @return Entry : lire avec .get() (renvoie du texte, a convertir en int/float)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=35).pack(side="left")
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


