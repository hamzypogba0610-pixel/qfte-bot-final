def detecter_value(data):
    marches = data.get("marches", [])
    resultat = []

    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        cote = float(m.get("cote", 2.0))
        fiabilite = float(m.get("fiabilite", 0.75))

        ev_net = (proba_calibree * cote) - 1

        # Plafond réaliste (un vrai EV dépasse rarement ±10%)
        ev_net = max(-0.10, min(0.10, ev_net))

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
