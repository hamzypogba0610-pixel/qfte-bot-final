def appliquer_discipline(data):
    marches = data.get("marches", [])
    liquidite_ok = bool(data.get("liquidite_ok", False))
    resultat = []

    for m in marches:
        fiabilite = float(m.get("fiabilite", 0.0))
        confiance = float(m.get("confiance", 0.0))
        ev_net = float(m.get("ev_net", 0.0))
        stake = float(m.get("stake", 0.0))

        filtres = {
            "fiabilite_ok": fiabilite >= 0.75,
            "confiance_ok": confiance >= 70.0,
            "ev_ok": ev_net >= 0.04,
            "stake_ok": 0.0 < stake <= 1.5,
            "liquidite_ok": liquidite_ok,
        }

        if all(filtres.values()):
            decision = "ATTAQUE FORTE" if ev_net >= 0.05 else "ATTAQUE"
        elif filtres["fiabilite_ok"] and filtres["ev_ok"] and filtres["liquidite_ok"]:
            decision = "LEAN"
        else:
            decision = "ÉVITER"

        m["filtres"] = filtres
        m["decision"] = decision
        resultat.append(m)

    data["marches"] = resultat

    ordre = {"ATTAQUE FORTE": 4, "ATTAQUE": 3, "LEAN": 2, "ÉVITER": 1}
    meilleure = max(resultat, key=lambda x: ordre.get(x["decision"], 0)) if resultat else {}
    data["decision"] = meilleure.get("decision", "ÉVITER")
    data["message_discipline"] = "Analyse multi-marchés QFTE V23.0"
    return data
