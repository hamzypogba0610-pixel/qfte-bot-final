"""
Module Elo Tennis — QFTE V23.0.

Système de classement Elo adapté au tennis, avec :
- Elo global par joueur
- Elo par surface (terre, gazon, dur, indoor)
- K-factor adaptatif selon le tournoi
- Mise à jour automatique après chaque match
- Blending avec la cote bookmaker

Inspiré de : FiveThirtyEight, Jeff Sackmann (Tennis Abstract),
et des travaux sur les systèmes Elo par surface.

Pur Python — aucune dépendance externe.
"""
import json
import os
import math

FICHIER_ELO = "elo_tennis.json"

ELO_INITIAL = 1500.0
ELO_MIN = 1000.0
ELO_MAX = 2400.0

# K-factor selon le type de tournoi
K_FACTORS = {
    "grand chelem": 50,
    "masters 1000": 40,
    "atp 500": 35,
    "atp 250": 32,
    "wta 1000": 40,
    "wta 500": 35,
    "wta 250": 32,
    "atp finals": 45,
    "default": 32,
}

# Surfaces reconnues
SURFACES = ["terre", "gazon", "dur", "indoor"]


# ============================================================
# CHARGEMENT / SAUVEGARDE
# ============================================================
def _charger_elo():
    """
    Charge la base Elo depuis le fichier JSON.
    Structure :
    {
        "nadal": {
            "global": 2050,
            "terre": 2200,
            "gazon": 1750,
            "dur": 1950,
            "indoor": 1850,
            "matchs": 450
        },
        ...
    }
    """
    if not os.path.exists(FICHIER_ELO):
        return {}
    try:
        with open(FICHIER_ELO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _ecrire_elo(data):
    try:
        with open(FICHIER_ELO, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def _normaliser_nom(nom):
    """Normalise le nom du joueur (lowercase, sans espaces superflus)."""
    if not nom:
        return ""
    return str(nom).lower().strip()


def _cle_surface(surface):
    """Normalise la surface saisie."""
    if not surface:
        return "dur"
    s = str(surface).lower().strip()
    if "terre" in s or "clay" in s or "roland" in s:
        return "terre"
    if "gazon" in s or "grass" in s or "wimbledon" in s:
        return "gazon"
    if "indoor" in s or "paris" in s or "bercy" in s or "final" in s:
        return "indoor"
    return "dur"


def get_joueur(nom):
    """Retourne le profil Elo d'un joueur (créé si absent)."""
    elo = _charger_elo()
    cle = _normaliser_nom(nom)
    if not cle:
        return {
            "global": ELO_INITIAL,
            "terre": ELO_INITIAL,
            "gazon": ELO_INITIAL,
            "dur": ELO_INITIAL,
            "indoor": ELO_INITIAL,
            "matchs": 0,
        }
    if cle not in elo:
        return {
            "global": ELO_INITIAL,
            "terre": ELO_INITIAL,
            "gazon": ELO_INITIAL,
            "dur": ELO_INITIAL,
            "indoor": ELO_INITIAL,
            "matchs": 0,
        }
    return elo[cle]


def _get_k_factor(competition):
    """Détecte le K-factor selon le tournoi."""
    comp = (competition or "").lower()
    for nom, k in K_FACTORS.items():
        if nom in comp:
            return k
    return K_FACTORS["default"]



# ============================================================
# CALCUL DE LA PROBABILITÉ À PARTIR DE L'ELO
# ============================================================
def proba_elo(joueur1, joueur2, surface="dur"):
    """
    Probabilité que joueur1 batte joueur2, selon le modèle Elo.

    Formule standard :
    P(j1 gagne) = 1 / (1 + 10^((elo2 - elo1) / 400))

    On utilise l'Elo SPÉCIFIQUE À LA SURFACE si disponible,
    avec un blending 70% surface / 30% global pour plus de stabilité.
    """
    elo1 = get_joueur(joueur1)
    elo2 = get_joueur(joueur2)
    surf = _cle_surface(surface)

    # Blending surface + global (70/30)
    elo1_surface = elo1.get(surf, ELO_INITIAL)
    elo2_surface = elo2.get(surf, ELO_INITIAL)
    elo1_global = elo1.get("global", ELO_INITIAL)
    elo2_global = elo2.get("global", ELO_INITIAL)

    elo1_final = 0.70 * elo1_surface + 0.30 * elo1_global
    elo2_final = 0.70 * elo2_surface + 0.30 * elo2_global

    # Nombre de matchs (confiance dans l'Elo)
    matchs1 = elo1.get("matchs", 0)
    matchs2 = elo2.get("matchs", 0)

    # Formule Elo classique
    ecart = elo2_final - elo1_final
    proba = 1.0 / (1.0 + 10 ** (ecart / 400.0))

    # Confiance basée sur le nombre de matchs (max 1.0 à 30 matchs)
    confiance_elo = min(1.0, (matchs1 + matchs2) / 60.0)

    return {
        "proba": round(proba, 4),
        "elo1_surface": round(elo1_surface, 1),
        "elo2_surface": round(elo2_surface, 1),
        "elo1_global": round(elo1_global, 1),
        "elo2_global": round(elo2_global, 1),
        "elo1_final": round(elo1_final, 1),
        "elo2_final": round(elo2_final, 1),
        "ecart": round(ecart, 1),
        "matchs1": matchs1,
        "matchs2": matchs2,
        "confiance_elo": round(confiance_elo, 3),
        "surface": surf,
    }


# ============================================================
# BLENDING ELO + COTE BOOKMAKER
# ============================================================
def blend_elo_cote(proba_cote, proba_elo_val, confiance_elo=0.5):
    """
    Combine la proba du bookmaker et celle de l'Elo.

    Pondération adaptative :
    - Si l'Elo a peu de données (confiance faible) → on fait
      confiance au bookmaker
    - Si l'Elo a beaucoup de données → on lui donne plus de poids

    Formule :
    poids_elo = 0.20 + 0.30 × confiance_elo   (entre 0.20 et 0.50)
    poids_cote = 1 - poids_elo
    """
    poids_elo = 0.20 + 0.30 * confiance_elo
    poids_cote = 1.0 - poids_elo

    proba_finale = poids_cote * proba_cote + poids_elo * proba_elo_val

    return {
        "proba_finale": round(max(0.02, min(0.98, proba_finale)), 4),
        "poids_elo": round(poids_elo, 4),
        "poids_cote": round(poids_cote, 4),
    }


# ============================================================
# MISE À JOUR APRÈS MATCH
# ============================================================
def _esperance_elo(elo1, elo2):
    """Espérance de gain du joueur 1 (probabilité de victoire selon Elo)."""
    return 1.0 / (1.0 + 10 ** ((elo2 - elo1) / 400.0))


def _maj_elo_paire(elo_j1, elo_j2, k_factor):
    """
    Calcule les nouveaux Elo après un match.
    Retourne (nouveau_elo_j1, nouveau_elo_j2).
    """
    e1 = _esperance_elo(elo_j1, elo_j2)
    e2 = 1.0 - e1

    # Score réel : 1 si le joueur 1 gagne, 0 sinon
    s1 = 1.0
    s2 = 0.0

    new_elo_j1 = elo_j1 + k_factor * (s1 - e1)
    new_elo_j2 = elo_j2 + k_factor * (s2 - e2)

    # Bornes
    new_elo_j1 = max(ELO_MIN, min(ELO_MAX, new_elo_j1))
    new_elo_j2 = max(ELO_MIN, min(ELO_MAX, new_elo_j2))

    return new_elo_j1, new_elo_j2


def enregistrer_match(joueur_gagnant, joueur_perdant, surface="dur", competition=""):
    """
    Met à jour les Elo (global + surface) des 2 joueurs après un match.

    - joueur_gagnant : nom du joueur qui a gagné
    - joueur_perdant : nom du joueur qui a perdu
    - surface : "terre", "gazon", "dur", "indoor"
    - competition : utile pour le K-factor
    """
    k_factor = _get_k_factor(competition)
    surf = _cle_surface(surface)

    elo = _charger_elo()
    cle1 = _normaliser_nom(joueur_gagnant)
    cle2 = _normaliser_nom(joueur_perdant)

    if not cle1 or not cle2:
        return None

    # Init profils si absents
    for cle in (cle1, cle2):
        if cle not in elo:
            elo[cle] = {
                "global": ELO_INITIAL,
                "terre": ELO_INITIAL,
                "gazon": ELO_INITIAL,
                "dur": ELO_INITIAL,
                "indoor": ELO_INITIAL,
                "matchs": 0,
            }

    # --- Mise à jour Elo global ---
    eg1, eg2 = _maj_elo_paire(elo[cle1]["global"], elo[cle2]["global"], k_factor)
    elo[cle1]["global"] = round(eg1, 1)
    elo[cle2]["global"] = round(eg2, 1)

    # --- Mise à jour Elo surface ---
    es1, es2 = _maj_elo_paire(elo[cle1][surf], elo[cle2][surf], k_factor)
    elo[cle1][surf] = round(es1, 1)
    elo[cle2][surf] = round(es2, 1)

    # --- Incrément du compteur de matchs ---
    elo[cle1]["matchs"] = elo[cle1].get("matchs", 0) + 1
    elo[cle2]["matchs"] = elo[cle2].get("matchs", 0) + 1

    _ecrire_elo(elo)

    return {
        "joueur_gagnant": cle1,
        "joueur_perdant": cle2,
        "surface": surf,
        "k_factor": k_factor,
        "nouveau_elo_gagnant_global": elo[cle1]["global"],
        "nouveau_elo_perdant_global": elo[cle2]["global"],
        "nouveau_elo_gagnant_surface": elo[cle1][surf],
        "nouveau_elo_perdant_surface": elo[cle2][surf],
    }


def get_top_joueurs(n=10, surface=None):
    """Retourne le top N des joueurs selon leur Elo global ou de surface."""
    elo = _charger_elo()
    if not elo:
        return []
    surf = _cle_surface(surface) if surface else None

    classement = []
    for nom, profil in elo.items():
        if surf:
            score = profil.get(surf, ELO_INITIAL)
        else:
            score = profil.get("global", ELO_INITIAL)
        classement.append({
            "nom": nom,
            "elo": round(score, 1),
            "matchs": profil.get("matchs", 0),
        })

    classement.sort(key=lambda x: x["elo"], reverse=True)
    return classement[:n]



# ============================================================
# ✨ MOMENTUM — Indice de dynamique récente
# ============================================================
def calculer_momentum(joueur, n_recent=5):
    """
    Calcule un indice de momentum pour un joueur.

    Basé sur les 5 derniers matchs enregistrés dans l'historique.
    Combine :
    - Streak de victoires/défaites récentes
    - Évolution de l'Elo sur les 30 derniers jours (approximée)
    - Nombre de sets gagnés/perdus

    Retourne un score entre -1.0 (mauvais momentum) et +1.0 (excellent momentum).
    """
    from qfte_engine.historique import charger_historique

    historique = charger_historique()
    cle = _normaliser_nom(joueur)

    matchs_recents = []
    for h in reversed(historique):
        if h.get("sport") != "tennis":
            continue
        e1 = _normaliser_nom(h.get("equipe1", ""))
        e2 = _normaliser_nom(h.get("equipe2", ""))
        if cle not in (e1, e2):
            continue
        res = h.get("resultat")
        if not res:
            continue
        sh = res.get("score_home", 0)
        sa = res.get("score_away", 0)
        if cle == e1:
            gagne = sh > sa
            sets_pour, sets_contre = sh, sa
        else:
            gagne = sa > sh
            sets_pour, sets_contre = sa, sh

        matchs_recents.append({
            "gagne": gagne,
            "sets_pour": sets_pour,
            "sets_contre": sets_contre,
            "date": h.get("date", ""),
        })
        if len(matchs_recents) >= n_recent:
            break

    if not matchs_recents:
        return {
            "score": 0.0,
            "victoires": 0,
            "defaites": 0,
            "streak": 0,
            "nb_matchs": 0,
            "interpretation": "Aucune donnée récente",
        }

    # --- Streak (série en cours, limité à n_recent) ---
    streak = 0
    for m in matchs_recents:
        if m["gagne"]:
            if streak >= 0:
                streak += 1
            else:
                break
        else:
            if streak <= 0:
                streak -= 1
            else:
                break

    # --- Victoires/défaites ---
    victoires = sum(1 for m in matchs_recents if m["gagne"])
    defaites = len(matchs_recents) - victoires

    # --- Ratio sets gagnés ---
    total_sets_p = sum(m["sets_pour"] for m in matchs_recents)
    total_sets_c = sum(m["sets_contre"] for m in matchs_recents)
    ratio_sets = total_sets_p / (total_sets_p + total_sets_c) if (total_sets_p + total_sets_c) > 0 else 0.5

    # --- Score composite ---
    # Poids : 40% winrate + 30% streak + 30% ratio sets
    winrate = victoires / len(matchs_recents)
    score_winrate = (winrate - 0.5) * 2  # -1 à +1
    score_streak = max(-1.0, min(1.0, streak / 5.0))
    score_ratio = (ratio_sets - 0.5) * 2  # -1 à +1

    score_final = 0.40 * score_winrate + 0.30 * score_streak + 0.30 * score_ratio

    # Interprétation
    if score_final >= 0.5:
        interpretation = "🔥 Excellent"
    elif score_final >= 0.2:
        interpretation = "✅ Bon"
    elif score_final >= -0.2:
        interpretation = "➖ Neutre"
    elif score_final >= -0.5:
        interpretation = "⚠️ Faible"
    else:
        interpretation = "❄️ Très faible"

    return {
        "score": round(score_final, 3),
        "victoires": victoires,
        "defaites": defaites,
        "streak": streak,
        "nb_matchs": len(matchs_recents),
        "winrate": round(winrate, 3),
        "ratio_sets": round(ratio_sets, 3),
        "interpretation": interpretation,
    }



# ============================================================
# ✨ FATIGUE — Impact du nombre de matchs récents
# ============================================================
def calculer_fatigue(matchs_7j, matchs_14j=0):
    """
    Calcule un indice de fatigue basé sur les matchs joués récemment.

    Paramètres :
    - matchs_7j : nombre de matchs joués dans les 7 derniers jours (0-10)
    - matchs_14j : nombre de matchs joués dans les 14 derniers jours (0-20)

    Retourne un score entre -0.30 (très fatigué) et +0.10 (reposé).

    Logique :
    - 0 matchs sur 7j → léger bonus (+0.05) — bien reposé
    - 1-2 matchs → neutre
    - 3-4 matchs → légère fatigue (-0.05)
    - 5-6 matchs → fatigue marquée (-0.15)
    - 7+ matchs → fatigue forte (-0.25)
    """
    try:
        m7 = max(0, int(matchs_7j or 0))
        m14 = max(0, int(matchs_14j or 0))
    except (ValueError, TypeError):
        m7 = 0
        m14 = 0

    # --- Impact principal : matchs sur 7 jours ---
    if m7 == 0:
        impact_7j = 0.05
    elif m7 <= 2:
        impact_7j = 0.0
    elif m7 <= 4:
        impact_7j = -0.05
    elif m7 <= 6:
        impact_7j = -0.15
    else:
        impact_7j = -0.25

    # --- Impact secondaire : densité sur 14 jours ---
    # Si plus de 10 matchs sur 14 jours = calendrier chargé
    impact_14j = 0.0
    if m14 >= 10:
        impact_14j = -0.08
    elif m14 >= 7:
        impact_14j = -0.04

    score_final = impact_7j + impact_14j
    score_final = max(-0.35, min(0.10, score_final))

    # Interprétation
    if score_final >= 0.03:
        interpretation = "💚 Bien reposé"
    elif score_final >= -0.03:
        interpretation = "➖ Fraîcheur normale"
    elif score_final >= -0.10:
        interpretation = "🟡 Légère fatigue"
    elif score_final >= -0.20:
        interpretation = "🟠 Fatigue marquée"
    else:
        interpretation = "🔴 Fatigue forte"

    return {
        "score": round(score_final, 3),
        "matchs_7j": m7,
        "matchs_14j": m14,
        "impact_7j": round(impact_7j, 3),
        "impact_14j": round(impact_14j, 3),
        "interpretation": interpretation,
    }
