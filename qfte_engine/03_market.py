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


def estimer_lambda(proba_home_cible, total_buts=2.7):
    """Cherche les λ (buts attendus) qui donnent P(home gagne) ≈ cible."""
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
    p_home_marque = 1 - poisson(0, lh)
    p_away_marque = 1 - poisson(0, la)
    return p_home_marque * p_away_marque


def analyser_marche(data):
    match = data.get("match", {})
    cote_ouverture = float(match.get("cote_ouverture", 2.0))
    cote_actuelle = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))

    marge = 0.05

    # --- Probabilité implicite de la cote actuelle ---
    proba_implicite_home = 1 / cote_actuelle

    # --- Dé-margeage ---
    proba_demargee_home = proba_implicite_home / (1 + marge)

    # --- Signal sharp : mouvement de la cote ---
    # Si la cote a baissé (mouvement négatif), l'argent intelligent est venu.
    # On ajoute un petit bonus pour refléter cette information.
    mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture
    bonus_sharp = -mouvement * 0.7
    bonus_sharp = max(-0.02, min(0.03, bonus_sharp))

    # --- Probabilité finale HA -0.5 (= victoire simple du favori) ---
    proba_ah = proba_demargee_home + bonus_sharp
    proba_ah = max(0.30, min(0.80, proba_ah))

    # --- Estimation des λ qui donnent P(home gagne) = proba_ah ---
    lambda_home, lambda_away = estimer_lambda(proba_ah, total_buts=2.7)

    # --- Probas O/U et BTTS via Poisson calibré ---
    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_btts_val = proba_btts(lambda_home, lambda_away)

    # --- Cotes utilisées : celles du bookmaker si fournies, sinon estimation ---
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
