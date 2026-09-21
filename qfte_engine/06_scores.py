import math


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def predire_scores(data):
    lambda_home = float(data.get("lambda_home", 1.4))
    lambda_away = float(data.get("lambda_away", 1.3))

    # --- 2 scores exacts les plus probables ---
    scores = []
    for i in range(0, 6):
        for j in range(0, 6):
            p = poisson(i, lambda_home) * poisson(j, lambda_away)
            scores.append({"score": f"{i}-{j}", "proba": round(p, 4)})
    scores.sort(key=lambda s: s["proba"], reverse=True)
    top_2_scores = scores[:2]

    # --- Score à la mi-temps le plus probable (~45% des buts en 1ère MT) ---
    lh_ht = lambda_home * 0.45
    la_ht = lambda_away * 0.45

    scores_ht = []
    for i in range(0, 4):
        for j in range(0, 4):
            p = poisson(i, lh_ht) * poisson(j, la_ht)
            scores_ht.append({"score": f"{i}-{j}", "proba": round(p, 4)})
    scores_ht.sort(key=lambda s: s["proba"], reverse=True)
    top_ht_score = scores_ht[0]

    # --- Ajout de la confiance sur chaque marché ---
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
