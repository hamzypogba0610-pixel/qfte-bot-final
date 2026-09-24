"""
Couche ORACLE — Simulateur Monte Carlo multi-scénarios QFTE V23.0.

Simule 10 000 versions futures du match en croisant TOUTES les couches :
- λ (buts attendus) pour le football
- Elo + p_set pour le tennis
- Écart moyen + total pour le basket
- Bruit contextuel (calendrier, fatigue, momentum)

Produit une distribution complète :
- Probabilité simulée
- Intervalle de confiance 95%
- VaR / CVaR
- Indice de stabilité
- Scénarios extrêmes

Pur Python — aucune dépendance externe.
© HAMZY × QFTE V23.0 · Couche ORACLE
"""
import math
import random
import hashlib
from datetime import datetime


N_SIMULATIONS = 10000


# ============================================================
# GÉNÉRATEURS ALÉATOIRES (sans numpy)
# ============================================================
def _random_normal(mu=0.0, sigma=1.0):
    """Box-Muller pour loi Normale."""
    if sigma <= 0:
        return mu
    u1 = random.random()
    u2 = random.random()
    if u1 <= 1e-12:
        u1 = 1e-12
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return mu + sigma * z


def _random_poisson(lam):
    """Knuth's algorithm pour Poisson (valide pour lam < 30)."""
    if lam <= 0:
        return 0
    if lam > 30:
        # Approximation Normale pour grands λ
        return max(0, int(round(_random_normal(lam, math.sqrt(lam)))))
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1


# ============================================================
# SIMULATEUR FOOTBALL (Dixon-Coles + bruit contextuel)
# ============================================================
def _simuler_football(data):
    """
    Simule un match de football.
    Retourne 1 si l'équipe 1 gagne, 0 sinon (nul = 0.5 pondéré).
    """
    lambda_home = float(data.get("lambda_home", 1.4) or 1.4)
    lambda_away = float(data.get("lambda_away", 1.3) or 1.3)

    # Bruit contextuel basé sur le calendrier
    calendrier = data.get("calendrier", {})
    if calendrier:
        impact_dom = float(calendrier.get("dom", {}).get("impact_lambda", 0) or 0)
        impact_ext = float(calendrier.get("ext", {}).get("impact_lambda", 0) or 0)
        lambda_home += _random_normal(impact_dom, 0.10)
        lambda_away += _random_normal(impact_ext, 0.10)

    # Ajout d'un bruit stochastique général (incertitude du modèle)
    lambda_home = max(0.10, lambda_home + _random_normal(0, 0.15))
    lambda_away = max(0.10, lambda_away + _random_normal(0, 0.15))

    # Simulation Poisson
    buts_dom = _random_poisson(lambda_home)
    buts_ext = _random_poisson(lambda_away)

    # Victoire / Nul / Défaite
    if buts_dom > buts_ext:
        return 1
    elif buts_dom == buts_ext:
        return 0.5  # Nul = "demi-victoire" pour l'EV
    return 0



# ============================================================
# SIMULATEUR BASKET (Normale + bruit)
# ============================================================
def _simuler_basket(data):
    """
    Simule un match de basket.
    Retourne 1 si l'équipe 1 gagne, 0 sinon.
    """
    ecart_moyen = float(data.get("lambda_home", 0) or 0)

    # Récupération du σ depuis la config basket
    basket_config = data.get("basket_config", {})
    sigma_ecart = float(basket_config.get("sigma_ecart", 12.0) or 12.0)

    # Bruit contextuel basé sur le calendrier basket
    calendrier_b = data.get("calendrier_basket", {})
    if calendrier_b:
        impact_dom = float(calendrier_b.get("dom", {}).get("score_points", 0) or 0)
        impact_ext = float(calendrier_b.get("ext", {}).get("score_points", 0) or 0)
        ecart_moyen += _random_normal(impact_dom - impact_ext, 1.5)

    # Bruit général
    ecart_moyen = ecart_moyen + _random_normal(0, 2.0)

    # Simulation de l'écart final
    ecart_simule = _random_normal(ecart_moyen, sigma_ecart)

    return 1 if ecart_simule > 0 else 0


# ============================================================
# SIMULATEUR TENNIS (Binomial séquentiel avec momentum)
# ============================================================
def _simuler_tennis(data):
    """
    Simule un match de tennis, set par set.
    Retourne 1 si le joueur 1 gagne, 0 sinon.
    """
    p_set = float(data.get("lambda_home", 0.5) or 0.5)

    tennis_config = data.get("tennis_config", {})
    best_of = int(tennis_config.get("best_of", 3) or 3)
    sets_pour_gagner = 2 if best_of == 3 else 3

    # Momentum impact (déjà dans p_set, mais on ajoute du bruit dynamique)
    momentum = data.get("momentum_info", {})
    momentum_impact = 0.0
    if momentum:
        momentum_impact = float(momentum.get("impact_proba", 0) or 0)

    # Fatigue impact
    fatigue = data.get("fatigue_info", {})
    fatigue_impact = 0.0
    if fatigue:
        fatigue_impact = float(fatigue.get("impact_proba", 0) or 0)

    # Simulation séquentielle
    sets_j1 = 0
    sets_j2 = 0

    while sets_j1 < sets_pour_gagner and sets_j2 < sets_pour_gagner:
        # p_set évolue légèrement set après set (momentum dynamique)
        p_set_dynamique = p_set + momentum_impact * 0.5 + fatigue_impact * 0.3
        p_set_dynamique += _random_normal(0, 0.05)
        p_set_dynamique = max(0.10, min(0.90, p_set_dynamique))

        if random.random() < p_set_dynamique:
            sets_j1 += 1
        else:
            sets_j2 += 1

    return 1 if sets_j1 > sets_j2 else 0



# ============================================================
# CALCUL DES MÉTRIQUES
# ============================================================
def _calculer_metriques(simulations):
    """
    Calcule toutes les métriques à partir de la liste de simulations.
    Chaque valeur : 1 (victoire J1), 0.5 (nul foot), 0 (défaite J1).
    """
    n = len(simulations)
    if n == 0:
        return {}

    # Probabilité simulée
    p_victoire = sum(simulations) / n

    # Écart-type
    variance = sum((x - p_victoire) ** 2 for x in simulations) / n
    ecart_type = variance ** 0.5

    # Intervalle de confiance 95% (approximation normale)
    erreur_std = ecart_type / (n ** 0.5)
    ic_bas = max(0.0, p_victoire - 1.96 * erreur_std)
    ic_haut = min(1.0, p_victoire + 1.96 * erreur_std)

    # Distribution triée pour percentiles
    triees = sorted(simulations)
    idx_5 = int(n * 0.05)
    idx_95 = int(n * 0.95)

    var_5 = triees[idx_5] if idx_5 < n else 0
    meilleur = triees[-1] if n > 0 else 1

    # CVaR 5% : moyenne des 5% pires scénarios
    pires = triees[:max(1, idx_5)]
    cvar_5 = sum(pires) / len(pires) if pires else 0

    # Indice de stabilité : basé sur l'écart-type (faible = stable)
    stabilite = max(0.0, min(100.0, (1.0 - ecart_type * 2) * 100))

    # Fréquence des "victoires nettes" (>= 0.9) et "défaites nettes" (<= 0.1)
    victoires_nettes = sum(1 for x in simulations if x >= 0.9) / n
    defaites_nettes = sum(1 for x in simulations if x <= 0.1) / n
    nuls_simules = sum(1 for x in simulations if 0.4 < x < 0.6) / n

    return {
        "proba_simulee": round(p_victoire, 4),
        "ecart_type": round(ecart_type, 4),
        "ic_bas": round(ic_bas, 4),
        "ic_haut": round(ic_haut, 4),
        "var_5": round(var_5, 4),
        "cvar_5": round(cvar_5, 4),
        "meilleur": round(meilleur, 4),
        "stabilite": round(stabilite, 1),
        "victoires_nettes": round(victoires_nettes, 4),
        "defaites_nettes": round(defaites_nettes, 4),
        "nuls_simules": round(nuls_simules, 4),
        "n_simulations": n,
    }


def _histogramme(simulations, buckets=10):
    """Génère un histogramme simplifié (10 buckets entre 0 et 1)."""
    n = len(simulations)
    if n == 0:
        return []

    histo = [0] * buckets
    for x in simulations:
        idx = min(buckets - 1, int(x * buckets))
        histo[idx] += 1

    # Normalisation en pourcentage
    return [round(h * 100 / n, 2) for h in histo]


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
def calculer_oracle(data):
    """
    Calcule la Couche ORACLE complète :
    - 10 000 simulations Monte Carlo
    - Métriques de distribution
    - Histogramme
    - Signature unique
    """
    match = data.get("match", {})
    sport = match.get("sport", "football")

    # --- Choix du simulateur ---
    if sport == "basket":
        simulateur = _simuler_basket
    elif sport == "tennis":
        simulateur = _simuler_tennis
    else:
        simulateur = _simuler_football

    # --- Lancement des simulations ---
    simulations = []
    for _ in range(N_SIMULATIONS):
        simulations.append(simulateur(data))

    # --- Calcul des métriques ---
    metriques = _calculer_metriques(simulations)

    # --- Histogramme ---
    histogramme = _histogramme(simulations, buckets=10)

    # --- Comparaison avec la proba calibrée ---
    recos = data.get("recommandations", [])
    proba_modele = 0.5
    if recos:
        try:
            p_str = str(recos[0].get("proba", "50%")).replace("%", "").strip()
            proba_modele = float(p_str) / 100
        except (ValueError, TypeError):
            proba_modele = 0.5

    ecart_modele_oracle = metriques.get("proba_simulee", 0.5) - proba_modele

    # Interprétation
    if abs(ecart_modele_oracle) < 0.03:
        interpretation = "✅ Modèle et Oracle alignés"
    elif abs(ecart_modele_oracle) < 0.08:
        interpretation = "🟡 Léger écart modèle/Oracle"
    else:
        interpretation = "⚠️ Écart significatif — prudence"

    if metriques.get("stabilite", 0) >= 80:
        stabilite_txt = "💎 Très stable"
    elif metriques.get("stabilite", 0) >= 60:
        stabilite_txt = "🏆 Stable"
    elif metriques.get("stabilite", 0) >= 40:
        stabilite_txt = "🥈 Modérément stable"
    else:
        stabilite_txt = "⚠️ Volatile"

    # --- Signature ---
    timestamp = datetime.now().isoformat()
    cle = "ORACLE-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        sport,
        metriques.get("proba_simulee", 0),
        timestamp,
    )
    empreinte = hashlib.sha256(cle.encode("utf-8")).hexdigest()

    data["oracle"] = {
        "sport": sport,
        "n_simulations": N_SIMULATIONS,
        "metriques": metriques,
        "histogramme": histogramme,
        "proba_modele": round(proba_modele, 4),
        "ecart_modele_oracle": round(ecart_modele_oracle, 4),
        "interpretation": interpretation,
        "stabilite_texte": stabilite_txt,
        "empreinte": empreinte,
        "empreinte_courte": empreinte[:12].upper(),
        "timestamp": timestamp,
        "sceau": "🔮 Couche ORACLE · 10 000 simulations Monte Carlo",
    }
    return data
