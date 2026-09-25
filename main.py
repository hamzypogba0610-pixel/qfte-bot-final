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
    surface: str = Form("dur"),
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
    cote_btts: float = Form(0.0),
    volume: int = Form(...),
    # Champs tennis
    matchs_7j_j1: int = Form(0),
    matchs_7j_j2: int = Form(0),
    matchs_14j_j1: int = Form(0),
    matchs_14j_j2: int = Form(0),
    # Champs calendrier football / hockey
    matchs_7j_dom: int = Form(0),
    matchs_14j_dom: int = Form(0),
    jours_repos_dom: int = Form(7),
    competition_suivante_dom: str = Form(""),
    jours_avant_suivant_dom: int = Form(7),
    matchs_7j_ext: int = Form(0),
    matchs_14j_ext: int = Form(0),
    jours_repos_ext: int = Form(7),
    competition_suivante_ext: str = Form(""),
    jours_avant_suivant_ext: int = Form(7),
    # Champs calendrier basket
    jours_repos_dom_basket: int = Form(2),
    matchs_4j_dom_basket: int = Form(0),
    voyage_long_dom_basket: str = Form(""),
    back_to_back_dom_basket: str = Form(""),
    jours_repos_ext_basket: int = Form(2),
    matchs_4j_ext_basket: int = Form(0),
    voyage_long_ext_basket: str = Form(""),
    back_to_back_ext_basket: str = Form(""),
):
    match = {
        "sport": sport,
        "competition": competition,
        "equipe1": equipe1,
        "equipe2": equipe2,
        "surface": surface,
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
        "matchs_7j_j1": matchs_7j_j1,
        "matchs_7j_j2": matchs_7j_j2,
        "matchs_14j_j1": matchs_14j_j1,
        "matchs_14j_j2": matchs_14j_j2,
        "matchs_7j_dom": matchs_7j_dom,
        "matchs_14j_dom": matchs_14j_dom,
        "jours_repos_dom": jours_repos_dom,
        "competition_suivante_dom": competition_suivante_dom,
        "jours_avant_suivant_dom": jours_avant_suivant_dom,
        "matchs_7j_ext": matchs_7j_ext,
        "matchs_14j_ext": matchs_14j_ext,
        "jours_repos_ext": jours_repos_ext,
        "competition_suivante_ext": competition_suivante_ext,
        "jours_avant_suivant_ext": jours_avant_suivant_ext,
        "jours_repos_dom_basket": jours_repos_dom_basket,
        "matchs_4j_dom_basket": matchs_4j_dom_basket,
        "voyage_long_dom_basket": bool(voyage_long_dom_basket),
        "back_to_back_dom_basket": bool(back_to_back_dom_basket),
        "jours_repos_ext_basket": jours_repos_ext_basket,
        "matchs_4j_ext_basket": matchs_4j_ext_basket,
        "voyage_long_ext_basket": bool(voyage_long_ext_basket),
        "back_to_back_ext_basket": bool(back_to_back_ext_basket),
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
            "auto_ou": resultat.get("auto_ou", {}),
            "copula_correlations": resultat.get("copula_correlations", {}),
            "copula_correlations_apprises": resultat.get("copula_correlations_apprises", 0),
            "copula_sport": resultat.get("copula_sport", ""),
            "attention": resultat.get("attention", {}),
            "bma_actif": resultat.get("bma_actif", False),
            "basket_config": resultat.get("basket_config", {}),
            "tennis_config": resultat.get("tennis_config", {}),
            "hockey_config": resultat.get("hockey_config", {}),
            "hockey_periodes": resultat.get("hockey_periodes", {}),
            "hockey_scores_periodes": resultat.get("hockey_scores_periodes", {}),
            "elo_info": resultat.get("elo_info", {}),
            "blend_info": resultat.get("blend_info", {}),
            "momentum_info": resultat.get("momentum_info", {}),
            "fatigue_info": resultat.get("fatigue_info", {}),
            "calendrier": resultat.get("calendrier", {}),
            "impact_calendrier_lambda": resultat.get("impact_calendrier_lambda", {}),
            "calendrier_basket": resultat.get("calendrier_basket", {}),
            "impact_calendrier_basket": resultat.get("impact_calendrier_basket", {}),
            "stats_avancees": resultat.get("stats_avancees", {}),
            "aura": resultat.get("aura", {}),
            "oracle": resultat.get("oracle", {}),
            "chronos": resultat.get("chronos", {}),
            "instinct": resultat.get("instinct", {}),
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
