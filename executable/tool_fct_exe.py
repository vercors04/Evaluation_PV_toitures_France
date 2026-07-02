from tkinter import ttk, messagebox
import tkinter as tk
import os

def formaterDuree(secondes):
    """
    Formate une duree en secondes vers 'XhYYminZZs' (heures/minutes omises si nulles).
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
    avec un bouton pour ouvrir leur dossier parent dans l'explorateur.
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

    rafraichir()
    return rafraichir


def selecFichier(parent, gpkg_dir):
    parent.columnconfigure(1, weight=1)
    parent.rowconfigure(1, weight=1)

    liste_gpkg = tk.Listbox(parent,  selectmode="extended")
    liste_gpkg.grid(row=1, column=1, sticky="nsew", padx=2)

    def rafraichir():
        liste_gpkg.delete(0, "end")
        if os.path.isdir(gpkg_dir):
            for nom in sorted(os.listdir(gpkg_dir)):
                liste_gpkg.insert("end", nom)

    ttk.Button(parent, text="rafraichir",
               command=lambda: rafraichir()).grid(row=2, column=1, pady=2)

    rafraichir()
    return rafraichir
