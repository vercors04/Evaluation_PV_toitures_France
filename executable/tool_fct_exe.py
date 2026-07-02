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
        lignes.append("Temps globaux (s) :")
        for k, v in glob.items():
            lignes.append(f"   {k:<12}: {v:.1f}")

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