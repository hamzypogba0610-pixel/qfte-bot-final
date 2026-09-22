"""
Calibration avancée QFTE V23.0.
Combine hybride multi-source + 3 calibrateurs + FORMULE MAGIQUE QFTE FUSION.
Version AVEC time-decay weighting.
"""
from qfte_engine.calibrateurs import (
    entrainer_ensemble,
    calibrer_ensemble,
    qfte_fusion_calibration,
    shrinkage_bayesien,
    intervalle_confiance,
)
from qfte_engine.historique import recuperer_donnees_apprentissage


def _poids_hybrides(volume, mouvement, cote_ok):
    w_marche, w_poisson, w_sharp, w_hist = 0.40, 0.35, 0.15, 0.10
    if volume < 50000:
        w_marche += 0.10; w_poisson -= 0.10
    if abs(mouvement) > 0.15:
        w_sharp += 0.10; w_marche -= 0.10
    if not cote_ok:
        w_marche += 0.15; w_poisson -= 0.15
    total = w_marche + w_poisson + w_sharp + w_hist
    return {
        "marche": w_marche / total,
        "poisson": w_poisson / total,
        "sharp": w_sharp / total,
        "hist": w_hist / total,
    }


def calibrer_probabilites(data):
    marches = data.get("marches", [])
    match = data.get("match", {})

    volume = float(match.get("volume", 50000) or 50000)
    co = float(match.get("cote_ouverture", 2.0) or 2.0)
    cf = float(match.get("cote_actuelle", 2.0) or 2.0)
    mouvement = (cf - co) / co if co > 0 else 0
    marge_estimee = float(data.get("marge_estimee", 0.05))

    # ---------- Chargement des calibrateurs entraînés (avec time-decay) ----------
    apprentissage = recuperer_donnees_apprentissage()
    ensembles = {}
    for nom_marche, donnees in apprentissage.items():
        if len(donnees["xs"]) >= 20:
            weights = donnees.get("ws", None)
            ensembles[nom_marche] = entrainer_ensemble(
                donnees["xs"], donnees["ys"], weights
            )

    data["calibrateurs_actifs"] = len(ensembles)

    resultat = []
    for m in marches:
        nom_marche = m.get("nom", "")
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

        # Source 4 : historique
        proba_hist = None
        if nom_marche in ensembles:
            proba_hist = calibrer_ensemble(proba_poisson_finale, ensembles[nom_marche])

        # Hybridation pondérée
        cote_ok = abs(cf - co) <= 0.15
        poids = _poids_hybrides(volume, mouvement, cote_ok)

        if proba_hist is not None:
            proba_hybride = (
                poids["marche"] * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
                + poids["hist"] * proba_hist
            )
        else:
            pm = poids["marche"] + poids["hist"]
            proba_hybride = (
                pm * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
            )

        # ✨ FORMULE MAGIQUE QFTE FUSION ✨
        force_signal = poids["marche"] + poids["poisson"]
        sharp_sig = -mouvement * 0.5
        proba_fusion = qfte_fusion_calibration(
            proba_hybride,
            force_signal=force_signal,
            marge_marche=marge_estimee,
            sharp_signal=sharp_sig,
        )

        # Shrinkage bayésien final
        proba_finale = shrinkage_bayesien(proba_fusion, force=20)

        # Intervalle de confiance
        n_obs = len(apprentissage[nom_marche]["xs"]) if nom_marche in apprentissage else 0
        ci_bas, ci_haut = intervalle_confiance(proba_finale, n_obs=n_obs, force=20)

        # Fiabilité multi-critères
        crit1 = max(0.25, min(1.0, 1 - abs(proba_finale - 0.5) * 1.5))
        crit2 = max(0.20, min(1.0, 1 - abs(proba_finale - proba_marche) * 2))
        crit3 = min(1.0, volume / 100000)
        if abs(mouvement) < 0.05: crit4 = 1.0
        elif abs(mouvement) < 0.15: crit4 = 0.85
        else: crit4 = 0.60

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
