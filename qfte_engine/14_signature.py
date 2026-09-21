"""
Couche Ω — Signature HAMZY.
Empreinte unique + credo QFTE apposés sur chaque analyse.

Chaque prédiction porte une empreinte cryptographique SHA-256 calculée
à partir des données du match + timestamp + sel QFTE. Cette empreinte
garantit la traçabilité et l'unicité de chaque analyse.

© HAMZY · QFTE V23.0 · Couche Ω
"""
import hashlib
from datetime import datetime


CREDO = [
    "La discipline paie toujours plus que le talent.",
    "Une cote cohérente vaut mieux qu'un EV brillant.",
    "Le doute est un signal, pas une faiblesse.",
    "Le marché est un adversaire patient. Sois plus patient.",
    "Miser peu souvent, miser juste : voilà la règle.",
]


def _generer_empreinte(match, timestamp):
    """Empreinte SHA-256 unique à partir des données du match."""
    cle = "{}-{}-{}-{}-{}-{}-{}".format(
        match.get("equipe1", ""),
        match.get("equipe2", ""),
        match.get("competition", ""),
        match.get("cote_ferm_1", ""),
        match.get("cote_ferm_2", ""),
        match.get("volume", ""),
        timestamp,
    )
    sel = "QFTE-V23-HAMZY-OMEGA"
    return hashlib.sha256((cle + sel).encode("utf-8")).hexdigest()


def apposer_signature(data):
    """
    Couche Ω : appose une empreinte cryptographique + un credo
    tournant + un sceau visuel sur chaque analyse.
    """
    match = data.get("match", {})
    timestamp = datetime.now().isoformat()
    empreinte = _generer_empreinte(match, timestamp)

    # Sélection du credo tournant (basé sur les 8 premiers hex de l'empreinte)
    try:
        index = int(empreinte[:8], 16) % len(CREDO)
    except ValueError:
        index = 0

    data["signature"] = {
        "empreinte": empreinte,
        "empreinte_courte": empreinte[:12].upper(),
        "credo": CREDO[index],
        "auteur": "HAMZY",
        "version": "QFTE V23.0",
        "couche": "Ω",
        "timestamp": timestamp,
        "sceau": "🦁 HAMZY · QFTE V23.0 · Couche Ω",
    }
    return data
