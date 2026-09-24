"""
Module Stats Avancées — QFTE V23.0.

Calcule des statistiques avancées par sport :
- Football : xG proxy, xPTS, Régularité, Pression, Overperformance
- Basket   : Net Rating, Pace-adjusted, Efficacité, Clutch
- Tennis   : Service Index, Return Index, Dominance Ratio, Surface Index

Pur Python — aucune dépendance externe.
"""


# ============================================================
# UTILITAIRES
# ============================================================
def _parse_scores(texte):
    """Parse '2-1,1-0,3-2' → [(2,1),(1,0),(3,2)]"""
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
    forme = contexte.get("forme", {})
    scores_ctx = contexte.get("scores", {})
    lambda_home = float(data.get("lambda_home", 1.4) or 1.4)
    lambda_away = float(data.get("lambda_away", 1.3) or 1.3)

    # Récupération des scores
    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    # --- xG / xGA proxy ---
    dom_marques = [s[0] for s in dom_scores] + [s[0] for s in dom_glob]
    dom_encaisses = [s[1] for s in dom_scores] + [s[1] for s in dom_glob]
    ext_marques = [s[0] for s in ext_scores] + [s[0] for s in ext_glob]
    ext_encaisses = [s[1] for s in ext_scores] + [s[1] for s in ext_glob]

    xg_dom = _moyenne(dom_marques) if dom_marques else lambda_home
    xga_dom = _moyenne(dom_encaisses) if dom_encaisses else lambda_away
    xg_ext = _moyenne(ext_marques) if ext_marques else lambda_away
    xga_ext = _moyenne(ext_encaisses) if ext_encaisses else lambda_home

    # --- xPTS (points attendus sur les 5 derniers matchs) ---
    def _points_match(buts_pour, buts_contre):
        if buts_pour > buts_contre: return 3
        elif buts_pour == buts_contre: return 1
        return 0

    pts_dom = [_points_match(s[0], s[1]) for s in (dom_scores + dom_glob)]
    pts_ext = [_points_match(s[0], s[1]) for s in (ext_scores + ext_glob)]

    xpts_dom = _moyenne(pts_dom) if pts_dom else 1.5
    xpts_ext = _moyenne(pts_ext) if pts_ext else 1.5

    # --- Indice de régularité (0-1, basé sur écart-type des résultats) ---
    dom_resultats = [(s[0] - s[1]) for s in (dom_scores + dom_glob)]
    ext_resultats = [(s[0] - s[1]) for s in (ext_scores + ext_glob)]

    ecart_dom = _ecart_type(dom_resultats)
    ecart_ext = _ecart_type(ext_resultats)

    # Écart-type faible = régularité forte
    regularite_dom = max(0.0, min(1.0, 1.0 - ecart_dom / 3.0))
    regularite_ext = max(0.0, min(1.0, 1.0 - ecart_ext / 3.0))

    # --- Indice de pression (performance dans les matchs serrés) ---
    def _pression(scores):
        serres = [s for s in scores if abs(s[0] - s[1]) <= 1]
        if not serres: return 0.5
        gagnes = sum(1 for s in serres if s[0] > s[1])
        return gagnes / len(serres)

    pression_dom = _pression(dom_scores + dom_glob)
    pression_ext = _pression(ext_scores + ext_glob)

    # --- Overperformance (buts réels vs λ) ---
    over_dom = xg_dom - lambda_home
    over_ext = xg_ext - lambda_away

    return {
        "type": "football",
        "dom": {
            "xg": round(xg_dom, 2),
            "xga": round(xga_dom, 2),
            "xpts": round(xpts_dom, 2),
            "regularite": round(regularite_dom, 3),
            "pression": round(pression_dom, 3),
            "overperformance": round(over_dom, 2),
            "matchs_analyses": len(dom_scores) + len(dom_glob),
        },
        "ext": {
            "xg": round(xg_ext, 2),
            "xga": round(xga_ext, 2),
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
    forme = contexte.get("forme", {})
    ecart_moyen = float(data.get("lambda_home", 0) or 0)
    total_estime = float(data.get("total_buts_comp", 180) or 180)

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_tous = dom_scores + dom_glob
    ext_tous = ext_scores + ext_glob

    # --- Net Rating (différentiel points marqués - encaissés) ---
    def _net_rating(scores):
        if not scores:
            return 0.0
        diff = [s[0] - s[1] for s in scores]
        return _moyenne(diff)

    net_dom = _net_rating(dom_tous)
    net_ext = _net_rating(ext_tous)

    # --- Pace-adjusted (points marqués normalisés sur un pace de 100) ---
    def _pace_adjusted(scores):
        if not scores:
            return 100.0
        # Moyenne des totaux de points par match
        totaux = [s[0] + s[1] for s in scores]
        pace = _moyenne(totaux) if totaux else 200
        # Score ajusté : points marqués × (100 / pace)
        pts_marques = _moyenne([s[0] for s in scores])
        if pace <= 0:
            return pts_marques
        return (pts_marques / pace) * 200

    pace_dom = _pace_adjusted(dom_tous)
    pace_ext = _pace_adjusted(ext_tous)

    # --- Efficacité offensive / défensive ---
    def _eff_off(scores):
        if not scores:
            return 100.0
        return _moyenne([s[0] for s in scores])

    def _eff_def(scores):
        if not scores:
            return 100.0
        return _moyenne([s[1] for s in scores])

    eff_off_dom = _eff_off(dom_tous)
    eff_def_dom = _eff_def(dom_tous)
    eff_off_ext = _eff_off(ext_tous)
    eff_def_ext = _eff_def(ext_tous)

    # --- Indice de Clutch (matchs serrés, écart <= 5 pts) ---
    def _clutch(scores):
        serres = [s for s in scores if abs(s[0] - s[1]) <= 5]
        if not serres:
            return 0.5
        gagnes = sum(1 for s in serres if s[0] > s[1])
        return gagnes / len(serres)

    clutch_dom = _clutch(dom_tous)
    clutch_ext = _clutch(ext_tous)

    # --- Régularité (écart-type des écarts) ---
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
    forme = contexte.get("forme", {})
    elo_info = data.get("elo_info", {})
    p_set = float(data.get("lambda_home", 0.5) or 0.5)

    dom_scores = _parse_scores(match.get("scores_dom_5", ""))
    ext_scores = _parse_scores(match.get("scores_ext_5", ""))
    dom_glob = _parse_scores(match.get("scores_dom_glob_5", ""))
    ext_glob = _parse_scores(match.get("scores_ext_glob_5", ""))

    dom_tous = dom_scores + dom_glob
    ext_tous = ext_scores + ext_glob

    # --- Service Index (jeux gagnés sur son service, approximé par sets gagnés) ---
    def _service_index(scores):
        if not scores:
            return 0.5
        # Approximation : ratio de sets gagnés = proxy de la domination au service
        total_sets_pour = sum(s[0] for s in scores)
        total_sets_contre = sum(s[1] for s in scores)
        total = total_sets_pour + total_sets_contre
        if total <= 0:
            return 0.5
        return total_sets_pour / total

    service_dom = _service_index(dom_tous)
    service_ext = _service_index(ext_tous)

    # --- Return Index (ratio de sets "volés", approximé) ---
    # On considère qu'un retour efficace se mesure par la capacité à gagner
    # des sets malgré la pression adverse.
    def _return_index(scores):
        if not scores:
            return 0.5
        # Ratio de sets gagnés quand on perd le 1er set (approximé)
        retours = sum(1 for s in scores if s[0] > s[1])
        return retours / len(scores) if scores else 0.5

    return_dom = _return_index(dom_tous)
    return_ext = _return_index(ext_tous)

    # --- Dominance Ratio (points gagnés / perdus) ---
    def _dominance(scores):
        if not scores:
            return 1.0
        pour = sum(s[0] for s in scores)
        contre = sum(s[1] for s in scores)
        if contre <= 0:
            return 2.0
        return pour / contre

    dominance_dom = _dominance(dom_tous)
    dominance_ext = _dominance(ext_tous)

    # --- Indice de Surface (écart entre surface actuelle et préférée) ---
    # On utilise l'Elo par surface pour détecter les spécialistes
    surface_actuelle = elo_info.get("surface", "dur")
    elo_dom_surf = float(elo_info.get("elo1_surface", 1500) or 1500)
    elo_dom_glob = float(elo_info.get("elo1_global", 1500) or 1500)
    elo_ext_surf = float(elo_info.get("elo2_surface", 1500) or 1500)
    elo_ext_glob = float(elo_info.get("elo2_global", 1500) or 1500)

    # Indice = différence entre Elo surface et Elo global (positif = spécialiste)
    surface_dom = elo_dom_surf - elo_dom_glob
    surface_ext = elo_ext_surf - elo_ext_glob

    # --- Régularité (écart-type des écarts) ---
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
        else:
            stats = _stats_football(data, match)
    except Exception as e:
        data["stats_avancees"] = {"type": sport, "erreur": str(e)}
        return data

    data["stats_avancees"] = stats
    return data
