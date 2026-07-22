import tkinter as tk
from tkinter import ttk, scrolledtext
import math
from tkinter import ttk, scrolledtext, messagebox


def onglets(parent):
    """Cree le conteneur d'onglets (ttk.Notebook)."""
    return ttk.Notebook(parent)

def onglet(notebook, titre):
    """Ajoute un onglet nomme au conteneur et renvoie son cadre."""
    f = ttk.Frame(notebook)
    notebook.add(f, text=titre)
    return f

def bulleAide(parent, message):
    """Petit '?' cliquable qui affiche message dans une boite d'information."""
    q = ttk.Label(parent, text="?", foreground="blue", cursor="hand2")
    q.pack(side="left", padx=(4, 0))
    q.bind("<Button-1>", lambda e: messagebox.showinfo("Aide", message))


def bouton(parent, libelle, commande, aide=None):
    """
    Un bouton avec bulle d'aide optionnelle, range automatiquement dans parent.
    --------
    @param[in] parent   : la boite ou ranger le bouton
    @param[in] libelle  : texte du bouton
    @param[in] commande : fonction appelee au clic
    @param[in] aide     : texte de la bulle d'aide (optionnel)

    @return Button : le bouton (modifier avec .configure(state=...))
    """
    ligne = ttk.Frame(parent); ligne.pack(pady=5)
    b = ttk.Button(ligne, text=libelle, command=commande)
    b.pack(side="left")
    if aide:
        bulleAide(ligne, aide)
    return b


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

    @return LabelFrame : a placer (pack ou grid), puis a remplir avec des champs
    """
    return ttk.LabelFrame(parent, text=titre)

def radioBoutons(parent, libelle, options, defaut, on_change=None, aide=None):
    """
    Un groupe de boutons radio (un seul choix a la fois).
    --------
    @param[in] parent    : conteneur ou ranger le groupe
    @param[in] libelle   : titre affiche au-dessus
    @param[in] options   : liste des choix
    @param[in] defaut    : choix selectionne au depart
    @param[in] on_change : fonction appelee a chaque changement de choix (optionnel)
    @param[in] aide      : texte de la bulle d'aide, a cote du titre (optionnel)

    @return StringVar : lire le choix courant avec .get()
    """
    ligne_titre = ttk.Frame(parent); ligne_titre.pack(anchor="w", fill="x", pady=(4, 0))
    ttk.Label(ligne_titre, text=libelle).pack(side="left")
    if aide:
        bulleAide(ligne_titre, aide)

    var = tk.StringVar(value=defaut)
    cb = ttk.Frame(parent)
    cb.pack(anchor="w", fill="x")

    for opt in options:
        ttk.Radiobutton(cb, text=opt, value=opt, variable=var,
                        command=on_change).pack(side="left", padx=5)
    return var


def barreProgression(parent):
    """
    Cree une barre de progression (0 a 100).
    --------
    @param[in] parent : conteneur

    @return Progressbar : a placer (pack ou grid) ; mettre a jour avec  barre["value"] = 0..100
    """
    return ttk.Progressbar(parent, maximum=100)


def zoneLogs(parent, hauteur=10):
    """
    Cree une zone de texte deroulante pour afficher des messages.
    --------
    @param[in] parent  : conteneur
    @param[in] hauteur : nombre de lignes visibles

    @return ScrolledText : a placer (pack ou grid) ;
                           ajouter une ligne avec  .insert("end", txt + "\\n")  puis  .see("end")
    """
    return scrolledtext.ScrolledText(parent, height=hauteur)



def champ(parent, libelle, defaut, aide = None):
    """
    Une ligne 'libelle : [case texte]', rangee automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger ce champ
    @param[in] libelle : texte a gauche
    @param[in] defaut  : valeur pre-remplie
    @param[in] aide    : texte de la bulle d'aide (optionnel)

    @return Entry : lire avec .get() (renvoie du texte, a convertir en int/float)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=18).pack(side="left")
    e = ttk.Entry(ligne); e.insert(0, str(defaut)); e.pack(side="left", fill="x", expand=True)
    if aide:
        bulleAide(ligne, aide)
    return e


def champ2(parent, libelle, defaut, aide = None):
    """
    Comme champ, avec un libelle large (45 caracteres) pour les intitules longs.
    --------
    @param[in] parent  : la boite ou ranger ce champ
    @param[in] libelle : texte a gauche
    @param[in] defaut  : valeur pre-remplie
    @param[in] aide    : texte de la bulle d'aide (optionnel)

    @return Entry : lire avec .get() (renvoie du texte, a convertir en int/float)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=45).pack(side="left")
    e = ttk.Entry(ligne); e.insert(0, str(defaut)); e.pack(side="left", fill="x", expand=True)
    if aide:
        bulleAide(ligne, aide)
    return e

def listeDeroulante(parent, libelle, options, defaut, aide = None):
    """
    Une ligne 'libelle : [liste deroulante]', a choix unique parmi options (lecture seule).
    --------
    @param[in] parent  : la boite ou ranger ce champ
    @param[in] libelle : texte a gauche
    @param[in] options : liste des choix possibles
    @param[in] defaut  : valeur selectionnee au depart
    @param[in] aide    : texte de la bulle d'aide (optionnel)

    @return Combobox : lire avec .get() (renvoie du texte, a convertir en int/float)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=45).pack(side="left")
    cb = ttk.Combobox(ligne, values=options, state="readonly")
    cb.set(defaut)
    cb.pack(side="left", fill="x", expand=True)
    if aide:
        bulleAide(ligne, aide)
    return cb


def case(parent, libelle, defaut, aide = None):
    """
    Une case a cocher (oui/non), rangee automatiquement dans parent.
    --------
    @param[in] parent  : la boite ou ranger la case
    @param[in] libelle : texte a cote de la case
    @param[in] defaut  : True/False coche au depart
    @param[in] aide    : texte de la bulle d'aide (optionnel)

    @return BooleanVar : lire avec .get() (True/False)
    """
    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    var = tk.BooleanVar(value=defaut)
    ttk.Checkbutton(ligne, text=libelle, variable=var).pack(anchor="w", pady=2)
    if aide:
        bulleAide(ligne, aide)
    return var




def menuCoches(parent, libelle, options, defaut, aide = None):
    """
    Un bouton qui ouvre un panneau de cases a cocher (compact, une seule fenetre a la fois).
    Au-dela de 5 options, elles sont reparties en colonnes cote a cote.
    --------
    @param[in] parent  : la boite ou ranger
    @param[in] libelle : texte a gauche
    @param[in] options : liste des choix possibles
    @param[in] defaut  : liste des choix coches au depart
    @param[in] aide    : texte de la bulle d'aide (optionnel)

    @return dict {option: BooleanVar} : lire avec  [o for o, v in d.items() if v.get()]
    """
    variables = {opt: tk.BooleanVar(value=(opt in defaut)) for opt in options}

    ligne = ttk.Frame(parent); ligne.pack(fill="x", pady=2)
    ttk.Label(ligne, text=libelle, width=18).pack(side="left")
    btn = ttk.Button(ligne); btn.pack(side="left")
    if aide:
        bulleAide(ligne, aide)
    etat = {"pop": None}                              

    def majTexte():
        n = sum(v.get() for v in variables.values())
        btn.configure(text=f"{n} sélectionné(s)  ▾")

    # le compteur se remet a jour a tout changement, y compris depuis l'exterieur
    # (ex: bouton "Reinitialiser les parametres"), pas seulement au clic d'une case
    for v in variables.values():
        v.trace_add("write", lambda *_: majTexte())

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
            ttk.Checkbutton(pop, text=opt, variable=v).grid(   # maj du compteur via le trace ci-dessus
                row=idx % par_col, column=idx // par_col, sticky="w", padx=10, pady=2)

        ttk.Button(pop, text="OK", command=pop.destroy).grid(
            row=par_col, column=0, columnspan=ncols, pady=6)

    btn.configure(command=ouvrir)
    majTexte()
    return variables


def boiteDefilante(parent, titre):
    """
    Comme boite(), mais le contenu peut defiler verticalement s'il est trop haut
    pour la fenetre (molette ou barre de defilement).
    --------
    @param[in] parent : la fenetre (ou une autre boite) ou la mettre
    @param[in] titre  : texte affiche en haut de la boite

    @return exterieur, interieur : exterieur a placer avec .grid(...) ;
                                   interieur a remplir avec des champs, comme une boite normale
    """
    exterieur = ttk.LabelFrame(parent, text=titre)
    canvas = tk.Canvas(exterieur, highlightthickness=0)
    scrollbar = ttk.Scrollbar(exterieur, orient="vertical", command=canvas.yview)
    interieur = ttk.Frame(canvas)
    fenetre_id = canvas.create_window((0, 0), window=interieur, anchor="nw")

    interieur.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(fenetre_id, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def molette(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", molette))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return exterieur, interieur