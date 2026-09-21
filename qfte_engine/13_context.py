"""
Module de contexte QFTE V23.0.
Analyse la forme récente, les confrontations directes (H2H)
et les cotes des 2 équipes pour enrichir le modèle.
"""


def parser_forme(texte):
    """Parse 'V V N D V' → [1, 1, 0, -1, 1]"""
    if not texte:
        return []
    t = texte.upper().replace(",", " ").replace("-", " ").strip()
    resultats = []
    for tok in t.split():
        if tok == "V":
            resultats.append(1)
        elif tok == "N":
            resultats.append(0)
        elif tok == "D":
            resultats.append(-1)
    return resultats


def calculer_score_forme(resultats):
    """
    Score de forme pondéré entre -1 et +1.
    Les matchs récents comptent plus (poids linéaire croissant).
    """
    if not resultats:
        return 0.0
    n = len(resultats)
    poids = list(range(1, n + 1))
    total_poids = sum(poids)
    score = sum(r * p for r, p in zip(resultats, poids)) / total_poids
    return max(-1.0, min(1.0, score))


def parser_scores_h2h(texte):
    """Parse '2-1,1-1,0-2,3-0,1-0' → [(2,1),(1,1),(0,2),(3,0),(1,0)]"""
    if not texte:
        return []
    scores = []
    for partie in texte.replace(";", ",").split(","):
        partie = partie.strip()
        if "-" in partie:
            try:
                h, a = partie.split("-")
                scores.append((int(h.strip()), int(a.strip())))
            except (ValueError, IndexError):
                pass
    return scores


def _forme_combinee(court, global_):
    """Combine forme courte (spécifique) + forme globale (tendance)."""
    if court and global_:
        return court * 0.60 + global_ * 0.40
    return court if court else global_


def analyser_contexte(data):
    match = data.get("match", {})

    # ---------- FORMES ----------
    f_dom_court = calculer_score_forme(parser_forme(match.get("forme_dom_5", "")))
    f_dom_glob = calculer_score_forme(parser_forme(match.get("forme_dom_glob_5", "")))
    f_ext_court = calculer_score_forme(parser_forme(match.get("forme_ext_5", "")))
    f_ext_glob = calculer_score_forme(parser_forme(match.get("forme_ext_glob_5", "")))

    forme_dom = _forme_combinee(f_dom_court, f_dom_glob)
    forme_ext = _forme_combinee(f_ext_court, f_ext_glob)

    # ---------- H2H ----------
    h2h = parser_scores_h2h(match.get("h2h_5", ""))
    h2h_analyse = {}
    if h2h:
        totaux = [h + a for h, a in h2h]
        h2h_analyse = {
            "n": len(h2h),
            "moy_buts": round(sum(totaux) / len(totaux), 2),
            "v_dom": sum(1 for h, a in h2h if h > a),
            "nuls": sum(1 for h, a in h2h if h == a),
            "v_ext": sum(1 for h, a in h2h if h < a),
            "domine": "dom" if sum(1 for h, a in h2h if h > a) > sum(1 for h, a in h2h if h < a)
                       else ("ext" if sum(1 for h, a in h2h if h < a) > sum(1 for h, a in h2h if h > a)
                             else "equilibre"),
        }

    # ---------- COTES 2 ÉQUIPES ----------
    co_1 = float(match.get("cote_ouv_1", 0) or 0)
    cf_1 = float(match.get("cote_ferm_1", 0) or 0)
    co_2 = float(match.get("cote_ouv_2", 0) or 0)
    cf_2 = float(match.get("cote_ferm_2", 0) or 0)

    cotes_analyse = {}
    if cf_1 > 0 and cf_2 > 0:
        p1 = 1 / cf_1
        p2 = 1 / cf_2
        overround = p1 + p2
        p_nul = max(0, 1 - p1 - p2)

        # Mouvement des 2 cotes
        mv_1 = (cf_1 - co_1) / co_1 if co_1 > 0 else 0
        mv_2 = (cf_2 - co_2) / co_2 if co_2 > 0 else 0

        cotes_analyse = {
            "proba_implicite_1": round(p1, 4),
            "proba_implicite_2": round(p2, 4),
            "proba_implicite_nul": round(p_nul, 4),
            "overround": round(overround, 4),
            "marge_book": round((overround - 1) * 100, 2),
            "mouvement_1": round(mv_1, 4),
            "mouvement_2": round(mv_2, 4),
            "sharp_signal": (
                "dom" if mv_1 < mv_2 - 0.02 else
                ("ext" if mv_2 < mv_1 - 0.02 else "aucun")
            ),
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
        "h2h": h2h_analyse,
        "cotes": cotes_analyse,
    }
    return data
