"""
Calibration avancée QFTE V23.0.
Combine 4 sources de probabilité + 3 calibrateurs en ensemble + shrinkage bayésien.
"""
from qfte_engine.calibrateurs import (
    entrainer_ensemble,
    calibrer_ensemble,
    shrinkage_bayesien,
    intervalle_confiance,
)
from qfte_engine.historique import recuperer_donnees_apprentissage


def _poids_hybrides(volume, mouvement, cote_ok):
    """
    Calcule les poids adaptatifs du modèle hybride :
    - Plus le marché est liquide et cohérent → plus on fait confiance au marché.
    - Moins il l'est → plus on s'appuie sur notre modèle Poisson.
    """
    # Base
    w_marche = 0.40
    w_poisson = 0.35
    w_sharp = 0.15
    w_hist = 0.10

    # Ajustements contextuels
    if volume < 50000:
        w_marche += 0.10
        w_poisson -= 0.10
    if abs(mouvement) > 0.15:
        w_sharp += 0.10
        w_marche -= 0.10
    if not cote_ok:
        w_marche += 0.15
        w_poisson -= 0.15

    # Normalisation
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
    cote_ouverture = float(match.get("cote_ouverture", 2.0) or 2.0)
    cote_actuelle = float(match.get("cote_actuelle", 2.0) or 2.0)
    mouvement = 0.0
    if cote_ouverture > 0:
        mouvement = (cote_actuelle - cote_ouverture) / cote_ouverture

    # ---------- Chargement des calibrateurs entraînés ----------
    apprentissage = recuperer_donnees_apprentissage()
    ensembles = {}
    for nom_marche, donnees in apprentissage.items():
        if len(donnees["xs"]) >= 20:
            ensembles[nom_marche] = entrainer_ensemble(donnees["xs"], donnees["ys"])

    data["calibrateurs_actifs"] = len(ensembles)

    resultat = []
    for m in marches:
        nom_marche = m.get("nom", "")
        cote = float(m.get("cote", 2.0) or 2.0)
        proba_poisson = float(m.get("proba_juste", 0.5))

        # ---------- Source 1 : marché (probabilité implicite dé-margée) ----------
        proba_marche_brute = 1 / cote if cote > 0 else 0.5
        proba_marche = proba_marche_brute * 0.95  # marge moyenne

        # ---------- Source 2 : Poisson/Dixon-Coles ----------
        proba_poisson_finale = proba_poisson

        # ---------- Source 3 : Sharp signal (mouvement de cote) ----------
        bonus_sharp = max(-0.03, min(0.03, -mouvement * 0.5))
        proba_sharp = proba_marche + bonus_sharp
        proba_sharp = max(0.05, min(0.95, proba_sharp))

        # ---------- Source 4 : Historique (calibrateur ensemble) ----------
        proba_hist = None
        if nom_marche in ensembles:
            proba_hist = calibrer_ensemble(proba_poisson_finale, ensembles[nom_marche])

        # ---------- Combinaison hybride pondérée ----------
        cote_ok = abs(cote_actuelle - cote_ouverture) <= 0.15
        poids = _poids_hybrides(volume, mouvement, cote_ok)

        if proba_hist is not None:
            proba_hybride = (
                poids["marche"] * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
                + poids["hist"] * proba_hist
            )
        else:
            # Pas de calibrateur → redistribue le poids hist sur le marché
            poids_marche = poids["marche"] + poids["hist"]
            proba_hybride = (
                poids_marche * proba_marche
                + poids["poisson"] * proba_poisson_finale
                + poids["sharp"] * proba_sharp
            )

        # ---------- Shrinkage bayésien ----------
        proba_finale = shrinkage_bayesien(proba_hybride, force=20)

        # ---------- Intervalle de confiance ----------
        n_obs = 0
        if nom_marche in apprentissage:
            n_obs = len(apprentissage[nom_marche]["xs"])
        ci_bas, ci_haut = intervalle_confiance(proba_finale, n_obs=n_obs, force=20)

        # ---------- Fiabilité multi-critères ----------
        crit1 = 1 - abs(proba_finale - 0.5) * 1.5
        crit1 = max(0.25, min(1.0, crit1))

        crit2 = 1 - abs(proba_finale - proba_marche) * 2
        crit2 = max(0.20, min(1.0, crit2))

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
