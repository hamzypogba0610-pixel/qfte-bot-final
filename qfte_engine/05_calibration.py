def calibrer_probabilites(data):
    proba_juste = float(data.get("proba_juste", 0.5))

    # Calibration simple : on "tire" légèrement vers 0.5 pour éviter les extrêmes
    alpha = 0.9
    proba_calibree = alpha * proba_juste + (1 - alpha) * 0.5

    # Bornes de sécurité
    proba_calibree = max(0.01, min(0.99, proba_calibree))

    # Fiabilité estimée (base simple pour l'instant, affinée plus tard)
    fiabilite = 0.75 + (0.15 * (1 - abs(proba_calibree - 0.5) * 2))
    fiabilite = round(min(0.95, fiabilite), 4)

    data["proba_calibree"] = round(proba_calibree, 4)
    data["fiabilite"] = fiabilite
    return data
