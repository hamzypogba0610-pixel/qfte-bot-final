"""
Module de calibration avancée QFTE V23.0.
Implémente 3 calibrateurs indépendants + ensemble pondéré.

Toutes les fonctions sont en pur Python (pas de numpy/scipy)
pour rester léger sur Render Free.
"""
import math


# ============================================================
# UTILITAIRES
# ============================================================

def sigmoid(z):
    if z > 500:
        return 1.0
    if z < -500:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def log_loss(ys, ps):
    """Log-loss (entropie croisée) moyenne. Plus bas = mieux."""
    eps = 1e-9
    n = len(ys)
    if n == 0:
        return 1.0
    s = 0.0
    for y, p in zip(ys, ps):
        p = max(eps, min(1 - eps, p))
        s -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return s / n


def brier_score(ys, ps):
    """Brier score : erreur quadratique moyenne."""
    n = len(ys)
    if n == 0:
        return 1.0
    return sum((p - y) ** 2 for y, p in zip(ys, ps)) / n


# ============================================================
# 1. PLATT SCALING
# ============================================================
# Modèle : p = sigmoid(A * x + B)
# Fit par descente de gradient sur la log-loss.

def platt_fit(xs, ys, lr=0.05, epochs=800):
    A, B = -1.0, 0.0
    n = len(xs)
    if n < 5:
        return A, B
    for _ in range(epochs):
        grad_A, grad_B = 0.0, 0.0
        for x, y in zip(xs, ys):
            p = sigmoid(A * x + B)
            err = p - y
            grad_A += err * x
            grad_B += err
        A -= lr * grad_A / n
        B -= lr * grad_B / n
    return A, B


def platt_predict(x, A, B):
    return sigmoid(A * x + B)


# ============================================================
# 2. BETA CALIBRATION
# ============================================================
# Modèle : p = sigmoid(a * log(x) + b * log(1-x) + c)
# Plus flexible que Platt, capture mieux les non-linéarités.

def beta_fit(xs, ys, lr=0.03, epochs=800):
    a, b, c = 1.0, 1.0, 0.0
    n = len(xs)
    if n < 5:
        return a, b, c
    eps = 1e-9
    for _ in range(epochs):
        ga, gb, gc = 0.0, 0.0, 0.0
        for x, y in zip(xs, ys):
            x = max(eps, min(1 - eps, x))
            lx = math.log(x)
            l1x = math.log(1 - x)
            z = a * lx + b * l1x + c
            p = sigmoid(z)
            err = p - y
            ga += err * lx
            gb += err * l1x
            gc += err
        a -= lr * ga / n
        b -= lr * gb / n
        c -= lr * gc / n
    return a, b, c


def beta_predict(x, a, b, c):
    eps = 1e-9
    x = max(eps, min(1 - eps, x))
    return sigmoid(a * math.log(x) + b * math.log(1 - x) + c)


# ============================================================
# 3. ISOTONIC REGRESSION (algorithme PAV)
# ============================================================
# Apprend une fonction monotone croissante sans paramètre.
# Référence en ML pour la calibration.

def isotonic_fit(xs, ys):
    if len(xs) < 5:
        return [(0.0, 0.0), (1.0, 1.0)]
    pairs = sorted(zip(xs, ys))
    blocks = []  # [sum_x, sum_y, count]
    for x, y in pairs:
        blocks.append([x, y, 1])
        while len(blocks) >= 2:
            b1, b2 = blocks[-2], blocks[-1]
            m1 = b1[1] / b1[2]
            m2 = b2[1] / b2[2]
            if m1 > m2:
                merged = [b1[0] + b2[0], b1[1] + b2[1], b1[2] + b2[2]]
                blocks.pop()
                blocks.pop()
                blocks.append(merged)
            else:
                break
    result = []
    for b in blocks:
        x_mid = b[0] / b[2]
        y_val = b[1] / b[2]
        result.append((x_mid, y_val))
    if not result:
        return [(0.0, 0.0), (1.0, 1.0)]
    if result[0][0] > 0.0:
        result.insert(0, (0.0, result[0][1]))
    if result[-1][0] < 1.0:
        result.append((1.0, result[-1][1]))
    return result


def isotonic_predict(x, breaks):
    if not breaks:
        return x
    for i in range(len(breaks) - 1):
        x1, y1 = breaks[i]
        x2, y2 = breaks[i + 1]
        if x <= x2:
            if x2 == x1:
                return y2
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return breaks[-1][1]


# ============================================================
# 4. ENTRAÎNEMENT GLOBAL + ENSEMBLE
# ============================================================

def entrainer_ensemble(xs, ys):
    """
    Entraîne les 3 calibrateurs et calcule les poids via
    l'inverse du log-loss (softmax inverse).
    """
    if len(xs) < 20:
        return None  # pas assez de données

    A, B = platt_fit(xs, ys)
    a, b, c = beta_fit(xs, ys)
    breaks = isotonic_fit(xs, ys)

    ps_platt = [platt_predict(x, A, B) for x in xs]
    ps_beta = [beta_predict(x, a, b, c) for x in xs]
    ps_iso = [isotonic_predict(x, breaks) for x in xs]

    ll_platt = log_loss(ys, ps_platt)
    ll_beta = log_loss(ys, ps_beta)
    ll_iso = log_loss(ys, ps_iso)

    eps = 1e-6
    inv_p = 1.0 / (ll_platt + eps)
    inv_b = 1.0 / (ll_beta + eps)
    inv_i = 1.0 / (ll_iso + eps)
    total = inv_p + inv_b + inv_i

    return {
        "platt": {"A": A, "B": B, "log_loss": ll_platt, "poids": inv_p / total},
        "beta": {"a": a, "b": b, "c": c, "log_loss": ll_beta, "poids": inv_b / total},
        "isotonic": {"breaks": breaks, "log_loss": ll_iso, "poids": inv_i / total},
        "n_echantillons": len(xs),
    }


def calibrer_ensemble(x, params):
    """Applique l'ensemble pondéré des 3 calibrateurs."""
    if not params:
        return None
    p1 = platt_predict(x, params["platt"]["A"], params["platt"]["B"])
    p2 = beta_predict(x, params["beta"]["a"], params["beta"]["b"], params["beta"]["c"])
    p3 = isotonic_predict(x, params["isotonic"]["breaks"])

    w1 = params["platt"]["poids"]
    w2 = params["beta"]["poids"]
    w3 = params["isotonic"]["poids"]

    return w1 * p1 + w2 * p2 + w3 * p3


# ============================================================
# 5. SHRINKAGE BAYÉSIEN
# ============================================================

def shrinkage_bayesien(p, force=20):
    """
    Tire légèrement p vers 0.5 pour éviter les extrêmes.
    force = 20 → modéré ; 50 → fort ; 10 → faible.
    Utilise une loi Beta(a, b) centrée sur p.
    """
    alpha = p * force
    beta = (1 - p) * force
    # Espérance d'une Beta(a,b) = a/(a+b), mais on veut une version shrinkée
    # On ajoute un prior uniforme Beta(1,1)
    alpha_new = alpha + 1
    beta_new = beta + 1
    return alpha_new / (alpha_new + beta_new)


def intervalle_confiance(p, n_obs=0, force=20, z=1.96):
    """Renvoie (bas, haut) de l'intervalle de confiance à 95%."""
    alpha = p * force + n_obs
    beta = (1 - p) * force + n_obs
    total = alpha + beta
    # Approximation via variance Beta
    var = (alpha * beta) / ((total ** 2) * (total + 1))
    std = math.sqrt(var)
    bas = max(0.0, p - z * std)
    haut = min(1.0, p + z * std)
    return round(bas, 4), round(haut, 4)
