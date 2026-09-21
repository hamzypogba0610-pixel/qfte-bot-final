def valider_coherence(data):
    match = data.get("match", {})
    marches = data.get("marches", [])

    alertes = []
    score_validation = 100  # sur 100

    # --- 1. Récupération des cotes ---
    cote_1x2 = float(match.get("cote_actuelle", 0) or 0)
    cote_ouverture = float(match.get("cote_ouverture", 0) or 0)
    cote_ah = float(match.get("cote_ah", 0) or 0)
    cote_over25 = float(match.get("cote_over25", 0) or 0)
    cote_btts = float(match.get("cote_btts", 0) or 0)

    # --- 2. Cohérence 1X2 vs HA -0.5 ---
    # Ces deux marchés sont quasi identiques : les cotes doivent être proches
    if cote_1x2 > 0 and cote_ah > 0:
        ecart_ah = abs(cote_1x2 - cote_ah)
        if ecart_ah > 0.20:
            alertes.append(
                f"🚨 Cotes incohérentes : 1X2 ({cote_1x2}) vs HA -0.5 ({cote_ah}) — écart de {round(ecart_ah, 2)}"
            )
            score_validation -= 30
        elif ecart_ah > 0.15:
            alertes.append(
                f"⚠️ Écart suspect : 1X2 ({cote_1x2}) vs HA -0.5 ({cote_ah}) — écart de {round(ecart_ah, 2)}"
            )
            score_validation -= 15

    # --- 3. Mouvement de cote ---
    if cote_ouverture > 0 and cote_1x2 > 0:
        mouvement = abs(cote_1x2 - cote_ouverture) / cote_ouverture
        if mouvement > 0.30:
            alertes.append(
                f"🚨 Mouvement de cote très fort : {round(mouvement * 100, 1)}% depuis l'ouverture"
            )
            score_validation -= 20
        elif mouvement > 0.15:
            alertes.append(
                f"⚠️ Mouvement de cote notable : {round(mouvement * 100, 1)}% depuis l'ouverture"
            )
            score_validation -= 10

    # --- 4. Plausibilité des cotes ---
    toutes_cotes = {
        "1X2": cote_1x2,
        "HA -0.5": cote_ah,
        "Over 2.5": cote_over25,
        "BTTS": cote_btts,
    }
    for nom, c in toutes_cotes.items():
        if c > 0:
            if c < 1.01:
                alertes.append(f"🚨 Cote {nom} invalide : {c} (< 1.01)")
                score_validation -= 25
            elif c > 50:
                alertes.append(f"⚠️ Cote {nom} très élevée : {c} (> 50)")
                score_validation -= 10

    # --- 5. Cohérence Over 2.5 vs BTTS ---
    # Si Over 2.5 est très bas (donc probable), BTTS ne devrait pas être trop haut
    if cote_over25 > 0 and cote_btts > 0:
        if cote_over25 < 1.50 and cote_btts > 2.50:
            alertes.append(
                "⚠️ Incohérence Over 2.5 / BTTS : Over très probable mais BTTS peu probable"
            )
            score_validation -= 10

    # --- 6. Marge bookmaker (via les 3 issues 1X2 théoriques) ---
    if cote_1x2 > 0:
        # Marge estimée simple sur le favori
        proba_implicite = 1 / cote_1x2
        if proba_implicite > 0.95:
            alertes.append(
                f"⚠️ Cote 1X2 {cote_1x2} implique {round(proba_implicite*100, 1)}% de proba — suspect"
            )
            score_validation -= 10

    score_validation = max(0, score_validation)

    # --- Niveau global ---
    if score_validation >= 85:
        niveau = "OK"
        message = "✅ Cotes cohérentes — analyse fiable"
    elif score_validation >= 60:
        niveau = "PRUDENCE"
        message = "⚠️ Quelques incohérences détectées — prudence"
    else:
        niveau = "DANGER"
        message = "🚨 Incohérences majeures — analyse peu fiable"

    data["validation"] = {
        "score": score_validation,
        "niveau": niveau,
        "message": message,
        "alertes": alertes,
    }
    return data
