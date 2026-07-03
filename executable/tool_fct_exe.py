from tkinter import ttk, messagebox
import tkinter as tk
import os
import geopandas as gpd 

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


def statsRapide(parent_selec, gpkg_dir, parent_stats):
    parent_selec.columnconfigure(1, weight=1)
    parent_selec.rowconfigure(1, weight=1)

    liste_gpkg = tk.Listbox(parent_selec,  selectmode="extended")
    liste_gpkg.grid(row=1, column=1, sticky="nsew", padx=2)

    zone_stats = tk.Text(parent_stats)
    zone_stats.pack(fill="both", expand=True)
    zone_stats.configure(state="disabled")


    def rafraichir():
        liste_gpkg.delete(0, "end")
        if os.path.isdir(gpkg_dir):
            for nom in sorted(os.listdir(gpkg_dir)):
                liste_gpkg.insert("end", nom)

    def stats():
        def conv (valeur, unite):
            if unite not in ("Wh", "Wc"):
                return f"{valeur:.1f} {unite}".strip()

            if valeur >= 1e12:
                return f"{valeur/1e12:.2f} P{unite}"
            if valeur >= 1e9:
                return f"{valeur/1e9:.2f} T{unite}"
            if valeur >= 1e6:
                return f"{valeur/1e6:.2f} G{unite}"
            if valeur >= 1e3:
                return f"{valeur/1e3:.2f} M{unite}"
            if valeur >= 1:
                return f"{valeur:.2f} k{unite}"
            if valeur >= 1e-3:
                return f"{valeur*1e3:.2f} {unite}"
            return f"{valeur*1e6:.4f} m{unite}"

        zone = liste_gpkg.curselection()
        if not zone:
            return
        nom = liste_gpkg.get(zone[0])
        gdf = gpd.read_file(os.path.join(gpkg_dir, nom))

        colonnes = {
            "hauteur_pts":       ("Hauteur du toit", "m"),
            "nb_pixels":         ("Nombre de pixels de toit", ""),
            "surf_tot_m2":       ("Surface totale ", "m2"),
            "surf_plate_m2":     ("Surface plate", "m2"),
            "surf_incl_m2":      ("Surface inclinee, toutes orientations", "m2"),
            "surf_incl_or_m2":   ("Surface inclinee orientee (azimut choisi)", "m2"),
            "surf_incl_N_m2":    ("Surface inclinee orientee Nord", "m2"),
            "surf_incl_NE_m2":   ("Surface inclinee orientee Nord-Est", "m2"),
            "surf_incl_E_m2":    ("Surface inclinee orientee Est", "m2"),
            "surf_incl_SE_m2":   ("Surface inclinee orientee Sud-Est", "m2"),
            "surf_incl_S_m2":    ("Surface inclinee orientee Sud", "m2"),
            "surf_incl_SO_m2":   ("Surface inclinee orientee Sud-Ouest", "m2"),
            "surf_incl_O_m2":    ("Surface inclinee orientee Ouest", "m2"),
            "surf_incl_NO_m2":   ("Surface inclinee orientee Nord-Ouest", "m2"),
            "irr_an_kwh":        ("Irradiation recue par an, toute la toiture", "Wh"),
            "pente_moy_incl":    ("Pente moyenne des pans inclines, toutes orientations", "deg"),
            "irr_an_kwh_orp":    ("Irradiation recue par an, base installable (plat + oriente)", "Wh"),
            "prod_an_kwh":       ("Production PV par an, toute la toiture", "Wh"),
            "prod_an_kwh_orp":   ("Production PV par an, base installable (plat + oriente)", "Wh"),
            "puissance_kwc_orp": ("Puissance installable, base installable (plat + oriente)", "Wc"),
            "prod_T1_kwh_orp":   ("Production PV trimestre 1 (jan-fev-mar), base installable", "Wh"),
            "prod_T2_kwh_orp":   ("Production PV trimestre 2 (avr-mai-juin), base installable", "Wh"),
            "prod_T3_kwh_orp":   ("Production PV trimestre 3 (juil-aout-sept), base installable", "Wh"),
            "prod_T4_kwh_orp":   ("Production PV trimestre 4 (oct-nov-dec), base installable", "Wh"),
        }

        lignes = [f"Fichier : {nom}", f"Nombre de toitures : {len(gdf)}", ""]

        for nom_colonne, (libelle, unite) in colonnes.items():
            if nom_colonne not in gdf.columns:
                continue   
            moyenne = conv(gdf[nom_colonne].mean(), unite)
            minimum = conv(gdf[nom_colonne].min(), unite)
            maximum = conv(gdf[nom_colonne].max(), unite)
            lignes.append(f"{libelle:<30}: moyenne={moyenne}  min={minimum}  max={maximum}")

        zone_stats.configure(state="normal")
        zone_stats.delete("1.0", "end")
        zone_stats .insert("1.0", "\n\n".join(lignes))
        zone_stats.configure(state="disabled")




    ttk.Button(parent_selec, text="rafraichir",
               command=lambda: rafraichir()).grid(row=2, column=1, pady=2)
    
    ttk.Button(parent_selec, text="statistiques",
               command=lambda: stats()).grid(row=3, column=1, pady=2)

    rafraichir()
    return rafraichir
