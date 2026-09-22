import math

TOTAL_BUTS_PAR_COMPETITION = {
    "premier league": 2.9, "ligue 1": 2.7, "liga": 2.6, "serie a": 2.6,
    "bundesliga": 3.1, "eredivisie": 3.0, "champions league": 2.8,
    "europa league": 2.8, "ligue 2": 2.4, "default": 2.7,
}

# ============================================================
# CONFIGURATION BASKET (par compétition)
# ============================================================
BASKET_CONFIG = {
    "nba": {
        "total_defaut": 220.5,       # Ligne totale NBA typique
        "sigma_total": 19.0,         # Variabilité du total
        "sigma_ecart": 13.5,         # Variabilité de l'écart
        "home_court_advantage": 2.5, # Avantage domicile NBA
    },
    "euroleague": {
        "total_defaut": 160.5,
        "sigma_total": 14.0,
        "sigma_ecart": 10.5,
        "home_court_advantage": 3.0,
    },
    "euro": {
        "total_defaut": 160.5,
        "sigma_total": 14.0,
        "sigma_ecart": 10.5,
        "home_court_advantage": 3.0,
    },
    "default": {
        "total_defaut": 180.5,       # Compromis par défaut
        "sigma_total": 17.0,
        "sigma_ecart": 12.0,
        "home_court_advantage": 2.8,
    },
}


def _config_basket(competition):
    """Détecte le type de basket selon la compétition."""
    comp = (competition or "").lower().strip()
    if "nba" in comp:
        return BASKET_CONFIG["nba"]
    if "euroleague" in comp or "euroligue" in comp:
        return BASKET_CONFIG["euroleague"]
    if "euro" in comp:
        return BASKET_CONFIG["euro"]
    return BASKET_CONFIG["default"]


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

    total_buts = _total_buts_competition(competition)
    if h2h.get("n", 0) >= 3:
        total_buts = (total_buts * 0.5) + (h2h["moy_buts"] * 0.5)

    total_avec_av = total_buts + 0.20
    lambda_poiss_h, lambda_poiss_a = estimer_lambda(proba_ah, total_buts=total_avec_av)

    sc_dom = {"marques": scores_ctx.get("dom_marques"), "encaisses": scores_ctx.get("dom_encaisses")}
    sc_ext = {"marques": scores_ctx.get("ext_marques"), "encaisses": scores_ctx.get("ext_encaisses")}
    lambda_data_h, lambda_data_a = _lambda_depuis_scores(sc_dom, sc_ext, lambda_poiss_h, lambda_poiss_a)

    has_data = scores_ctx.get("dom_marques") is not None and scores_ctx.get("ext_marques") is not None

    if has_data:
        lambda_home = 0.50 * lambda_poiss_h + 0.50 * lambda_data_h
        lambda_away = 0.50 * lambda_poiss_a + 0.50 * lambda_data_a
    else:
        lambda_home = lambda_poiss_h
        lambda_away = lambda_poiss_a

    lambda_home += float(forme.get("dom_finale", 0)) * 0.25
    lambda_away += float(forme.get("ext_finale", 0)) * 0.25

    if h2h.get("domine") == "dom":
        lambda_home += 0.10; lambda_away -= 0.05
    elif h2h.get("domine") == "ext":
        lambda_away += 0.10; lambda_home -= 0.05

    lambda_home = max(0.20, lambda_home)
    lambda_away = max(0.20, lambda_away)

    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_under25 = 1 - proba_over25
    proba_btts_val = proba_btts(lambda_home, lambda_away)

    # --- Auto-détection Over/Under 2.5 ---
    cote_over25_brute = float(match.get("cote_over25") or 0)
    if cote_over25_brute <= 0:
        cote_over25_brute = 1 / (proba_over25 * (1 + marge))

    cote_under25 = 1 / (proba_under25 * (1 + marge)) if proba_under25 > 0 else 10.0

    ev_over = (proba_over25 * cote_over25_brute) - 1
    ev_under = (proba_under25 * cote_under25) - 1

    if ev_over >= ev_under:
        selection_ou = "Over 2.5"
        proba_ou = proba_over25
        cote_ou = cote_over25_brute
    else:
        selection_ou = "Under 2.5"
        proba_ou = proba_under25
        cote_ou = cote_under25

    cote_ah_f = float(match.get("cote_ah") or (1 / (proba_ah * (1 + marge))))
    cote_btts_f = float(match.get("cote_btts") or (1 / (proba_btts_val * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(lambda_home, 3)
    data["lambda_away"] = round(lambda_away, 3)
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_buts, 2)
    data["modele_lambda"] = "mixte (marché + scores)" if has_data else "marché seul"
    data["auto_ou"] = {
        "ev_over": round(ev_over, 4),
        "ev_under": round(ev_under, 4),
        "choix": selection_ou,
    }

    data["marches"] = [
        {"nom": "Handicap Asiatique -0.5", "selection": match.get("equipe1", "-"),
         "cote": round(cote_ah_f, 2), "cote_ouverture": round(cote_ah_f * 1.02, 2),
         "proba_juste": round(proba_ah, 4), "mouvement": round(mouvement, 4)},
        {"nom": "Over/Under 2.5", "selection": selection_ou,
         "cote": round(cote_ou, 2), "cote_ouverture": round(cote_ou * 1.02, 2),
         "proba_juste": round(proba_ou, 4), "mouvement": round(mouvement * 0.8, 4)},
        {"nom": "BTTS", "selection": "Oui",
         "cote": round(cote_btts_f, 2), "cote_ouverture": round(cote_btts_f * 1.02, 2),
         "proba_juste": round(proba_btts_val, 4), "mouvement": round(mouvement * 0.6, 4)},
    ]
    return data



def _analyser_basket(data, match):
    """
    Analyse basket améliorée QFTE V23.0.

    Améliorations :
    - Détection NBA / EuroLeague / défaut
    - Sigma (σ) adaptatif par type de compétition
    - Ligne totale dynamique (NBA ≈ 220, Euro ≈ 160)
    - Home court advantage spécifique
    - Ajustement par la forme et le H2H
    """
    co = float(match.get("cote_ouverture", 1.85))
    cf = float(match.get("cote_actuelle", 1.85))
    volume = float(match.get("volume", 50000))
    competition = match.get("competition", "")

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})

    # --- Configuration spécifique au type de basket ---
    cfg = _config_basket(competition)
    ligne_totale = cfg["total_defaut"]
    sigma_total = cfg["sigma_total"]
    sigma_ecart = cfg["sigma_ecart"]
    home_advantage = cfg["home_court_advantage"]

    # --- Marge et proba ML ---
    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_ml = max(0.20, min(0.85, proba_demargee + bonus_sharp))

    # --- Estimation de l'écart moyen via la loi Normale ---
    # On cherche μ tel que P(écart > 0) = proba_ml avec σ = sigma_ecart
    lo, hi = -40.0, 40.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = 1 - norm_cdf(0, mid, sigma_ecart)
        if p < proba_ml:
            lo = mid
        else:
            hi = mid
    ecart_moyen = (lo + hi) / 2

    # --- Ajustement par la forme ---
    forme_dom = float(forme.get("dom_finale", 0))
    forme_ext = float(forme.get("ext_finale", 0))
    ecart_moyen += forme_dom * 3.5
    ecart_moyen -= forme_ext * 3.5

    # --- Ajustement par le H2H ---
    if h2h.get("domine") == "dom":
        ecart_moyen += 2.0
    elif h2h.get("domine") == "ext":
        ecart_moyen -= 2.0

    # --- Ajustement home court advantage ---
    # (déjà partiellement inclus dans le calcul de la proba ML,
    #  mais on le renforce sur l'écart)
    ecart_moyen += home_advantage * 0.4

    # --- Estimation du total de points via les moyennes de scores si dispo ---
    scores_ctx = contexte.get("scores", {})
    dom_marques = scores_ctx.get("dom_marques")
    ext_marques = scores_ctx.get("ext_marques")
    dom_encaisses = scores_ctx.get("dom_encaisses")
    ext_encaisses = scores_ctx.get("ext_encaisses")

    has_data_scores = (dom_marques is not None and ext_marques is not None
                       and dom_encaisses is not None and ext_encaisses is not None)

    if has_data_scores:
        # Estimation : (marqués par dom + encaissés par ext) / 2 → points dom
        #              (marqués par ext + encaissés par dom) / 2 → points ext
        pts_dom_estimes = (float(dom_marques) + float(ext_encaisses)) / 2
        pts_ext_estimes = (float(ext_marques) + float(dom_encaisses)) / 2
        total_points_estime = pts_dom_estimes + pts_ext_estimes
        # Ajustement vers la ligne de la compétition (blend)
        total_points_estime = 0.6 * total_points_estime + 0.4 * ligne_totale
    else:
        total_points_estime = ligne_totale

    # --- Ajustement du total par la forme offensive ---
    total_points_estime += (forme_dom + forme_ext) * 1.5
    total_points_estime = max(ligne_totale * 0.75, min(ligne_totale * 1.25, total_points_estime))

    # --- Calcul des probas via la loi Normale ---
    proba_over_tot = 1 - norm_cdf(ligne_totale, total_points_estime, sigma_total)
    proba_over_tot = max(0.15, min(0.85, proba_over_tot))
    proba_under_tot = 1 - proba_over_tot

    # Spread -4.5 : équipe 1 doit gagner par 5+ (P(écart > 4.5))
    proba_spread = 1 - norm_cdf(4.5, ecart_moyen, sigma_ecart)
    proba_spread = max(0.10, min(0.90, proba_spread))

    # --- Auto-détection Over/Under Total Points ---
    cote_over_brute = float(match.get("cote_over25") or 0)
    if cote_over_brute <= 0:
        cote_over_brute = 1 / (proba_over_tot * (1 + marge))
    cote_under_tot = 1 / (proba_under_tot * (1 + marge)) if proba_under_tot > 0 else 10.0

    ev_over = (proba_over_tot * cote_over_brute) - 1
    ev_under = (proba_under_tot * cote_under_tot) - 1

    if ev_over >= ev_under:
        selection_ou = "Over " + str(ligne_totale)
        proba_ou = proba_over_tot
        cote_ou = cote_over_brute
    else:
        selection_ou = "Under " + str(ligne_totale)
        proba_ou = proba_under_tot
        cote_ou = cote_under_tot

    # --- Cotes finales ---
    cote_ml_f = float(match.get("cote_ah") or (1 / (proba_ml * (1 + marge))))
    cote_sp_f = float(match.get("cote_over25") or (1 / (proba_spread * (1 + marge))))

    # --- Stockage ---
    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(ecart_moyen, 2)
    data["lambda_away"] = 0
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_points_estime, 2)
    data["modele_lambda"] = "Normale (basket " + competition + ")"
    data["basket_config"] = {
        "type": "NBA" if "nba" in (competition or "").lower() else
                ("EuroLeague" if "euro" in (competition or "").lower() else "Standard"),
        "ligne_totale": ligne_totale,
        "sigma_ecart": sigma_ecart,
        "sigma_total": sigma_total,
        "home_advantage": home_advantage,
    }
    data["auto_ou"] = {
        "ev_over": round(ev_over, 4),
        "ev_under": round(ev_under, 4),
        "choix": selection_ou,
    }

    data["marches"] = [
        {
            "nom": "Money Line",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_ml_f, 2),
            "cote_ouverture": round(cote_ml_f * 1.02, 2),
            "proba_juste": round(proba_ml, 4),
            "mouvement": round(mouvement, 4),
        },
        {
            "nom": "Spread -4.5",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_sp_f, 2),
            "cote_ouverture": round(cote_sp_f * 1.02, 2),
            "proba_juste": round(proba_spread, 4),
            "mouvement": round(mouvement * 0.8, 4),
        },
        {
            "nom": "Total Points",
            "selection": selection_ou,
            "cote": round(cote_ou, 2),
            "cote_ouverture": round(cote_ou * 1.02, 2),
            "proba_juste": round(proba_ou, 4),
            "mouvement": round(mouvement * 0.6, 4),
        },
    ]
    return data
