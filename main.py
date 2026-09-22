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
    cote_ouv_1: float = Form(...),
    cote_ferm_1: float = Form(...),
    cote_ouv_2: float = Form(...),
    cote_ferm_2: float = Form(...),
    forme_dom_5: str = Form(""),
    scores_dom_5: str = Form(""),
    forme_dom_glob_5: str = Form(""),
    scores_dom_glob_5: str = Form(""),
    forme_ext_5: str = Form(""),
    scores_ext_5: str = Form(""),
    forme_ext_glob_5: str = Form(""),
    scores_ext_glob_5: str = Form(""),
    h2h_5: str = Form(""),
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
        "cote_ouverture": cote_ouv_1,
        "cote_actuelle": cote_ferm_1,
        "cote_ouv_2": cote_ouv_2,
        "cote_ferm_2": cote_ferm_2,
        "cote_ah": cote_ah,
        "cote_over25": cote_over25,
        "cote_btts": cote_btts,
        "volume": volume,
        "forme_dom_5": forme_dom_5,
        "scores_dom_5": scores_dom_5,
        "forme_dom_glob_5": forme_dom_glob_5,
        "scores_dom_glob_5": scores_dom_glob_5,
        "forme_ext_5": forme_ext_5,
        "scores_ext_5": scores_ext_5,
        "forme_ext_glob_5": forme_ext_glob_5,
        "scores_ext_glob_5": scores_ext_glob_5,
        "h2h_5": h2h_5,
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
            "marge_estimee": resultat.get("marge_estimee", "-"),
            "total_buts_comp": resultat.get("total_buts_comp", "-"),
            "contexte": resultat.get("contexte", {}),
            "modele_lambda": resultat.get("modele_lambda", "-"),
            "signature": resultat.get("signature", {}),
            "seuils_amplifies": resultat.get("seuils_amplifies", {}),
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
