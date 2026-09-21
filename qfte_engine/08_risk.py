def gerer_risques(data):
    stake_brut = float(data.get("stake_brut", 0.0))
    fiabilite = float(data.get("fiabilite", 0.75))

    # Kelly fractionné adaptatif : λ varie avec la fiabilité
    # fiabilité 0.75 → λ = 0.25 (prudent)
    # fiabilité 0.95 → λ = 0.50 (plus agressif)
    lambda_kelly = 0.25 + (fiabilite - 0.75) * (0.25 / 0.20)
    lambda_kelly = max(0.20, min(0.50, lambda_kelly))

    stake_final = stake_brut * lambda_kelly

    # Plafond strict : 1.5% de la bankroll
    stake_final = min(1.5, stake_final)
    stake_final = round(stake_final, 2)

    data["stake"] = stake_final
    data["lambda_kelly"] = round(lambda_kelly, 4)
    return data
