#=====================================
#AFFICHAGE TEMPORAIRE TERMINAL
#=====================================

def afficherBilan(bilan):
    """
    Affiche en terminal le bilan retourne par runPipeline (debug).
    --------
    @param[in] bilan : dict retourne par runPipeline, ou None
    """
    if not bilan:
        print("Aucun bilan (zone introuvable ou aucun batiment).")
        return

    print(f"\nFichier      : {bilan.get('fichier')}")
    print(f"Total dalles : {bilan.get('total')}")

    moy = bilan.get("moyennes_dalle", {})
    if moy:
        print("Temps moyens par dalle (s) :")
        for k, v in moy.items():
            print(f"   {k:<15}: {v:.3f}")

    glob = bilan.get("temps_globaux", {})
    if glob:
        print("Temps globaux (s) :")
        for k, v in glob.items():
            print(f"   {k:<12}: {v:.1f}")

    bat = bilan.get("batiments", {})
    if bat:
        print("Batiments :")
        for k, v in bat.items():
            print(f"   {k:<20}: {v}")

    echecs = bilan.get("echecs", [])
    if echecs:
        print(f"{len(echecs)} dalle(s) en echec :")
        for n in echecs:
            print(f"   - {n}")


def progressTerminal(i, total):
    """
    Canal de progression terminal : reecrit le pourcentage sur la meme ligne.
    --------
    @param[in] i     : nombre de dalles traitees
    @param[in] total : nombre total de dalles
    """
    pct = i * 100 // total
    print(f"\r{pct}%", end="", flush=True)
    if i >= total:
        print()