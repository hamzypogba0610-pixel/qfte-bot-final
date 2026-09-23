"""
Module Calendrier Basket — QFTE V23.0.

Modélise l'impact du calendrier sur la performance des équipes NBA/EuroLeague :
- Back-to-back (2 matchs en 2 jours) : impact majeur
- 3 matchs en 4 nuits : impact très fort
- Voyage long (côte Est ↔ côte Ouest en NBA)
- Jours de repos

Inspiré des travaux sur la fatigue NBA (ESPN Sports Analytics,
NBA Advanced Stats) et des modèles de restauration.

Pur Python — aucune dépendance externe.
"""

# Impact en points sur l'écart attendu
IMPACT_BACK_TO_BACK = -3.5      # 2 matchs en 2 jours
IMPACT_3_EN_4 = -5.5            # 3 matchs en 4 nuits
IMPACT_VOYAGE_LONG = -2.0       # Voyage côte à côte


def _impact_repos_basket(jours_repos):
    """
    Impact des jours de repos avant le match (en points).

    - 4+ jours  → +1.5 (bien reposé)
    - 3 jours   → +0.5
    - 2 jours   → 0.0 (normal NBA)
    - 1 jour    → -3.5 (back-to-back)
    - 0 jour    → -5.5 (2 matchs en 2 jours consécutifs sans nuit complète)
    """
    try:
        j = float(jours_repos if jours_repos is not None else 2)
    except (ValueError, TypeError):
        j = 2

    if j >= 4:
        return 1.5
    elif j >= 3:
        return 0.5
    elif j >= 2:
        return 0.0
    elif j >= 1:
        return IMPACT_BACK_TO_BACK
    else:
        return IMPACT_3_EN_4


def _impact_voyage(deplacement_long=False):
    """
    Impact du voyage longue distance (côte Est ↔ Ouest).

    Retourne 0 ou IMPACT_VOYAGE_LONG.
    """
    if deplacement_long:
        return IMPACT_VOYAGE_LONG
    return 0.0


def _impact_3_en_4(matchs_4j):
    """
    Impact si l'équipe joue son 3ème match en 4 nuits.

    Retourne un malus supplémentaire si matchs_4j >= 3.
    """
    try:
        m = int(matchs_4j or 0)
    except (ValueError, TypeError):
        m = 0

    if m >= 4:
        return -2.0
    elif m >= 3:
        return -1.0
    return 0.0



def calculer_indice_calendrier_basket(
    jours_repos=2,
    matchs_4j=0,
    deplacement_long=False,
    back_to_back=False,
):
    """
    Calcule l'indice calendrier global pour une équipe de basket.

    Retourne un dict avec :
    - score_points : impact en points sur l'écart attendu
    - interpretation : texte lisible
    - détails des sous-composantes
    """
    impact_repos = _impact_repos_basket(jours_repos)
    impact_voyage = _impact_voyage(deplacement_long)
    impact_3_4 = _impact_3_en_4(matchs_4j)

    # Bonus/malus back-to-back explicite (si coché)
    bonus_btb = 0.0
    if back_to_back and impact_repos > IMPACT_BACK_TO_BACK:
        bonus_btb = IMPACT_BACK_TO_BACK
    elif not back_to_back and impact_repos <= IMPACT_BACK_TO_BACK:
        # Si non déclaré mais jours_repos <= 1 → on garde l'impact
        bonus_btb = 0.0

    score_points = impact_repos + impact_voyage + impact_3_4 + bonus_btb
    score_points = max(-8.0, min(2.0, score_points))

    # Interprétation
    if score_points >= 1.0:
        interpretation = "💚 Bien reposé"
    elif score_points >= -0.5:
        interpretation = "➖ Fraîcheur normale"
    elif score_points >= -2.5:
        interpretation = "🟡 Légère fatigue"
    elif score_points >= -5.0:
        interpretation = "🟠 Fatigue marquée"
    else:
        interpretation = "🔴 Fatigue critique"

    return {
        "score_points": round(score_points, 2),
        "impact_repos": round(impact_repos, 2),
        "impact_voyage": round(impact_voyage, 2),
        "impact_3_en_4": round(impact_3_4, 2),
        "interpretation": interpretation,
        "details": {
            "jours_repos": jours_repos,
            "matchs_4j": matchs_4j,
            "deplacement_long": deplacement_long,
            "back_to_back": back_to_back,
        },
    }


def analyser_calendrier_basket(data):
    """
    Applique l'analyse calendrier sur les équipes de basket.
    """
    match = data.get("match", {})
    if match.get("sport") != "basket":
        return data

    # --- Équipe 1 (domicile) ---
    cal_dom = calculer_indice_calendrier_basket(
        jours_repos=int(match.get("jours_repos_dom_basket", 2) or 2),
        matchs_4j=int(match.get("matchs_4j_dom_basket", 0) or 0),
        deplacement_long=bool(match.get("voyage_long_dom_basket", False)),
        back_to_back=bool(match.get("back_to_back_dom_basket", False)),
    )

    # --- Équipe 2 (extérieur) ---
    cal_ext = calculer_indice_calendrier_basket(
        jours_repos=int(match.get("jours_repos_ext_basket", 2) or 2),
        matchs_4j=int(match.get("matchs_4j_ext_basket", 0) or 0),
        deplacement_long=bool(match.get("voyage_long_ext_basket", False)),
        back_to_back=bool(match.get("back_to_back_ext_basket", False)),
    )

    # --- Différentiel (impact net en points sur l'écart) ---
    diff = cal_dom["score_points"] - cal_ext["score_points"]

    data["calendrier_basket"] = {
        "dom": cal_dom,
        "ext": cal_ext,
        "difference_points": round(diff, 2),
    }
    return data
