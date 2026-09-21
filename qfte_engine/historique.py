import json
import os
from datetime import datetime

FICHIER_HISTORIQUE = "historique.json"


def charger_historique():
    if not os.path.exists(FICHIER_HISTORIQUE):
        return []
    try:
        with open(FICHIER_HISTORIQUE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def sauvegarder_analyse(match, resultat):
    historique = charger_historique()

    reco_principale = {}
    recos = resultat.get("recommandations", [])
    if recos:
        reco_principale = recos[0]

    entree = {
        "date": datetime.now().isoformat(),
        "sport": match.get("sport", "-"),
        "competition": match.get("competition", "-"),
        "equipe1": match.get("equipe1", "-"),
        "equipe2": match.get("equipe2", "-"),
        "cotes": {
            "ouverture": match.get("cote_ouverture"),
            "actuelle": match.get("cote_actuelle"),
            "ah": match.get("cote_ah"),
            "over25": match.get("cote_over25"),
            "btts": match.get("cote_btts"),
        },
        "decision": resultat.get("decision", "-"),
        "meilleure_reco": reco_principale,
        "lambda_home": resultat.get("lambda_home"),
        "lambda_away": resultat.get("lambda_away"),
    }

    historique.append(entree)

    try:
        with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except IOError:
        pass

    return entree


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

    # Détection simple de dérive : ratio ATTAQUE / total
    total_attaques = (
        stats["par_decision"].get("ATTAQUE FORTE", 0)
        + stats["par_decision"].get("ATTAQUE", 0)
    )
    ratio_attaques = total_attaques / total

    if ratio_attaques < 0.05 and total >= 10:
        stats["niveau_drift"] = "CRITIQUE"
        stats["message_drift"] = (
            "Aucune opportunité détectée sur les 10 dernières analyses. "
            "Modèle trop strict ou dérive."
        )
    elif ratio_attaques < 0.10 and total >= 10:
        stats["niveau_drift"] = "SURVEILLANCE"
        stats["message_drift"] = (
            "Peu d'opportunités détectées récemment. Vérifier la calibration."
        )

    return stats
