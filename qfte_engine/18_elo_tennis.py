"""
Module Elo Tennis — QFTE V23.0.

Système de classement Elo adapté au tennis, avec :
- Elo global par joueur
- Elo par surface (terre, gazon, dur, indoor)
- K-factor adaptatif selon le tournoi
- Mise à jour automatique après chaque match
- Blending avec la cote bookmaker

Inspiré de : FiveThirtyEight, Jeff Sackmann (Tennis Abstract),
et des travaux sur les systèmes Elo par surface.

Pur Python — aucune dépendance externe.
"""
import json
import os
import math

FICHIER_ELO = "elo_tennis.json"

ELO_INITIAL = 1500.0
ELO_MIN = 1000.0
ELO_MAX = 2400.0

# K-factor selon le type de tournoi
K_FACTORS = {
    "grand chelem": 50,
    "masters 1000": 40,
    "atp 500": 35,
    "atp 250": 32,
    "wta 1000": 40,
    "wta 500": 35,
    "wta 250": 32,
    "atp finals": 45,
    "default": 32,
}

# Surfaces reconnues
SURFACES = ["terre", "gazon", "dur", "indoor"]


# ============================================================
# CHARGEMENT / SAUVEGARDE
# ============================================================
def _charger_elo():
    """
    Charge la base Elo depuis le fichier JSON.
    Structure :
    {
        "nadal": {
            "global": 2050,
            "terre": 2200,
            "gazon": 1750,
            "dur": 1950,
            "indoor": 1850,
            "matchs": 450
        },
        ...
    }
    """
    if not os.path.exists(FICHIER_ELO):
        return {}
    try:
        with open(FICHIER_ELO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _ecrire_elo(data):
    try:
        with open(FICHIER_ELO, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def _normaliser_nom(nom):
    """Normalise le nom du joueur (lowercase, sans espaces superflus)."""
    if not nom:
        return ""
    return str(nom).lower().strip()


def _cle_surface(surface):
    """Normalise la surface saisie."""
    if not surface:
        return "dur"
    s = str(surface).lower().strip()
    if "terre" in s or "clay" in s or "roland" in s:
        return "terre"
    if "gazon" in s or "grass" in s or "wimbledon" in s:
        return "gazon"
    if "indoor" in s or "paris" in s or "bercy" in s or "final" in s:
        return "indoor"
    return "dur"


def get_joueur(nom):
    """Retourne le profil Elo d'un joueur (créé si absent)."""
    elo = _charger_elo()
    cle = _normaliser_nom(nom)
    if not cle:
        return {
            "global": ELO_INITIAL,
            "terre": ELO_INITIAL,
            "gazon": ELO_INITIAL,
            "dur": ELO_INITIAL,
            "indoor": ELO_INITIAL,
            "matchs": 0,
        }
    if cle not in elo:
        return {
            "global": ELO_INITIAL,
            "terre": ELO_INITIAL,
            "gazon": ELO_INITIAL,
            "dur": ELO_INITIAL,
            "indoor": ELO_INITIAL,
            "matchs": 0,
        }
    return elo[cle]


def _get_k_factor(competition):
    """Détecte le K-factor selon le tournoi."""
    comp = (competition or "").lower()
    for nom, k in K_FACTORS.items():
        if nom in comp:
            return k
    return K_FACTORS["default"]
