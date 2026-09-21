def predire_scores(data):
    proba_calibree = float(data.get("proba_calibree", 0.5))
    cote_actuelle = float(data.get("match", {}).get("cote_actuelle", 2.0))

    # Confiance : combien la proba calibrée est "assurée"
    confiance = proba_calibree if proba_calibree >= 0.5 else (1 - proba_calibree)
    confiance_pct = round(confiance * 100, 1)

    # Top score le plus probable (très simplifié pour l'instant)
    if proba_calibree >= 0.5:
        score_proba = f"{round(proba_calibree * 100, 1)}% (favori)"
    else:
        score_proba = f"{round((1 - proba_calibree) * 100, 1)}% (outsider)"

    data["confiance"] = confiance_pct
    data["score_proba"] = score_proba
    data["cote"] = cote_actuelle
    return data
