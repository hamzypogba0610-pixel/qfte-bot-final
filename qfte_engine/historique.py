import json
import os
import math
import importlib
from datetime import datetime

_elo_tennis = importlib.import_module("qfte_engine.18_elo_tennis")

FICHIER_HISTORIQUE = "historique.json"
BANKROLL_DEPART = 1000.0
DEMI_VIE_JOURS = 30.0


def charger_historique():
    if not os.path.exists(FICHIER_HISTORIQUE):
        return []
    try:
        with open(FICHIER_HISTORIQUE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _ecrire_historique(historique):
    try:
        with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def _poids_temporel(date_str):
    if not date_str:
        return 0.5
    try:
        date_match = datetime.fromisoformat(date_str.replace("Z", "").split("+")[0])
        age_jours = (datetime.now() - date_match).total_seconds() / 86400.0
        if age_jours < 0:
            age_jours = 0
        return math.exp(-age_jours / DEMI_VIE_JOURS)
    except (ValueError, TypeError):
        return 0.5


def sauvegarder_analyse(match, resultat):
    historique = charger_historique()

    recos = resultat.get("recommandations", [])
    reco_principale = recos[0] if recos else {}

    id_unique = datetime.now().strftime("%Y%m%d%H%M%S%f")

    entree = {
        "id": id_unique,
        "date": datetime.now().isoformat(),
        "sport": match.get("sport", "-"),
        "competition": match.get("competition", "-"),
        "surface": match.get("surface", ""),
        "equipe1": match.get("equipe1", "-"),
        "equipe2": match.get("equipe2", "-"),
        "cotes": {
            "ouv_1": match.get("cote_ouv_1"),
            "ferm_1": match.get("cote_ferm_1"),
            "ouv_2": match.get("cote_ouv_2"),
            "ferm_2": match.get("cote_ferm_2"),
            "ah": match.get("cote_ah"),
            "over25": match.get("cote_over25"),
            "btts": match.get("cote_btts"),
        },
        "decision": resultat.get("decision", "-"),
        "recommandations": recos,
        "meilleure_reco": reco_principale,
        "lambda_home": resultat.get("lambda_home"),
        "lambda_away": resultat.get("lambda_away"),
        "resultat": None,
    }

    historique.append(entree)
    _ecrire_historique(historique)
    return entree


def _pari_gagne(marche, selection, score_home, score_away):
    total = score_home + score_away
    selection = (selection or "").lower()
    marche_lower = (marche or "").lower()

    # Football
    if "handicap" in marche_lower:
        return score_home > score_away

    if "over/under 2.5" in marche_lower or ("2.5" in marche_lower and "total" not in marche_lower and "jeux" not in marche_lower):
        if "under" in selection:
            return total < 2.5
        else:
            return total > 2.5

    if "btts" in marche_lower:
        return score_home >= 1 and score_away >= 1

    # Basket
    if "money line" in marche_lower:
        return score_home > score_away

    if "spread" in marche_lower:
        return (score_home - score_away) > 4.5

    if "total points" in marche_lower:
        if "under" in selection:
            return total < 180.5
        return total > 180.5

    # Tennis
    if "vainqueur" in marche_lower:
        return score_home > score_away

    if "over/under jeux" in marche_lower:
        if "under" in selection:
            return total < 22.5
        return total > 22.5

    if "score exact" in marche_lower or "score 2-0" in marche_lower:
        return score_home > score_away and score_away == 0

    return False


def enregistrer_resultat(id_unique, score_home, score_away, marches_joues):
    historique = charger_historique()

    for h in historique:
        if h.get("id") == id_unique:
            paris = []
            for reco in h.get("recommandations", []):
                marche = reco.get("marche", "")
                if marche in marches_joues:
                    gagne = _pari_gagne(
                        marche, reco.get("selection", ""), score_home, score_away
                    )
                    stake_pct = float(str(reco.get("stake", "0")).replace("%", "") or 0)
                    cote = float(reco.get("cote", 1.0))
                    mise = BANKROLL_DEPART * (stake_pct / 100)
                    gain = mise * (cote - 1) if gagne else -mise
                    paris.append({
                        "marche": marche,
                        "cote": cote,
                        "stake_pct": stake_pct,
                        "mise": round(mise, 2),
                        "gagne": gagne,
                        "gain": round(gain, 2),
                    })

            h["resultat"] = {
                "score_home": score_home,
                "score_away": score_away,
                "paris": paris,
                "date_resultat": datetime.now().isoformat(),
            }
            _ecrire_historique(historique)

            # ✨ Mise à jour Elo Tennis si applicable
            if h.get("sport", "") == "tennis":
                _maj_elo_tennis(h, score_home, score_away)

            return h

    return None



def _maj_elo_tennis(h, score_home, score_away):
    """
    ✨ Mise à jour Elo Tennis après un match enregistré.

    - Détermine le gagnant/perdant à partir des scores en sets
    - Récupère la surface depuis l'entrée historique
    - Appelle enregistrer_match() du module Elo
    """
    try:
        equipe1 = h.get("equipe1", "")
        equipe2 = h.get("equipe2", "")
        surface = h.get("surface", "dur")
        competition = h.get("competition", "")

        if not equipe1 or not equipe2:
            return None

        # Score en sets : score_home = sets joueur 1, score_away = sets joueur 2
        if score_home > score_away:
            gagnant, perdant = equipe1, equipe2
        elif score_away > score_home:
            gagnant, perdant = equipe2, equipe1
        else:
            # Pas de match nul au tennis → on ignore
            return None

        resultat_maj = _elo_tennis.enregistrer_match(
            gagnant, perdant, surface=surface, competition=competition
        )

        # Sauvegarde de l'info Elo dans l'entrée historique
        h["elo_maj"] = resultat_maj
        return resultat_maj

    except Exception as e:
        # On ne bloque jamais l'enregistrement à cause de l'Elo
        h["elo_erreur"] = str(e)
        return None


def calculer_roi():
    historique = charger_historique()
    total_paris = 0
    paris_gagnes = 0
    paris_perdus = 0
    total_mise = 0.0
    total_gain = 0.0

    for h in historique:
        res = h.get("resultat")
        if not res:
            continue
        for p in res.get("paris", []):
            total_paris += 1
            total_mise += p["mise"]
            total_gain += p["gain"]
            if p["gagne"]:
                paris_gagnes += 1
            else:
                paris_perdus += 1

    if total_mise == 0:
        roi_pct = 0.0
        taux_reussite = 0.0
    else:
        roi_pct = (total_gain / total_mise) * 100
        taux_reussite = (paris_gagnes / total_paris) * 100 if total_paris > 0 else 0.0

    bankroll_finale = BANKROLL_DEPART + total_gain

    return {
        "bankroll_depart": BANKROLL_DEPART,
        "bankroll_finale": round(bankroll_finale, 2),
        "profit": round(total_gain, 2),
        "roi_pct": round(roi_pct, 2),
        "taux_reussite": round(taux_reussite, 2),
        "total_paris": total_paris,
        "paris_gagnes": paris_gagnes,
        "paris_perdus": paris_perdus,
        "total_mise": round(total_mise, 2),
    }


def calculer_statistiques():
    historique = charger_historique()
    total = len(historique)

    stats = {
        "total": total,
        "par_decision": {},
        "par_marche": {},
        "par_sport": {},
        "niveau_drift": "NORMAL",
        "message_drift": "Modèle stable, aucune dérive détectée.",
    }

    if total == 0:
        stats["message_drift"] = "Aucune analyse enregistrée pour le moment."
        return stats

    for h in historique:
        d = h.get("decision", "INCONNU")
        stats["par_decision"][d] = stats["par_decision"].get(d, 0) + 1

        s = h.get("sport", "inconnu")
        stats["par_sport"][s] = stats["par_sport"].get(s, 0) + 1

        recos = h.get("meilleure_reco", {})
        marche = recos.get("marche") if recos else None
        if marche:
            stats["par_marche"][marche] = stats["par_marche"].get(marche, 0) + 1

    total_attaques = (
        stats["par_decision"].get("ATTAQUE FORTE", 0)
        + stats["par_decision"].get("ATTAQUE", 0)
    )
    ratio_attaques = total_attaques / total

    if ratio_attaques < 0.05 and total >= 10:
        stats["niveau_drift"] = "CRITIQUE"
        stats["message_drift"] = "Aucune opportunité détectée sur les 10 dernières analyses."
    elif ratio_attaques < 0.10 and total >= 10:
        stats["niveau_drift"] = "SURVEILLANCE"
        stats["message_drift"] = "Peu d'opportunités détectées récemment. Vérifier la calibration."

    return stats


def _cle_apprentissage(sport, marche):
    """
    ✨ PRÉFIXAGE PAR SPORT — anti-contamination.
    Les calibrateurs, BMA et Copula apprennent sur ces clés,
    donc chaque sport a son propre apprentissage, isolé.
    """
    return "{}\u0001{}".format(sport or "inconnu", marche or "")


def recuperer_donnees_apprentissage():
    """
    Extrait les paires (proba_prédite, résultat) + poids temporel,
    AVEC PRÉFIXAGE PAR SPORT dans les clés.
    """
    historique = charger_historique()
    data = {}

    for h in historique:
        res = h.get("resultat")
        if not res:
            continue

        score_h = res.get("score_home", 0)
        score_a = res.get("score_away", 0)
        poids = _poids_temporel(h.get("date", ""))
        sport = h.get("sport", "inconnu")

        for reco in h.get("recommandations", []):
            marche = reco.get("marche", "")
            proba_str = str(reco.get("proba", "0%")).replace("%", "").strip()
            try:
                proba = float(proba_str) / 100
            except ValueError:
                continue
            if proba <= 0 or proba >= 1:
                continue

            outcome = 1 if _pari_gagne(
                marche, reco.get("selection", ""), score_h, score_a
            ) else 0

            cle = _cle_apprentissage(sport, marche)
            if cle not in data:
                data[cle] = {"xs": [], "ys": [], "ws": []}
            data[cle]["xs"].append(proba)
            data[cle]["ys"].append(outcome)
            data[cle]["ws"].append(poids)

    return data


def recuperer_donnees_bma():
    """
    Extrait les triplets (proba_marche, proba_poisson, proba_sharp,
    outcome, poids_temporel) pour chaque marché, AVEC PRÉFIXAGE PAR SPORT.
    """
    historique = charger_historique()
    data = {}

    for h in historique:
        res = h.get("resultat")
        if not res:
            continue

        score_h = res.get("score_home", 0)
        score_a = res.get("score_away", 0)
        poids = _poids_temporel(h.get("date", ""))
        sport = h.get("sport", "inconnu")

        for reco in h.get("recommandations", []):
            marche = reco.get("marche", "")
            outcome = 1 if _pari_gagne(
                marche, reco.get("selection", ""), score_h, score_a
            ) else 0

            pm = reco.get("proba_marche")
            pp = reco.get("proba_poisson")
            ps = reco.get("proba_sharp")

            if pm is None or pp is None or ps is None:
                continue

            try:
                pm = float(pm)
                pp = float(pp)
                ps = float(ps)
            except (ValueError, TypeError):
                continue

            cle = _cle_apprentissage(sport, marche)
            if cle not in data:
                data[cle] = {"marche": [], "poisson": [], "sharp": [], "y": [], "w": []}

            data[cle]["marche"].append(pm)
            data[cle]["poisson"].append(pp)
            data[cle]["sharp"].append(ps)
            data[cle]["y"].append(outcome)
            data[cle]["w"].append(poids)

    return data
