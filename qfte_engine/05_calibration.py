"""
Calibration avancée QFTE V23.0.
Combine hybride multi-source + 3 calibrateurs + QFTE FUSION
+ BMA (Bayesian Model Averaging) + Attention contextuelle.

✨ VERSION 3 : Isolation par sport (anti-contamination) ✨
"""
from qfte_engine.calibrateurs import (
    entrainer_ensemble,
    calibrer_ensemble,
    qfte_fusion_calibration,
    shrinkage_bayesien,
    intervalle_confiance,
    calculer_poids_bma,
    calculer_attention,
    combiner_bma_attention,
)
from qfte_engine.historique import (
    recuperer_donnees_apprentissage,
    recuperer_donnees_bma,
)


SEPARATEUR = "\u0001"
POIDS_DEFAUT = {"marche": 0.40, "poisson": 0.45, "sharp": 0.15}


def _cle_apprentissage(sport, marche):
    """Reconstruit la clé préfixée par sport utilisée dans l'historique."""
    return "{}{}{}".format(sport or "inconnu", SEPARATEUR, marche or "")


def _poids_hybrides_fallback(volume, mouvement, cote_ok):
    w_marche = POIDS_DEFAUT["marche"]
    w_poisson = POIDS_DEFAUT["poisson"]
    w_sharp = POIDS_DEFAUT["sharp"]

    if volume < 50000:
        w_marche += 0.10
        w_poisson -= 0.10
    if abs(mouvement) > 0.15:
        w_sharp += 0.10
        w_marche -= 0.10
    if not cote_ok:
        w_marche += 0.15
        w_poisson -= 0.15

    w_marche = max(0.10, w_marche)
    w_poisson = max(0.10, w_poisson)
    w_sharp = max(0.05, w_sharp)

    total = w_marche + w_poisson + w_sharp
    return {
        "marche": w_marche / total,
        "poisson": w_poisson / total,
        "sharp": w_sharp / total,
        "hist": 0.10,
        "source": "fallback_contextuel",
    }


def _extraire_signaux_contextuels(data, volume, mouvement):
    match = data.get("match", {})
    contexte = data.get("contexte", {})
    cotes_ctx = contexte.get("cotes", {})
    forme = contexte.get("forme", {})
    h2h = contexte.get("h2h", {})

    co = float(match.get("cote_ouverture", 2.0) or 2.0)
    cf = float(match.get("cote_actuelle", 2.0) or 2.0)
    ecart_cotes = abs(cf - co) / co if co > 0 else 0
    coherence = max(0.0, 1.0 - ecart_cotes / 0.15)

    liquidite = min(1.0, volume / 200000)

    mvt_abs = abs(mouvement)
    mouvement_norm = min(1.0, mvt_abs / 0.20)

    f_dom = float(forme.get("dom_finale", 0))
    f_ext = float(forme.get("ext_finale", 0))
    ecart_forme = abs(f_dom - f_ext)
    forme_nette = min(1.0, ecart_forme / 1.5)

    if h2h.get("n", 0) >= 3:
        v_dom = h2h.get("v_dom", 0)
        v_ext = h2h.get("v_ext", 0)
        nuls = h2h.get("nuls", 0)
        total = v_dom + v_ext + nuls
        if total > 0:
            domination = max(v_dom, v_ext) / total
            h2h_net = max(0.0, (domination - 0.33) / 0.67)
        else:
            h2h_net = 0.3
    else:
        h2h_net = 0.3

    return {
        "coherence": round(coherence, 4),
        "liquidite": round(liquidite, 4),
        "mouvement": round(mouvement_norm, 4),
        "forme_nette": round(forme_nette, 4),
        "h2h_net": round(h2h_net, 4),
}



def calibrer_probabilites(data):
    marches = data.get("marches", [])
    match = data.get("match", {})
    sport = match.get("sport", "football")

    volume = float(match.get("volume", 50000) or 50000)
    co = float(match.get("cote_ouverture", 2.0) or 2.0)
    cf = float(match.get("cote_actuelle", 2.0) or 2.0)
    mouvement = (cf - co) / co if co > 0 else 0
    marge_estimee = float(data.get("marge_estimee", 0.05))
    cote_ok = abs(cf - co) <= 0.15

    # ---------- Chargement des calibrateurs (time-decay, préfixés par sport) ----------
    apprentissage = recuperer_donnees_apprentissage()
    ensembles = {}
    for cle, donnees in apprentissage.items():
        if len(donnees["xs"]) >= 20:
            weights = donnees.get("ws", None)
            ensembles[cle] = entrainer_ensemble(
                donnees["xs"], donnees["ys"], weights
            )
    # On ne compte que les calibrateurs du sport courant
    calibrateurs_sport = sum(
        1 for k in ensembles.keys()
        if isinstance(k, str) and k.startswith(sport + SEPARATEUR)
    )
    data["calibrateurs_actifs"] = calibrateurs_sport

    # ---------- BMA : poids appris par sport ----------
    donnees_bma = recuperer_donnees_bma()
    poids_bma = {}
    bma_actif = False
    for cle, donnees in donnees_bma.items():
        if not isinstance(cle, str) or not cle.startswith(sport + SEPARATEUR):
            continue
        if len(donnees["y"]) >= 15:
            poids_bma[cle] = calculer_poids_bma(
                donnees, poids_defaut=POIDS_DEFAUT, lissage=0.15
            )
            bma_actif = True
    data["bma_actif"] = bma_actif

    # Poids BMA global (moyenne sur les marchés du sport courant)
    if poids_bma:
        w_m = sum(p["marche"] for p in poids_bma.values()) / len(poids_bma)
        w_p = sum(p["poisson"] for p in poids_bma.values()) / len(poids_bma)
        w_s = sum(p["sharp"] for p in poids_bma.values()) / len(poids_bma)
        t = w_m + w_p + w_s or 1.0
        poids_global_bma = {"marche": w_m / t, "poisson": w_p / t, "sharp": w_s / t}
    else:
        poids_global_bma = dict(POIDS_DEFAUT)

    # ---------- Attention contextuelle ----------
    signaux = _extraire_signaux_contextuels(data, volume, mouvement)
    attention = calculer_attention(signaux)
    data["attention"] = attention
    data["signaux_contexte"] = signaux

    # ---------- Combinaison BMA × Attention ----------
    alpha = 0.6 if bma_actif else 0.3
    poids_global = combiner_bma_attention(poids_global_bma, attention, alpha=alpha)
    poids_global["hist"] = 0.10
    poids_global["source"] = "BMA×Attention" if bma_actif else "Attention (fallback)"
    poids_global["alpha_bma"] = alpha
    poids_global["sport"] = sport
    data["poids_global"] = poids_global

    # ---------- Boucle par marché ----------
    resultat = []
    for m in marches:
        nom_marche = m.get("nom", "")
        cle_marche = _cle_apprentissage(sport, nom_marche)
        cote = float(m.get("cote", 2.0) or 2.0)
        proba_poisson = float(m.get("proba_juste", 0.5))

        # Source 1 : marché
        proba_marche_brute = 1 / cote if cote > 0 else 0.5
        proba_marche = proba_marche_brute * 0.95

        # Source 2 : Poisson
        proba_poisson_finale = proba_poisson

        # Source 3 : sharp
        bonus_sharp = max(-0.03, min(0.03, -mouvement * 0.5))
        proba_sharp = max(0.05, min(0.95, proba_marche + bonus_sharp))

        # Source 4 : historique (calibrateur du sport courant)
        proba_hist = None
        if cle_marche in ensembles:
            proba_hist = calibrer_ensemble(proba_poisson_finale, ensembles[cle_marche])

        # ---------- Poids pour ce marché ----------
        if cle_marche in poids_bma:
            pb = poids_bma[cle_marche]
            pa = attention
            poids = combiner_bma_attention(pb, pa, alpha=alpha)
        else:
            poids = {
                "marche": poids_global["marche"],
                "poisson": poids_global["poisson"],
                "sharp": poids_global["sharp"],
            }

        # Réservation de 10% pour l'historique si dispo
        w_total = poids["marche"] + poids["poisson"] + poids["sharp"] or 1.0
        if proba_hist is not None:
            poids["marche"] = (poids["marche"] / w_total) * 0.90
            poids["poisson"] = (poids["poisson"] / w_total) * 0.90
            poids["sharp"] = (poids["sharp"] / w_total) * 0.90
            poids["hist"] = 0.10
        else:
            poids["marche"] = poids["marche"] / w_total
            poids["poisson"] = poids["poisson"] / w_total
            poids["sharp"] = poids["sharp"] / w_total
            poids["hist"] = 0.0

        poids["source"] = poids_global["source"]
        poids["sport"] = sport

        # ---------- Hybridation ----------
        if proba_hist is not None:
            proba_hybride = (
                poids["marche"] * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
                + poids["hist"] * proba_hist
            )
        else:
            proba_hybride = (
                poids["marche"] * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
            )

        # ---------- QFTE Fusion ----------
        force_signal = poids["marche"] + poids["poisson"]
        proba_fusion = qfte_fusion_calibration(
            proba_hybride,
            force_signal=force_signal,
            marge_marche=marge_estimee,
            sharp_signal=-mouvement * 0.5,
        )

        proba_finale = shrinkage_bayesien(proba_fusion, force=20)

        # ---------- Intervalle de confiance ----------
        n_obs = len(apprentissage[cle_marche]["xs"]) if cle_marche in apprentissage else 0
        ci_bas, ci_haut = intervalle_confiance(proba_finale, n_obs=n_obs, force=20)

        # ---------- Fiabilité multi-critères ----------
        crit1 = max(0.25, min(1.0, 1 - abs(proba_finale - 0.5) * 1.5))
        crit2 = max(0.20, min(1.0, 1 - abs(proba_finale - proba_marche) * 2))
        crit3 = min(1.0, volume / 100000)
        if abs(mouvement) < 0.05:
            crit4 = 1.0
        elif abs(mouvement) < 0.15:
            crit4 = 0.85
        else:
            crit4 = 0.60

        fiabilite = crit1 * 0.30 + crit2 * 0.30 + crit3 * 0.20 + crit4 * 0.20
        fiabilite = max(0.50, min(0.98, fiabilite))

        m["proba_calibree"] = round(proba_finale, 4)
        m["fiabilite"] = round(fiabilite, 4)
        m["intervalle_confiance"] = {"bas": ci_bas, "haut": ci_haut}
        m["poids_hybrides"] = poids
        m["proba_marche"] = round(proba_marche, 4)
        m["proba_poisson"] = round(proba_poisson_finale, 4)
        m["proba_sharp"] = round(proba_sharp, 4)
        m["proba_hist"] = round(proba_hist, 4) if proba_hist is not None else None
        resultat.append(m)

    data["marches"] = resultat
    return data
