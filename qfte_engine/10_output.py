def formater_recommandation(data):
    match = data.get("match", {})

    reco = {
        "niveau": data.get("niveau", "AVOID"),
        "marche": "1X2 - Domicile",
        "selection": match.get("equipe1", "-"),
        "proba": f"{round(float(data.get('proba_calibree', 0.0)) * 100, 1)}%",
        "cote": data.get("cote", "-"),
        "ev": f"{round(float(data.get('ev_net', 0.0)) * 100, 2)}%",
        "stake": f"{data.get('stake', 0.0)}%",
        "fiabilite": str(data.get("fiabilite", 0.0)),
    }

    data["recommandation_finale"] = reco
    return data
