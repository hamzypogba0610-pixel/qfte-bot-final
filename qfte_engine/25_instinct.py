"""
Couche L'INSTINCT · Le Tueur — QFTE V23.0.

Le N°9 algorithmique : prend TOUTES les couches (AURA + ORACLE + CHRONOS
+ les 22 autres) et délivre UNE frappe nette, précise, sans hésitation.

Attributs du N°9 :
- Sang-froid : ignore le bruit
- Précision : choisit LE marché
- Vitesse : décide en un coup
- Puissance : conviction binaire (FEU ou PAS DE FEU)
- Lecture : lit le marché en un regard
- Finition : transforme l'opportunité en frappe nette
- Mental : assume le pari

Sortie :
- INSTINCT SCORE (0-100)
- DÉCISION BINAIRE (FEU VERT / FEU ORANGE / PAS DE FEU)
- ZONE DE FRAPPE (marché/sélection/cote/mise)
- INSTINCT PUR (phrase signature)

© HAMZY × QFTE V23.0 · Couche INSTINCT
"""
import hashlib
from datetime import datetime


# Configuration par sport
INSTINCT_CONFIG = {
    "football": {"seuil_feu_vert": 75, "seuil_feu_orange": 55},
    "basket":   {"seuil_feu_vert": 72, "seuil_feu_orange": 52},
    "tennis":   {"seuil_feu_vert": 78, "seuil_feu_orange": 58},
    "hockey":   {"seuil_feu_vert": 74, "seuil_feu_orange": 54},
}


def _borne(x, mini=0.0, maxi=1.0):
    return max(mini, min(maxi, x))


def _config_instinct(sport):
    return INSTINCT_CONFIG.get(sport, INSTINCT_CONFIG["football"])


# ============================================================
# LECTURE DES COUCHES — On rassemble TOUT
# ============================================================
def _lire_couches(data):
    """
    Lit les scores de toutes les couches principales.
    """
    aura = data.get("aura", {})
    oracle = data.get("oracle", {})
    chronos = data.get("chronos", {})

    # AURA (qualité globale)
    aura_score = float(aura.get("score", 50))

    # ORACLE (stabilité)
    oracle_metriques = oracle.get("metriques", {})
    oracle_stabilite = float(oracle_metriques.get("stabilite", 50))
    oracle_ecart = float(oracle_metriques.get("ecart_type", 0.5))
    oracle_ic_largeur = float(oracle_metriques.get("ic_haut", 0)) - float(oracle_metriques.get("ic_bas", 0))

    # CHRONOS (timing + génie)
    chronos_genie = float(chronos.get("genie", {}).get("score", 50))
    chronos_decision = chronos.get("decision", {}).get("decision", "WAIT")
    chronos_sharp = float(chronos.get("sharp", {}).get("score", 0))

    return {
        "aura": aura_score,
        "oracle_stabilite": oracle_stabilite,
        "oracle_ecart": oracle_ecart,
        "oracle_ic_largeur": oracle_ic_largeur,
        "chronos_genie": chronos_genie,
        "chronos_decision": chronos_decision,
        "chronos_sharp": chronos_sharp,
}



# ============================================================
# INSTINCT SCORE — La conviction pure
# ============================================================
def _calculer_instinct_score(data, lecture):
    """
    Calcule le score de conviction (0-100).
    Agrège les couches en une conviction binaire.
    """
    scores = []
    poids = []

    # --- Composante 1 : AURA (qualité globale) ---
    scores.append(lecture["aura"] / 100.0)
    poids.append(0.25)

    # --- Composante 2 : CHRONOS Génie (intelligence situation) ---
    scores.append(lecture["chronos_genie"] / 100.0)
    poids.append(0.25)

    # --- Composante 3 : ORACLE stabilité ---
    scores.append(lecture["oracle_stabilite"] / 100.0)
    poids.append(0.15)

    # --- Composante 4 : Signal sharp (argent intelligent) ---
    scores.append(lecture["chronos_sharp"] / 100.0)
    poids.append(0.15)

    # --- Composante 5 : Décision timing (bonus) ---
    decision_timing = lecture["chronos_decision"]
    if decision_timing == "BET NOW":
        timing_score = 1.0
    elif decision_timing == "WAIT":
        timing_score = 0.55
    elif decision_timing == "ALERT":
        timing_score = 0.20
    else:  # ABORT
        timing_score = 0.10
    scores.append(timing_score)
    poids.append(0.10)

    # --- Composante 6 : Concision de l'IC ORACLE ---
    # IC étroit = confiance élevée
    ic_largeur = lecture["oracle_ic_largeur"]
    if ic_largeur < 0.05:
        ic_score = 1.0
    elif ic_largeur < 0.10:
        ic_score = 0.8
    elif ic_largeur < 0.15:
        ic_score = 0.6
    elif ic_largeur < 0.20:
        ic_score = 0.4
    else:
        ic_score = 0.2
    scores.append(ic_score)
    poids.append(0.10)

    # --- Moyenne pondérée ---
    total_poids = sum(poids)
    instinct_score = sum(s * p for s, p in zip(scores, poids)) / total_poids * 100
    instinct_score = round(instinct_score, 1)

    return {
        "score": instinct_score,
        "composantes": {
            "aura": round(scores[0], 3),
            "chronos_genie": round(scores[1], 3),
            "oracle_stabilite": round(scores[2], 3),
            "signal_sharp": round(scores[3], 3),
            "timing": round(scores[4], 3),
            "ic_concision": round(scores[5], 3),
        },
    }


# ============================================================
# DÉCISION BINAIRE — FEU ou PAS DE FEU
# ============================================================
def _decision_binaire(instinct_score, lecture, sport):
    """
    Décision binaire du N°9.
    Pas d'hésitation : FEU VERT / FEU ORANGE / PAS DE FEU.
    """
    cfg = _config_instinct(sport)
    seuil_vert = cfg["seuil_feu_vert"]
    seuil_orange = cfg["seuil_feu_orange"]

    score = instinct_score["score"]

    # Blocage dur : si CHRONOS dit ABORT ou ALERT
    if lecture["chronos_decision"] in ("ABORT", "ALERT"):
        return {
            "decision": "PAS DE FEU",
            "emoji": "🚫",
            "couleur": "#6b7280",
            "message": "CHRONOS bloque — on range les crampons",
        }

    # FEU VERT : tous les signaux alignés
    if score >= seuil_vert:
        return {
            "decision": "FEU VERT",
            "emoji": "🟢",
            "couleur": "#4ade80",
            "message": "Le N°9 ne réfléchit pas. Il frappe. Maintenant.",
        }

    # FEU ORANGE : situation exploitable mais pas optimale
    if score >= seuil_orange:
        return {
            "decision": "FEU ORANGE",
            "emoji": "🟡",
            "couleur": "#facc15",
            "message": "Frappe modérée. Prudence, mais opportunité présente.",
        }

    # PAS DE FEU
    return {
        "decision": "PAS DE FEU",
        "emoji": "🔴",
        "couleur": "#ef4444",
        "message": "Trop de défenseurs. On temporise, on cherche l'ouverture.",
    }


# ============================================================
# ZONE DE FRAPPE — LE pari unique
# ============================================================
def _zone_de_frappe(data):
    """
    Choisit LE marché, LA sélection, LA cote, LA mise.
    Le N°9 ne tire qu'une fois.
    """
    recos = data.get("recommandations", [])
    if not recos:
        return {
            "marche": "-",
            "selection": "-",
            "cote": "-",
            "mise": "0%",
            "niveau": "AVOID",
        }

    # Sélection de la meilleure reco par EV
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
            "marche": "-",
            "selection": "-",
            "cote": "-",
            "mise": "0%",
            "niveau": "AVOID",
        }

    return {
        "marche": meilleure.get("marche", "-"),
        "selection": meilleure.get("selection", "-"),
        "cote": meilleure.get("cote", "-"),
        "mise": meilleure.get("stake", "0%"),
        "niveau": meilleure.get("niveau", "AVOID"),
        "ev": meilleure.get("ev", "0%"),
        "fiabilite": meilleure.get("fiabilite", "0"),
  }



# ============================================================
# INSTINCT PUR — La phrase qui claque
# ============================================================
def _generer_instinct_pur(decision, instinct_score, lecture, zone):
    """
    Génère une phrase signature du N°9.
    Courte. Tranchante. Mémorable.
    """
    d = decision["decision"]
    score = instinct_score["score"]
    sharp = lecture["chronos_sharp"]
    timing = lecture["chronos_decision"]
    niveau = zone.get("niveau", "AVOID")

    # --- FEU VERT ---
    if d == "FEU VERT":
        if score >= 90 and sharp >= 75 and timing == "BET NOW":
            return "Ce n'est pas un tir. C'est une exécution. La lucarne est ouverte."
        if score >= 85 and timing == "BET NOW":
            return "Tout est aligné. Le N°9 ne réfléchit pas. Il frappe. Maintenant."
        if niveau == "ELITE":
            return "Le gardien est avancé. La frappe est évidente. Sang-froid."
        return "Feu vert. Le N°9 arme sa frappe. Précision chirurgicale."

    # --- FEU ORANGE ---
    if d == "FEU ORANGE":
        if score >= 68 and sharp >= 55:
            return "Le ballon arrive. Le N°9 temporise, cherche l'ouverture parfaite."
        if timing == "WAIT":
            return "Frappe possible, mais le N°9 voit mieux dans 2h. Patience."
        if niveau in ("GOOD", "PREMIUM"):
            return "Frappe contrôlée. Le N°9 garde le ballon, prêt à accélérer."
        return "Signaux partiels. Le N°9 teste la défense. Frappe modérée."

    # --- PAS DE FEU ---
    if d == "PAS DE FEU":
        if timing in ("ABORT", "ALERT"):
            return "CHRONOS a bloqué. Le N°9 baisse la tête. On range les crampons."
        if score < 40:
            return "Aucun signal. Le N°9 ne frappe pas dans le vide. On passe."
        if timing == "WAIT":
            return "Pas le moment. Le N°9 temporise, l'occasion viendra."
        return "Trop de défenseurs. Le N°9 recule, cherche une autre brèche."

    # --- Défaut ---
    return "Le N°9 analyse. Rien ne presse. Il attend son moment."


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
def calculer_instinct(data):
    """
    Couche L'INSTINCT · Le Tueur :
    - Lecture des autres couches
    - INSTINCT SCORE (0-100)
    - DÉCISION BINAIRE (FEU VERT / FEU ORANGE / PAS DE FEU)
    - ZONE DE FRAPPE (marché/sélection/cote/mise)
    - INSTINCT PUR (phrase signature)
    - Signature unique
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    # --- LECTURE des couches ---
    lecture = _lire_couches(data)

    # --- INSTINCT SCORE ---
    instinct_score = _calculer_instinct_score(data, lecture)

    # --- DÉCISION BINAIRE ---
    decision = _decision_binaire(instinct_score, lecture, sport)

    # --- ZONE DE FRAPPE ---
    zone = _zone_de_frappe(data)

    # --- INSTINCT PUR ---
    instinct_pur = _generer_instinct_pur(decision, instinct_score, lecture, zone)

    # --- SIGNATURE ---
    timestamp = datetime.now().isoformat()
    cle = "INSTINCT-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        sport,
        instinct_score["score"],
        timestamp,
    )
    empreinte = hashlib.sha256(cle.encode("utf-8")).hexdigest()

    data["instinct"] = {
        "sport": sport,
        "lecture": lecture,
        "instinct_score": instinct_score,
        "decision": decision,
        "zone": zone,
        "instinct_pur": instinct_pur,
        "empreinte": empreinte,
        "empreinte_courte": empreinte[:12].upper(),
        "timestamp": timestamp,
        "sceau": "💀 INSTINCT · Le Tueur · QFTE V23.0",
    }
    return data
