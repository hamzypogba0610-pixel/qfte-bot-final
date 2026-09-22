"""
Couche Σ — Partenariat HAMZY × QFTE V23.0.

Indice de Confiance Partenariale (ICP) : un score algorithmique
sur 100 qui agrège 7 signaux pondérés pour valider la robustesse
globale d'une analyse.

Signature cryptographique double SHA-256 :
  • Empreinte du match (unique par analyse)
  • Empreinte du partenariat (constante du projet)

© HAMZY × QFTE V23.0 · Couche Σ · 2026
"""
import hashlib
from datetime import datetime


DATE_PARTENARIAT = "2026-09-21"
SEL_PARTENARIAT = "QFTE-V23-HAMZY-SIGMA-SIGNATURE-PARTENARIAT-2026"


CREDOS = {
    "DIAMANT": "L'analyse parfaite n'existe pas — mais celle-ci s'en approche.",
    "OR": "La rigueur d'aujourd'hui est la bankroll de demain.",
    "ARGENT": "Le doute est un signal, pas une faiblesse.",
    "BRONZE": "Mieux vaut manquer un pari que forcer une analyse.",
    "VERRE": "Le marché est un adversaire patient. Sois plus patient.",
}


def _empreinte_match(match, timestamp):
    cle = "{}-{}-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        match.get("competition", ""),
        match.get("cote_ferm_1", ""),
        match.get("cote_ferm_2", ""),
        match.get("volume", ""),
        timestamp,
    )
    return hashlib.sha256((cle + SEL_PARTENARIAT).encode("utf-8")).hexdigest()


def _empreinte_partenariat():
    """Empreinte immuable du partenariat HAMZY × QFTE."""
    cle = "HAMZY-QFTE-V23-OMEGA-SIGMA-{}".format(DATE_PARTENARIAT)
    return hashlib.sha256((cle + SEL_PARTENARIAT).encode("utf-8")).hexdigest()


def _calculer_icp(data):
    """
    Indice de Confiance Partenariale — 7 signaux pondérés.
    Chaque signal retourne une note entre 0 et 1.
    """
    signaux = {}

    # --- Signal 1 : fiabilité moyenne des recommandations (poids 20%) ---
    recos = data.get("recommandations", [])
    fiabilites = []
    for r in recos:
        try:
            fiabilites.append(float(r.get("fiabilite", 0)))
        except (ValueError, TypeError):
            pass
    sig1 = sum(fiabilites) / len(fiabilites) if fiabilites else 0.5

    # --- Signal 2 : score de validation (poids 15%) ---
    validation = data.get("validation", {})
    sig2 = float(validation.get("score", 70)) / 100.0

    # --- Signal 3 : cohérence contextuelle (poids 15%) ---
    contexte = data.get("contexte", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})
    cotes_ctx = contexte.get("cotes", {})

    sig3_components = []
    # Forme cohérente entre les 2 équipes
    f_dom = abs(float(forme.get("dom_finale", 0)))
    f_ext = abs(float(forme.get("ext_finale", 0)))
    sig3_components.append(1.0 - (f_dom + f_ext) / 4.0)
    # H2H non-ambigu
    if h2h.get("n", 0) >= 3:
        if h2h.get("domine") in ("dom", "ext"):
            sig3_components.append(0.9)
        else:
            sig3_components.append(0.6)
    # Marge bookmaker raisonnable
    marge = cotes_ctx.get("marge_book", 5.0)
    sig3_components.append(max(0.0, 1.0 - marge / 15.0))
    sig3 = sum(sig3_components) / len(sig3_components) if sig3_components else 0.5

    # --- Signal 4 : qualité de calibration (poids 15%) ---
    largeurs_ic = []
    for r in recos:
        ic = r.get("intervalle_confiance")
        if ic:
            largeur = ic.get("haut", 0) - ic.get("bas", 0)
            largeurs_ic.append(largeur)
    if largeurs_ic:
        largeur_moy = sum(largeurs_ic) / len(largeurs_ic)
        # Largeur idéale : 0.10-0.15. Trop large = mauvais.
        sig4 = max(0.0, 1.0 - largeur_moy / 0.30)
    else:
        sig4 = 0.5

    # --- Signal 5 : liquidité (poids 10%) ---
    volume = float(data.get("volume", 0))
    sig5 = min(1.0, volume / 200000)

    # --- Signal 6 : consensus des sources (poids 15%) ---
    # Si marché, poisson et sharp sont proches → bonne convergence
    sig6_components = []
    for r in recos:
        pm = r.get("proba_marche")
        pp = r.get("proba_poisson")
        ps = r.get("proba_sharp")
        if pm is not None and pp is not None and ps is not None:
            ecart_max = max(abs(pm - pp), abs(pp - ps), abs(pm - ps))
            sig6_components.append(max(0.0, 1.0 - ecart_max * 3))
    sig6 = sum(sig6_components) / len(sig6_components) if sig6_components else 0.5

    # --- Signal 7 : robustesse des λ (poids 10%) ---
    lambda_h = float(data.get("lambda_home", 0) or 0)
    lambda_a = float(data.get("lambda_away", 0) or 0)
    if lambda_h > 0 and lambda_a > 0:
        ecart_lambda = abs(lambda_h - lambda_a)
        sig7 = max(0.0, 1.0 - ecart_lambda / 4.0)
    else:
        sig7 = 0.5

    signaux = {
        "fiabilite": round(sig1, 3),
        "validation": round(sig2, 3),
        "contexte": round(sig3, 3),
        "calibration": round(sig4, 3),
        "liquidite": round(sig5, 3),
        "consensus": round(sig6, 3),
        "robustesse": round(sig7, 3),
    }

    icp = (
        sig1 * 0.20
        + sig2 * 0.15
        + sig3 * 0.15
        + sig4 * 0.15
        + sig5 * 0.10
        + sig6 * 0.15
        + sig7 * 0.10
    ) * 100

    return round(icp, 1), signaux


def _niveau_partenariat(icp):
    if icp >= 90: return "DIAMANT", "💎"
    if icp >= 75: return "OR", "🏆"
    if icp >= 60: return "ARGENT", "🥈"
    if icp >= 40: return "BRONZE", "🥉"
    return "VERRE", "⚪"


def apposer_signature(data):
    """Couche Σ — applique l'ICP + la signature partenariale."""
    match = data.get("match", {})
    timestamp = datetime.now().isoformat()

    # --- Calcul ICP ---
    icp, signaux = _calculer_icp(data)
    niveau, emoji = _niveau_partenariat(icp)
    credo = CREDOS[niveau]

    # --- Empreintes ---
    empreinte_match = _empreinte_match(match, timestamp)
    empreinte_partenariat = _empreinte_partenariat()

    # --- Impact sur la décision : si ICP < 50, forcer ÉVITER ---
    if icp < 50:
        data["decision"] = "ÉVITER"
        data["message_discipline"] = (
            "Analyse rejetée par la Couche Σ (ICP < 50). Fiabilité globale insuffisante."
        )

    data["signature"] = {
        "icp": icp,
        "niveau": niveau,
        "emoji": emoji,
        "credo": credo,
        "signaux": signaux,
        "empreinte_match": empreinte_match,
        "empreinte_match_courte": empreinte_match[:12].upper(),
        "empreinte_partenariat": empreinte_partenariat,
        "empreinte_partenariat_courte": empreinte_partenariat[:12].upper(),
        "auteur": "HAMZY",
        "coequipier": "QFTE V23.0",
        "partenariat_depuis": DATE_PARTENARIAT,
        "timestamp": timestamp,
        "sceau": "🦁 HAMZY × QFTE V23.0 · Couche Σ",
    }
    return data
