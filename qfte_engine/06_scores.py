import math


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def rho_adaptatif(lh, la):
    total = lh + la
    if total < 2.3:
        return -0.15
    elif total <= 3.0:
        return -0.10
    else:
        return -0.05


def correction_dixon_coles(i, j, lh, la, rho):
    if i == 0 and j == 0:
        return 1 - lh * la * rho
    elif i == 0 and j == 1:
        return 1 + lh * rho
    elif i == 1 and j == 0:
        return 1 + la * rho
    elif i == 1 and j == 1:
        return 1 - rho
    return 1.0


def proba_score(i, j, lh, la, rho):
    p = poisson(i, lh) * poisson(j, la)
    tau = correction_dixon_coles(i, j, lh, la, rho)
    return p * tau


def norm_cdf(x, mu, sigma):
    z = (x - mu) / sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def predire_scores(data):
    match = data.get("match", {})
    sport = match.get("sport", "football")

    if sport == "basket":
        return _scores_basket(data)
    if sport == "tennis":
        return _scores_tennis(data)
    if sport == "hockey":
        return _scores_hockey(data)
    return _scores_football(data)


def _scores_football(data):
    lambda_home = float(data.get("lambda_home", 1.4))
    lambda_away = float(data.get("lambda_away", 1.3))

    rho = rho_adaptatif(lambda_home, lambda_away)
    data["rho_utilise"] = rho

    scores = []
    for i in range(0, 6):
        for j in range(0, 6):
            p = proba_score(i, j, lambda_home, lambda_away, rho)
            scores.append({"score": f"{i}-{j}", "proba": round(p, 4)})
    scores.sort(key=lambda s: s["proba"], reverse=True)
    top_2_scores = scores[:2]

    lh_ht = lambda_home * 0.45
    la_ht = lambda_away * 0.45
    rho_ht = rho_adaptatif(lh_ht, la_ht)

    scores_ht = []
    for i in range(0, 4):
        for j in range(0, 4):
            p = proba_score(i, j, lh_ht, la_ht, rho_ht)
            scores_ht.append({"score": f"{i}-{j}", "proba": round(p, 4)})
    scores_ht.sort(key=lambda s: s["proba"], reverse=True)
    top_ht_score = scores_ht[0]

    marches = data.get("marches", [])
    resultat = []
    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        confiance = proba_calibree if proba_calibree >= 0.5 else (1 - proba_calibree)
        m["confiance"] = round(confiance * 100, 1)
        resultat.append(m)

    data["marches"] = resultat
    data["top_2_scores"] = top_2_scores
    data["top_ht_score"] = top_ht_score
    return data


def _scores_basket(data):
    ecart_moyen = float(data.get("lambda_home", 0))

    marges = []
    for m in range(int(ecart_moyen) - 4, int(ecart_moyen) + 5):
        p = norm_cdf(m + 0.5, ecart_moyen, 12) - norm_cdf(m - 0.5, ecart_moyen, 12)
        if p > 0:
            marges.append({"score": f"+{m}" if m > 0 else str(m), "proba": round(p, 4)})
    marges.sort(key=lambda x: x["proba"], reverse=True)
    top_2_scores = marges[:2]

    total_estime = 180
    score_ht = total_estime / 2
    proj_ht = f"{(score_ht + ecart_moyen/2):.0f}-{(score_ht - ecart_moyen/2):.0f}"

    top_ht_score = {"score": proj_ht, "proba": 0.15}

    marches = data.get("marches", [])
    resultat = []
    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        confiance = proba_calibree if proba_calibree >= 0.5 else (1 - proba_calibree)
        m["confiance"] = round(confiance * 100, 1)
        resultat.append(m)

    data["marches"] = resultat
    data["top_2_scores"] = top_2_scores
    data["top_ht_score"] = top_ht_score
    return data



def _scores_tennis(data):
    tennis_cfg = data.get("tennis_config", {})
    p_set = float(tennis_cfg.get("p_set", 0.5))
    best_of = int(tennis_cfg.get("best_of", 3))
    ligne_jeux = float(tennis_cfg.get("ligne_jeux", 22.5))

    p_opp = 1 - p_set

    scores = []

    if best_of == 3:
        scores.append({"score": "2-0", "proba": round(p_set ** 2, 4)})
        scores.append({"score": "2-1", "proba": round(2 * (p_set ** 2) * p_opp, 4)})
        scores.append({"score": "1-2", "proba": round(2 * p_set * (p_opp ** 2), 4)})
        scores.append({"score": "0-2", "proba": round(p_opp ** 2, 4)})
    else:
        scores.append({"score": "3-0", "proba": round(p_set ** 3, 4)})
        scores.append({"score": "3-1", "proba": round(3 * (p_set ** 3) * p_opp, 4)})
        scores.append({"score": "3-2", "proba": round(6 * (p_set ** 3) * (p_opp ** 2), 4)})
        scores.append({"score": "2-3", "proba": round(6 * (p_set ** 2) * (p_opp ** 3), 4)})
        scores.append({"score": "1-3", "proba": round(3 * p_set * (p_opp ** 3), 4)})
        scores.append({"score": "0-3", "proba": round(p_opp ** 3, 4)})

    scores.sort(key=lambda s: s["proba"], reverse=True)
    top_2_scores = scores[:2]

    if p_set >= 0.5:
        top_ht_score = {"score": "1-0", "proba": round(p_set, 4)}
    else:
        top_ht_score = {"score": "0-1", "proba": round(p_opp, 4)}

    marches = data.get("marches", [])
    resultat = []
    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        confiance = proba_calibree if proba_calibree >= 0.5 else (1 - proba_calibree)
        m["confiance"] = round(confiance * 100, 1)
        resultat.append(m)

    data["marches"] = resultat
    data["top_2_scores"] = top_2_scores
    data["top_ht_score"] = top_ht_score
    data["ligne_jeux_tennis"] = ligne_jeux
    return data



def _scores_hockey(data):
    """
    Prédiction des scores hockey + prédiction par période.

    - Score exact le plus probable (0-0 à 8-8)
    - Top 2 scores exacts
    - Score après 1ère période
    - Scores prédits par période (P1, P2, P3)
    """
    lambda_home = float(data.get("lambda_home", 3.0))
    lambda_away = float(data.get("lambda_away", 2.8))

    # Répartition par période (doit correspondre à 03_market.py)
    repartition = {"p1": 0.28, "p2": 0.35, "p3": 0.37}

    # --- Scores exacts sur le match entier (Poisson simple, pas de DC au hockey) ---
    scores = []
    for i in range(0, 9):
        for j in range(0, 9):
            p = poisson(i, lambda_home) * poisson(j, lambda_away)
            scores.append({"score": f"{i}-{j}", "proba": round(p, 4)})

    scores.sort(key=lambda s: s["proba"], reverse=True)
    top_2_scores = scores[:2]

    # --- Score après 1ère période ---
    lh_p1 = lambda_home * repartition["p1"]
    la_p1 = lambda_away * repartition["p1"]

    scores_p1 = []
    for i in range(0, 5):
        for j in range(0, 5):
            p = poisson(i, lh_p1) * poisson(j, la_p1)
            scores_p1.append({"score": f"{i}-{j}", "proba": round(p, 4)})
    scores_p1.sort(key=lambda s: s["proba"], reverse=True)
    top_ht_score = scores_p1[0]

    # --- Scores par période (P1, P2, P3) ---
    scores_periodes = {}
    for periode, part in repartition.items():
        lh_p = lambda_home * part
        la_p = lambda_away * part

        scores_p = []
        for i in range(0, 5):
            for j in range(0, 5):
                p = poisson(i, lh_p) * poisson(j, la_p)
                scores_p.append({"score": f"{i}-{j}", "proba": round(p, 4)})
        scores_p.sort(key=lambda s: s["proba"], reverse=True)

        nom_periode = {
            "p1": "1ère période",
            "p2": "2ème période",
            "p3": "3ème période",
        }[periode]

        scores_periodes[periode] = {
            "nom": nom_periode,
            "lambda_h": round(lh_p, 3),
            "lambda_a": round(la_p, 3),
            "top_score": scores_p[0],
            "top_3": scores_p[:3],
        }

    # --- Confiance sur chaque marché ---
    marches = data.get("marches", [])
    resultat = []
    for m in marches:
        proba_calibree = float(m.get("proba_calibree", 0.5))
        confiance = proba_calibree if proba_calibree >= 0.5 else (1 - proba_calibree)
        m["confiance"] = round(confiance * 100, 1)
        resultat.append(m)

    data["marches"] = resultat
    data["top_2_scores"] = top_2_scores
    data["top_ht_score"] = top_ht_score
    data["hockey_scores_periodes"] = scores_periodes
    return data
