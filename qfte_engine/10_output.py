def formater_recommandation(data):
    marches = data.get("marches", [])
    marches_tries = sorted(marches, key=lambda m: m.get("ev_net", 0), reverse=True)

    recos = []
    for m in marches_tries[:3]:
        recos.append({
            "niveau": m.get("niveau", "AVOID"),
            "marche": m.get("nom", "-"),
            "selection": m.get("selection", "-"),
            "proba": f"{round(float(m.get('proba_calibree', 0.0)) * 100, 1)}%",
            "cote": m.get("cote", "-"),
            "ev": f"{round(float(m.get('ev_net', 0.0)) * 100, 2)}%",
            "stake": f"{m.get('stake', 0.0)}%",
            "fiabilite": str(m.get("fiabilite", 0.0)),
        })

    data["recommandations"] = recos
    return data
