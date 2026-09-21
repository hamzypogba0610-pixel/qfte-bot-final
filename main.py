from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from qfte_engine.pipeline import analyser_match

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
    volume: int = Form(...),
):
    match = {
        "sport": sport,
        "competition": competition,
        "equipe1": equipe1,
        "equipe2": equipe2,
        "cote_ouverture": cote_ouverture,
        "cote_actuelle": cote_actuelle,
        "volume": volume,
    }

    _ = analyser_match(match)

    recommandations = [
        {
            "niveau": "ELITE",
            "marche": "1X2 - Domicile",
            "selection": equipe1,
            "proba": "58%",
            "cote": cote_actuelle,
            "ev": "+6.2%",
            "stake": "1.5%",
            "fiabilite": "0.82",
        },
        {
            "niveau": "PREMIUM",
            "marche": "Over/Under 2.5",
            "selection": "Over 2.5",
            "proba": "54%",
            "cote": "1.95",
            "ev": "+5.3%",
            "stake": "1.0%",
            "fiabilite": "0.78",
        },
        {
            "niveau": "GOOD",
            "marche": "BTTS",
            "selection": "Oui",
            "proba": "52%",
            "cote": "1.90",
            "ev": "+4.8%",
            "stake": "0.8%",
            "fiabilite": "0.76",
        },
    ]

    return templates.TemplateResponse(
        request,
        "resultats.html",
        {
            "match": match,
            "recommandations": recommandations,
        },
    )
