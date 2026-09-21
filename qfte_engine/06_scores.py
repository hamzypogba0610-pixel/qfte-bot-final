import math


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def rho_adaptatif(lh, la):
    """
    ρ Dixon-Coles adaptatif selon le total de buts attendu :
    - Match défensif (total < 2.3) → ρ = -0.15 (correction forte)
    - Match moyen    (total 2.3-3.0) → ρ = -0.10 (valeur standard)
    - Match offensif (total > 3.0) → ρ = -0.05 (correction faible)
    """
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

    top_ht_score = {
        "score": proj_ht,
        "proba": 0.15,
    }

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
