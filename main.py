from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from qfte_engine.pipeline import analyser_match
from qfte_engine.historique import (
    charger_historique,
    calculer_statistiques,
    calculer_roi,
    enregistrer_resultat,
)

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def accueil(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/analyser", response_class=HTMLResponse)
async def analyser(
    request: Request,
    sport: str = Form(...),
    competition: str = Form(...),
    equipe1: str = Form(...),
    equipe2: str = Form(...),
    cote_ouverture: float = Form(...),
    cote_actuelle: float = Form(...),
    cote_ah: float = Form(...),
    cote_over25: float = Form(...),
    cote_btts: float = Form(...),
    volume: int = Form(...),
):
    match = {
        "sport": sport,
        "competition": competition,
        "equipe1": equipe1,
        "equipe2": equipe2,
        "cote_ouverture": cote_ouverture,
        "cote_actuelle": cote_actuelle,
        "cote_ah": cote_ah,
        "cote_over25": cote_over25,
        "cote_btts": cote_btts,
        "volume": volume,
    }

    resultat = analyser_match(match)

    return templates.TemplateResponse(
        request,
        "resultats.html",
        {
            "match": match,
            "recommandations": resultat.get("recommandations", []),
            "decision": resultat.get("decision", "-"),
            "message_discipline": resultat.get("message_discipline", ""),
            "top_ht_score": resultat.get("top_ht_score", {}),
            "top_2_scores": resultat.get("top_2_scores", []),
            "lambda_home": resultat.get("lambda_home", "-"),
            "lambda_away": resultat.get("lambda_away", "-"),
            "validation": resultat.get("validation", {}),
            "analyse_id": resultat.get("analyse_id", ""),
        },
    )


@app.post("/resultat")
async def enregistrer(
    analyse_id: str = Form(...),
    score_home: int = Form(...),
    score_away: int = Form(...),
    marches: str = Form(""),
):
    marches_joues = [m for m in marches.split("|") if m]
    enregistrer_resultat(analyse_id, score_home, score_away, marches_joues)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = calculer_statistiques()
    roi = calculer_roi()
    historique = charger_historique()
    dernieres = list(reversed(historique[-20:]))

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "roi": roi,
            "dernieres": dernieres,
        },
    )
