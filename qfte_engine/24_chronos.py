"""
Couche CHRONOS · L'Architecte — QFTE V23.0.

Le N°10 algorithmique : analyse le TIMING des cotes, prédit les horizons
futurs, détecte les fenêtres d'or et délivre un plan de bataille.

7 piliers :
1. Vélocité (line velocity)
2. Direction prédite
3. Fenêtre optimale
4. Signal sharp money
5. Pression temporelle
6. VISION multi-horizons (T+2h, T+6h, T+12h)
7. GÉNIE SCORE + INSIGHT unique + PLAN DE BATAILLE

Adaptatif aux 4 sports.

© HAMZY × QFTE V23.0 · Couche CHRONOS
"""
import math
import hashlib
from datetime import datetime


# ============================================================
# CONFIGURATION PAR SPORT
# ============================================================
CHRONOS_CONFIG = {
    "football": {
        "fenetre_min_h": 4,
        "fenetre_max_h": 12,
        "volatilite_base": 0.035,
        "seuil_steam": 0.08,
    },
    "basket": {
        "fenetre_min_h": 3,
        "fenetre_max_h": 8,
        "volatilite_base": 0.045,
        "seuil_steam": 0.10,
    },
    "tennis": {
        "fenetre_min_h": 2,
        "fenetre_max_h": 6,
        "volatilite_base": 0.030,
        "seuil_steam": 0.06,
    },
    "hockey": {
        "fenetre_min_h": 3,
        "fenetre_max_h": 10,
        "volatilite_base": 0.040,
        "seuil_steam": 0.09,
    },
}


def _borne(x, mini=0.0, maxi=1.0):
    return max(mini, min(maxi, x))


def _config_chronos(sport):
    return CHRONOS_CONFIG.get(sport, CHRONOS_CONFIG["football"])


# ============================================================
# PILIER 1 — VÉLOCITÉ
# ============================================================
def _analyse_velocite(match):
    """
    Analyse la vitesse du mouvement de cote.
    On suppose une fenêtre d'observation standard de 24h.
    """
    co = float(match.get("cote_ouverture", 2.0) or 2.0)
    cf = float(match.get("cote_actuelle", 2.0) or 2.0)

    if co <= 0:
        return {"velocite": 0.0, "mouvement_total": 0.0, "mouvement_pct": 0.0}

    mouvement = cf - co
    mouvement_pct = mouvement / co

    # Fenêtre d'observation assumée : 24h
    heures_observation = 24.0
    velocite = mouvement_pct / heures_observation

    # Interprétation qualitative
    v_abs = abs(velocite)
    if v_abs < 0.0005:
        intensite = "🟢 Faible"
    elif v_abs < 0.002:
        intensite = "🟡 Modérée"
    elif v_abs < 0.005:
        intensite = "🟠 Forte"
    else:
        intensite = "🔴 Très forte"

    return {
        "velocite": round(velocite, 5),
        "mouvement_total": round(mouvement, 3),
        "mouvement_pct": round(mouvement_pct, 4),
        "intensite": intensite,
    }


# ============================================================
# PILIER 2 — DIRECTION PRÉDITE
# ============================================================
def _analyser_direction(velocite_data):
    """
    Prédit la direction future de la cote.
    Une vélocité négative = la cote baisse = sharps chargent.
    """
    v = velocite_data["velocite"]

    if v < -0.005:
        direction = "baisse_rapide"
        emoji = "📉📉"
        interpretation = "Sharps chargent fortement"
    elif v < -0.001:
        direction = "baisse"
        emoji = "📉"
        interpretation = "Cote en baisse progressive"
    elif v > 0.005:
        direction = "hausse_rapide"
        emoji = "📈📈"
        interpretation = "Cote en explosion — suspect"
    elif v > 0.001:
        direction = "hausse"
        emoji = "📈"
        interpretation = "Cote en hausse — public probable"
    else:
        direction = "stable"
        emoji = "➡️"
        interpretation = "Marché stable"

    return {
        "direction": direction,
        "emoji": emoji,
        "interpretation": interpretation,
    }


# ============================================================
# PILIER 6 — VISION MULTI-HORIZONS
# ============================================================
def _vision_horizons(match, velocite, direction):
    """
    Prédit la cote à T+2h, T+6h, T+12h.
    Utilise la vélocité + un facteur de dampening (les marchés ralentissent).
    """
    cf = float(match.get("cote_actuelle", 2.0) or 2.0)
    v = velocite

    # Dampening : les marchés ralentissent dans le temps
    dampening = {
        "baisse_rapide": 0.70,
        "baisse": 0.85,
        "stable": 1.00,
        "hausse": 0.85,
        "hausse_rapide": 0.70,
    }.get(direction["direction"], 1.0)

    horizons = []
    for h, label in [(2, "T+2h"), (6, "T+6h"), (12, "T+12h")]:
        variation = v * h * dampening
        cote_predite = cf * (1 + variation)
        cote_predite = max(1.01, round(cote_predite, 3))
        variation_pct = round(variation * 100, 2)

        if variation_pct < -1.0:
            tendance = "📉"
        elif variation_pct > 1.0:
            tendance = "📈"
        else:
            tendance = "➡️"

        horizons.append({
            "label": label,
            "heures": h,
            "cote_predite": cote_predite,
            "variation_pct": variation_pct,
            "tendance": tendance,
        })

    return horizons



# ============================================================
# PILIER 3 — FENÊTRE OPTIMALE
# ============================================================
def _fenetre_optimale(sport, velocite, direction):
    """
    Détermine la fenêtre d'or pour parier.
    Basée sur la vélocité, la direction et la config sport.
    """
    cfg = _config_chronos(sport)
    min_h = cfg["fenetre_min_h"]
    max_h = cfg["fenetre_max_h"]

    d = direction["direction"]

    if d == "baisse_rapide":
        # La cote chute vite → il faut agir MAINTENANT
        fenetre_min = 0
        fenetre_max = 2
        urgence = "🔴 IMMÉDIAT"
        message = "La cote chute vite — fenêtre ultra-courte"
    elif d == "baisse":
        # La cote baisse progressivement
        fenetre_min = 0
        fenetre_max = max(2, min_h)
        urgence = "🟠 COURTE"
        message = "Fenêtre courte mais exploitable"
    elif d == "stable":
        # Marché stable → on peut attendre
        fenetre_min = min_h
        fenetre_max = max_h
        urgence = "🟢 CONFORTABLE"
        message = "Marché calme — fenêtre large"
    elif d == "hausse":
        # La cote monte → pas de rush
        fenetre_min = 0
        fenetre_max = max_h + 4
        urgence = "🟢 LARGE"
        message = "Cote en hausse — pas d'urgence"
    else:  # hausse_rapide
        # La cote explose → suspect, prudence
        fenetre_min = 0
        fenetre_max = max_h
        urgence = "🟡 SUSPECT"
        message = "Cote en explosion — marché suspect, prudence"

    return {
        "fenetre_min_h": fenetre_min,
        "fenetre_max_h": fenetre_max,
        "urgence": urgence,
        "message": message,
    }


# ============================================================
# PILIER 4 — SIGNAL SHARP MONEY
# ============================================================
def _signal_sharp(velocite_data, marge, volume):
    """
    Détecte l'argent intelligent.
    Combine : mouvement de cote + marge + volume.
    Score 0-100.
    """
    score = 0.0

    # Composante 1 : direction de la vélocité (0-40 pts)
    v = velocite_data["velocite"]
    if v < -0.005:
        score += 40
    elif v < -0.002:
        score += 30
    elif v < -0.001:
        score += 20
    elif v < 0:
        score += 10

    # Composante 2 : marge bookmaker (0-30 pts)
    # Marge faible = marché efficient + sharps présents
    if marge < 0.03:
        score += 30
    elif marge < 0.04:
        score += 22
    elif marge < 0.05:
        score += 15
    elif marge < 0.06:
        score += 8

    # Composante 3 : volume (0-30 pts)
    if volume > 500000:
        score += 30
    elif volume > 200000:
        score += 22
    elif volume > 100000:
        score += 15
    elif volume > 50000:
        score += 8

    score = max(0, min(100, score))

    # Interprétation
    if score >= 75:
        niveau = "🐋 Sharp Money FORT"
        emoji = "🐋"
    elif score >= 55:
        niveau = "🎯 Sharp Money probable"
        emoji = "🎯"
    elif score >= 35:
        niveau = "🟡 Signal modéré"
        emoji = "🟡"
    else:
        niveau = "➖ Pas de signal sharp"
        emoji = "➖"

    return {
        "score": round(score, 1),
        "niveau": niveau,
        "emoji": emoji,
    }


# ============================================================
# PILIER 5 — PRESSION TEMPORELLE
# ============================================================
def _pression_temporelle(velocite_data, fenetre, direction):
    """
    Mesure l'urgence du marché.
    Score -1 (aucune urgence) à +1 (urgence maximale).
    """
    pression = 0.0

    # Composante 1 : vélocité absolue
    v_abs = abs(velocite_data["velocite"])
    pression += _borne(v_abs / 0.01, 0, 1) * 0.5

    # Composante 2 : urgence de la fenêtre
    urgence_map = {
        "🔴 IMMÉDIAT": 0.5,
        "🟠 COURTE": 0.3,
        "🟢 CONFORTABLE": 0.05,
        "🟢 LARGE": -0.1,
        "🟡 SUSPECT": 0.2,
    }
    pression += urgence_map.get(fenetre["urgence"], 0.0)

    # Composante 3 : direction (baisse = pression positive)
    d = direction["direction"]
    if d == "baisse_rapide":
        pression += 0.3
    elif d == "baisse":
        pression += 0.15
    elif d == "hausse":
        pression -= 0.1
    elif d == "hausse_rapide":
        pression -= 0.2

    pression = max(-1.0, min(1.0, pression))

    if pression >= 0.6:
        niveau = "🔥 Urgence forte"
    elif pression >= 0.3:
        niveau = "🟠 Urgence modérée"
    elif pression >= 0:
        niveau = "🟢 Urgence faible"
    else:
        niveau = "❄️ Aucune urgence"

    return {
        "score": round(pression, 3),
        "niveau": niveau,
  }



# ============================================================
# GÉNIE SCORE — Agrégation de 7 dimensions
# ============================================================
def _calculer_genie_score(data, velocite, direction, fenetre, sharp, pression):
    """
    Calcule un score global (0-100) qui mesure l'intelligence de la situation.

    7 dimensions :
    1. Cohérence des couches (AURA + ORACLE)
    2. Qualité de la value (EV)
    3. Timing optimal
    4. Force du signal sharp
    5. Liquidité
    6. Consensus des modèles
    7. Robustesse globale
    """
    scores = []
    poids = []

    # --- Dimension 1 : Cohérence AURA (0-1) ---
    aura = data.get("aura", {})
    aura_score = float(aura.get("score", 50)) / 100.0
    scores.append(aura_score)
    poids.append(0.20)

    # --- Dimension 2 : Qualité de la value (EV) ---
    recos = data.get("recommandations", [])
    ev_max = 0.0
    for r in recos:
        try:
            ev_str = str(r.get("ev", "0%")).replace("%", "").strip()
            ev_val = abs(float(ev_str)) / 100
            if ev_val > ev_max:
                ev_max = ev_val
        except (ValueError, TypeError):
            pass
    # EV de 0% → 0.3, EV de 8% → 1.0
    value_score = _borne(0.3 + ev_max / 0.08 * 0.7)
    scores.append(value_score)
    poids.append(0.15)

    # --- Dimension 3 : Timing optimal ---
    # Basé sur la pression temporelle et la fenêtre
    pression_score = (pression["score"] + 1) / 2  # -1..1 → 0..1
    scores.append(pression_score)
    poids.append(0.15)

    # --- Dimension 4 : Force du signal sharp ---
    sharp_score = sharp["score"] / 100.0
    scores.append(sharp_score)
    poids.append(0.15)

    # --- Dimension 5 : Liquidité ---
    volume = float(data.get("volume", 0))
    liquidite = _borne(volume / 200000)
    scores.append(liquidite)
    poids.append(0.10)

    # --- Dimension 6 : Consensus des modèles ---
    # Basé sur la fiabilité moyenne des recos
    fiabilites = []
    for r in recos:
        try:
            fiabilites.append(float(r.get("fiabilite", 0)))
        except (ValueError, TypeError):
            pass
    if fiabilites:
        fiab_moy = sum(fiabilites) / len(fiabilites)
        scores.append(_borne(fiab_moy))
    else:
        scores.append(0.5)
    poids.append(0.15)

    # --- Dimension 7 : Robustesse ORACLE ---
    oracle = data.get("oracle", {})
    oracle_metriques = oracle.get("metriques", {})
    stabilite = float(oracle_metriques.get("stabilite", 50)) / 100.0
    scores.append(stabilite)
    poids.append(0.10)

    # --- Moyenne pondérée ---
    total_poids = sum(poids)
    genie_score = sum(s * p for s, p in zip(scores, poids)) / total_poids * 100
    genie_score = round(genie_score, 1)

    # --- Niveau ---
    if genie_score >= 90:
        niveau = "GÉNIE"
        emoji = "🎩"
        couleur = "#fbbf24"
        description = "Analyse exceptionnelle — situation rare"
    elif genie_score >= 75:
        niveau = "MAESTRO"
        emoji = "🎯"
        couleur = "#facc15"
        description = "Analyse brillante — situation solide"
    elif genie_score >= 60:
        niveau = "CRÉATIF"
        emoji = "🎨"
        couleur = "#60a5fa"
        description = "Analyse correcte — situation exploitable"
    elif genie_score >= 40:
        niveau = "EXÉCUTANT"
        emoji = "⚙️"
        couleur = "#9ca3af"
        description = "Analyse moyenne — prudence"
    else:
        niveau = "AUTOMATE"
        emoji = "🤖"
        couleur = "#6b7280"
        description = "Analyse faible — situation à éviter"

    return {
        "score": genie_score,
        "niveau": niveau,
        "emoji": emoji,
        "couleur": couleur,
        "description": description,
        "dimensions": {
            "cohérence_aura": round(scores[0], 3),
            "qualité_value": round(scores[1], 3),
            "timing": round(scores[2], 3),
            "signal_sharp": round(scores[3], 3),
            "liquidité": round(scores[4], 3),
            "consensus": round(scores[5], 3),
            "robustesse": round(scores[6], 3),
        },
    }


# ============================================================
# DÉCISION TIMING PRINCIPALE
# ============================================================
def _decision_timing(direction, fenetre, sharp, pression, genie):
    """
    Décision finale : BET NOW / WAIT / ABORT / ALERT
    """
    d = direction["direction"]
    urgence = fenetre["urgence"]

    # Conditions d'abandon
    if d == "hausse_rapide":
        return {
            "decision": "ALERT",
            "emoji": "🔴",
            "couleur": "#ef4444",
            "message": "Cote en explosion — marché suspect, on recule",
        }

    if genie["score"] < 40:
        return {
            "decision": "ABORT",
            "emoji": "🚫",
            "couleur": "#6b7280",
            "message": "Analyse trop faible — range les crampons",
        }

    # BET NOW conditions
    if d in ("baisse_rapide", "baisse") or urgence == "🔴 IMMÉDIAT":
        if sharp["score"] >= 50:
            return {
                "decision": "BET NOW",
                "emoji": "🟢",
                "couleur": "#4ade80",
                "message": "Fenêtre d'or active — sharp money présent — FEU",
            }
        else:
            return {
                "decision": "BET NOW",
                "emoji": "🟢",
                "couleur": "#4ade80",
                "message": "Fenêtre se referme — agir maintenant",
            }

    # WAIT conditions
    if d == "stable" and pression["score"] < 0.3:
        return {
            "decision": "WAIT",
            "emoji": "🟡",
            "couleur": "#facc15",
            "message": "Marché calme — attends 2-4h, la cote peut s'améliorer",
        }

    # BET NOW par défaut si genie élevé
    if genie["score"] >= 75:
        return {
            "decision": "BET NOW",
            "emoji": "🟢",
            "couleur": "#4ade80",
            "message": "Situation optimale — FEU VERT immédiat",
        }

    # Sinon WAIT
    return {
        "decision": "WAIT",
        "emoji": "🟡",
        "couleur": "#facc15",
        "message": "Attends la prochaine mise à jour des cotes",
  }



# ============================================================
# INSIGHT UNIQUE — La phrase signature du N°10
# ============================================================
def _generer_insight(direction, sharp, pression, genie, fenetre, velocite):
    """
    Génère une phrase unique qui capture l'essence de la situation.
    """
    d = direction["direction"]
    g = genie["score"]
    s = sharp["score"]
    p = pression["score"]

    # Cas 1 : Situation exceptionnelle
    if g >= 85 and d == "baisse_rapide" and s >= 70:
        return "Tout converge. C'est une des 5% de situations où le N°10 tente la frappe."

    if g >= 85 and d == "stable":
        return "Le marché dort encore. La value va disparaître. Réveille-toi."

    # Cas 2 : Value + timing parfait
    if g >= 75 and d == "baisse":
        return "La cote chute progressivement. Les sharps chargent. Suis-les."

    if g >= 75 and d == "hausse":
        return "Le public charge, les sharps reculent. Reste calme, la value arrive."

    # Cas 3 : Pression forte
    if p >= 0.6 and d == "baisse_rapide":
        return "Fenêtre ultra-courte. 2h pour agir. Après, la cote s'effondre."

    if p >= 0.5 and d == "stable":
        return "Tout est calme, mais l'orage approche. Positionne-toi maintenant."

    # Cas 4 : Steam move détecté
    if s >= 75:
        return "Steam move en cours. L'argent intelligent est déjà passé. Tu peux suivre."

    # Cas 5 : Marché suspect
    if d == "hausse_rapide":
        return "La cote explose sans raison claire. Les sharps se retirent. Piège probable."

    # Cas 6 : Situation faible
    if g < 40:
        return "Match trop incertain même pour un Architecte. On passe, sans regret."

    # Cas 7 : Statu quo
    if d == "stable" and s < 35:
        return "Rien ne bouge. Pas de signal. Le N°10 temporise, la balle circule."

    # Cas 8 : Génie fort générique
    if g >= 75:
        return "La situation est mûre. Le N°10 voit l'ouverture. Prépare la frappe."

    # Cas 9 : Génie moyen
    if g >= 60:
        return "Quelques signaux positifs. Le N°10 teste la défense. Œil ouvert."

    # Cas 10 : Défaut
    return "Marché ordinaire. Le N°10 garde le ballon, attend son moment."


# ============================================================
# PLAN DE BATAILLE
# ============================================================
def _plan_de_bataille(data, decision, genie, direction):
    """
    Génère un plan stratégique en 3 lignes : Action, Mise, Sortie.
    """
    recos = data.get("recommandations", [])
    meilleure = None
    meilleur_ev = -999
    for r in recos:
        try:
            ev_str = str(r.get("ev", "0%")).replace("%", "").strip()
            ev_val = float(ev_str)
            if ev_val > meilleur_ev:
                meilleur_ev = ev_val
                meilleure = r
        except (ValueError, TypeError):
            pass

    if not meilleure:
        return {
            "action": "Aucun pari recommandé",
            "mise": "0%",
            "sortie": "Revenir quand le marché bouge",
        }

    marche = meilleure.get("marche", "-")
    selection = meilleure.get("selection", "-")
    cote = meilleure.get("cote", "-")
    stake = meilleure.get("stake", "0%")

    # Action
    if decision["decision"] == "BET NOW":
        action = f"Frapper sur {marche} — {selection} @ {cote}"
    elif decision["decision"] == "WAIT":
        action = f"Attendre 2-4h, puis viser {marche} — {selection}"
    elif decision["decision"] == "ALERT":
        action = f"Surveiller {marche} — situation instable"
    else:
        action = "Ne pas parier sur ce match"

    # Mise
    if decision["decision"] == "BET NOW" and genie["score"] >= 75:
        mise = f"Mise forte recommandée : {stake}"
    elif decision["decision"] == "BET NOW":
        mise = f"Mise standard : {stake}"
    else:
        mise = "Mise : en attente"

    # Sortie
    d = direction["direction"]
    if d == "baisse":
        sortie = "Si la cote chute encore de 5% → hedge partiel"
    elif d == "baisse_rapide":
        sortie = "Si la cote atteint -8% → sortie totale"
    elif d == "hausse":
        sortie = "Surveiller la stabilisation, entrer au pic"
    else:
        sortie = "Prendre le résultat, pas de gestion active"

    return {
        "action": action,
        "mise": mise,
        "sortie": sortie,
    }


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
def calculer_chronos(data):
    """
    Couche CHRONOS · L'Architecte :
    - Analyse 7 piliers temporels
    - Génie Score (0-100)
    - Décision timing (BET NOW / WAIT / ABORT / ALERT)
    - Insight unique
    - Plan de bataille
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    # Récupération des données pour l'analyse
    marge = float(data.get("marge_estimee", 0.05) or 0.05)
    volume = float(data.get("volume", 50000) or 50000)

    # --- 7 PILIERS ---
    velocite_data = _analyse_velocite(match)
    direction = _analyser_direction(velocite_data)
    horizons = _vision_horizons(match, velocite_data["velocite"], direction)
    fenetre = _fenetre_optimale(sport, velocite_data, direction)
    sharp = _signal_sharp(velocite_data, marge, volume)
    pression = _pression_temporelle(velocite_data, fenetre, direction)

    # --- GÉNIE SCORE ---
    genie = _calculer_genie_score(
        data, velocite_data, direction, fenetre, sharp, pression
    )

    # --- DÉCISION TIMING ---
    decision = _decision_timing(direction, fenetre, sharp, pression, genie)

    # --- INSIGHT UNIQUE ---
    insight = _generer_insight(
        direction, sharp, pression, genie, fenetre, velocite_data
    )

    # --- PLAN DE BATAILLE ---
    plan = _plan_de_bataille(data, decision, genie, direction)

    # --- SIGNATURE ---
    timestamp = datetime.now().isoformat()
    cle = "CHRONOS-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        sport,
        genie["score"],
        timestamp,
    )
    empreinte = hashlib.sha256(cle.encode("utf-8")).hexdigest()

    data["chronos"] = {
        "sport": sport,
        "velocite": velocite_data,
        "direction": direction,
        "horizons": horizons,
        "fenetre": fenetre,
        "sharp": sharp,
        "pression": pression,
        "genie": genie,
        "decision": decision,
        "insight": insight,
        "plan": plan,
        "empreinte": empreinte,
        "empreinte_courte": empreinte[:12].upper(),
        "timestamp": timestamp,
        "sceau": "🎩 CHRONOS · L'Architecte · QFTE V23.0",
    }
    return data
