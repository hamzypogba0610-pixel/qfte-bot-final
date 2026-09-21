import math

TOTAL_BUTS_PAR_COMPETITION = {
    "premier league": 2.9, "ligue 1": 2.7, "liga": 2.6, "serie a": 2.6,
    "bundesliga": 3.1, "eredivisie": 3.0, "champions league": 2.8,
    "europa league": 2.8, "ligue 2": 2.4, "default": 2.7,
}


def poisson(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def proba_resultat_1x2(lh, la, max_buts=8):
    p_home, p_nul, p_away = 0.0, 0.0, 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            p = poisson(i, lh) * poisson(j, la)
            if i > j: p_home += p
            elif i == j: p_nul += p
            else: p_away += p
    return p_home, p_nul, p_away


def estimer_lambda(proba_home_cible, total_buts=2.7):
    lo, hi = 0.20, 0.90
    for _ in range(30):
        mid = (lo + hi) / 2
        lh = total_buts * mid
        la = total_buts * (1 - mid)
        p_h, _, _ = proba_resultat_1x2(lh, la)
        if p_h < proba_home_cible: lo = mid
        else: hi = mid
    mid = (lo + hi) / 2
    return total_buts * mid, total_buts * (1 - mid)


def proba_over(lh, la, ligne=2.5, max_buts=12):
    p = 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            if i + j > ligne:
                p += poisson(i, lh) * poisson(j, la)
    return p


def proba_btts(lh, la):
    return (1 - poisson(0, lh)) * (1 - poisson(0, la))


def norm_cdf(x, mu, sigma):
    z = (x - mu) / sigma
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _total_buts_competition(competition):
    comp = (competition or "").lower().strip()
    for nom, v in TOTAL_BUTS_PAR_COMPETITION.items():
        if nom in comp: return v
    return TOTAL_BUTS_PAR_COMPETITION["default"]


def _marge_dynamique(co, cf):
    if co <= 0: return 0.05
    m = abs(cf - co) / co
    if m < 0.03: return 0.03
    elif m < 0.10: return 0.05
    elif m < 0.20: return 0.06
    return 0.07


def _lambda_depuis_scores(sc_dom, sc_ext, defaut_dom, defaut_ext):
    """
    Modèle attaque × défense :
    λ_home = (buts marqués dom. équipe1 + buts encaissés ext. équipe2) / 2
    λ_away = (buts marqués ext. équipe2 + buts encaissés dom. équipe1) / 2
    """
    if sc_dom.get("marques") is None or sc_ext.get("marques") is None:
        return defaut_dom, defaut_ext

    dom_att = sc_dom.get("marques")
    dom_def = sc_dom.get("encaisses")
    ext_att = sc_ext.get("marques")
    ext_def = sc_ext.get("encaisses")

    lam_h = (dom_att + ext_def) / 2
    lam_a = (ext_att + dom_def) / 2

    return max(0.20, lam_h), max(0.20, lam_a)


def analyser_marche(data):
    match = data.get("match", {})
    if match.get("sport") == "basket":
        return _analyser_basket(data, match)
    return _analyser_football(data, match)


def _analyser_football(data, match):
    co = float(match.get("cote_ouverture", 2.0))
    cf = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))
    competition = match.get("competition", "")

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})
    scores_ctx = contexte.get("scores", {})

    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_ah = max(0.30, min(0.80, proba_demargee + bonus_sharp))

    # Total de buts (H2H si dispo, sinon compétition)
    total_buts = _total_buts_competition(competition)
    if h2h.get("n", 0) >= 3:
        total_buts = (total_buts * 0.5) + (h2h["moy_buts"] * 0.5)

    total_avec_av = total_buts + 0.20
    lambda_poiss_h, lambda_poiss_a = estimer_lambda(proba_ah, total_buts=total_avec_av)

    # ---------- Modèle attaque × défense (scores réels) ----------
    sc_dom = {
        "marques": scores_ctx.get("dom_marques"),
        "encaisses": scores_ctx.get("dom_encaisses"),
    }
    sc_ext = {
        "marques": scores_ctx.get("ext_marques"),
        "encaisses": scores_ctx.get("ext_encaisses"),
    }
    lambda_data_h, lambda_data_a = _lambda_depuis_scores(
        sc_dom, sc_ext, lambda_poiss_h, lambda_poiss_a
    )

    has_data_scores = scores_ctx.get("dom_marques") is not None and scores_ctx.get("ext_marques") is not None

    # Blend : 50% Poisson (marché) + 50% data (scores réels) si dispo
    if has_data_scores:
        lambda_home = 0.50 * lambda_poiss_h + 0.50 * lambda_data_h
        lambda_away = 0.50 * lambda_poiss_a + 0.50 * lambda_data_a
    else:
        lambda_home = lambda_poiss_h
        lambda_away = lambda_poiss_a

    # Ajustements forme (±0.25)
    lambda_home += float(forme.get("dom_finale", 0)) * 0.25
    lambda_away += float(forme.get("ext_finale", 0)) * 0.25

    # Ajustement H2H
    if h2h.get("domine") == "dom":
        lambda_home += 0.10; lambda_away -= 0.05
    elif h2h.get("domine") == "ext":
        lambda_away += 0.10; lambda_home -= 0.05

    lambda_home = max(0.20, lambda_home)
    lambda_away = max(0.20, lambda_away)

    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_btts_val = proba_btts(lambda_home, lambda_away)

    cote_ah_f = float(match.get("cote_ah") or (1 / (proba_ah * (1 + marge))))
    cote_over_f = float(match.get("cote_over25") or (1 / (proba_over25 * (1 + marge))))
    cote_btts_f = float(match.get("cote_btts") or (1 / (proba_btts_val * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(lambda_home, 3)
    data["lambda_away"] = round(lambda_away, 3)
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_buts, 2)
    data["modele_lambda"] = "mixte (marché + scores)" if has_data_scores else "marché seul"

    data["marches"] = [
        {"nom": "Handicap Asiatique -0.5", "selection": match.get("equipe1", "-"),
         "cote": round(cote_ah_f, 2), "cote_ouverture": round(cote_ah_f * 1.02, 2),
         "proba_juste": round(proba_ah, 4), "mouvement": round(mouvement, 4)},
        {"nom": "Over/Under 2.5", "selection": "Over 2.5",
         "cote": round(cote_over_f, 2), "cote_ouverture": round(cote_over_f * 1.02, 2),
         "proba_juste": round(proba_over25, 4), "mouvement": round(mouvement * 0.8, 4)},
        {"nom": "BTTS", "selection": "Oui",
         "cote": round(cote_btts_f, 2), "cote_ouverture": round(cote_btts_f * 1.02, 2),
         "proba_juste": round(proba_btts_val, 4), "mouvement": round(mouvement * 0.6, 4)},
    ]
    return data


def _analyser_basket(data, match):
    co = float(match.get("cote_ouverture", 1.85))
    cf = float(match.get("cote_actuelle", 1.85))
    volume = float(match.get("volume", 50000))
    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})

    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_ml = max(0.20, min(0.85, proba_demargee + bonus_sharp))

    total_points = 180.0
    lo, hi = -30.0, 30.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = 1 - norm_cdf(0, mid, 12)
        if p < proba_ml: lo = mid
        else: hi = mid
    ecart = (lo + hi) / 2

    ecart += float(forme.get("dom_finale", 0)) * 3
    ecart -= float(forme.get("ext_finale", 0)) * 3

    proba_over_tot = 1 - norm_cdf(180.5, total_points, 18)
    proba_over_tot = max(0.30, min(0.70, proba_over_tot))
    proba_spread = 1 - norm_cdf(4.5, ecart, 12)
    proba_spread = max(0.20, min(0.85, proba_spread))

    cote_ml_f = float(match.get("cote_ah") or (1 / (proba_ml * (1 + marge))))
    cote_sp_f = float(match.get("cote_over25") or (1 / (proba_spread * (1 + marge))))
    cote_tot_f = float(match.get("cote_btts") or (1 / (proba_over_tot * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(ecart, 2)
    data["lambda_away"] = 0
    data["marge_estimee"] = marge

    data["marches"] = [
        {"nom": "Money Line", "selection": match.get("equipe1", "-"),
         "cote": round(cote_ml_f, 2), "cote_ouverture": round(cote_ml_f * 1.02, 2),
         "proba_juste": round(proba_ml, 4), "mouvement": round(mouvement, 4)},
        {"nom": "Spread -4.5", "selection": match.get("equipe1", "-"),
         "cote": round(cote_sp_f, 2), "cote_ouverture": round(cote_sp_f * 1.02, 2),
         "proba_juste": round(proba_spread, 4), "mouvement": round(mouvement * 0.8, 4)},
        {"nom": "Total Points Over 180.5", "selection": "Over 180.5",
         "cote": round(cote_tot_f, 2), "cote_ouverture": round(cote_tot_f * 1.02, 2),
         "proba_juste": round(proba_over_tot, 4), "mouvement": round(mouvement * 0.6, 4)},
    ]
    return data
