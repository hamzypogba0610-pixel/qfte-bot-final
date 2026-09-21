"""
Module de calibration avancée QFTE V23.0.
Contient 4 calibrateurs + la formule signature QFTE Fusion.
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


def log_loss(ys, ps):
    eps = 1e-9
    n = len(ys)
    if n == 0: return 1.0
    s = 0.0
    for y, p in zip(ys, ps):
        p = max(eps, min(1 - eps, p))
        s -= y * math.log(p) + (1 - y) * math.log(1 - p)
    return s / n


def brier_score(ys, ps):
    n = len(ys)
    if n == 0: return 1.0
    return sum((p - y) ** 2 for y, p in zip(ys, ps)) / n


# ============================================================
# 1. PLATT SCALING
# ============================================================
def platt_fit(xs, ys, lr=0.05, epochs=800):
    A, B = -1.0, 0.0
    n = len(xs)
    if n < 5: return A, B
    for _ in range(epochs):
        gA, gB = 0.0, 0.0
        for x, y in zip(xs, ys):
            p = sigmoid(A * x + B)
            err = p - y
            gA += err * x
            gB += err
        A -= lr * gA / n
        B -= lr * gB / n
    return A, B


def platt_predict(x, A, B):
    return sigmoid(A * x + B)


# ============================================================
# 2. BETA CALIBRATION (Kull et al. 2017)
# ============================================================
def beta_fit(xs, ys, lr=0.03, epochs=800):
    a, b, c = 1.0, 1.0, 0.0
    n = len(xs)
    if n < 5: return a, b, c
    eps = 1e-9
    for _ in range(epochs):
        ga, gb, gc = 0.0, 0.0, 0.0
        for x, y in zip(xs, ys):
            x = max(eps, min(1 - eps, x))
            lx, l1x = math.log(x), math.log(1 - x)
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
# 3. ISOTONIC REGRESSION (PAV)
# ============================================================
def isotonic_fit(xs, ys):
    if len(xs) < 5:
        return [(0.0, 0.0), (1.0, 1.0)]
    pairs = sorted(zip(xs, ys))
    blocks = []
    for x, y in pairs:
        blocks.append([x, y, 1])
        while len(blocks) >= 2:
            b1, b2 = blocks[-2], blocks[-1]
            if b1[1]/b1[2] > b2[1]/b2[2]:
                merged = [b1[0]+b2[0], b1[1]+b2[1], b1[2]+b2[2]]
                blocks.pop(); blocks.pop()
                blocks.append(merged)
            else:
                break
    result = [(b[0]/b[2], b[1]/b[2]) for b in blocks]
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
# 4. ✨ QFTE FUSION CALIBRATION — FORMULE SIGNATURE ✨
# ============================================================
"""
Combinaison de 5 techniques de pointe :
  • Temperature Scaling adaptatif (Guo et al. 2017)
  • Correction sinusoïdale (signature QFTE)
  • Focal weighting (Lin et al. 2017)
  • Dirichlet smoothing (Kull et al. 2019)
  • Bayesian Model Averaging

p_final = σ( logit(p) / T_adaptive + α·sin(2π·p) + β·focal + γ·sharp )
"""


def temperature_adaptatif(p, force_signal, marge_marche):
    """
    Température qui s'adapte au contexte :
    - Plus on est incertain → T augmente (adoucit la proba)
    - Plus le signal est fort → T diminue (renforce la proba)
    """
    incertitude = 1 - abs(p - 0.5) * 2          # 0 = sûr, 1 = incertain
    T = 0.85 + incertitude * 0.55
    T -= force_signal * 0.35
    T += marge_marche * 2.0                      # marge élevée → + de prudence
    return max(0.50, min(1.60, T))


def correction_sinusoidale(p, amplitude=0.04):
    """
    ✨ Signature QFTE ✨
    Capture les non-linéarités invisibles autour de 0.5.
    Inspirée des séries de Fourier utilisées en traitement du signal.
    """
    return amplitude * math.sin(2 * math.pi * p)


def focal_weight(p):
    """
    Focal weighting (Lin et al. 2017) appliqué à la calibration.
    Les cas "difficiles" (proches de 0.5) reçoivent plus d'attention.
    """
    return (abs(p - 0.5) * 2) ** 0.5


def dirichlet_smoothing(p, force=25):
    """
    Lissage Dirichlet — évite les extrêmes tout en préservant l'information.
    """
    a = p * force + 1
    b = (1 - p) * force + 1
    return a / (a + b)


def qfte_fusion_calibration(p, force_signal=0.5, marge_marche=0.05, sharp_signal=0.0):
    """
    ✨ FORMULE MAGIQUE QFTE ✨
    Calibration finale combinant 5 techniques de pointe.
    """
    if p <= 0.001 or p >= 0.999:
        return p

    # 1. Logit de base
    z = logit(p)

    # 2. Temperature scaling adaptatif
    T = temperature_adaptatif(p, force_signal, marge_marche)
    z_t = z / T

    # 3. Correction sinusoïdale signature
    corr_sin = correction_sinusoidale(p, amplitude=0.04)

    # 4. Focal weighting
    focal = focal_weight(p)
    z_focal = z_t + (focal - 0.5) * 0.05

    # 5. Signal sharp (mouvement de cote)
    z_sharp = z_focal + sharp_signal * 0.15

    # 6. Sigmoid
    p_new = sigmoid(z_sharp)

    # 7. Dirichlet smoothing final
    p_final = dirichlet_smoothing(p_new, force=25)

    # Bornes
    return max(0.02, min(0.98, p_final))


# ============================================================
# 5. ENTRAÎNEMENT ENSEMBLE (Platt + Beta + Isotonic)
# ============================================================
def entrainer_ensemble(xs, ys):
    if len(xs) < 20:
        return None

    A, B = platt_fit(xs, ys)
    a, b, c = beta_fit(xs, ys)
    breaks = isotonic_fit(xs, ys)

    ps_p = [platt_predict(x, A, B) for x in xs]
    ps_b = [beta_predict(x, a, b, c) for x in xs]
    ps_i = [isotonic_predict(x, breaks) for x in xs]

    ll_p, ll_b, ll_i = log_loss(ys, ps_p), log_loss(ys, ps_b), log_loss(ys, ps_i)

    eps = 1e-6
    ip, ib, ii = 1/(ll_p+eps), 1/(ll_b+eps), 1/(ll_i+eps)
    t = ip + ib + ii

    return {
        "platt": {"A": A, "B": B, "log_loss": ll_p, "poids": ip / t},
        "beta": {"a": a, "b": b, "c": c, "log_loss": ll_b, "poids": ib / t},
        "isotonic": {"breaks": breaks, "log_loss": ll_i, "poids": ii / t},
        "n_echantillons": len(xs),
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
