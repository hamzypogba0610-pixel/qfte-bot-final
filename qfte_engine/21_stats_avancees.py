"""
Module Stats Avancées — QFTE V23.0.

Calcule des statistiques avancées par sport :
- Football : xG proxy, xPTS, Régularité, Pression, Overperformance
- Basket   : Net Rating, Pace-adjusted, Efficacité, Clutch
- Tennis   : Service Index, Return Index, Dominance Ratio, Surface Index
- Hockey   : Corsi, Fenwick, PDO, xG hockey, Indice de puissance

Pur Python — aucune dépendance externe.
"""


def _parse_scores(texte):
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


def _moyenne(liste):
    return sum(liste) / len(liste) if liste else 0.0


def _ecart_type(liste):
    if len(liste) < 2:
        return 0.0
    m = _moyenne(liste)
    var = sum((x - m) ** 2 for x in liste) / len(liste)
    return var ** 0.5


# ============================================================
# FOOTBALL
# ============================================================
def _stats_football(data, match):
    contexte = data.get("contexte", {})
    scores_ctx = contexte.get("scores", {})
    lambda_home = float(data.get("lambda_home", 1.4) or 1.4)
    lambda_away = float(data.get("lambda_away", 1.3) or 1.3)

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_marques = [s[0] for s in dom_scores] + [s[0] for s in dom_glob]
    dom_encaisses = [s[1] for s in dom_scores] + [s[1] for s in dom_glob]
    ext_marques = [s[0] for s in ext_scores] + [s[0] for s in ext_glob]
    ext_encaisses = [s[1] for s in ext_scores] + [s[1] for s in ext_glob]

    xg_dom = _moyenne(dom_marques) if dom_marques else lambda_home
    xga_dom = _moyenne(dom_encaisses) if dom_encaisses else lambda_away
    xg_ext = _moyenne(ext_marques) if ext_marques else lambda_away
    xga_ext = _moyenne(ext_encaisses) if ext_encaisses else lambda_home

    def _points_match(bp, bc):
        if bp > bc: return 3
        elif bp == bc: return 1
        return 0

    pts_dom = [_points_match(s[0], s[1]) for s in (dom_scores + dom_glob)]
    pts_ext = [_points_match(s[0], s[1]) for s in (ext_scores + ext_glob)]

    xpts_dom = _moyenne(pts_dom) if pts_dom else 1.5
    xpts_ext = _moyenne(pts_ext) if pts_ext else 1.5

    dom_resultats = [(s[0] - s[1]) for s in (dom_scores + dom_glob)]
    ext_resultats = [(s[0] - s[1]) for s in (ext_scores + ext_glob)]

    ecart_dom = _ecart_type(dom_resultats)
    ecart_ext = _ecart_type(ext_resultats)

    regularite_dom = max(0.0, min(1.0, 1.0 - ecart_dom / 3.0))
    regularite_ext = max(0.0, min(1.0, 1.0 - ecart_ext / 3.0))

    def _pression(scores):
        serres = [s for s in scores if abs(s[0] - s[1]) <= 1]
        if not serres: return 0.5
        gagnes = sum(1 for s in serres if s[0] > s[1])
        return gagnes / len(serres)

    pression_dom = _pression(dom_scores + dom_glob)
    pression_ext = _pression(ext_scores + ext_glob)

    over_dom = xg_dom - lambda_home
    over_ext = xg_ext - lambda_away

    return {
        "type": "football",
        "dom": {
            "xg": round(xg_dom, 2), "xga": round(xga_dom, 2),
            "xpts": round(xpts_dom, 2),
            "regularite": round(regularite_dom, 3),
            "pression": round(pression_dom, 3),
            "overperformance": round(over_dom, 2),
            "matchs_analyses": len(dom_scores) + len(dom_glob),
        },
        "ext": {
            "xg": round(xg_ext, 2), "xga": round(xga_ext, 2),
            "xpts": round(xpts_ext, 2),
            "regularite": round(regularite_ext, 3),
            "pression": round(pression_ext, 3),
            "overperformance": round(over_ext, 2),
            "matchs_analyses": len(ext_scores) + len(ext_glob),
        },
                  }



# ============================================================
# BASKET
# ============================================================
def _stats_basket(data, match):
    contexte = data.get("contexte", {})
    ecart_moyen = float(data.get("lambda_home", 0) or 0)
    total_estime = float(data.get("total_buts_comp", 180) or 180)

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_tous = dom_scores + dom_glob
    ext_tous = ext_scores + ext_glob

    def _net_rating(scores):
        if not scores: return 0.0
        diff = [s[0] - s[1] for s in scores]
        return _moyenne(diff)

    net_dom = _net_rating(dom_tous)
    net_ext = _net_rating(ext_tous)

    def _pace_adjusted(scores):
        if not scores: return 100.0
        totaux = [s[0] + s[1] for s in scores]
        pace = _moyenne(totaux) if totaux else 200
        pts_marques = _moyenne([s[0] for s in scores])
        if pace <= 0: return pts_marques
        return (pts_marques / pace) * 200

    pace_dom = _pace_adjusted(dom_tous)
    pace_ext = _pace_adjusted(ext_tous)

    def _eff_off(scores):
        if not scores: return 100.0
        return _moyenne([s[0] for s in scores])

    def _eff_def(scores):
        if not scores: return 100.0
        return _moyenne([s[1] for s in scores])

    eff_off_dom = _eff_off(dom_tous)
    eff_def_dom = _eff_def(dom_tous)
    eff_off_ext = _eff_off(ext_tous)
    eff_def_ext = _eff_def(ext_tous)

    def _clutch(scores):
        serres = [s for s in scores if abs(s[0] - s[1]) <= 5]
        if not serres: return 0.5
        gagnes = sum(1 for s in serres if s[0] > s[1])
        return gagnes / len(serres)

    clutch_dom = _clutch(dom_tous)
    clutch_ext = _clutch(ext_tous)

    ecart_dom = _ecart_type([s[0] - s[1] for s in dom_tous])
    ecart_ext = _ecart_type([s[0] - s[1] for s in ext_tous])

    regularite_dom = max(0.0, min(1.0, 1.0 - ecart_dom / 20.0))
    regularite_ext = max(0.0, min(1.0, 1.0 - ecart_ext / 20.0))

    return {
        "type": "basket",
        "dom": {
            "net_rating": round(net_dom, 2),
            "pace_adjusted": round(pace_dom, 2),
            "eff_off": round(eff_off_dom, 2),
            "eff_def": round(eff_def_dom, 2),
            "clutch": round(clutch_dom, 3),
            "regularite": round(regularite_dom, 3),
            "matchs_analyses": len(dom_tous),
        },
        "ext": {
            "net_rating": round(net_ext, 2),
            "pace_adjusted": round(pace_ext, 2),
            "eff_off": round(eff_off_ext, 2),
            "eff_def": round(eff_def_ext, 2),
            "clutch": round(clutch_ext, 3),
            "regularite": round(regularite_ext, 3),
            "matchs_analyses": len(ext_tous),
        },
    }


# ============================================================
# TENNIS
# ============================================================
def _stats_tennis(data, match):
    contexte = data.get("contexte", {})
    elo_info = data.get("elo_info", {})

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_tous = dom_scores + dom_glob
    ext_tous = ext_scores + ext_glob

    def _service_index(scores):
        if not scores: return 0.5
        total_pour = sum(s[0] for s in scores)
        total_contre = sum(s[1] for s in scores)
        total = total_pour + total_contre
        if total <= 0: return 0.5
        return total_pour / total

    service_dom = _service_index(dom_tous)
    service_ext = _service_index(ext_tous)

    def _return_index(scores):
        if not scores: return 0.5
        retours = sum(1 for s in scores if s[0] > s[1])
        return retours / len(scores) if scores else 0.5

    return_dom = _return_index(dom_tous)
    return_ext = _return_index(ext_tous)

    def _dominance(scores):
        if not scores: return 1.0
        pour = sum(s[0] for s in scores)
        contre = sum(s[1] for s in scores)
        if contre <= 0: return 2.0
        return pour / contre

    dominance_dom = _dominance(dom_tous)
    dominance_ext = _dominance(ext_tous)

    surface_actuelle = elo_info.get("surface", "dur")
    elo_dom_surf = float(elo_info.get("elo1_surface", 1500) or 1500)
    elo_dom_glob = float(elo_info.get("elo1_global", 1500) or 1500)
    elo_ext_surf = float(elo_info.get("elo2_surface", 1500) or 1500)
    elo_ext_glob = float(elo_info.get("elo2_global", 1500) or 1500)

    surface_dom = elo_dom_surf - elo_dom_glob
    surface_ext = elo_ext_surf - elo_ext_glob

    ecart_dom = _ecart_type([s[0] - s[1] for s in dom_tous])
    ecart_ext = _ecart_type([s[0] - s[1] for s in ext_tous])

    regularite_dom = max(0.0, min(1.0, 1.0 - ecart_dom / 2.0))
    regularite_ext = max(0.0, min(1.0, 1.0 - ecart_ext / 2.0))

    return {
        "type": "tennis",
        "dom": {
            "service_index": round(service_dom, 3),
            "return_index": round(return_dom, 3),
            "dominance_ratio": round(dominance_dom, 2),
            "surface_index": round(surface_dom, 1),
            "surface_actuelle": surface_actuelle,
            "regularite": round(regularite_dom, 3),
            "matchs_analyses": len(dom_tous),
        },
        "ext": {
            "service_index": round(service_ext, 3),
            "return_index": round(return_ext, 3),
            "dominance_ratio": round(dominance_ext, 2),
            "surface_index": round(surface_ext, 1),
            "surface_actuelle": surface_actuelle,
            "regularite": round(regularite_ext, 3),
            "matchs_analyses": len(ext_tous),
        },
    }



# ============================================================
# HOCKEY SUR GLACE
# ============================================================
def _stats_hockey(data, match):
    """
    Stats avancées hockey :
    - Corsi proxy (% de tirs tentés pour, approximé par les buts)
    - Fenwick proxy (% de tirs non bloqués)
    - PDO (chance : % de tirs réussis + % d'arrêts)
    - xG hockey (basé sur les buts réels)
    - Indice de puissance (ratio buts pour/contre)
    """
    contexte = data.get("contexte", {})
    lambda_home = float(data.get("lambda_home", 3.0) or 3.0)
    lambda_away = float(data.get("lambda_away", 2.8) or 2.8)

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_tous = dom_scores + dom_glob
    ext_tous = ext_scores + ext_glob

    # --- Buts marqués / encaissés moyens ---
    def _buts_pour(scores):
        return _moyenne([s[0] for s in scores]) if scores else lambda_home

    def _buts_contre(scores):
        return _moyenne([s[1] for s in scores]) if scores else lambda_away

    bp_dom = _buts_pour(dom_tous)
    bc_dom = _buts_contre(dom_tous)
    bp_ext = _buts_pour(ext_tous)
    bc_ext = _buts_contre(ext_tous)

    # --- xG hockey (proxy : buts réels ajustés par la qualité de l'adversaire) ---
    xg_dom = bp_dom if dom_tous else lambda_home
    xg_ext = bp_ext if ext_tous else lambda_away
    xga_dom = bc_dom if dom_tous else lambda_away
    xga_ext = bc_ext if ext_tous else lambda_home

    # --- Corsi proxy : ratio de buts marqués / (marqués + encaissés) ---
    # (approximation basée sur les scores, sans données de tirs réelles)
    def _corsi(bp, bc):
        total = bp + bc
        if total <= 0: return 50.0
        return (bp / total) * 100.0

    corsi_dom = _corsi(bp_dom, bc_dom)
    corsi_ext = _corsi(bp_ext, bc_ext)

    # --- Fenwick proxy (légèrement différent : on retire ~15% des tirs bloqués) ---
    def _fenwick(bp, bc):
        # Approximation : on suppose 15% des tirs sont bloqués
        bp_adj = bp * 0.85
        bc_adj = bc * 0.85
        total = bp_adj + bc_adj
        if total <= 0: return 50.0
        return (bp_adj / total) * 100.0

    fenwick_dom = _fenwick(bp_dom, bc_dom)
    fenwick_ext = _fenwick(bp_ext, bc_ext)

    # --- PDO (chance) : % tirs réussis + % arrêts ---
    # PDO moyen NHL = 100. Au-dessus = chance, en-dessous = malchance
    # Approximation : on suppose ~8% de conversion en but par tir
    def _pdo(bp, bc):
        # Si on marque bp et encaisse bc, on a :
        #   - taux de conversion = bp / (bp * 12.5) ≈ 8%
        #   - taux d'arrêt = 1 - bc / (bc * 12.5) ≈ 92%
        # PDO = (taux_conversion + taux_arret) × 100
        if bp <= 0 and bc <= 0: return 100.0
        taux_conversion = 8.0 + (bp - bc) * 0.5  # Ajustement basé sur le différentiel
        taux_arret = 92.0 - (bp - bc) * 0.5
        pdo = taux_conversion + taux_arret
        return max(90.0, min(110.0, pdo))

    pdo_dom = _pdo(bp_dom, bc_dom)
    pdo_ext = _pdo(bp_ext, bc_ext)

    # --- Indice de puissance (ratio buts pour/contre) ---
    def _power_index(bp, bc):
        if bc <= 0: return 2.0
        return bp / bc

    power_dom = _power_index(bp_dom, bc_dom)
    power_ext = _power_index(bp_ext, bc_ext)

    # --- Régularité (écart-type des écarts) ---
    ecart_dom = _ecart_type([s[0] - s[1] for s in dom_tous])
    ecart_ext = _ecart_type([s[0] - s[1] for s in ext_tous])

    regularite_dom = max(0.0, min(1.0, 1.0 - ecart_dom / 3.0))
    regularite_ext = max(0.0, min(1.0, 1.0 - ecart_ext / 3.0))

    return {
        "type": "hockey",
        "dom": {
            "corsi": round(corsi_dom, 1),
            "fenwick": round(fenwick_dom, 1),
            "pdo": round(pdo_dom, 1),
            "xg": round(xg_dom, 2),
            "xga": round(xga_dom, 2),
            "power_index": round(power_dom, 2),
            "regularite": round(regularite_dom, 3),
            "matchs_analyses": len(dom_tous),
        },
        "ext": {
            "corsi": round(corsi_ext, 1),
            "fenwick": round(fenwick_ext, 1),
            "pdo": round(pdo_ext, 1),
            "xg": round(xg_ext, 2),
            "xga": round(xga_ext, 2),
            "power_index": round(power_ext, 2),
            "regularite": round(regularite_ext, 3),
            "matchs_analyses": len(ext_tous),
        },
    }


# ============================================================
# FONCTION PRINCIPALE (dispatcher)
# ============================================================
def calculer_stats_avancees(data):
    """
    Calcule les statistiques avancées selon le sport.
    Stocke le résultat dans data["stats_avancees"].
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    try:
        if sport == "basket":
            stats = _stats_basket(data, match)
        elif sport == "tennis":
            stats = _stats_tennis(data, match)
        elif sport == "hockey":
            stats = _stats_hockey(data, match)
        else:
            stats = _stats_football(data, match)
    except Exception as e:
        data["stats_avancees"] = {"type": sport, "erreur": str(e)}
        return data

    data["stats_avancees"] = stats
    return data
