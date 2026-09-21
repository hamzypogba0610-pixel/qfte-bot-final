def analyser_marche(data):
    match = data.get("match", {})
    cote_ouverture = float(match.get("cote_ouverture", 2.0))
    cote_actuelle = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))

    # Probabilité implicite de la cote actuelle
    proba_implicite = 1 / cote_actuelle

    # Mouvement de cote (en %)
    mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture

    # Marge estimée du bookmaker (5% par défaut)
    marge = 0.05

    # Probabilité "juste" estimée
    proba_juste = proba_implicite / (1 + marge)

    # Value brute
    value = (proba_juste * cote_actuelle) - 1

    # Liquidité
    liquidite_ok = volume >= 50000

    return {
        "status": "ok",
        "etape": "marche",
        "match": match,
        "proba_implicite": round(proba_implicite, 4),
        "mouvement": round(mouvement, 4),
        "proba_juste": round(proba_juste, 4),
        "value": round(value, 4),
        "liquidite_ok": liquidite_ok,
    }
