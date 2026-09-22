"""
Module de calibration avancée QFTE V23.0.
Contient 4 calibrateurs + QFTE Fusion + Bayesian Model Averaging.
Version AVEC time-decay weighting et BMA.

Pur Python — aucune dépendance externe.
"""
import math


def sigmoid(z):
    if z > 500: return 1.0
    if z < -500: return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def logit(p):
    eps = 1e-9
    p = max(eps, min(1 - eps, p))
    return math.log(p / (1 - p))


# ============================================================
# LOG-LOSS PONDÉRÉ (WEIGHTED) — Time-decay
# ============================================================
def log_loss(ys, ps, ws=None):
    eps = 1e-9
    n = len(ys)
    if n == 0: return 1.0
    if ws is None:
        ws = [1.0] * n
    total_w = sum(ws)
    if total_w <= 0: return 1.0
    s = 0.0
    for y, p, w in zip(ys, ps, ws):
        p = max(eps, min(1 - eps, p))
        s -= w * (y * math.log(p) + (1 - y) * math.log(1 - p))
    return s / total_w


def brier_score(ys, ps, ws=None):
    n = len(ys)
    if n == 0: return 1.0
    if ws is None:
        ws = [1.0] * n
    total_w = sum(ws)
    if total_w <= 0: return 1.0
    return sum(w * (p - y) ** 2 for y, p, w in zip(ys, ps, ws)) / total_w


# ============================================================
# 1. PLATT SCALING (pondéré)
# ============================================================
def platt_fit(xs, ys, ws=None, lr=0.05, epochs=800):
    A, B = -1.0, 0.0
    n = len(xs)
    if n < 5: return A, B
    if ws is None: ws = [1.0] * n
    total_w = sum(ws) or 1.0

    for _ in range(epochs):
        gA, gB = 0.0, 0.0
        for x, y, w in zip(xs, ys, ws):
            p = sigmoid(A * x + B)
            err = (p - y) * w
            gA += err * x
            gB += err
        A -= lr * gA / total_w
        B -= lr * gB / total_w
    return A, B


def platt_predict(x, A, B):
    return sigmoid(A * x + B)


# ============================================================
# 2. BETA CALIBRATION (pondéré)
# ============================================================
def beta_fit(xs, ys, ws=None, lr=0.03, epochs=800):
    a, b, c = 1.0, 1.0, 0.0
    n = len(xs)
    if n < 5: return a, b, c
    if ws is None: ws = [1.0] * n
    total_w = sum(ws) or 1.0
    eps = 1e-9

    for _ in range(epochs):
        ga, gb, gc = 0.0, 0.0, 0.0
        for x, y, w in zip(xs, ys, ws):
            x = max(eps, min(1 - eps, x))
            lx, l1x = math.log(x), math.log(1 - x)
            z = a * lx + b * l1x + c
            p = sigmoid(z)
            err = (p - y) * w
            ga += err * lx
            gb += err * l1x
            gc += err
        a -= lr * ga / total_w
        b -= lr * gb / total_w
        c -= lr * gc / total_w
    return a, b, c


def beta_predict(x, a, b, c):
    eps = 1e-9
    x = max(eps, min(1 - eps, x))
    return sigmoid(a * math.log(x) + b * math.log(1 - x) + c)


# ============================================================
# 3. ISOTONIC REGRESSION (pondérée, PAV)
# ============================================================
def isotonic_fit(xs, ys, ws=None):
    if len(xs) < 5:
        return [(0.0, 0.0), (1.0, 1.0)]
    if ws is None:
        ws = [1.0] * len(xs)

    pairs = sorted(zip(xs, ys, ws), key=lambda t: t[0])
    blocks = []
    for x, y, w in pairs:
        blocks.append([x * w, y * w, w])
        while len(blocks) >= 2:
            b1, b2 = blocks[-2], blocks[-1]
            m1 = b1[1] / b1[2] if b1[2] > 0 else 0
            m2 = b2[1] / b2[2] if b2[2] > 0 else 0
            if m1 > m2:
                merged = [b1[0] + b2[0], b1[1] + b2[1], b1[2] + b2[2]]
                blocks.pop(); blocks.pop()
                blocks.append(merged)
            else:
                break

    result = []
    for b in blocks:
        if b[2] > 0:
            result.append((b[0] / b[2], b[1] / b[2]))
    if not result:
        return [(0.0, 0.0), (1.0, 1.0)]
    if result[0][0] > 0.0:
        result.insert(0, (0.0, result[0][1]))
    if result[-1][0] < 1.0:
        result.append((1.0, result[-1][1]))
    return result


def isotonic_predict(x, breaks):
    if not breaks: return x
    for i in range(len(breaks) - 1):
        x1, y1 = breaks[i]
        x2, y2 = breaks[i + 1]
        if x <= x2:
            if x2 == x1: return y2
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return breaks[-1][1]


# ============================================================
# 4. ✨ QFTE FUSION CALIBRATION — SIGNATURE ✨
# ============================================================
def temperature_adaptatif(p, force_signal, marge_marche):
    incertitude = 1 - abs(p - 0.5) * 2
    T = 0.85 + incertitude * 0.55
    T -= force_signal * 0.35
    T += marge_marche * 2.0
    return max(0.50, min(1.60, T))


def correction_sinusoidale(p, amplitude=0.04):
    return amplitude * math.sin(2 * math.pi * p)


def focal_weight(p):
    return (abs(p - 0.5) * 2) ** 0.5


def dirichlet_smoothing(p, force=25):
    a = p * force + 1
    b = (1 - p) * force + 1
    return a / (a + b)


def qfte_fusion_calibration(p, force_signal=0.5, marge_marche=0.05, sharp_signal=0.0):
    if p <= 0.001 or p >= 0.999:
        return p
    z = logit(p)
    T = temperature_adaptatif(p, force_signal, marge_marche)
    z_t = z / T
    focal = focal_weight(p)
    z_focal = z_t + (focal - 0.5) * 0.05
    z_sharp = z_focal + sharp_signal * 0.15
    p_new = sigmoid(z_sharp)
    p_final = dirichlet_smoothing(p_new, force=25)
    return max(0.02, min(0.98, p_final))


# ============================================================
# 5. ENSEMBLE (Platt + Beta + Isotonic) avec time-decay
# ============================================================
def entrainer_ensemble(xs, ys, ws=None):
    if len(xs) < 20:
        return None
    if ws is None:
        ws = [1.0] * len(xs)

    A, B = platt_fit(xs, ys, ws)
    a, b, c = beta_fit(xs, ys, ws)
    breaks = isotonic_fit(xs, ys, ws)

    ps_p = [platt_predict(x, A, B) for x in xs]
    ps_b = [beta_predict(x, a, b, c) for x in xs]
    ps_i = [isotonic_predict(x, breaks) for x in xs]

    ll_p = log_loss(ys, ps_p, ws)
    ll_b = log_loss(ys, ps_b, ws)
    ll_i = log_loss(ys, ps_i, ws)

    eps = 1e-6
    ip, ib, ii = 1/(ll_p+eps), 1/(ll_b+eps), 1/(ll_i+eps)
    t = ip + ib + ii

    return {
        "platt": {"A": A, "B": B, "log_loss": ll_p, "poids": ip / t},
        "beta": {"a": a, "b": b, "c": c, "log_loss": ll_b, "poids": ib / t},
        "isotonic": {"breaks": breaks, "log_loss": ll_i, "poids": ii / t},
        "n_echantillons": len(xs),
        "poids_total": round(sum(ws), 2),
    }


def calibrer_ensemble(x, params):
    if not params:
        return None
    p1 = platt_predict(x, params["platt"]["A"], params["platt"]["B"])
    p2 = beta_predict(x, params["beta"]["a"], params["beta"]["b"], params["beta"]["c"])
    p3 = isotonic_predict(x, params["isotonic"]["breaks"])
    w1, w2, w3 = params["platt"]["poids"], params["beta"]["poids"], params["isotonic"]["poids"]
    return w1 * p1 + w2 * p2 + w3 * p3


# ============================================================
# 6. SHRINKAGE BAYÉSIEN + INTERVALLE
# ============================================================
def shrinkage_bayesien(p, force=20):
    a = p * force + 1
    b = (1 - p) * force + 1
    return a / (a + b)


def intervalle_confiance(p, n_obs=0, force=20, z=1.96):
    a = p * force + n_obs
    b = (1 - p) * force + n_obs
    t = a + b
    var = (a * b) / ((t ** 2) * (t + 1))
    std = math.sqrt(var)
    return round(max(0.0, p - z * std), 4), round(min(1.0, p + z * std), 4)


# ============================================================
# 7. ✨ BAYESIAN MODEL AVERAGING (BMA) ✨
# ============================================================
def _log_loss_source(probas, ys, ws):
    """Log-loss pondéré pour une source unique."""
    eps = 1e-9
    n = len(ys)
    if n == 0: return 1.0
    total_w = sum(ws) or 1.0
    s = 0.0
    for p, y, w in zip(probas, ys, ws):
        p = max(eps, min(1 - eps, p))
        s -= w * (y * math.log(p) + (1 - y) * math.log(1 - p))
    return s / total_w


def calculer_poids_bma(donnees, poids_defaut=None, lissage=0.15):
    """
    ✨ Bayesian Model Averaging ✨
    Apprend les poids optimaux des 3 sources (Marché / Poisson / Sharp)
    à partir de l'historique.

    Paramètres :
      donnees : dict { "marche": [...], "poisson": [...], "sharp": [...],
                       "y": [...], "w": [...] }
      poids_defaut : dict de repli si l'historique est insuffisant
      lissage : force du shrinkage vers les poids par défaut (0.0 = aucun, 1.0 = total)

    Retourne : dict { "marche": w1, "poisson": w2, "sharp": w3 }
    """
    if poids_defaut is None:
        poids_defaut = {"marche": 0.40, "poisson": 0.45, "sharp": 0.15}

    # Pas assez de données → poids par défaut
    n = len(donnees.get("y", []))
    if n < 15:
        return dict(poids_defaut)

    ys = donnees["y"]
    ws = donnees["w"]

    ll_marche = _log_loss_source(donnees["marche"], ys, ws)
    ll_poisson = _log_loss_source(donnees["poisson"], ys, ws)
    ll_sharp = _log_loss_source(donnees["sharp"], ys, ws)

    # Poids = inverse du log-loss (softmax inverse)
    eps = 1e-6
    inv_m = 1.0 / (ll_marche + eps)
    inv_p = 1.0 / (ll_poisson + eps)
    inv_s = 1.0 / (ll_sharp + eps)
    total = inv_m + inv_p + inv_s

    w_m = inv_m / total
    w_p = inv_p / total
    w_s = inv_s / total

    # Shrinkage vers les poids par défaut (évite les extrêmes)
    w_m = (1 - lissage) * w_m + lissage * poids_defaut["marche"]
    w_p = (1 - lissage) * w_p + lissage * poids_defaut["poisson"]
    w_s = (1 - lissage) * w_s + lissage * poids_defaut["sharp"]

    # Normalisation finale
    t = w_m + w_p + w_s
    return {
        "marche": round(w_m / t, 4),
        "poisson": round(w_p / t, 4),
        "sharp": round(w_s / t, 4),
        "log_loss_marche": round(ll_marche, 4),
        "log_loss_poisson": round(ll_poisson, 4),
        "log_loss_sharp": round(ll_sharp, 4),
        "n_obs": n,
        "source_apprise": True,
    }
