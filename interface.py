import tkinter as tk
import queue, threading
from tkinter import ttk
import multiprocessing
from executable.tool_exe import GROUPES_SORTIE, champ, case, menu, fenetre, boite, bouton, menu_coches
from executable.tool_exe import USAGE_1, NATURES, ECHELLES, ATTRS_BDTOPO

if __name__ == "__main__":
    multiprocessing.freeze_support()   
    fen1=fenetre("roofTool", 700, 450)


    #-------------parametres globaux-------------
    bne = boite(fen1, "paramètres globaux")
    bne.grid(row=0, column=1, sticky="ne", padx=10, pady=10)

    surf_min   = champ(bne, "Surface min (m2)", 5)
    haut_min   = champ(bne, "Hauteur min (m)", 2)
    haut_max   = champ(bne, "Hauteur max (m)", 35)
    az_min     = champ(bne, "Azimut min", 90)
    az_max     = champ(bne, "Azimut max", 270)
    pente_plat = champ(bne, "Pente plat (deg)", 10)
    pente_max  = champ(bne, "Pente max (deg)", 45)

    const_leg   = case(bne, "Inclure constructions legeres", False)

    attrs       = menu_coches(bne, "Attributs BD TOPO", 
                                ATTRS_BDTOPO,
                                ["nature", "usage_1", "hauteur", "nombre_d_etages"])

    etat = menu_coches (bne, "Etat", ["En service", "En construction", "En ruines", "Detruit"], "En service")
    nature      = menu_coches(bne, "Natures gardees", NATURES,
                                ['Indifférenciée', 'Industriel, agricole ou commercial'])
    usage_1  = menu_coches(bne, "Usages gardees", USAGE_1,
                                ['Résidentiel', 'Commercial et services', 'Indifférencié', 'Industriel', 'Agricole'])
    attrs       = menu_coches(bne, "Attributs BD TOPO", 
                                ATTRS_BDTOPO,
                                ["nature", "usage_1", "hauteur", "nombre_d_etages"])
    
    sortie = menu_coches(bne, "Colonnes de sortie", list(GROUPES_SORTIE), list(GROUPES_SORTIE))    

    #-------------lancement pipeline-------------
    bnw = boite(fen1, "pipeline")
    bnw.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

    menu (bnw, "echelle", ECHELLES, [])



    fen1.mainloop()                  


    