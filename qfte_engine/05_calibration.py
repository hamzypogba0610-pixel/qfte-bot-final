def calibrer_probabilites(data):
    marches = data.get("marches", [])
    alpha = 0.9
    resultat = []

    for m in marches:
        proba_juste = float(m.get("proba_juste", 0.5))
        proba_calibree = alpha * proba_juste + (1 - alpha) * 0.5
        proba_calibree = max(0.01, min(0.99, proba_calibree))

        fiabilite = 0.75 + (0.15 * (1 - abs(proba_calibree - 0.5) * 2))
        fiabilite = round(min(0.95, fiabilite), 4)

        m["proba_calibree"] = round(proba_calibree, 4)
        m["fiabilite"] = fiabilite
        resultat.append(m)

    data["marches"] = resultat
    return data
