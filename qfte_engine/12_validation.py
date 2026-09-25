"""
Module de validation QFTE V23.0.
Vérifie la cohérence des cotes — football, basket, tennis ET hockey.
"""


def _valider_football(match):
    alertes = []
    score_validation = 100

    cote_1x2 = float(match.get("cote_actuelle", 0) or 0)
    cote_ouverture = float(match.get("cote_ouverture", 0) or 0)
    cote_ah = float(match.get("cote_ah", 0) or 0)
    cote_over25 = float(match.get("cote_over25", 0) or 0)
    cote_btts = float(match.get("cote_btts", 0) or 0)

    if cote_1x2 > 0 and cote_ah > 0:
        ecart_ah = abs(cote_1x2 - cote_ah)
        if ecart_ah > 0.20:
            alertes.append(f"🚨 Cotes incohérentes : 1X2 ({cote_1x2}) vs HA -0.5 ({cote_ah}) — écart de {round(ecart_ah, 2)}")
            score_validation -= 30
        elif ecart_ah > 0.15:
            alertes.append(f"⚠️ Écart suspect : 1X2 ({cote_1x2}) vs HA -0.5 ({cote_ah})")
            score_validation -= 15

    if cote_ouverture > 0 and cote_1x2 > 0:
        mouvement = abs(cote_1x2 - cote_ouverture) / cote_ouverture
        if mouvement > 0.30:
            alertes.append(f"🚨 Mouvement de cote très fort : {round(mouvement * 100, 1)}%")
            score_validation -= 20
        elif mouvement > 0.15:
            alertes.append(f"⚠️ Mouvement de cote notable : {round(mouvement * 100, 1)}%")
            score_validation -= 10

    toutes_cotes = {"1X2": cote_1x2, "HA -0.5": cote_ah, "Over 2.5": cote_over25, "BTTS": cote_btts}
    for nom, c in toutes_cotes.items():
        if c > 0:
            if c < 1.01:
                alertes.append(f"🚨 Cote {nom} invalide : {c} (< 1.01)")
                score_validation -= 25
            elif c > 50:
                alertes.append(f"⚠️ Cote {nom} très élevée : {c} (> 50)")
                score_validation -= 10

    if cote_over25 > 0 and cote_btts > 0:
        if cote_over25 < 1.50 and cote_btts > 2.50:
            alertes.append("⚠️ Incohérence Over 2.5 / BTTS")
            score_validation -= 10

    if cote_1x2 > 0:
        proba_implicite = 1 / cote_1x2
        if proba_implicite > 0.95:
            alertes.append(f"⚠️ Cote 1X2 {cote_1x2} implique {round(proba_implicite*100, 1)}% — suspect")
            score_validation -= 10

    return score_validation, alertes


def _valider_basket(match):
    alertes = []
    score_validation = 100

    cote_ml = float(match.get("cote_actuelle", 0) or 0)
    cote_ouverture = float(match.get("cote_ouverture", 0) or 0)
    cote_spread = float(match.get("cote_ah", 0) or 0)
    cote_total = float(match.get("cote_over25", 0) or 0)

    if cote_ml > 0 and cote_spread > 0:
        ecart = cote_spread - cote_ml
        if ecart < -0.10:
            alertes.append(f"🚨 Incohérence ML/Spread : ML ({cote_ml}) > Spread ({cote_spread})")
            score_validation -= 30
        elif ecart < 0:
            alertes.append(f"⚠️ Spread -4.5 légèrement inférieur au ML")
            score_validation -= 10
        elif ecart > 0.80:
            alertes.append(f"⚠️ Écart très important ML/Spread : +{round(ecart, 2)}")
            score_validation -= 10

    if cote_total > 0:
        if cote_total < 1.60:
            alertes.append(f"⚠️ Cote Total Points {cote_total} très basse")
            score_validation -= 10
        elif cote_total > 2.30:
            alertes.append(f"⚠️ Cote Total Points {cote_total} très haute")
            score_validation -= 10

    if cote_ouverture > 0 and cote_ml > 0:
        mouvement = abs(cote_ml - cote_ouverture) / cote_ouverture
        if mouvement > 0.25:
            alertes.append(f"🚨 Mouvement de ML fort : {round(mouvement * 100, 1)}%")
            score_validation -= 20
        elif mouvement > 0.12:
            alertes.append(f"⚠️ Mouvement de ML notable : {round(mouvement * 100, 1)}%")
            score_validation -= 10

    if cote_ml > 0:
        proba_ml = 1 / cote_ml
        if proba_ml > 0.90:
            alertes.append(f"⚠️ ML {cote_ml} implique {round(proba_ml*100, 1)}% — suspect")
            score_validation -= 15
        elif proba_ml < 0.25:
            alertes.append(f"⚠️ ML {cote_ml} implique seulement {round(proba_ml*100, 1)}%")
            score_validation -= 5

    toutes = {"ML": cote_ml, "Spread": cote_spread, "Total": cote_total}
    for nom, c in toutes.items():
        if c > 0:
            if c < 1.01:
                alertes.append(f"🚨 Cote {nom} invalide : {c} (< 1.01)")
                score_validation -= 25
            elif c > 20:
                alertes.append(f"⚠️ Cote {nom} très élevée : {c} (> 20)")
                score_validation -= 10

    return score_validation, alertes


def _valider_tennis(match):
    alertes = []
    score_validation = 100

    cote_vainqueur = float(match.get("cote_actuelle", 0) or 0)
    cote_ouverture = float(match.get("cote_ouverture", 0) or 0)
    cote_ou_jeux = float(match.get("cote_over25", 0) or 0)
    cote_score_2_0 = float(match.get("cote_btts", 0) or 0)

    if cote_vainqueur > 0 and cote_score_2_0 > 0:
        ecart = cote_score_2_0 - cote_vainqueur
        if ecart < -0.10:
            alertes.append(f"🚨 Incohérence Vainqueur/Score 2-0")
            score_validation -= 30
        elif ecart < 0:
            alertes.append(f"⚠️ Score 2-0 légèrement inférieur au Vainqueur")
            score_validation -= 10
        elif ecart > 2.0:
            alertes.append(f"⚠️ Écart très important Vainqueur/Score 2-0 : +{round(ecart, 2)}")
            score_validation -= 10

    if cote_ou_jeux > 0:
        if cote_ou_jeux < 1.50:
            alertes.append(f"⚠️ Cote Over/Under Jeux {cote_ou_jeux} très basse")
            score_validation -= 10
        elif cote_ou_jeux > 2.50:
            alertes.append(f"⚠️ Cote Over/Under Jeux {cote_ou_jeux} très haute")
            score_validation -= 10

    if cote_ouverture > 0 and cote_vainqueur > 0:
        mouvement = abs(cote_vainqueur - cote_ouverture) / cote_ouverture
        if mouvement > 0.25:
            alertes.append(f"🚨 Mouvement de cote fort : {round(mouvement * 100, 1)}%")
            score_validation -= 20
        elif mouvement > 0.12:
            alertes.append(f"⚠️ Mouvement de cote notable : {round(mouvement * 100, 1)}%")
            score_validation -= 10

    if cote_vainqueur > 0:
        proba_v = 1 / cote_vainqueur
        if proba_v > 0.90:
            alertes.append(f"⚠️ Vainqueur {cote_vainqueur} implique {round(proba_v*100, 1)}% — suspect")
            score_validation -= 15
        elif proba_v < 0.15:
            alertes.append(f"⚠️ Vainqueur {cote_vainqueur} implique seulement {round(proba_v*100, 1)}%")
            score_validation -= 5

    toutes = {"Vainqueur": cote_vainqueur, "O/U Jeux": cote_ou_jeux, "Score 2-0": cote_score_2_0}
    for nom, c in toutes.items():
        if c > 0:
            if c < 1.01:
                alertes.append(f"🚨 Cote {nom} invalide : {c} (< 1.01)")
                score_validation -= 25
            elif c > 20:
                alertes.append(f"⚠️ Cote {nom} très élevée : {c} (> 20)")
                score_validation -= 10

    return score_validation, alertes



def _valider_hockey(match):
    """Validation spécifique au hockey sur glace."""
    alertes = []
    score_validation = 100

    cote_ml = float(match.get("cote_actuelle", 0) or 0)
    cote_ouverture = float(match.get("cote_ouverture", 0) or 0)
    cote_puck_line = float(match.get("cote_ah", 0) or 0)
    cote_total = float(match.get("cote_over25", 0) or 0)

    # --- 1. Cohérence Money Line vs Puck Line ---
    # Puck Line -1.5 est plus restrictif que ML (il faut gagner par 2+ buts)
    # Donc cote_puck_line doit être PLUS ÉLEVÉE que cote_ml
    if cote_ml > 0 and cote_puck_line > 0:
        ecart = cote_puck_line - cote_ml
        if ecart < -0.15:
            alertes.append(
                f"🚨 Incohérence ML/Puck Line : ML ({cote_ml}) > Puck Line ({cote_puck_line}). "
                "Le Puck Line -1.5 doit être ≥ ML."
            )
            score_validation -= 30
        elif ecart < 0:
            alertes.append(f"⚠️ Puck Line -1.5 légèrement inférieur au ML — vérifier")
            score_validation -= 10
        elif ecart > 1.50:
            alertes.append(f"⚠️ Écart très important ML/Puck Line : +{round(ecart, 2)}")
            score_validation -= 10

    # --- 2. Plausibilité de la ligne totale ---
    # La cote Total Buts hockey est typiquement entre 1.70 et 2.10
    if cote_total > 0:
        if cote_total < 1.60:
            alertes.append(f"⚠️ Cote Total Buts {cote_total} très basse — la ligne est probablement mal saisie")
            score_validation -= 10
        elif cote_total > 2.30:
            alertes.append(f"⚠️ Cote Total Buts {cote_total} très haute — la ligne est probablement mal saisie")
            score_validation -= 10

    # --- 3. Mouvement de cote ---
    if cote_ouverture > 0 and cote_ml > 0:
        mouvement = abs(cote_ml - cote_ouverture) / cote_ouverture
        if mouvement > 0.25:
            alertes.append(f"🚨 Mouvement de ML fort : {round(mouvement * 100, 1)}%")
            score_validation -= 20
        elif mouvement > 0.12:
            alertes.append(f"⚠️ Mouvement de ML notable : {round(mouvement * 100, 1)}%")
            score_validation -= 10

    # --- 4. Plausibilité Money Line ---
    if cote_ml > 0:
        proba_ml = 1 / cote_ml
        if proba_ml > 0.90:
            alertes.append(f"⚠️ ML {cote_ml} implique {round(proba_ml*100, 1)}% — suspect")
            score_validation -= 15
        elif proba_ml < 0.20:
            alertes.append(f"⚠️ ML {cote_ml} implique seulement {round(proba_ml*100, 1)}% — outsider très faible")
            score_validation -= 5

    # --- 5. Plausibilité des cotes globales ---
    toutes = {"ML": cote_ml, "Puck Line": cote_puck_line, "Total": cote_total}
    for nom, c in toutes.items():
        if c > 0:
            if c < 1.01:
                alertes.append(f"🚨 Cote {nom} invalide : {c} (< 1.01)")
                score_validation -= 25
            elif c > 20:
                alertes.append(f"⚠️ Cote {nom} très élevée : {c} (> 20)")
                score_validation -= 10

    # --- 6. Vérification de la ligne de période (2.5 ou 1.5) ---
    # La ligne de période doit être beaucoup plus basse que la ligne totale
    # (un match entier = 5.5 buts, une période = ~1.5 buts)
    if cote_total > 0 and cote_total < 1.40:
        alertes.append("⚠️ Cote Total Buts très basse — vérifier qu'il s'agit bien du match entier (pas d'une période)")
        score_validation -= 5

    return score_validation, alertes


def valider_coherence(data):
    """
    Point d'entrée : choisit la validation selon le sport.
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    if sport == "basket":
        score_validation, alertes = _valider_basket(match)
    elif sport == "tennis":
        score_validation, alertes = _valider_tennis(match)
    elif sport == "hockey":
        score_validation, alertes = _valider_hockey(match)
    else:
        score_validation, alertes = _valider_football(match)

    score_validation = max(0, score_validation)

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
        "sport_valide": sport,
    }
    return data
