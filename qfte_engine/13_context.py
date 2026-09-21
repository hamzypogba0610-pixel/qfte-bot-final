"""
Module de contexte QFTE V23.0.
Analyse la forme, les scores, le H2H et les cotes des 2 équipes.
"""


def parser_forme(texte):
    if not texte:
        return []
    t = texte.upper().replace(",", " ").replace("-", " ").strip()
    resultats = []
    for tok in t.split():
        if tok == "V": resultats.append(1)
        elif tok == "N": resultats.append(0)
        elif tok == "D": resultats.append(-1)
    return resultats


def calculer_score_forme(resultats):
    if not resultats:
        return 0.0
    n = len(resultats)
    poids = list(range(1, n + 1))
    total_poids = sum(poids)
    score = sum(r * p for r, p in zip(resultats, poids)) / total_poids
    return max(-1.0, min(1.0, score))


def parser_scores(texte):
    """
    Parse '2-1,1-0,3-2' → [(2,1),(1,0),(3,2)]
    Chaque tuple = (buts_pour, buts_contre)
    """
    if not texte:
        return []
    scores = []
    for partie in texte.replace(";", ",").split(","):
        partie = partie.strip()
        if "-" in partie:
            try:
                p, c = partie.split("-")
                scores.append((int(p.strip()), int(c.strip())))
            except (ValueError, IndexError):
                pass
    return scores


def calculer_moyennes(scores):
    """Renvoie {'marques': X, 'encaisses': Y, 'n': N}"""
    if not scores:
        return {"marques": None, "encaisses": None, "n": 0}
    n = len(scores)
    marques = sum(s[0] for s in scores) / n
    encaisses = sum(s[1] for s in scores) / n
    return {
        "marques": round(marques, 3),
        "encaisses": round(encaisses, 3),
        "n": n,
    }


def _blend(court, glob_):
    """Combinaison pondérée : 60% spécifique, 40% global."""
    if court["n"] > 0 and glob_["n"] > 0:
        return {
            "marques": round(court["marques"] * 0.6 + glob_["marques"] * 0.4, 3),
            "encaisses": round(court["encaisses"] * 0.6 + glob_["encaisses"] * 0.4, 3),
            "n": court["n"] + glob_["n"],
        }
    return court if court["n"] > 0 else glob_


def analyser_contexte(data):
    match = data.get("match", {})

    # ---------- FORMES ----------
    f_dom_court = calculer_score_forme(parser_forme(match.get("forme_dom_5", "")))
    f_dom_glob = calculer_score_forme(parser_forme(match.get("forme_dom_glob_5", "")))
    f_ext_court = calculer_score_forme(parser_forme(match.get("forme_ext_5", "")))
    f_ext_glob = calculer_score_forme(parser_forme(match.get("forme_ext_glob_5", "")))

    forme_dom = f_dom_court * 0.60 + f_dom_glob * 0.40 if (f_dom_court or f_dom_glob) else 0
    forme_ext = f_ext_court * 0.60 + f_ext_glob * 0.40 if (f_ext_court or f_ext_glob) else 0

    # ---------- SCORES (moyennes) ----------
    sc_dom = calculer_moyennes(parser_scores(match.get("scores_dom_5", "")))
    sc_dom_glob = calculer_moyennes(parser_scores(match.get("scores_dom_glob_5", "")))
    sc_ext = calculer_moyennes(parser_scores(match.get("scores_ext_5", "")))
    sc_ext_glob = calculer_moyennes(parser_scores(match.get("scores_ext_glob_5", "")))

    moy_dom = _blend(sc_dom, sc_dom_glob)     # équipe 1
    moy_ext = _blend(sc_ext, sc_ext_glob)     # équipe 2

    # ---------- H2H ----------
    h2h = parser_scores(match.get("h2h_5", ""))
    h2h_analyse = {}
    if h2h:
        totaux = [h + a for h, a in h2h]
        h2h_analyse = {
            "n": len(h2h),
            "moy_buts": round(sum(totaux) / len(totaux), 2),
            "v_dom": sum(1 for h, a in h2h if h > a),
            "nuls": sum(1 for h, a in h2h if h == a),
            "v_ext": sum(1 for h, a in h2h if h < a),
            "domine": ("dom" if sum(1 for h, a in h2h if h > a) > sum(1 for h, a in h2h if h < a)
                       else ("ext" if sum(1 for h, a in h2h if h < a) > sum(1 for h, a in h2h if h > a)
                             else "equilibre")),
        }

    # ---------- COTES 2 ÉQUIPES ----------
    co1 = float(match.get("cote_ouv_1", 0) or 0)
    cf1 = float(match.get("cote_ferm_1", 0) or 0)
    co2 = float(match.get("cote_ouv_2", 0) or 0)
    cf2 = float(match.get("cote_ferm_2", 0) or 0)

    cotes_analyse = {}
    if cf1 > 0 and cf2 > 0:
        p1 = 1 / cf1
        p2 = 1 / cf2
        overround = p1 + p2
        p_nul = max(0, 1 - p1 - p2)
        mv1 = (cf1 - co1) / co1 if co1 > 0 else 0
        mv2 = (cf2 - co2) / co2 if co2 > 0 else 0
        cotes_analyse = {
            "proba_implicite_1": round(p1, 4),
            "proba_implicite_2": round(p2, 4),
            "proba_implicite_nul": round(p_nul, 4),
            "overround": round(overround, 4),
            "marge_book": round((overround - 1) * 100, 2),
            "mouvement_1": round(mv1, 4),
            "mouvement_2": round(mv2, 4),
            "sharp_signal": ("dom" if mv1 < mv2 - 0.02 else
                             ("ext" if mv2 < mv1 - 0.02 else "aucun")),
        }

    data["contexte"] = {
        "forme": {
            "dom_court": round(f_dom_court, 3),
            "dom_global": round(f_dom_glob, 3),
            "ext_court": round(f_ext_court, 3),
            "ext_global": round(f_ext_glob, 3),
            "dom_finale": round(forme_dom, 3),
            "ext_finale": round(forme_ext, 3),
        },
        "scores": {
            "dom_marques": moy_dom.get("marques"),
            "dom_encaisses": moy_dom.get("encaisses"),
            "ext_marques": moy_ext.get("marques"),
            "ext_encaisses": moy_ext.get("encaisses"),
        },
        "h2h": h2h_analyse,
        "cotes": cotes_analyse,
    }
    return data
