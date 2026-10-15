"""Analyse des résultats de campagnes : ce qu'une équipe sécurité doit savoir.

Principes :
  1. Pas de taux sans intervalle de confiance.
  2. Pas de comparaison entre campagnes sans tenir compte de leur DIFFICULTÉ
     (NIST Phish Scale) : sinon une campagne facile passe pour un progrès.
  3. Le signalement compte autant que le clic (Lain et al., 2022) : on mesure
     le taux de signalement, sa vitesse, et le rapport signalements / clics.
  4. L'effet d'une formation se mesure contre un groupe témoin, avec la
     puissance statistique en face (Ho et al., 2025).
  5. Confidentialité : aucun résultat individuel publié ; un groupe de moins de
     MIN_GROUP personnes n'est jamais affiché.
"""
from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .phishscale import rate
from .stats import (Z95, campaign_level_trend, clustered_rate, logistic, norm_cdf, sample_size_two_proportions,
                    two_proportions, wilson)

MIN_GROUP = 10
DIFF_ORDER = ["least", "moderately", "very"]


def load(data_dir: Path, campaigns_file: Path):
    campaigns = __import__("json").loads(campaigns_file.read_text(encoding="utf-8"))
    with open(data_dir / "employees.csv", encoding="utf-8") as f:
        employees = {r["employee"]: r for r in csv.DictReader(f)}
    with open(data_dir / "events.csv", encoding="utf-8") as f:
        events = list(csv.DictReader(f))
    for e in events:
        for k in ("clicked", "submitted", "reported"):
            e[k] = int(e[k])
        for k in ("click_delay_min", "report_delay_min"):
            e[k] = float(e[k]) if e[k] != "" else None
    return campaigns, employees, events


def _rate(k, n):
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": p, "ci": (lo, hi)}


def per_campaign(campaigns, events):
    by = defaultdict(list)
    for e in events:
        by[e["campaign"]].append(e)
    rows = []
    for c in campaigns:
        ev = by[c["id"]]
        n = len(ev)
        clicks = sum(e["clicked"] for e in ev)
        reports = sum(e["reported"] for e in ev)
        delays = sorted(e["report_delay_min"] for e in ev if e["reported"])
        r = rate(c)
        rows.append({
            "id": c["id"], "month": c["month"], "theme_fr": c["theme_fr"],
            "theme_en": c["theme_en"], "difficulty": r["difficulty"], "phishscale": r,
            "click": _rate(clicks, n), "submit": _rate(sum(e["submitted"] for e in ev), n),
            "report": _rate(reports, n),
            "reports_per_click": reports / clicks if clicks else float("inf"),
            "first_report_min": delays[0] if delays else None,
            "median_report_min": float(np.median(delays)) if delays else None,
            "reports_within_5": sum(d <= 5 for d in delays) / len(delays) if delays else 0,
            "reports_within_30": sum(d <= 30 for d in delays) / len(delays) if delays else 0,
        })
    return rows


def naive_trend(rows):
    """Ce qu'on conclurait en regardant seulement le taux brut : début vs fin."""
    first, last = rows[:3], rows[-3:]
    k1, n1 = sum(r["click"]["k"] for r in first), sum(r["click"]["n"] for r in first)
    k2, n2 = sum(r["click"]["k"] for r in last), sum(r["click"]["n"] for r in last)
    t = two_proportions(k1, n1, k2, n2)
    return {"first": k1 / n1, "last": k2 / n2, "first_ids": [r["id"] for r in first],
            "last_ids": [r["id"] for r in last], **t}


def model(campaigns, employees, events):
    """Clic ~ effets fixes campagne + formation + service (niveau employé).

    Les effets fixes « campagne » absorbent tout ce qui est propre à une
    campagne (difficulté, aléa du jour) : la formation et le service sont
    comparés À L'INTÉRIEUR de chaque campagne. Erreurs standard robustes par
    employé. La difficulté et la tendance, elles, se testent au niveau
    campagne (voir trends()).
    """
    ids = [c["id"] for c in campaigns]
    idx = {c: i for i, c in enumerate(ids)}
    depts = sorted({e["department"] for e in employees.values()})
    ref_dept = Counter(e["department"] for e in employees.values()).most_common(1)[0][0]
    other = [d for d in depts if d != ref_dept]
    names = ["constante"] + [f"campagne : {c}" for c in ids[1:]] + ["formation"] \
        + [f"service : {d}" for d in other]
    X, y, cl = [], [], []
    for e in events:
        emp = employees[e["employee"]]
        c = e["campaign"]
        trained = emp["group"] == "formation" and idx[c] > 0
        X.append([1] + [c == k for k in ids[1:]] + [trained]
                 + [emp["department"] == d for d in other])
        y.append(e["clicked"])
        cl.append(e["employee"])
    X, y = np.array(X, float), np.array(y, float)
    return {"reference_department": ref_dept,
            "robust": logistic(X, y, names, clusters=cl),
            "naive": logistic(X, y, names)}


def trends(rows):
    """Tendances du clic et du signalement, à difficulté égale, testées par campagne."""
    diff = [r["difficulty"] for r in rows]
    return {
        "click": campaign_level_trend([(r["click"]["k"], r["click"]["n"]) for r in rows], diff),
        "report": campaign_level_trend([(r["report"]["k"], r["report"]["n"]) for r in rows],
                                       diff),
    }


def training_effect(campaigns, employees, events):
    """Groupe formé vs témoin, sur les campagnes qui suivent la 1re.

    Intervalles robustes par employé (les deux groupes sont des personnes
    différentes, donc indépendants entre eux, mais pas en leur sein).
    """
    after = {c["id"] for c in campaigns[1:]}
    ev = [e for e in events if e["campaign"] in after]
    res, var = {}, {}
    for g in ("formation", "témoin"):
        sub = [e for e in ev if employees[e["employee"]]["group"] == g]
        res[g] = _clustered(sub, "clicked")
        var[g] = ((res[g]["ci"][1] - res[g]["ci"][0]) / (2 * Z95)) ** 2
    diff = res["formation"]["rate"] - res["témoin"]["rate"]
    se = math.sqrt(var["formation"] + var["témoin"])
    p_ctrl = res["témoin"]["rate"]
    # Taille d'échantillon pour détecter l'effet rapporté par Ho et al. (-1,7 pt),
    # en supposant des observations indépendantes : c'est donc un MINIMUM.
    needed = sample_size_two_proportions(p_ctrl, max(1e-4, p_ctrl - 0.017))
    return {"formation": res["formation"], "témoin": res["témoin"], "diff": diff,
            "ci": (diff - Z95 * se, diff + Z95 * se),
            "p_value": 2 * (1 - norm_cdf(abs(diff / se))) if se else float("nan"),
            "obs_per_group": min(r["n"] for r in res.values()),
            "needed_per_group_for_1_7pt": needed}


def departments(employees, events):
    by = defaultdict(list)
    for e in events:
        by[employees[e["employee"]]["department"]].append(e)
    head = Counter(e["department"] for e in employees.values())
    org_click = sum(e["clicked"] for e in events) / len(events)
    org_rep = sum(e["reported"] for e in events) / len(events)
    rows = []
    for d, ev in sorted(by.items()):
        if head[d] < MIN_GROUP:
            rows.append({"department": d, "headcount": head[d], "suppressed": True})
            continue
        c, r = _clustered(ev, "clicked"), _clustered(ev, "reported")
        rows.append({"department": d, "headcount": head[d], "suppressed": False,
                     "click": c, "report": r,
                     "click_above_org": c["ci"][0] > org_click,
                     "report_below_org": r["ci"][1] < org_rep})
    return {"org_click": org_click, "org_report": org_rep, "rows": rows}


def _clustered(ev, field):
    k, n = defaultdict(int), defaultdict(int)
    for x in ev:
        k[x["employee"]] += x[field]
        n[x["employee"]] += 1
    keys = sorted(n)
    p, lo, hi = clustered_rate([k[i] for i in keys], [n[i] for i in keys])
    return {"k": sum(k.values()), "n": sum(n.values()), "rate": p, "ci": (lo, hi)}


def repeat_behaviour(events):
    """Répartition agrégée : combien d'employés ont cliqué 0, 1, 2, 3+ fois."""
    per = Counter()
    emps = set()
    for e in events:
        emps.add(e["employee"])
        per[e["employee"]] += e["clicked"]
    dist = Counter(min(v, 3) for v in (per[x] for x in emps))
    total_clicks = sum(per.values())
    heavy = sum(v for v in per.values() if v >= 3)
    return {"employees": len(emps), "distribution": {k: dist.get(k, 0) for k in range(4)},
            "clicked_at_least_once": sum(1 for x in emps if per[x] > 0) / len(emps),
            "share_clicks_from_3plus": heavy / total_clicks if total_clicks else 0}


def analyze(campaigns, employees, events) -> dict:
    rows = per_campaign(campaigns, events)
    return {"campaigns": rows, "naive_trend": naive_trend(rows), "trends": trends(rows),
            "model": model(campaigns, employees, events),
            "training": training_effect(campaigns, employees, events),
            "departments": departments(employees, events),
            "repeat": repeat_behaviour(events)}
