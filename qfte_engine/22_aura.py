"""
Couche AURA — Analyse Universelle de Robustesse et d'Attribution
QFTE V23.0.

Couche méta qui agrège toutes les autres couches en un score unique 0-100,
adapté aux 3 sports, avec attribution, détection de conflits et signature.

AURA = 4 signaux composites :
- A : Forces contextuelles (forme, H2H, momentum, fatigue, calendrier)
- U : Qualité des données (liquidité, cohérence, validation)
- R : Robustesse du modèle (calibration, BMA, attention, copula)
- A : Amplification (Couche A, ICP)

© HAMZY × QFTE V23.0 · Couche AURA
"""
import hashlib
from datetime import datetime


# Poids des signaux AURA par sport
POIDS_SPORT = {
    "football": {"A": 0.30, "U": 0.20, "R": 0.30, "AMP": 0.20},
    "basket":   {"A": 0.25, "U": 0.20, "R": 0.30, "AMP": 0.25},
    "tennis":   {"A": 0.35, "U": 0.15, "R": 0.30, "AMP": 0.20},
}


def _borne(x, mini=0.0, maxi=1.0):
    return max(mini, min(maxi, x))


# ============================================================
# SIGNAL A — Forces contextuelles
# ============================================================
def _signal_contextuel(data):
    """Agrège les signaux contextuels en un score 0-1."""
    scores = []
    poids = []

    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})

    # Forme nette (écart entre les 2 équipes)
    f_dom = abs(float(forme.get("dom_finale", 0)))
    f_ext = abs(float(forme.get("ext_finale", 0)))
    forme_clarte = _borne((f_dom + f_ext) / 2.0)
    scores.append(forme_clarte)
    poids.append(0.25)

    # H2H clarté
    if h2h.get("n", 0) >= 3:
        v_dom = h2h.get("v_dom", 0)
        v_ext = h2h.get("v_ext", 0)
        nuls = h2h.get("nuls", 0)
        total = v_dom + v_ext + nuls
        h2h_net = _borne((max(v_dom, v_ext) / total - 0.33) / 0.67) if total > 0 else 0.3
    else:
        h2h_net = 0.3
    scores.append(h2h_net)
    poids.append(0.20)

    # Momentum (tennis) ou calendrier impact (foot)
    momentum = data.get("momentum_info", {})
    if momentum:
        diff = abs(float(momentum.get("diff", 0)))
        scores.append(_borne(diff / 1.0))
        poids.append(0.20)

    calendrier = data.get("calendrier", {})
    if calendrier and calendrier.get("difference_lambda") is not None:
        diff = abs(float(calendrier["difference_lambda"]))
        scores.append(_borne(diff / 0.30))
        poids.append(0.20)

    calendrier_b = data.get("calendrier_basket", {})
    if calendrier_b and calendrier_b.get("difference_points") is not None:
        diff = abs(float(calendrier_b["difference_points"]))
        scores.append(_borne(diff / 8.0))
        poids.append(0.20)

    # Fatigue (tennis)
    fatigue = data.get("fatigue_info", {})
    if fatigue:
        diff = abs(float(fatigue.get("diff", 0)))
        scores.append(_borne(diff / 0.30))
        poids.append(0.15)

    if not scores:
        return 0.5

    total_poids = sum(poids)
    return sum(s * p for s, p in zip(scores, poids)) / total_poids


# ============================================================
# SIGNAL U — Qualité des données
# ============================================================
def _signal_qualite(data):
    """Agrège la qualité des données en un score 0-1."""
    scores = []
    poids = []

    # Score de validation des cotes
    validation = data.get("validation", {})
    val_score = float(validation.get("score", 70)) / 100.0
    scores.append(val_score)
    poids.append(0.40)

    # Liquidité
    volume = float(data.get("volume", 0))
    liquidite = _borne(volume / 200000)
    scores.append(liquidite)
    poids.append(0.30)

    # Cohérence des cotes (via contexte)
    contexte = data.get("contexte", {})
    cotes_ctx = contexte.get("cotes", {})
    if cotes_ctx:
        marge = float(cotes_ctx.get("marge_book", 5.0))
        coherence = _borne(1.0 - marge / 15.0)
        scores.append(coherence)
        poids.append(0.30)

    if not scores:
        return 0.5

    total_poids = sum(poids)
    return sum(s * p for s, p in zip(scores, poids)) / total_poids



# ============================================================
# SIGNAL R — Robustesse du modèle
# ============================================================
def _signal_robustesse(data):
    """Agrège la robustesse du modèle en un score 0-1."""
    scores = []
    poids = []

    # BMA actif ?
    bma_actif = bool(data.get("bma_actif", False))
    scores.append(1.0 if bma_actif else 0.4)
    poids.append(0.20)

    # Calibrateurs actifs (nombre)
    calib_actifs = int(data.get("calibrateurs_actifs", 0))
    scores.append(_borne(calib_actifs / 3.0))
    poids.append(0.15)

    # Attention contextuelle (qualité moyenne des poids)
    attention = data.get("attention", {})
    if attention:
        # Plus les poids sont "concentrés", plus l'attention est nette
        max_poids = max(attention.values()) if attention else 0.33
        scores.append(_borne(max_poids / 0.6))
        poids.append(0.15)

    # Copula (corrélations apprises)
    copula_apprises = int(data.get("copula_correlations_apprises", 0))
    scores.append(_borne(copula_apprises / 3.0))
    poids.append(0.15)

    # Fiabilité moyenne des recommandations
    recos = data.get("recommandations", [])
    fiabilites = []
    for r in recos:
        try:
            fiabilites.append(float(r.get("fiabilite", 0)))
        except (ValueError, TypeError):
            pass
    if fiabilites:
        fiab_moy = sum(fiabilites) / len(fiabilites)
        scores.append(_borne(fiab_moy))
        poids.append(0.20)

    # Largeur des intervalles de confiance (plus étroit = meilleur)
    largeurs = []
    for r in recos:
        ic = r.get("intervalle_confiance")
        if ic:
            largeur = float(ic.get("haut", 0)) - float(ic.get("bas", 0))
            largeurs.append(largeur)
    if largeurs:
        largeur_moy = sum(largeurs) / len(largeurs)
        scores.append(_borne(1.0 - largeur_moy / 0.30))
        poids.append(0.15)

    if not scores:
        return 0.5

    total_poids = sum(poids)
    return sum(s * p for s, p in zip(scores, poids)) / total_poids


# ============================================================
# SIGNAL AMP — Amplification
# ============================================================
def _signal_amplification(data):
    """Agrège l'amplification (Couche A + ICP) en un score 0-1."""
    scores = []
    poids = []

    # ICP (Couche Σ)
    signature = data.get("signature", {})
    icp = float(signature.get("icp", 50))
    scores.append(_borne(icp / 100.0))
    poids.append(0.50)

    # Couche A — facteurs d'amplification
    recos = data.get("recommandations", [])
    facteurs_utilises = 0
    for r in recos:
        f = r.get("facteurs_amplification", {})
        if f:
            facteurs_utilises += 1
    if recos:
        scores.append(_borne(facteurs_utilises / len(recos)))
        poids.append(0.30)

    # Décision finale (bonus si ATTAQUE)
    decision = data.get("decision", "ÉVITER")
    if decision in ("ATTAQUE FORTE", "ATTAQUE"):
        scores.append(1.0)
    elif decision == "LEAN":
        scores.append(0.6)
    else:
        scores.append(0.2)
    poids.append(0.20)

    if not scores:
        return 0.5

    total_poids = sum(poids)
    return sum(s * p for s, p in zip(scores, poids)) / total_poids



# ============================================================
# DÉTECTION DES CONFLITS
# ============================================================
def _detecter_conflits(data, signaux):
    """
    Détecte les conflits entre couches.
    Retourne une liste d'alertes.
    """
    alertes = []

    decision = data.get("decision", "ÉVITER")
    validation = data.get("validation", {})
    val_niveau = validation.get("niveau", "OK")

    # Conflit 1 : décision ATTAQUE mais validation DANGER
    if decision in ("ATTAQUE FORTE", "ATTAQUE") and val_niveau == "DANGER":
        alertes.append("⚠️ Décision offensive mais validation des cotes en DANGER")

    # Conflit 2 : décision ÉVITER mais signal contextuel fort
    if decision == "ÉVITER" and signaux["A"] >= 0.75:
        alertes.append("⚠️ Décision ÉVITER alors que le contexte est très favorable")

    # Conflit 3 : forte amplification mais robustesse faible
    if signaux["AMP"] >= 0.70 and signaux["R"] <= 0.40:
        alertes.append("⚠️ Amplification forte mais robustesse du modèle faible")

    # Conflit 4 : qualité des données faible mais confiance élevée
    if signaux["U"] <= 0.35 and decision in ("ATTAQUE FORTE", "ATTAQUE"):
        alertes.append("⚠️ Données de faible qualité mais décision offensive")

    return alertes


# ============================================================
# CALCUL GLOBAL AURA
# ============================================================
def calculer_aura(data):
    """
    Calcule la Couche AURA complète :
    - 4 signaux composites (A, U, R, AMP)
    - AURA Score (0-100)
    - AURA Niveau (Faible / Modéré / Fort / Exceptionnel)
    - Attribution détaillée
    - Détection de conflits
    - Signature unique
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    # --- Calcul des 4 signaux ---
    signal_A = _signal_contextuel(data)
    signal_U = _signal_qualite(data)
    signal_R = _signal_robustesse(data)
    signal_AMP = _signal_amplification(data)

    signaux = {
        "A": round(signal_A, 4),
        "U": round(signal_U, 4),
        "R": round(signal_R, 4),
        "AMP": round(signal_AMP, 4),
    }

    # --- Poids par sport ---
    poids = POIDS_SPORT.get(sport, POIDS_SPORT["football"])

    # --- Score global ---
    aura_score = (
        poids["A"] * signal_A
        + poids["U"] * signal_U
        + poids["R"] * signal_R
        + poids["AMP"] * signal_AMP
    ) * 100
    aura_score = round(aura_score, 1)

    # --- Niveau ---
    if aura_score >= 85:
        niveau = "EXCEPTIONNEL"
        emoji = "💎"
        couleur = "#a78bfa"
    elif aura_score >= 70:
        niveau = "FORT"
        emoji = "🏆"
        couleur = "#facc15"
    elif aura_score >= 55:
        niveau = "MODÉRÉ"
        emoji = "🥈"
        couleur = "#60a5fa"
    elif aura_score >= 40:
        niveau = "FAIBLE"
        emoji = "🥉"
        couleur = "#9ca3af"
    else:
        niveau = "TRÈS FAIBLE"
        emoji = "⚪"
        couleur = "#6b7280"

    # --- Détection de conflits ---
    conflits = _detecter_conflits(data, signaux)

    # --- Attribution en pourcentage (contribution relative) ---
    contrib_A = round(poids["A"] * signal_A * 100, 1)
    contrib_U = round(poids["U"] * signal_U * 100, 1)
    contrib_R = round(poids["R"] * signal_R * 100, 1)
    contrib_AMP = round(poids["AMP"] * signal_AMP * 100, 1)

    # --- Signature unique ---
    timestamp = datetime.now().isoformat()
    cle_sig = "AURA-{}-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        sport,
        aura_score,
        niveau,
        timestamp,
    )
    empreinte = hashlib.sha256(cle_sig.encode("utf-8")).hexdigest()

    data["aura"] = {
        "score": aura_score,
        "niveau": niveau,
        "emoji": emoji,
        "couleur": couleur,
        "signaux": signaux,
        "poids_sport": poids,
        "sport": sport,
        "attribution": {
            "A": contrib_A,
            "U": contrib_U,
            "R": contrib_R,
            "AMP": contrib_AMP,
        },
        "conflits": conflits,
        "nb_conflits": len(conflits),
        "empreinte": empreinte,
        "empreinte_courte": empreinte[:12].upper(),
        "timestamp": timestamp,
        "sceau": "⚡ Couche AURA · QFTE V23.0",
    }
    return data
