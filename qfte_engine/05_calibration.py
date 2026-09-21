def calibrer_probabilites(data):
    marches = data.get("marches", [])
    match = data.get("match", {})

    volume = float(match.get("volume", 50000) or 50000)
    cote_ouverture = float(match.get("cote_ouverture", 2.0) or 2.0)
    cote_actuelle = float(match.get("cote_actuelle", 2.0) or 2.0)

    alpha = 0.9
    resultat = []

    for m in marches:
        proba_juste = float(m.get("proba_juste", 0.5))
        proba_calibree = alpha * proba_juste + (1 - alpha) * 0.5
        proba_calibree = max(0.01, min(0.99, proba_calibree))

        # ---------- Critère 1 : éloignement de 0.5 ----------
        # Proba proche de 0.5 = signal faible ; proba ~0.65-0.75 = confortable
        crit1 = 1 - abs(proba_calibree - 0.5) * 1.5
        crit1 = max(0.25, min(1.0, crit1))

        # ---------- Critère 2 : cohérence avec le marché ----------
        cote_ref = float(m.get("cote", 2.0) or 2.0)
        proba_marche = 1 / cote_ref if cote_ref > 0 else 0.5
        crit2 = 1 - abs(proba_calibree - proba_marche) * 2
        crit2 = max(0.20, min(1.0, crit2))

        # ---------- Critère 3 : liquidité ----------
        crit3 = min(1.0, volume / 100000)

        # ---------- Critère 4 : mouvement de cote ----------
        if cote_ouverture > 0:
            mouvement = abs(cote_actuelle - cote_ouverture) / cote_ouverture
        else:
            mouvement = 0

        if mouvement < 0.05:
            crit4 = 1.0
        elif mouvement < 0.15:
            crit4 = 0.85
        else:
            crit4 = 0.60

        # ---------- Moyenne pondérée ----------
        fiabilite = crit1 * 0.30 + crit2 * 0.30 + crit3 * 0.20 + crit4 * 0.20
        fiabilite = max(0.50, min(0.98, fiabilite))

        m["proba_calibree"] = round(proba_calibree, 4)
        m["fiabilite"] = round(fiabilite, 4)
        m["crit_calibration"] = {
            "crit1_eloignement": round(crit1, 3),
            "crit2_coherence": round(crit2, 3),
            "crit3_liquidite": round(crit3, 3),
            "crit4_mouvement": round(crit4, 3),
        }
        resultat.append(m)

    data["marches"] = resultat
    return data
