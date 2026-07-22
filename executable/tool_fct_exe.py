import threading
from tkinter import ttk, messagebox
import tkinter as tk
import os
import geopandas as gpd
import json
import pyogrio
from src import config


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


def formaterDuree(secondes):
    """
    Formate une duree en secondes vers 'Xh YYmin ZZs' (heures/minutes omises si nulles).
    --------
    @param[in] secondes : duree en secondes

    @return str : duree formatee, ex. '1h 12min 05s', '3min 42s' ou '8s'
    """
    h, reste = divmod(int(secondes), 3600)
    m, s = divmod(reste, 60)
    if h:
        return f"{h}h {m:02d}min {s:02d}s"
    if m:
        return f"{m}min {s:02d}s"
    return f"{s}s"


def afficherBilan(bilan):
    """
    Formate le bilan retourne par runPipeline en lignes de texte, pour affichage GUI.
    --------
    @param[in] bilan : dict retourne par runPipeline, ou None

    @return lignes : liste de chaines, une par ligne a afficher
    """
    if not bilan:
        return ["Aucun bilan (zone introuvable ou aucun batiment)."]

    lignes = []
    lignes.append(f"Fichier      : {bilan.get('fichier')}")
    lignes.append(f"Total dalles : {bilan.get('total')}")

    moy = bilan.get("moyennes_dalle", {})
    if moy:
        lignes.append("Temps moyens par dalle (s) :")
        for k, v in moy.items():
            lignes.append(f"   {k:<15}: {v:.3f}")

    glob = bilan.get("temps_globaux", {})
    if glob:
        lignes.append("Temps globaux :")
        for k, v in glob.items():
            lignes.append(f"   {k:<12}: {formaterDuree(v)}")

    bat = bilan.get("batiments", {})
    if bat:
        lignes.append("Batiments :")
        for k, v in bat.items():
            lignes.append(f"   {k:<20}: {v}")

    echecs = bilan.get("echecs", [])
    if echecs:
        lignes.append(f"{len(echecs)} dalle(s) en echec :")
        for e in echecs:
            lignes.append(f"   - {e['nom']} : {e['erreur']}")

    return lignes




def listesFichiers(parent, geojson_dir, gpkg_dir):
    """
    Affiche cote a cote la liste des fichiers de deux dossiers (geojson / gpkg),
    avec des boutons pour supprimer la selection et ouvrir le dossier parent.
    --------
    @param[in] parent      : la boite ou ranger les listes
    @param[in] geojson_dir : dossier des .geojson
    @param[in] gpkg_dir    : dossier des .gpkg

    @return fonction rafraichir : rescanne les deux dossiers et met a jour l'affichage
    """
    colonnes = ttk.Frame(parent); colonnes.pack(fill="both", expand=True)
    colonnes.columnconfigure(0, weight=1)
    colonnes.columnconfigure(1, weight=1)
    colonnes.rowconfigure(1, weight=1)

    ttk.Label(colonnes, text="geojson").grid(row=0, column=0)
    liste_geojson = tk.Listbox(colonnes, selectmode="extended")
    liste_geojson.grid(row=1, column=0, sticky="nsew", padx=2)

    ttk.Label(colonnes, text="gpkg").grid(row=0, column=1)
    liste_gpkg = tk.Listbox(colonnes, selectmode="extended")
    liste_gpkg.grid(row=1, column=1, sticky="nsew", padx=2)

    def rafraichir():
        liste_geojson.delete(0, "end")
        liste_gpkg.delete(0, "end")
        if os.path.isdir(geojson_dir):
            for nom in sorted(os.listdir(geojson_dir)):
                liste_geojson.insert("end", nom)
        if os.path.isdir(gpkg_dir):
            for nom in sorted(os.listdir(gpkg_dir)):
                liste_gpkg.insert("end", nom)

    def supprimer(listbox, dossier):
        selection = listbox.curselection()
        if not selection:
            return
        noms = [listbox.get(i) for i in selection]
        if not messagebox.askyesno("Confirmer", f"Supprimer {len(noms)} fichier(s) ?\n" + "\n".join(noms)):
            return
        for nom in noms:
            os.remove(os.path.join(dossier, nom))
        rafraichir()
    
    ttk.Button(colonnes, text="Supprimer",
               command=lambda: supprimer(liste_geojson, geojson_dir)).grid(row=2, column=0, pady=2)
    ttk.Button(colonnes, text="Supprimer",
               command=lambda: supprimer(liste_gpkg, gpkg_dir)).grid(row=2, column=1, pady=2)

    ttk.Button(parent, text="Ouvrir dans l'explorateur",
               command=lambda: os.startfile(os.path.dirname(geojson_dir))).pack(pady=4)
    
    ttk.Button(parent, text="Rafraîchir",
               command=lambda: rafraichir()).pack(pady=5)

    rafraichir()
    return rafraichir


def statsRapide(parent_selec, gpkg_dir, parent_stats):
    """
    Liste des gpkg calcules et statistiques (total, mediane, moyenne, P10-P90 par colonne) du fichier choisi.
    La lecture du gpkg tourne dans un thread pour ne pas geler l'interface.
    --------
    @param[in] parent_selec : la boite ou ranger la liste des fichiers
    @param[in] gpkg_dir     : dossier des .gpkg
    @param[in] parent_stats : la boite ou afficher les statistiques

    @return fonction rafraichir : rescanne le dossier et met a jour la liste
    """
    parent_selec.columnconfigure(1, weight=1)
    parent_selec.rowconfigure(1, weight=1)

    liste_gpkg = tk.Listbox(parent_selec, selectmode="browse")
    liste_gpkg.grid(row=1, column=1, sticky="nsew", padx=2)

    scrollbar_gpkg = ttk.Scrollbar(parent_selec, orient="vertical", command=liste_gpkg.yview)
    scrollbar_gpkg.grid(row=1, column=2, sticky="ns")
    liste_gpkg.configure(yscrollcommand=scrollbar_gpkg.set)

    
    scrollbar_x = ttk.Scrollbar(parent_stats, orient="horizontal", command=lambda *a: zone_stats.xview(*a))
    scrollbar_x.pack(side="bottom", fill="x")

    zone_stats = tk.Text(parent_stats, wrap="none", xscrollcommand=scrollbar_x.set)
    zone_stats.pack(fill="both", expand=True)
    zone_stats.configure(state="disabled")


    def rafraichir():
        liste_gpkg.delete(0, "end")
        if os.path.isdir(gpkg_dir):
            for nom in sorted(os.listdir(gpkg_dir)):
                liste_gpkg.insert("end", nom)

    def stats():
        zone = liste_gpkg.curselection()
        if not zone:
            return
        nom = liste_gpkg.get(zone[0])
        btn_stats.configure(state="disabled")
        zone_stats.configure(state="normal")
        zone_stats.delete("1.0", "end")
        zone_stats.insert("1.0", "Calcul en cours...")
        zone_stats.configure(state="disabled")
        threading.Thread(target=calcul, args=(nom,), daemon=True).start()

    def calcul(nom):
        gdf = gpd.read_file(os.path.join(gpkg_dir, nom), ignore_geometry=True)

        lignes = [f"Fichier : {nom}", f"Nombre de toitures : {len(gdf)}", ""]

        for nom_colonne, (libelle, unite) in config.COLONNES_SORTIE.items():
            if nom_colonne not in gdf.columns:
                continue
            col = gdf[nom_colonne]
            texte = (f"médiane={formater(col.median(), unite)}  "
                     f"moyenne={formater(col.mean(), unite)}  "
                     f"P10–P90={formater(col.quantile(0.10), unite)} à {formater(col.quantile(0.90), unite)}")
            if unite not in ("m", "deg"):
                texte = f"total={formater(col.sum(), unite)}  " + texte
            lignes.append(f"{libelle:<30}: {texte}")

        def montrer():
            zone_stats.configure(state="normal")
            zone_stats.delete("1.0", "end")
            zone_stats.insert("1.0", "\n\n".join(lignes))
            zone_stats.configure(state="disabled")
            btn_stats.configure(state="normal")
        zone_stats.after(0, montrer)

    def metadonnees():
        zone = liste_gpkg.curselection()
        if not zone:
            return
        nom = liste_gpkg.get(zone[0])
        info = pyogrio.read_info(os.path.join(gpkg_dir, nom), layer="batiments")

        zone_stats.configure(state="normal")
        zone_stats.delete("1.0", "end")
        zone_stats.insert("1.0", json.dumps(info["dataset_metadata"], indent=2, ensure_ascii=False))
        zone_stats.configure(state="disabled")



    ttk.Button(parent_selec, text="Rafraîchir",
               command=lambda: rafraichir()).grid(row=2, column=1, pady=2)
    
    btn_stats = ttk.Button(parent_selec, text="Statistiques",
                           command=lambda: stats())
    btn_stats.grid(row=3, column=1, pady=2)

    btn_meta = ttk.Button(parent_selec, text="Métadonnées", command=lambda: metadonnees())
    btn_meta.grid(row=4, column=1, pady=2)

    rafraichir()
    return rafraichir
