import importlib

_collect = importlib.import_module("qfte_engine.01_collect")
_normalize = importlib.import_module("qfte_engine.02_normalize")
_market = importlib.import_module("qfte_engine.03_market")
_sport = importlib.import_module("qfte_engine.04_sport")
_calibration = importlib.import_module("qfte_engine.05_calibration")
_scores = importlib.import_module("qfte_engine.06_scores")
_value = importlib.import_module("qfte_engine.07_value")
_risk = importlib.import_module("qfte_engine.08_risk")
_discipline = importlib.import_module("qfte_engine.09_discipline")
_output = importlib.import_module("qfte_engine.10_output")
_monitor = importlib.import_module("qfte_engine.11_monitor")


def analyser_match(match):
    data = _collect.collecter_donnees(match)
    data = _normalize.normaliser_donnees(data)
    data = _market.analyser_marche(data)
    data = _sport.analyser_sport(data)
    data = _calibration.calibrer_probabilites(data)
    data = _scores.predire_scores(data)
    data = _value.detecter_value(data)
    data = _risk.gerer_risques(data)
    data = _discipline.appliquer_discipline(data)
    data = _output.formater_recommandation(data)
    data = _monitor.surveiller(data)
    return data
