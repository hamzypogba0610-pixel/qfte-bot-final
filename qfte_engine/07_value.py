def detecter_value(data):
    marches = data.get("marches", [])
    match = data.get("match", {})
    resultat = []

    cote_1x2 = float(match.get("cote_actuelle", 2.0))
    cote_ah = float(match.get("cote_ah", cote_1x2))

    # --- Vérification de cohérence ---
    # 1X2 Domicile et HA -0.5 sont quasi identiques → cotes proches
    incoherence = abs(cote_1x2 - cote_ah) > 0.15

    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        cote = float(m.get("cote", 2.0))
        fiabilite = float(m.get("fiabilite", 0.75))
        nom_marche = m.get("nom", "")

        ev_net = (proba_calibree * cote) - 1

        # Plafond réaliste (±8%)
        ev_net = max(-0.08, min(0.08, ev_net))

        # Incohérence détectée sur le marché HA
        if incoherence and "Handicap" in nom_marche:
            m["ev_net"] = 0.0
            m["niveau"] = "AVOID"
            m["stake_brut"] = 0.0
            m["alerte"] = "⚠️ Cotes incohérentes (1X2 vs HA)"
            resultat.append(m)
            continue

        if ev_net >= 0.05 and fiabilite >= 0.80:
            niveau = "ELITE"
            stake = 1.5
        elif ev_net >= 0.04 and fiabilite >= 0.78:
            niveau = "PREMIUM"
            stake = 1.0
        elif ev_net >= 0.03 and fiabilite >= 0.75:
            niveau = "GOOD"
            stake = 0.8
        elif ev_net >= 0.0:
            niveau = "SURVEILLANCE"
            stake = 0.3
        else:
            niveau = "AVOID"
            stake = 0.0

        m["ev_net"] = round(ev_net, 4)
        m["niveau"] = niveau
        m["stake_brut"] = stake
        resultat.append(m)

    data["marches"] = resultat
    return data
