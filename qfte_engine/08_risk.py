def gerer_risques(data):
    marches = data.get("marches", [])
    resultat = []

    for m in marches:
        stake_brut = float(m.get("stake_brut", 0.0))
        fiabilite = float(m.get("fiabilite", 0.75))

        lambda_kelly = 0.25 + (fiabilite - 0.75) * (0.25 / 0.20)
        lambda_kelly = max(0.20, min(0.50, lambda_kelly))

        stake_final = stake_brut * lambda_kelly
        stake_final = min(1.5, stake_final)

        m["stake"] = round(stake_final, 2)
        m["lambda_kelly"] = round(lambda_kelly, 4)
        resultat.append(m)

    data["marches"] = resultat
    return data
