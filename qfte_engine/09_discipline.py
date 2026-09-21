def appliquer_discipline(data):
    fiabilite = float(data.get("fiabilite", 0.0))
    confiance = float(data.get("confiance", 0.0))
    ev_net = float(data.get("ev_net", 0.0))
    stake = float(data.get("stake", 0.0))
    liquidite_ok = bool(data.get("liquidite_ok", False))

    # Seuils V23.0
    filtres = {
        "fiabilite_ok": fiabilite >= 0.75,
        "confiance_ok": confiance >= 70.0,
        "ev_ok": ev_net >= 0.04,
        "stake_ok": 0.0 < stake <= 1.5,
        "liquidite_ok": liquidite_ok,
    }

    # Décision finale
    if all(filtres.values()):
        decision = "ATTAQUE FORTE" if ev_net >= 0.05 else "ATTAQUE"
    elif filtres["fiabilite_ok"] and filtres["ev_ok"] and filtres["liquidite_ok"]:
        decision = "LEAN"
    else:
        decision = "ÉVITER"

    # Message de discipline
    if decision == "ATTAQUE FORTE":
        message = "Tous les filtres validés. Feu vert."
    elif decision == "ATTAQUE":
        message = "Filtres validés. Mise recommandée."
    elif decision == "LEAN":
        message = "Filtres partiels. Prudence conseillée."
    else:
        message = "Ne respecte pas les critères V23.0. On passe."

    data["filtres"] = filtres
    data["decision"] = decision
    data["message_discipline"] = message
    return data
