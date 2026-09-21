from qfte_engine.historique import sauvegarder_analyse


def surveiller(data):
    match = data.get("match", {})
    try:
        entree = sauvegarder_analyse(match, data)
        data["historique_ok"] = True
        data["analyse_id"] = entree.get("id", "")
    except Exception as e:
        data["historique_ok"] = False
        data["historique_erreur"] = str(e)
        data["analyse_id"] = ""
    return data
