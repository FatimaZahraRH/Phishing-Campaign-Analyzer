"""Génère les résultats d'une série de campagnes d'entraînement.

Aucune donnée réelle de campagne n'est publique (et c'est normal : ce sont
des données personnelles d'employés). On simule donc les événements avec un
modèle explicite dont les paramètres viennent des études (config/simulation.json).

Intérêt méthodologique : comme on connaît la « vérité », on peut vérifier que
l'analyse la retrouve (scripts/validate.py). Une méthode qui ne retrouve pas
un effet connu sur des données simulées ne mérite pas confiance sur des
données réelles.
"""
from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

import numpy as np

from .phishscale import rate

FIELDS = ["employee", "campaign", "clicked", "submitted", "reported",
          "click_delay_min", "report_delay_min"]


def _logit(p):
    return math.log(p / (1 - p))


def _expit(x):
    return 1 / (1 + np.exp(-x))


def simulate(campaigns: list[dict], cfg: dict, seed: int | None = None):
    rng = np.random.default_rng(cfg["seed"] if seed is None else seed)
    n = cfg["n_employees"]
    depts = list(cfg["departments"])
    dept = rng.choice(depts, size=n, p=np.array(list(cfg["departments"].values())))
    group = np.where(rng.random(n) < cfg["training_share"], "formation", "témoin")
    suscept = rng.normal(0, cfg["individual_susceptibility_sd"], n)
    salt = str(cfg["seed"] if seed is None else seed)
    ids = [("E" + hashlib.sha256(f"{salt}-{i}".encode()).hexdigest()[:8]) for i in range(n)]
    off = np.array([cfg["department_logit_offset"][d] for d in dept])
    log_or = math.log(cfg["training_odds_ratio"])

    employees = [{"employee": ids[i], "department": dept[i], "group": group[i]}
                 for i in range(n)]
    events = []
    for c_idx, c in enumerate(campaigns):
        diff = rate(c)["difficulty"]
        base = _logit(cfg["click_rate_by_difficulty"][diff]) \
            + rng.normal(0, cfg["campaign_logit_jitter_sd"])
        trained = (group == "formation") & (c_idx > 0)   # formation après la 1re campagne
        p_click = _expit(base + suscept + off + log_or * trained)
        clicked = rng.random(n) < p_click
        submitted = clicked & (rng.random(n) < cfg["submit_given_click"])
        p_rep = (cfg["report_rate_first_campaign"]
                 + cfg["report_rate_gain_per_campaign"] * c_idx) \
            * cfg["report_multiplier_by_difficulty"][diff]
        p_rep = np.where(clicked, p_rep * cfg["report_multiplier_if_clicked"], p_rep)
        reported = rng.random(n) < p_rep
        cdel = rng.lognormal(math.log(cfg["click_delay_median_min"]), cfg["click_delay_sigma"], n)
        # Un signalement arrive au plus tard 3 jours après l'envoi (fin d'exercice).
        rdel = np.minimum(rng.lognormal(math.log(cfg["report_delay_median_min"]),
                                        cfg["report_delay_sigma"], n), 4320)
        for i in range(n):
            events.append({"employee": ids[i], "campaign": c["id"],
                           "clicked": int(clicked[i]), "submitted": int(submitted[i]),
                           "reported": int(reported[i]),
                           "click_delay_min": round(float(cdel[i]), 1) if clicked[i] else "",
                           "report_delay_min": round(float(rdel[i]), 1) if reported[i] else ""})
    return employees, events


def write(employees, events, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "employees.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["employee", "department", "group"])
        w.writeheader()
        w.writerows(employees)
    with open(out / "events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(events)
