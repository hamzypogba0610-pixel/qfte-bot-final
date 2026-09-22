"""
Module Copula Calibration — QFTE V23.0.

Modélise les dépendances entre marchés (football et basket) via une
copule gaussienne. Apprend les corrélations depuis l'historique et
ajuste les probabilités marginales en conséquence.

Pur Python — aucune dépendance externe.
"""
import math


# ============================================================
# FONCTIONS NORMALES (CDF + approximation inverse)
# ============================================================
def norm_cdf(x):
    """CDF de la loi normale standard."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """
    Approximation de l'inverse de la CDF normale (Acklam).
    Précision ~1e-9. Suffisant pour la copule.
    """
    if p <= 0: return -8.0
    if p >= 1: return 8.0
    if p == 0.5: return 0.0

    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]

    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


# ============================================================
# COPULE GAUSSIENNE BIVARIÉE
# ============================================================
def copule_gaussienne_bivariee(p1, p2, rho):
    """
    Retourne P(Y1=1, Y2=1) pour deux variables binaires de marges p1, p2
    et de corrélation ρ via la copule gaussienne.
    """
    if p1 <= 0 or p1 >= 1 or p2 <= 0 or p2 >= 1:
        return p1 * p2
    rho = max(-0.95, min(0.95, rho))
    z1 = norm_ppf(p1)
    z2 = norm_ppf(p2)

    phi_a = math.exp(-z1**2/2) / math.sqrt(2*math.pi)
    phi_b = math.exp(-z2**2/2) / math.sqrt(2*math.pi)

    joint = norm_cdf(z1) * norm_cdf(z2) + rho * phi_a * phi_b * (1 + rho * rho / 6)
    return max(0.0, min(1.0, joint))


def ajuster_marginale(p_cible, p_partenaire, rho, force=0.30):
    """Ajuste p_cible en fonction de p_partenaire et de leur corrélation."""
    if rho == 0 or p_cible <= 0 or p_cible >= 1:
        return p_cible

    ecart_signe = (p_cible - 0.5) * (p_partenaire - 0.5)
    if ecart_signe >= 0:
        facteur = force * 0.15
    else:
        facteur = force * 0.50

    delta = rho * facteur * (p_partenaire - 0.5) * 2
    p_new = p_cible + delta
    return max(0.02, min(0.98, p_new))


# ============================================================
# APPRENTISSAGE DES CORRÉLATIONS
# ============================================================
def _correlation_empirique(xs, ys):
    n = len(xs)
    if n < 5:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom <= 0:
        return 0.0
    return max(-0.95, min(0.95, cov / denom))


def apprendre_correlations():
    """Apprend les corrélations empiriques depuis l'historique."""
    from qfte_engine.historique import charger_historique, _pari_gagne

    historique = charger_historique()
    par_date = {}

    for h in historique:
        res = h.get("resultat")
        if not res:
            continue
        score_h = res.get("score_home", 0)
        score_a = res.get("score_away", 0)
        date = h.get("date", "")
        par_date[date] = {}

        for reco in h.get("recommandations", []):
            marche = reco.get("marche", "")
            sel = reco.get("selection", "")
            outcome = 1 if _pari_gagne(marche, sel, score_h, score_a) else 0
            par_date[date][marche] = outcome

    paires = {}
    for date, marches in par_date.items():
        noms = list(marches.keys())
        for i in range(len(noms)):
            for j in range(i + 1, len(noms)):
                m1, m2 = noms[i], noms[j]
                cle = tuple(sorted([m1, m2]))
                if cle not in paires:
                    paires[cle] = ([], [])
                paires[cle][0].append(marches[m1])
                paires[cle][1].append(marches[m2])

    correlations = {}
    for cle, (xs, ys) in paires.items():
        if len(xs) >= 10:
            rho = _correlation_empirique(xs, ys)
            correlations[cle] = round(rho, 4)

    return correlations


# ============================================================
# CORRÉLATIONS PAR DÉFAUT
# ============================================================
# --- Football ---
CORRELATIONS_FOOT = {
    tuple(sorted(["Handicap Asiatique -0.5", "Over/Under 2.5"])): 0.25,
    tuple(sorted(["Handicap Asiatique -0.5", "BTTS"])): 0.10,
    tuple(sorted(["Over/Under 2.5", "BTTS"])): 0.55,
}

# --- Basket ---
CORRELATIONS_BASKET = {
    # Money Line et Spread sont très corrélés (même direction)
    tuple(sorted(["Money Line", "Spread -4.5"])): 0.70,
    # Money Line et Total Points : faiblement corrélés
    tuple(sorted(["Money Line", "Total Points"])): 0.05,
    # Spread et Total Points : faiblement corrélés aussi
    tuple(sorted(["Spread -4.5", "Total Points"])): 0.15,
}

# Ancien nom conservé pour compatibilité
CORRELATIONS_DEFAUT = {**CORRELATIONS_FOOT, **CORRELATIONS_BASKET}


def _trouver_correlation(marche_a, marche_b, correlations):
    cle = tuple(sorted([marche_a, marche_b]))
    if cle in correlations:
        return correlations[cle]
    if cle in CORRELATIONS_DEFAUT:
        return CORRELATIONS_DEFAUT[cle]
    return 0.0


# ============================================================
# APPLICATION
# ============================================================
def appliquer_copule(data):
    """
    Applique la copule gaussienne sur les probabilités calibrées
    pour assurer la cohérence inter-marchés (football ET basket).
    """
    marches = data.get("marches", [])
    if len(marches) < 2:
        return data

    # Apprentissage des corrélations
    correlations = apprendre_correlations()
    data["copula_correlations_apprises"] = len(correlations)
    data["copula_correlations"] = {
        f"{k[0]} × {k[1]}": v for k, v in list(correlations.items())[:5]
    }

    # Extraction des probas actuelles
    probas = {}
    for m in marches:
        nom = m.get("nom", "")
        probas[nom] = float(m.get("proba_calibree", 0.5))

    # Application de l'ajustement croisé
    for m in marches:
        nom = m.get("nom", "")
        p_orig = probas.get(nom, 0.5)
        p_ajustee = p_orig
        poids_total = 0.0

        for autre_nom, p_autre in probas.items():
            if autre_nom == nom:
                continue
            rho = _trouver_correlation(nom, autre_nom, correlations)
            if rho == 0:
                continue

            p_temp = ajuster_marginale(p_ajustee, p_autre, rho, force=0.30)
            poids = abs(rho)
            p_ajustee = p_ajustee * (1 - poids) + p_temp * poids
            poids_total += poids

        if poids_total == 0:
            p_ajustee = p_orig

        p_ajustee = max(0.02, min(0.98, p_ajustee))

        m["proba_avant_copule"] = round(p_orig, 4)
        m["proba_calibree"] = round(p_ajustee, 4)

    data["marches"] = marches
    return data
