"""
Module Calendrier Football — QFTE V23.0.

Modélise l'impact du calendrier sur la performance des équipes :
- Congestion (matchs sur 7j / 14j)
- Jours de repos avant ce match
- Match suivant important (rotation probable)
- Compétitions multiples

Inspiré des travaux sur la fatigue en football (Dupont et al., 
Carling et al.) et des modèles d'optimisation de rotation.

Pur Python — aucune dépendance externe.
"""

# Poids d'importance par type de compétition suivante
IMPORTANCE_COMPETITION = {
    "champions league": 1.0,
    "ligue des champions": 1.0,
    "europa league": 0.85,
    "ligue europa": 0.85,
    "conference league": 0.70,
    "ligue conference": 0.70,
    "coupe du monde": 1.0,
    "euro": 0.95,
    "coupe nationale": 0.75,
    "coupe de france": 0.75,
    "fa cup": 0.75,
    "copa del rey": 0.75,
    "coppa italia": 0.75,
    "dfb pokal": 0.75,
    "championnat": 0.40,
    "ligue 1": 0.40,
    "premier league": 0.40,
    "liga": 0.40,
    "serie a": 0.40,
    "bundesliga": 0.40,
    "default": 0.50,
}


def _poids_competition(competition):
    """Retourne le poids d'importance d'une compétition (0 à 1)."""
    comp = (competition or "").lower().strip()
    for nom, poids in IMPORTANCE_COMPETITION.items():
        if nom in comp:
            return poids
    return IMPORTANCE_COMPETITION["default"]


def _impact_congestion(matchs_7j, matchs_14j):
    """
    Impact de la congestion (nombre de matchs joués récemment).

    Retourne un score entre -0.25 et +0.05.
    - 0 match sur 7j  → +0.05 (frais)
    - 1 match sur 7j  → 0.00 (normal)
    - 2 matchs sur 7j → -0.08
    - 3 matchs sur 7j → -0.18
    - 4+ matchs        → -0.25
    """
    try:
        m7 = max(0, int(matchs_7j or 0))
        m14 = max(0, int(matchs_14j or 0))
    except (ValueError, TypeError):
        m7, m14 = 0, 0

    if m7 == 0:
        impact = 0.05
    elif m7 == 1:
        impact = 0.00
    elif m7 == 2:
        impact = -0.08
    elif m7 == 3:
        impact = -0.18
    else:
        impact = -0.25

    # Ajustement secondaire sur 14 jours
    if m14 >= 6:
        impact -= 0.05
    elif m14 >= 4:
        impact -= 0.02

    return max(-0.30, min(0.05, impact))



def _impact_repos(jours_repos):
    """
    Impact des jours de repos avant le match.

    Retourne un score entre -0.15 et +0.05.
    - 7+ jours  → +0.05 (frais)
    - 5-6 jours → 0.00 (normal)
    - 4 jours   → -0.03
    - 3 jours   → -0.08
    - 2 jours   → -0.15
    - 1 jour    → -0.20
    - 0 jour    → -0.25
    """
    try:
        j = float(jours_repos or 7)
    except (ValueError, TypeError):
        j = 7

    if j >= 7:
        return 0.05
    elif j >= 5:
        return 0.00
    elif j >= 4:
        return -0.03
    elif j >= 3:
        return -0.08
    elif j >= 2:
        return -0.15
    elif j >= 1:
        return -0.20
    else:
        return -0.25


def _impact_match_suivant(competition_suivante, jours_avant_match_suivant):
    """
    Impact du match suivant important (rotation probable).

    Si une équipe joue un gros match dans 2-4 jours, elle va probablement
    faire tourner son effectif sur ce match-ci.

    Retourne un score entre -0.20 et 0.00.
    """
    if not competition_suivante:
        return 0.00

    try:
        jours = float(jours_avant_match_suivant or 7)
    except (ValueError, TypeError):
        jours = 7

    poids = _poids_competition(competition_suivante)

    # Impact fort si match important ET proche
    if jours <= 2:
        impact_base = -0.20
    elif jours <= 4:
        impact_base = -0.12
    elif jours <= 6:
        impact_base = -0.05
    else:
        impact_base = 0.00

    return round(impact_base * poids, 3)


def calculer_indice_calendrier(
    matchs_7j=0,
    matchs_14j=0,
    jours_repos=7,
    competition_suivante="",
    jours_avant_match_suivant=7,
):
    """
    Calcule l'indice calendrier global pour une équipe.

    Retourne un dict avec :
    - score : indice global (-0.40 à +0.10)
    - impact_lambda : impact sur les buts attendus
    - interpretation : texte lisible
    - détails des sous-composantes
    """
    impact_congestion = _impact_congestion(matchs_7j, matchs_14j)
    impact_repos = _impact_repos(jours_repos)
    impact_suivant = _impact_match_suivant(competition_suivante, jours_avant_match_suivant)

    # Score composite (avec pondération)
    # Congestion : 35% / Repos : 35% / Match suivant : 30%
    score = (
        0.35 * impact_congestion
        + 0.35 * impact_repos
        + 0.30 * impact_suivant
    )
    score = max(-0.40, min(0.10, score))

    # Impact sur les buts attendus (λ) : ±0.30 buts max
    impact_lambda = score * 0.75

    # Interprétation
    if score >= 0.03:
        interpretation = "💚 Calendrier favorable"
    elif score >= -0.05:
        interpretation = "➖ Calendrier normal"
    elif score >= -0.15:
        interpretation = "🟡 Légère congestion"
    elif score >= -0.25:
        interpretation = "🟠 Congestion marquée"
    else:
        interpretation = "🔴 Calendrier très chargé"

    return {
        "score": round(score, 3),
        "impact_lambda": round(impact_lambda, 3),
        "impact_congestion": round(impact_congestion, 3),
        "impact_repos": round(impact_repos, 3),
        "impact_suivant": round(impact_suivant, 3),
        "interpretation": interpretation,
        "details": {
            "matchs_7j": matchs_7j,
            "matchs_14j": matchs_14j,
            "jours_repos": jours_repos,
            "competition_suivante": competition_suivante or "Aucune",
            "jours_avant_suivant": jours_avant_match_suivant,
        },
    }


def analyser_calendrier(data):
    """
    Applique l'analyse calendrier sur les équipes de football.

    Récupère les données du match, calcule les indices pour les 2 équipes,
    et stocke le résultat dans data["calendrier"].
    """
    match = data.get("match", {})
    if match.get("sport") != "football":
        return data

    # --- Équipe 1 (domicile) ---
    cal_dom = calculer_indice_calendrier(
        matchs_7j=int(match.get("matchs_7j_dom", 0) or 0),
        matchs_14j=int(match.get("matchs_14j_dom", 0) or 0),
        jours_repos=int(match.get("jours_repos_dom", 7) or 7),
        competition_suivante=match.get("competition_suivante_dom", ""),
        jours_avant_match_suivant=int(match.get("jours_avant_suivant_dom", 7) or 7),
    )

    # --- Équipe 2 (extérieur) ---
    cal_ext = calculer_indice_calendrier(
        matchs_7j=int(match.get("matchs_7j_ext", 0) or 0),
        matchs_14j=int(match.get("matchs_14j_ext", 0) or 0),
        jours_repos=int(match.get("jours_repos_ext", 7) or 7),
        competition_suivante=match.get("competition_suivante_ext", ""),
        jours_avant_match_suivant=int(match.get("jours_avant_suivant_ext", 7) or 7),
    )

    # --- Différentiel (impact net sur le match) ---
    diff = cal_dom["impact_lambda"] - cal_ext["impact_lambda"]

    data["calendrier"] = {
        "dom": cal_dom,
        "ext": cal_ext,
        "difference_lambda": round(diff, 3),
    }
    return data
