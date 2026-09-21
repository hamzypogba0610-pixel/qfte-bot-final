from qfte_engine.historique import sauvegarder_analyse


def surveiller(data):
    match = data.get("match", {})
    try:
        sauvegarder_analyse(match, data)
        data["historique_ok"] = True
    except Exception as e:
        data["historique_ok"] = False
        data["historique_erreur"] = str(e)
    return data
