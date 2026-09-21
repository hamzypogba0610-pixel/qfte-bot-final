import math


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def proba_resultat_1x2(lh, la, max_buts=8):
    p_home = 0.0
    p_nul = 0.0
    p_away = 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            p = poisson(i, lh) * poisson(j, la)
            if i > j:
                p_home += p
            elif i == j:
                p_nul += p
            else:
                p_away += p
    return p_home, p_nul, p_away


def proba_over(lh, la, ligne=2.5, max_buts=10):
    p_over = 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            if i + j > ligne:
                p_over += poisson(i, lh) * poisson(j, la)
    return p_over


def proba_btts(lh, la):
    p_home_marque = 1 - poisson(0, lh)
    p_away_marque = 1 - poisson(0, la)
    return p_home_marque * p_away_marque


def analyser_marche(data):
    match = data.get("match", {})
    cote_ouverture = float(match.get("cote_ouverture", 2.0))
    cote_actuelle = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))

    marge = 0.05

    # --- Estimation des buts attendus (λ) à partir de la cote domicile ---
    proba_home_implicite = 1 / cote_actuelle
    ratio_home = 0.5 + (proba_home_implicite - 0.33) * 0.9
    ratio_home = max(0.30, min(0.72, ratio_home))

    total_buts_estime = 2.7
    lambda_home = total_buts_estime * ratio_home
    lambda_away = total_buts_estime * (1 - ratio_home)

    # --- Calcul des probas des marchés ---
    p_home, p_nul, p_away = proba_resultat_1x2(lambda_home, lambda_away)
    proba_ah = p_home  # Handicap -0.5 = victoire simple

    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_btts_val = proba_btts(lambda_home, lambda_away)

    # --- Cotes estimées à partir des probas (avec marge bookmaker) ---
    cote_ah = round(1 / (proba_ah * (1 + marge)), 2)
    cote_over25 = round(1 / (proba_over25 * (1 + marge)), 2)
    cote_btts_calc = round(1 / (proba_btts_val * (1 + marge)), 2)

    # Mouvement de cote (sur le marché principal)
    mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(lambda_home, 3)
    data["lambda_away"] = round(lambda_away, 3)

    data["marches"] = [
        {
            "nom": "Handicap Asiatique -0.5",
            "selection": match.get("equipe1", "-"),
            "cote": cote_ah,
            "cote_ouverture": round(cote_ah * 1.02, 2),
            "proba_juste": round(proba_ah, 4),
            "mouvement": round(mouvement, 4),
        },
        {
            "nom": "Over/Under 2.5",
            "selection": "Over 2.5",
            "cote": cote_over25,
            "cote_ouverture": round(cote_over25 * 1.02, 2),
            "proba_juste": round(proba_over25, 4),
            "mouvement": round(mouvement * 0.8, 4),
        },
        {
            "nom": "BTTS",
            "selection": "Oui",
            "cote": cote_btts_calc,
            "cote_ouverture": round(cote_btts_calc * 1.02, 2),
            "proba_juste": round(proba_btts_val, 4),
            "mouvement": round(mouvement * 0.6, 4),
        },
    ]

    return data
