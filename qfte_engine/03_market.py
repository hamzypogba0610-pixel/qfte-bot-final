import math
import importlib
_elo_tennis = importlib.import_module("qfte_engine.18_elo_tennis")

TOTAL_BUTS_PAR_COMPETITION = {
    "premier league": 2.9, "ligue 1": 2.7, "liga": 2.6, "serie a": 2.6,
    "bundesliga": 3.1, "eredivisie": 3.0, "champions league": 2.8,
    "europa league": 2.8, "ligue 2": 2.4, "default": 2.7,
}

BASKET_CONFIG = {
    "nba": {"total_defaut": 220.5, "sigma_total": 19.0, "sigma_ecart": 13.5, "home_court_advantage": 2.5},
    "euroleague": {"total_defaut": 160.5, "sigma_total": 14.0, "sigma_ecart": 10.5, "home_court_advantage": 3.0},
    "euro": {"total_defaut": 160.5, "sigma_total": 14.0, "sigma_ecart": 10.5, "home_court_advantage": 3.0},
    "default": {"total_defaut": 180.5, "sigma_total": 17.0, "sigma_ecart": 12.0, "home_court_advantage": 2.8},
}

TENNIS_CONFIG = {
    "grand chelem": {"best_of": 5, "ligne_jeux": 32.5, "sigma_jeux": 6.0, "moyenne_jeux_set": 9.5},
    "atp": {"best_of": 3, "ligne_jeux": 22.5, "sigma_jeux": 4.5, "moyenne_jeux_set": 9.5},
    "wta": {"best_of": 3, "ligne_jeux": 21.5, "sigma_jeux": 4.5, "moyenne_jeux_set": 9.0},
    "default": {"best_of": 3, "ligne_jeux": 22.5, "sigma_jeux": 4.5, "moyenne_jeux_set": 9.5},
}

# ============================================================
# CONFIGURATION HOCKEY SUR GLACE
# ============================================================
HOCKEY_CONFIG = {
    "nhl": {
        "total_defaut": 5.8,
        "home_advantage": 0.20,
        "ligne_periode": 1.5,
    },
    "khl": {
        "total_defaut": 4.8,
        "home_advantage": 0.15,
        "ligne_periode": 1.5,
    },
    "shl": {
        "total_defaut": 5.0,
        "home_advantage": 0.18,
        "ligne_periode": 1.5,
    },
    "liiga": {
        "total_defaut": 5.0,
        "home_advantage": 0.18,
        "ligne_periode": 1.5,
    },
    "del": {
        "total_defaut": 5.2,
        "home_advantage": 0.18,
        "ligne_periode": 1.5,
    },
    "world cup": {
        "total_defaut": 5.5,
        "home_advantage": 0.15,
        "ligne_periode": 1.5,
    },
    "olympic": {
        "total_defaut": 5.5,
        "home_advantage": 0.15,
        "ligne_periode": 1.5,
    },
    "default": {
        "total_defaut": 5.5,
        "home_advantage": 0.18,
        "ligne_periode": 1.5,
    },
}

# Répartition des buts par période (statistiques NHL)
REPARTITION_PERIODES = {
    "p1": 0.28,
    "p2": 0.35,
    "p3": 0.37,
}


def _config_basket(competition):
    comp = (competition or "").lower().strip()
    if "nba" in comp: return BASKET_CONFIG["nba"]
    if "euroleague" in comp or "euroligue" in comp: return BASKET_CONFIG["euroleague"]
    if "euro" in comp: return BASKET_CONFIG["euro"]
    return BASKET_CONFIG["default"]


def _config_tennis(competition):
    comp = (competition or "").lower().strip()
    if any(x in comp for x in ["roland", "wimbledon", "us open", "australian", "grand chelem", "grand slam"]):
        return TENNIS_CONFIG["grand chelem"]
    if "wta" in comp: return TENNIS_CONFIG["wta"]
    if "atp" in comp: return TENNIS_CONFIG["atp"]
    return TENNIS_CONFIG["default"]


def _config_hockey(competition):
    """Détecte la config hockey selon la compétition."""
    comp = (competition or "").lower().strip()
    if "nhl" in comp:
        return HOCKEY_CONFIG["nhl"]
    if "khl" in comp:
        return HOCKEY_CONFIG["khl"]
    if "shl" in comp or "suède" in comp or "sweden" in comp:
        return HOCKEY_CONFIG["shl"]
    if "liiga" in comp or "finlande" in comp or "finland" in comp:
        return HOCKEY_CONFIG["liiga"]
    if "del" in comp or "allemagne" in comp or "germany" in comp:
        return HOCKEY_CONFIG["del"]
    if "world cup" in comp or "coupe du monde" in comp:
        return HOCKEY_CONFIG["world cup"]
    if "olympic" in comp or "jo" in comp or "olympique" in comp:
        return HOCKEY_CONFIG["olympic"]
    return HOCKEY_CONFIG["default"]


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
    sport = match.get("sport", "football")
    if sport == "basket":
        return _analyser_basket(data, match)
    if sport == "tennis":
        return _analyser_tennis(data, match)
    if sport == "hockey":
        return _analyser_hockey(data, match)
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

    calendrier = data.get("calendrier", {})
    impact_cal_dom = 0.0
    impact_cal_ext = 0.0
    if calendrier:
        impact_cal_dom = float(calendrier.get("dom", {}).get("impact_lambda", 0) or 0)
        impact_cal_ext = float(calendrier.get("ext", {}).get("impact_lambda", 0) or 0)
        lambda_home += impact_cal_dom
        lambda_away += impact_cal_ext

    lambda_home = max(0.20, lambda_home)
    lambda_away = max(0.20, lambda_away)

    proba_over25 = proba_over(lambda_home, lambda_away, 2.5)
    proba_under25 = 1 - proba_over25
    proba_btts_val = proba_btts(lambda_home, lambda_away)

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
    data["modele_lambda"] = "mixte + calendrier" if has_data else "marché + calendrier"
    data["impact_calendrier_lambda"] = {
        "dom": round(impact_cal_dom, 3),
        "ext": round(impact_cal_ext, 3),
    }
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
    co = float(match.get("cote_ouverture", 1.85))
    cf = float(match.get("cote_actuelle", 1.85))
    volume = float(match.get("volume", 50000))
    competition = match.get("competition", "")

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})

    cfg = _config_basket(competition)
    ligne_totale = cfg["total_defaut"]
    sigma_total = cfg["sigma_total"]
    sigma_ecart = cfg["sigma_ecart"]
    home_advantage = cfg["home_court_advantage"]

    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_ml = max(0.20, min(0.85, proba_demargee + bonus_sharp))

    lo, hi = -40.0, 40.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = 1 - norm_cdf(0, mid, sigma_ecart)
        if p < proba_ml: lo = mid
        else: hi = mid
    ecart_moyen = (lo + hi) / 2

    forme_dom = float(forme.get("dom_finale", 0))
    forme_ext = float(forme.get("ext_finale", 0))
    ecart_moyen += forme_dom * 3.5
    ecart_moyen -= forme_ext * 3.5

    if h2h.get("domine") == "dom":
        ecart_moyen += 2.0
    elif h2h.get("domine") == "ext":
        ecart_moyen -= 2.0

    ecart_moyen += home_advantage * 0.4

    calendrier_basket = data.get("calendrier_basket", {})
    impact_cal_dom_pts = 0.0
    impact_cal_ext_pts = 0.0
    if calendrier_basket:
        impact_cal_dom_pts = float(calendrier_basket.get("dom", {}).get("score_points", 0) or 0)
        impact_cal_ext_pts = float(calendrier_basket.get("ext", {}).get("score_points", 0) or 0)
        diff_pts = impact_cal_dom_pts - impact_cal_ext_pts
        ecart_moyen += diff_pts

    scores_ctx = contexte.get("scores", {})
    dom_marques = scores_ctx.get("dom_marques")
    ext_marques = scores_ctx.get("ext_marques")
    dom_encaisses = scores_ctx.get("dom_encaisses")
    ext_encaisses = scores_ctx.get("ext_encaisses")

    has_data_scores = (dom_marques is not None and ext_marques is not None
                       and dom_encaisses is not None and ext_encaisses is not None)

    if has_data_scores:
        pts_dom_estimes = (float(dom_marques) + float(ext_encaisses)) / 2
        pts_ext_estimes = (float(ext_marques) + float(dom_encaisses)) / 2
        total_points_estime = pts_dom_estimes + pts_ext_estimes
        total_points_estime = 0.6 * total_points_estime + 0.4 * ligne_totale
    else:
        total_points_estime = ligne_totale

    total_points_estime += (forme_dom + forme_ext) * 1.5

    impact_cal_total = (impact_cal_dom_pts + impact_cal_ext_pts) * 0.3
    total_points_estime += impact_cal_total

    total_points_estime = max(ligne_totale * 0.75, min(ligne_totale * 1.25, total_points_estime))

    proba_over_tot = 1 - norm_cdf(ligne_totale, total_points_estime, sigma_total)
    proba_over_tot = max(0.15, min(0.85, proba_over_tot))
    proba_under_tot = 1 - proba_over_tot

    proba_spread = 1 - norm_cdf(4.5, ecart_moyen, sigma_ecart)
    proba_spread = max(0.10, min(0.90, proba_spread))

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

    cote_ml_f = float(match.get("cote_ah") or (1 / (proba_ml * (1 + marge))))
    cote_sp_f = float(match.get("cote_over25") or (1 / (proba_spread * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(ecart_moyen, 2)
    data["lambda_away"] = 0
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_points_estime, 2)
    data["modele_lambda"] = "Normale + calendrier (basket " + competition + ")"
    data["basket_config"] = {
        "type": "NBA" if "nba" in (competition or "").lower() else
                ("EuroLeague" if "euro" in (competition or "").lower() else "Standard"),
        "ligne_totale": ligne_totale,
        "sigma_ecart": sigma_ecart,
        "sigma_total": sigma_total,
        "home_advantage": home_advantage,
    }
    data["impact_calendrier_basket"] = {
        "dom_points": round(impact_cal_dom_pts, 2),
        "ext_points": round(impact_cal_ext_pts, 2),
        "diff_ecart": round(impact_cal_dom_pts - impact_cal_ext_pts, 2),
        "impact_total": round(impact_cal_total, 2),
    }
    data["auto_ou"] = {
        "ev_over": round(ev_over, 4),
        "ev_under": round(ev_under, 4),
        "choix": selection_ou,
    }

    data["marches"] = [
        {"nom": "Money Line", "selection": match.get("equipe1", "-"),
         "cote": round(cote_ml_f, 2), "cote_ouverture": round(cote_ml_f * 1.02, 2),
         "proba_juste": round(proba_ml, 4), "mouvement": round(mouvement, 4)},
        {"nom": "Spread -4.5", "selection": match.get("equipe1", "-"),
         "cote": round(cote_sp_f, 2), "cote_ouverture": round(cote_sp_f * 1.02, 2),
         "proba_juste": round(proba_spread, 4), "mouvement": round(mouvement * 0.8, 4)},
        {"nom": "Total Points", "selection": selection_ou,
         "cote": round(cote_ou, 2), "cote_ouverture": round(cote_ou * 1.02, 2),
         "proba_juste": round(proba_ou, 4), "mouvement": round(mouvement * 0.6, 4)},
    ]
    return data



def _analyser_tennis(data, match):
    co = float(match.get("cote_ouverture", 1.85))
    cf = float(match.get("cote_actuelle", 1.85))
    volume = float(match.get("volume", 50000))
    competition = match.get("competition", "")
    surface = match.get("surface", "dur")

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})

    cfg = _config_tennis(competition)
    best_of = cfg["best_of"]
    ligne_jeux = cfg["ligne_jeux"]
    sigma_jeux = cfg["sigma_jeux"]
    moyenne_jeux_set = cfg["moyenne_jeux_set"]

    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_cote = max(0.10, min(0.90, proba_demargee + bonus_sharp))

    joueur1 = match.get("equipe1", "")
    joueur2 = match.get("equipe2", "")
    elo_info = _elo_tennis.proba_elo(joueur1, joueur2, surface)

    blend = _elo_tennis.blend_elo_cote(
        proba_cote,
        elo_info["proba"],
        elo_info["confiance_elo"],
    )
    proba_ml = blend["proba_finale"]

    momentum_j1 = _elo_tennis.calculer_momentum(joueur1, n_recent=5)
    momentum_j2 = _elo_tennis.calculer_momentum(joueur2, n_recent=5)
    diff_momentum = momentum_j1["score"] - momentum_j2["score"]
    impact_momentum = diff_momentum * 0.03
    proba_ml += impact_momentum

    matchs_7j_j1 = int(match.get("matchs_7j_j1", 0) or 0)
    matchs_7j_j2 = int(match.get("matchs_7j_j2", 0) or 0)
    matchs_14j_j1 = int(match.get("matchs_14j_j1", 0) or 0)
    matchs_14j_j2 = int(match.get("matchs_14j_j2", 0) or 0)

    fatigue_j1 = _elo_tennis.calculer_fatigue(matchs_7j_j1, matchs_14j_j1)
    fatigue_j2 = _elo_tennis.calculer_fatigue(matchs_7j_j2, matchs_14j_j2)
    diff_fatigue = fatigue_j1["score"] - fatigue_j2["score"]
    impact_fatigue = diff_fatigue * 0.02
    proba_ml += impact_fatigue

    forme_dom = float(forme.get("dom_finale", 0))
    forme_ext = float(forme.get("ext_finale", 0))
    proba_ml += (forme_dom - forme_ext) * 0.02

    proba_ml = max(0.10, min(0.90, proba_ml))

    def proba_match(p_set):
        if best_of == 3:
            return (p_set ** 2) + 2 * (p_set ** 2) * (1 - p_set)
        else:
            return (p_set ** 3) + 3 * (p_set ** 3) * (1 - p_set) + 6 * (p_set ** 3) * ((1 - p_set) ** 2)

    lo, hi = 0.05, 0.95
    for _ in range(50):
        mid = (lo + hi) / 2
        p = proba_match(mid)
        if p < proba_ml:
            lo = mid
        else:
            hi = mid
    p_set = (lo + hi) / 2

    if best_of == 3:
        proba_2_0 = p_set ** 2
        proba_2_1 = 2 * (p_set ** 2) * (1 - p_set)
    else:
        proba_3_0 = p_set ** 3
        proba_3_1 = 3 * (p_set ** 3) * (1 - p_set)
        proba_3_2 = 6 * (p_set ** 3) * ((1 - p_set) ** 2)
        proba_2_0 = proba_3_0
        proba_2_1 = proba_3_1

    if best_of == 3:
        nb_sets_moyen = 2 * (proba_2_0) + 3 * (proba_2_1) + 2 * (1 - proba_ml)
    else:
        nb_sets_moyen = 3 * proba_3_0 + 4 * proba_3_1 + 5 * proba_3_2

    total_jeux_estime = nb_sets_moyen * moyenne_jeux_set
    total_jeux_estime = max(ligne_jeux * 0.7, min(ligne_jeux * 1.3, total_jeux_estime))

    proba_over_jeux = 1 - norm_cdf(ligne_jeux, total_jeux_estime, sigma_jeux)
    proba_over_jeux = max(0.15, min(0.85, proba_over_jeux))
    proba_under_jeux = 1 - proba_over_jeux

    cote_over_brute = float(match.get("cote_over25") or 0)
    if cote_over_brute <= 0:
        cote_over_brute = 1 / (proba_over_jeux * (1 + marge))
    cote_under_jeux = 1 / (proba_under_jeux * (1 + marge)) if proba_under_jeux > 0 else 10.0

    ev_over = (proba_over_jeux * cote_over_brute) - 1
    ev_under = (proba_under_jeux * cote_under_jeux) - 1

    if ev_over >= ev_under:
        selection_ou = "Over " + str(ligne_jeux)
        proba_ou = proba_over_jeux
        cote_ou = cote_over_brute
    else:
        selection_ou = "Under " + str(ligne_jeux)
        proba_ou = proba_under_jeux
        cote_ou = cote_under_jeux

    cote_ml_f = float(match.get("cote_ah") or (1 / (proba_ml * (1 + marge))))
    cote_score_f = float(match.get("cote_btts") or (1 / (proba_2_0 * (1 + marge))))

    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(p_set, 4)
    data["lambda_away"] = round(1 - p_set, 4)
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_jeux_estime, 2)
    data["modele_lambda"] = "Binomial + Elo + Momentum + Fatigue (best of " + str(best_of) + ")"
    data["elo_info"] = elo_info
    data["blend_info"] = blend
    data["momentum_info"] = {
        "j1": momentum_j1,
        "j2": momentum_j2,
        "diff": round(diff_momentum, 3),
        "impact_proba": round(impact_momentum, 4),
    }
    data["fatigue_info"] = {
        "j1": fatigue_j1,
        "j2": fatigue_j2,
        "diff": round(diff_fatigue, 3),
        "impact_proba": round(impact_fatigue, 4),
    }
    data["tennis_config"] = {
        "type": ("Grand Chelem" if best_of == 5 else
                 ("WTA" if "wta" in (competition or "").lower() else
                  ("ATP" if "atp" in (competition or "").lower() else "Standard"))),
        "best_of": best_of,
        "ligne_jeux": ligne_jeux,
        "sigma_jeux": sigma_jeux,
        "p_set": round(p_set, 4),
        "nb_sets_moyen": round(nb_sets_moyen, 2),
        "surface": elo_info.get("surface", "dur"),
    }
    data["auto_ou"] = {
        "ev_over": round(ev_over, 4),
        "ev_under": round(ev_under, 4),
        "choix": selection_ou,
    }

    data["marches"] = [
        {"nom": "Vainqueur", "selection": match.get("equipe1", "-"),
         "cote": round(cote_ml_f, 2), "cote_ouverture": round(cote_ml_f * 1.02, 2),
         "proba_juste": round(proba_ml, 4), "mouvement": round(mouvement, 4)},
        {"nom": "Over/Under Jeux", "selection": selection_ou,
         "cote": round(cote_ou, 2), "cote_ouverture": round(cote_ou * 1.02, 2),
         "proba_juste": round(proba_ou, 4), "mouvement": round(mouvement * 0.8, 4)},
        {"nom": "Score Exact Sets", "selection": match.get("equipe1", "-") + " 2-0",
         "cote": round(cote_score_f, 2), "cote_ouverture": round(cote_score_f * 1.02, 2),
         "proba_juste": round(proba_2_0, 4), "mouvement": round(mouvement * 0.6, 4)},
    ]
    return data



def _analyser_hockey(data, match):
    """
    Analyse Hockey sur Glace QFTE V23.0.

    Marchés analysés (6 en interne, 4 affichés) :
    - Money Line (vainqueur incl. prolongation)
    - Puck Line -1.5 (victoire par 2+ buts)
    - Total Buts Over/Under (ligne config)
    - Total Période (auto-sélection parmi P1, P2, P3)
    """
    co = float(match.get("cote_ouverture", 2.0))
    cf = float(match.get("cote_actuelle", 2.0))
    volume = float(match.get("volume", 50000))
    competition = match.get("competition", "")

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})
    scores_ctx = contexte.get("scores", {})

    # --- Config hockey ---
    cfg = _config_hockey(competition)
    ligne_totale = cfg["total_defaut"]
    home_advantage = cfg["home_advantage"]
    ligne_periode = cfg["ligne_periode"]

    # --- Proba ML depuis la cote ---
    marge = _marge_dynamique(co, cf)
    proba_impl = 1 / cf
    proba_demargee = proba_impl / (1 + marge)
    mouvement = (cf - co) / co if co > 0 else 0
    bonus_sharp = max(-0.02, min(0.03, -mouvement * 0.7))
    proba_ml = max(0.20, min(0.85, proba_demargee + bonus_sharp))

    # --- Total buts (H2H si dispo, sinon config) ---
    total_buts = ligne_totale
    if h2h.get("n", 0) >= 3:
        total_buts = (total_buts * 0.5) + (h2h["moy_buts"] * 0.5)

    # --- Estimation des λ ---
    total_avec_av = total_buts + home_advantage
    lambda_poiss_h, lambda_poiss_a = estimer_lambda(proba_ml, total_buts=total_avec_av)

    # --- Modèle attaque × défense (scores réels) ---
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

    # --- Ajustements forme et H2H ---
    lambda_home += float(forme.get("dom_finale", 0)) * 0.20
    lambda_away += float(forme.get("ext_finale", 0)) * 0.20

    if h2h.get("domine") == "dom":
        lambda_home += 0.15; lambda_away -= 0.10
    elif h2h.get("domine") == "ext":
        lambda_away += 0.15; lambda_home -= 0.10

    lambda_home = max(0.20, lambda_home)
    lambda_away = max(0.20, lambda_away)

    # ============================================================
    # MARCHÉ 1 : Money Line (probabilité de gagner, incl. prolongation)
    # ============================================================
    p_home, p_nul, p_away = proba_resultat_1x2(lambda_home, lambda_away)
    # En NHL, si match nul en temps réglementaire → prolongation
    # Le favori a ~55% de chances de gagner en prolongation, l'outsider ~45%
    proba_home_ml = p_home + p_nul * 0.55
    proba_away_ml = p_away + p_nul * 0.45

    # ============================================================
    # MARCHÉ 2 : Puck Line -1.5 (victoire par 2+ buts)
    # ============================================================
    proba_puck_line = 0.0
    for i in range(0, 12):
        for j in range(0, 12):
            if (i - j) >= 2:
                proba_puck_line += poisson(i, lambda_home) * poisson(j, lambda_away)

    # ============================================================
    # MARCHÉ 3 : Total Buts (Over/Under)
    # ============================================================
    proba_over = proba_over_total(lambda_home, lambda_away, ligne_totale)
    proba_under = 1 - proba_over

    # ============================================================
    # MARCHÉ 4 : Total Période — Auto-sélection parmi P1/P2/P3
    # ============================================================
    probas_periodes = []
    for periode, part in REPARTITION_PERIODES.items():
        lam_h_p = lambda_home * part
        lam_a_p = lambda_away * part
        p_over_p = proba_over_total(lam_h_p, lam_a_p, ligne_periode)
        probas_periodes.append({
            "periode": periode,
            "nom": {"p1": "1ère période", "p2": "2ème période", "p3": "3ème période"}[periode],
            "proba_over": p_over_p,
            "lambda_h": round(lam_h_p, 3),
            "lambda_a": round(lam_a_p, 3),
        })

    # ============================================================
    # AUTO-SÉLECTION DE LA MEILLEURE PÉRIODE
    # ============================================================
    cote_over_brute = float(match.get("cote_over25") or 0)
    if cote_over_brute <= 0:
        cote_over_brute = 1 / (proba_over * (1 + marge))

    meilleure_periode = None
    meilleur_ev_periode = -999

    for p in probas_periodes:
        # EV estimé pour Over et Under de cette période
        cote_p_over = cote_over_brute  # cote similaire pour toutes les périodes
        cote_p_under = 1 / ((1 - p["proba_over"]) * (1 + marge)) if p["proba_over"] < 1 else 10.0
        ev_p_over = (p["proba_over"] * cote_p_over) - 1
        ev_p_under = ((1 - p["proba_over"]) * cote_p_under) - 1
        ev_max = max(ev_p_over, ev_p_under)

        if ev_max > meilleur_ev_periode:
            meilleur_ev_periode = ev_max
            meilleure_periode = {
                "periode": p["periode"],
                "nom": p["nom"],
                "proba_over": p["proba_over"],
                "ev_over": ev_p_over,
                "ev_under": ev_p_under,
                "selection": "Over" if ev_p_over >= ev_p_under else "Under",
                "proba_selection": p["proba_over"] if ev_p_over >= ev_p_under else (1 - p["proba_over"]),
                "cote_selection": cote_p_over if ev_p_over >= ev_p_under else cote_p_under,
                "lambda_h": p["lambda_h"],
                "lambda_a": p["lambda_a"],
            }

    # ============================================================
    # EV POUR LES AUTRES MARCHÉS
    # ============================================================
    cote_ml_f = float(match.get("cote_ah") or (1 / (proba_home_ml * (1 + marge))))
    cote_puck_line_f = float(match.get("cote_btts") or (1 / (proba_puck_line * (1 + marge))))

    cote_under_tot = 1 / (proba_under * (1 + marge)) if proba_under > 0 else 10.0

    ev_over = (proba_over * cote_over_brute) - 1
    ev_under = (proba_under * cote_under_tot) - 1

    if ev_over >= ev_under:
        selection_ou = "Over " + str(ligne_totale)
        proba_ou = proba_over
        cote_ou = cote_over_brute
    else:
        selection_ou = "Under " + str(ligne_totale)
        proba_ou = proba_under
        cote_ou = cote_under_tot

    # ============================================================
    # STOCKAGE
    # ============================================================
    data["volume"] = volume
    data["liquidite_ok"] = volume >= 50000
    data["lambda_home"] = round(lambda_home, 3)
    data["lambda_away"] = round(lambda_away, 3)
    data["marge_estimee"] = marge
    data["total_buts_comp"] = round(total_buts, 2)
    data["modele_lambda"] = "Poisson hockey + attaque/défense"
    data["hockey_config"] = {
        "type": "NHL" if "nhl" in (competition or "").lower() else
                ("KHL" if "khl" in (competition or "").lower() else "Standard"),
        "ligne_totale": ligne_totale,
        "ligne_periode": ligne_periode,
        "home_advantage": home_advantage,
    }
    data["auto_ou"] = {
        "ev_over": round(ev_over, 4),
        "ev_under": round(ev_under, 4),
        "choix": selection_ou,
    }
    data["hockey_periodes"] = {
        "toutes": probas_periodes,
        "meilleure": meilleure_periode,
    }

    data["marches"] = [
        {
            "nom": "Money Line",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_ml_f, 2),
            "cote_ouverture": round(cote_ml_f * 1.02, 2),
            "proba_juste": round(proba_home_ml, 4),
            "mouvement": round(mouvement, 4),
        },
        {
            "nom": "Puck Line -1.5",
            "selection": match.get("equipe1", "-"),
            "cote": round(cote_puck_line_f, 2),
            "cote_ouverture": round(cote_puck_line_f * 1.02, 2),
            "proba_juste": round(proba_puck_line, 4),
            "mouvement": round(mouvement * 0.8, 4),
        },
        {
            "nom": "Total Buts",
            "selection": selection_ou,
            "cote": round(cote_ou, 2),
            "cote_ouverture": round(cote_ou * 1.02, 2),
            "proba_juste": round(proba_ou, 4),
            "mouvement": round(mouvement * 0.6, 4),
        },
        {
            "nom": "Total " + meilleure_periode["nom"] + " " + str(ligne_periode),
            "selection": meilleure_periode["selection"],
            "cote": round(meilleure_periode["cote_selection"], 2),
            "cote_ouverture": round(meilleure_periode["cote_selection"] * 1.02, 2),
            "proba_juste": round(meilleure_periode["proba_selection"], 4),
            "mouvement": round(mouvement * 0.4, 4),
        },
    ]
    return data


def proba_over_total(lh, la, ligne=5.5, max_buts=15):
    """Probabilité Over pour une ligne donnée."""
    p = 0.0
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            if i + j > ligne:
                p += poisson(i, lh) * poisson(j, la)
    return p
