import math


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def proba_resultat_1x2(lh, la, max_buts=8):
    p_home, p_nul, p_away = 0.0, 0.0, 0.0
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


def estimer_lambda(proba_home_cible, total_buts=2.7):
    lo, hi = 0.20, 0.90
    for _ in range(30):
        mid = (lo + hi) / 2
        lh = total_buts * mid
        la = total_buts * (1 - mid)
        p_h, _, _ = proba_resultat_1x2(lh, la)
        if p_h < proba_home_cible:
            lo = mid
        else:
            hi = mid
    mid = (lo + hi) / 2
    return total_buts * mid, total_buts * (1 - mid)


def proba_over(lh, la, ligne=2.5, max_buts=10):
    p_over = 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            if i + j > ligne:
                p_over += poisson(i, lh) * poisson(j, la)
    return p_over


def proba_btts(lh, la):
    return (1 - poisson(0, lh)) * (1 - poisson(0, la))


def norm_cdf(x, mu, sigma):
    """Fonction de répartition de la loi Normale."""
    z = (x - mu) / sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def analyser_marche(data):
    match = data.get("match", {})
    sport = match.get("sport", "football")

    if sport == "basket":
        return _analyser_basket(data, match)
    else:
        return _analyser_football(data, match)


def _analyser_football(data, match):
    cote_ouverture = float(match.get("cote_ouverture", 2.0))
    cote_actuelle = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))

    marge = 0.05
    proba_implicite_home = 1 / cote_actuelle
    proba_demargee_home = proba_implicite_home / (1 + marge)

    mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))

    proba_ah = max(0.30, min(0.80, proba_demargee_home + bonus_sharp))
    lambda_home, lambda_away = estimer_lambda(proba_ah, total_buts=2.7)

    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_btts_val = proba_btts(lambda_home, lambda_away)

    cote_ah_final = float(match.get("cote_ah") or (1 / (proba_ah * (1 + marge))))
    cote_over25_final = float(match.get("cote_over25") or (1 / (proba_over25 * (1 + marge))))
    cote_btts_final = float(match.get("cote_btts") or (1 / (proba_btts_val * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(lambda_home, 3)
    data["lambda_away"] = round(lambda_away, 3)

    data["marches"] = [
        {
            "nom": "Handicap Asiatique -0.5",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_ah_final, 2),
            "cote_ouverture": round(cote_ah_final * 1.02, 2),
            "proba_juste": round(proba_ah, 4),
            "mouvement": round(mouvement, 4),
        },
        {
            "nom": "Over/Under 2.5",
            "selection": "Over 2.5",
            "cote": round(cote_over25_final, 2),
            "cote_ouverture": round(cote_over25_final * 1.02, 2),
            "proba_juste": round(proba_over25, 4),
            "mouvement": round(mouvement * 0.8, 4),
        },
        {
            "nom": "BTTS",
            "selection": "Oui",
            "cote": round(cote_btts_final, 2),
            "cote_ouverture": round(cote_btts_final * 1.02, 2),
            "proba_juste": round(proba_btts_val, 4),
            "mouvement": round(mouvement * 0.6, 4),
        },
    ]
    return data


def _analyser_basket(data, match):
    """
    Basket : modèle basé sur la loi Normale.
    - Total de points attendu : ~180.5 (Europe) à ~220.5 (NBA)
    - Écart-type : ~12 points pour l'écart, ~18 pour le total
    """
    cote_ouverture = float(match.get("cote_ouverture", 1.85))
    cote_actuelle = float(match.get("cote_actuelle", 1.85))
    volume = float(match.get("volume", 50000))

    marge = 0.05
    proba_implicite_home = 1 / cote_actuelle
    proba_demargee_home = proba_implicite_home / (1 + marge)

    mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))

    proba_ml = max(0.20, min(0.85, proba_demargee_home + bonus_sharp))

    # Ligne totale de points : on suppose Over 180.5 par défaut
    ligne_totale = 180.5
    total_points_estime = 180.0

    # Écart moyen estimé à partir de la proba ML
    # proba_ml = 0.5 → écart 0 ; proba_ml = 0.85 → écart ~+10
    z_ml = 0.0
    # Recherche de l'écart μ tel que P(écart > 0) = proba_ml avec σ=12
    lo, hi = -30.0, 30.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = 1 - norm_cdf(0, mid, 12)
        if p < proba_ml:
            lo = mid
        else:
            hi = mid
    ecart_moyen = (lo + hi) / 2

    # Proba Over 180.5 (avec σ = 18)
    proba_over_totale = 1 - norm_cdf(ligne_totale, total_points_estime, 18)
    proba_over_totale = max(0.30, min(0.70, proba_over_totale))

    # Spread -4.5 Domicile = équipe 1 gagne par 5+
    ligne_spread = -4.5
    proba_spread = 1 - norm_cdf(-ligne_spread, ecart_moyen, 12)
    proba_spread = max(0.20, min(0.85, proba_spread))

    cote_ml_final = float(match.get("cote_ah") or (1 / (proba_ml * (1 + marge))))
    cote_spread_final = float(match.get("cote_over25") or (1 / (proba_spread * (1 + marge))))
    cote_total_final = float(match.get("cote_btts") or (1 / (proba_over_totale * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(ecart_moyen, 2)
    data["lambda_away"] = 0

    data["marches"] = [
        {
            "nom": "Money Line",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_ml_final, 2),
            "cote_ouverture": round(cote_ml_final * 1.02, 2),
            "proba_juste": round(proba_ml, 4),
            "mouvement": round(mouvement, 4),
        },
        {
            "nom": "Spread -4.5",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_spread_final, 2),
            "cote_ouverture": round(cote_spread_final * 1.02, 2),
            "proba_juste": round(proba_spread, 4),
            "mouvement": round(mouvement * 0.8, 4),
        },
        {
            "nom": "Total Points Over 180.5",
            "selection": "Over 180.5",
            "cote": round(cote_total_final, 2),
            "cote_ouverture": round(cote_total_final * 1.02, 2),
            "proba_juste": round(proba_over_totale, 4),
            "mouvement": round(mouvement * 0.6, 4),
        },
    ]
    return data
