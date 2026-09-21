# 🦁 QFTE V23.0 — Bot d'analyse sportive

Bot web en Python (FastAPI) qui exécute le pipeline QFTE V23.0 (11 étapes) et renvoie 3 recommandations de paris classées par fiabilité.

## 🚀 Déploiement

- **Build** : `pip install -r requirements.txt`
- **Start** : `uvicorn main:app --host 0.0.0.0 --port $PORT`

## 📁 Structure

- `main.py` — Application FastAPI
- `templates/` — Pages HTML (formulaire + résultats)
- `qfte_engine/` — Pipeline à 11 étapes
- `sports/` — Modules sport (à venir)
