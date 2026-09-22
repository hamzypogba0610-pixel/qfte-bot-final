import json
import os
import math
from datetime import datetime

FICHIER_HISTORIQUE = "historique.json"
BANKROLL_DEPART = 1000.0
DEMI_VIE_JOURS = 30.0  # Time-decay : match d'il y a 30j = poids 0.5


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
    """
    Time-decay : retourne un poids entre 0 et 1 selon la récence.
    poids = exp(-âge_jours / demi_vie)
      - Match du jour     → 1.00
      - Match il y a 30j  → 0.37
      - Match il y a 90j  → 0.05
    """
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

    if "Handicap" in marche:
        return score_home > score_away

    if "Over/Under 2.5" in marche or ("2.5" in marche and "Total" not in marche):
        if "under" in selection:
            return total < 2.5
        else:
            return total > 2.5

    if "BTTS" in marche:
        return score_home >= 1 and score_away >= 1

    if "Money Line" in marche:
        return score_home > score_away

    if "Spread" in marche:
        return (score_home - score_away) > 4.5

    if "Total Points" in marche:
        if "under" in selection:
            return total < 180.5
        return total > 180.5

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
            return h

    return None


def calculer_roi():
    """ROI calculé à parts égales (pas de time-decay) — mesure la réalité."""
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


def recuperer_donnees_apprentissage():
    """
    Extrait les paires (proba_prédite, résultat) + un POIDS TEMPOREL
    pour chaque marché à partir des analyses passées ayant un résultat.
    Utilisé pour entraîner les calibrateurs avec time-decay.
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

            if marche not in data:
                data[marche] = {"xs": [], "ys": [], "ws": []}
            data[marche]["xs"].append(proba)
            data[marche]["ys"].append(outcome)
            data[marche]["ws"].append(poids)

    return data
