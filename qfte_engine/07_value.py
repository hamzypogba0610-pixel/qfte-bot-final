def detecter_value(data):
    proba_calibree = float(data.get("proba_calibree", 0.5))
    cote = float(data.get("cote", 2.0))
    value = float(data.get("value", 0.0))
    fiabilite = float(data.get("fiabilite", 0.75))

    # EV net = (proba calibrée × cote) - 1
    ev_net = (proba_calibree * cote) - 1

    # Classification du niveau
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

    data["ev_net"] = round(ev_net, 4)
    data["niveau"] = niveau
    data["stake_brut"] = stake
    return data
