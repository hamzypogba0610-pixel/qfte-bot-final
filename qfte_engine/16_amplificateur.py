"""
Couche A — Amplification Agressive QFTE V23.0.

Transforme des signaux faibles en recommandations tranchées
grâce à 5 formules algorithmiques imbriquées.

⚠️ Garde-fous intégrés : jamais d'EV > ±15%, jamais de stake > 2%.
"""
import math


# ============================================================
# 1. CONVERGENCE SIGNAL AMPLIFICATION (CSA)
# ============================================================
def csa(p_marche, p_poisson, p_sharp):
    """
    Détecte la convergence des 3 sources principales.
    Plus elles convergent, plus on amplifie la confiance.
    Retourne un facteur entre 0.5 et 1.5.
    """
    ecart_max = max(
        abs(p_marche - p_poisson),
        abs(p_poisson - p_sharp),
        abs(p_marche - p_sharp),
    )
    # ecart_max = 0 → convergence parfaite → facteur 1.5
    # ecart_max = 0.15 → divergence forte → facteur 0.5
    if ecart_max <= 0.02:
        return 1.50
    elif ecart_max <= 0.05:
        return 1.30
    elif ecart_max <= 0.10:
        return 1.10
    elif ecart_max <= 0.15:
        return 0.85
    return 0.50


# ============================================================
# 2. CONFIDENCE BOOST EXPONENTIEL (CBE)
# ============================================================
def cbe(fiabilite):
    """
    Boost exponentiel quand la fiabilité dépasse 0.85.
    Au-delà, chaque point de fiabilité compte double.
    """
    if fiabilite < 0.75:
        return 1.0
    # Mapping : 0.75 → 1.0 ; 0.85 → 1.25 ; 0.95 → 1.60
    x = (fiabilite - 0.75) / 0.20  # 0 à 1
    return 1.0 + 0.6 * (x ** 1.5)


# ============================================================
# 3. VALUE STACKING (VS)
# ============================================================
def value_stacking(ev_brut, mouvement, liquidite_ok, icp_preview=None):
    """
    Empile plusieurs signaux de value.
    Chaque signal convergent ajoute un bonus multiplicatif.
    """
    multiplicateur = 1.0
    signaux = 0

    # Signal 1 : mouvement de cote fort vers l'équipe (indique info sharp)
    if mouvement < -0.05:
        multiplicateur += 0.25
        signaux += 1

    # Signal 2 : liquidité élevée
    if liquidite_ok:
        multiplicateur += 0.15
        signaux += 1

    # Signal 3 : ICP preview élevé (si dispo)
    if icp_preview is not None and icp_preview >= 75:
        multiplicateur += 0.20
        signaux += 1

    # Signal 4 : EV brut déjà positif
    if ev_brut > 0.03:
        multiplicateur += 0.10
        signaux += 1

    # Bonus "full house" : tous les signaux alignés
    if signaux >= 4:
        multiplicateur += 0.20

    return min(1.80, multiplicateur)


# ============================================================
# 4. SEUILS ADAPTATIFS (SAT)
# ============================================================
def seuils_adaptatifs(icp, liquidite_ok, fiabilite_max):
    """
    Les seuils V23.0 deviennent adaptatifs :
    - Contexte très favorable → seuils abaissés
    - Contexte défavorable → seuils relevés
    Retourne (seuil_ev, seuil_fiabilite).
    """
    seuil_ev = 0.04
    seuil_fiabilite = 0.75

    # Si contexte très favorable, on descend les seuils
    if icp >= 80 and liquidite_ok and fiabilite_max >= 0.85:
        seuil_ev = 0.025
        seuil_fiabilite = 0.70

    # Si contexte correct
    elif icp >= 65 and liquidite_ok:
        seuil_ev = 0.035
        seuil_fiabilite = 0.73

    # Si contexte défavorable, on monte les seuils
    elif icp < 50 or not liquidite_ok:
        seuil_ev = 0.055
        seuil_fiabilite = 0.78

    return seuil_ev, seuil_fiabilite


# ============================================================
# 5. SHARP DIVERGENCE DETECTOR (SDD)
# ============================================================
def sharp_divergence(p_poisson, cote, proba_implicite):
    """
    Détecte quand notre modèle Poisson s'écarte du marché
    avec un signal fort : c'est là qu'il y a la vraie value.

    Retourne un facteur d'amplification entre 0.5 et 1.5.
    """
    ecart = abs(p_poisson - proba_implicite)

    # Si Poisson dit que le marché se trompe fortement
    if ecart >= 0.15:
        return 1.50  # Divergence forte = signal
    elif ecart >= 0.10:
        return 1.30
    elif ecart >= 0.05:
        return 1.10
    elif ecart >= 0.02:
        return 0.95
    return 0.75


# ============================================================
# APPLICATION GLOBALE
# ============================================================
def amplifier(data):
    """
    Amplifie la force de frappe du bot :
    - Fiabilité boostée par CBE
    - EV amplifié par VS + SDD
    - Seuils adaptatifs SAT
    - Convergence CSA
    """
    recos = data.get("recommandations", [])
    icp_preview = float(data.get("signature", {}).get("icp", 60))
    liquidite_ok = bool(data.get("liquidite_ok", True))

    fiabilite_max = max(
        (float(r.get("fiabilite", 0)) for r in recos), default=0.5
    )
    seuil_ev, seuil_fiab = seuils_adaptatifs(icp_preview, liquidite_ok, fiabilite_max)
    data["seuils_amplifies"] = {"seuil_ev": seuil_ev, "seuil_fiabilite": seuil_fiab}

    nouvelles = []
    for r in recos:
        # --- Récupération des valeurs ---
        try:
            fiab = float(r.get("fiabilite", 0))
        except (ValueError, TypeError):
            fiab = 0.5

        ev_str = str(r.get("ev", "0%")).replace("%", "").strip()
        try:
            ev_brut = float(ev_str) / 100
        except ValueError:
            ev_brut = 0.0

        p_marche = float(r.get("proba_marche", 0.5) or 0.5)
        p_poisson = float(r.get("proba_poisson", 0.5) or 0.5)
        p_sharp = float(r.get("proba_sharp", 0.5) or 0.5)

        cote = float(r.get("cote", 2.0) or 2.0)
        proba_implicite = 1 / cote if cote > 0 else 0.5

        # --- Application des 5 formules ---
        f_csa = csa(p_marche, p_poisson, p_sharp)
        f_cbe = cbe(fiab)
        f_sdd = sharp_divergence(p_poisson, cote, proba_implicite)

        mouvement = 0.0  # récupéré du contexte
        ctx = data.get("contexte", {})
        cotes_ctx = ctx.get("cotes", {})
        if cotes_ctx:
            mouvement = float(cotes_ctx.get("mouvement_1", 0) or 0)

        f_vs = value_stacking(ev_brut, mouvement, liquidite_ok, icp_preview)

        # --- Amplification EV ---
        ev_amplifie = ev_brut * f_vs * f_sdd
        ev_amplifie = max(-0.15, min(0.15, ev_amplifie))  # Garde-fou

        # --- Amplification Fiabilité ---
        fiab_amplifiee = fiab * f_cbe
        # Blend CSA : si les sources convergent, la fiabilité augmente
        fiab_amplifiee = fiab_amplifiee * (1 + (f_csa - 1) * 0.3)
        fiab_amplifiee = max(0.50, min(0.99, fiab_amplifiee))

        # --- Recalcul du niveau selon seuils adaptatifs ---
        if ev_amplifie >= seuil_ev + 0.03 and fiab_amplifiee >= seuil_fiab + 0.05:
            niveau = "ELITE"
            stake = 2.0
        elif ev_amplifie >= seuil_ev + 0.015 and fiab_amplifiee >= seuil_fiab + 0.02:
            niveau = "PREMIUM"
            stake = 1.5
        elif ev_amplifie >= seuil_ev and fiab_amplifiee >= seuil_fiab:
            niveau = "GOOD"
            stake = 1.0
        elif ev_amplifie >= 0.01:
            niveau = "SURVEILLANCE"
            stake = 0.4
        else:
            niveau = "AVOID"
            stake = 0.0

        # --- Plafond de stake absolu ---
        stake = min(2.0, stake)

        r["ev_brut_avant_amplification"] = r.get("ev")
        r["ev"] = "{:.2f}%".format(ev_amplifie * 100)
        r["fiabilite_avant_amplification"] = r.get("fiabilite")
        r["fiabilite"] = str(round(fiab_amplifiee, 4))
        r["niveau"] = niveau
        r["stake"] = "{}%".format(stake)
        r["facteurs_amplification"] = {
            "csa": round(f_csa, 3),
            "cbe": round(f_cbe, 3),
            "vs": round(f_vs, 3),
            "sdd": round(f_sdd, 3),
        }
        nouvelles.append(r)

    data["recommandations"] = nouvelles

    # --- Recalcul de la décision globale ---
    ordre = {"ELITE": 5, "PREMIUM": 4, "GOOD": 3, "SURVEILLANCE": 2, "AVOID": 1}
    meilleure = max(nouvelles, key=lambda x: ordre.get(x["niveau"], 0)) if nouvelles else None
    if meilleure:
        niveau_top = meilleure["niveau"]
        if niveau_top in ("ELITE", "PREMIUM"):
            data["decision"] = "ATTAQUE FORTE"
            data["message_discipline"] = "Couche A activée — signaux convergents, opportunité amplifiée."
        elif niveau_top == "GOOD":
            data["decision"] = "ATTAQUE"
            data["message_discipline"] = "Couche A activée — opportunité détectée."
        elif niveau_top == "SURVEILLANCE":
            data["decision"] = "LEAN"
            data["message_discipline"] = "Signal faible mais non négligeable."
        else:
            data["decision"] = "ÉVITER"
            data["message_discipline"] = "Aucun signal exploitable."

    return data
