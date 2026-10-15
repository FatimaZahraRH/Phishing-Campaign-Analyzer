#!/usr/bin/env python3
"""L'analyse retrouve-t-elle la vérité ? Validation sur données simulées.

On rejoue la simulation avec N graines différentes. Comme on CONNAÎT les vrais
paramètres, on peut mesurer :
  1. le piège du taux brut : combien de fois la comparaison début/fin conclut
     à tort à un progrès « significatif » (vraie tendance : aucune) ;
  2. la tendance à difficulté égale : faux positifs (doit rester proche de 5 %),
     modèle par employé contre test au niveau campagne ;
  3. l'effet de la formation (vrai OR 0,905) : estimation moyenne, couverture
     de l'IC 95 % avec et sans correction par employé, puissance ;
  4. la tendance du signalement (vraie hausse) : puissance.

  python scripts/validate.py --runs 200
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from phishcamp.analyze import model, naive_trend, per_campaign, trends  # noqa: E402
from phishcamp.simulate import simulate  # noqa: E402

def employee_level_trend(camps, emps, ev):
    """Ce qu'on ferait naïvement : tendance dans un modèle par employé
    (difficulté + n° de campagne), erreurs robustes par employé. Renvoie la p-valeur."""
    from phishcamp.phishscale import rate
    from phishcamp.stats import logistic
    idx = {c["id"]: i for i, c in enumerate(camps)}
    diff = {c["id"]: rate(c)["difficulty"] for c in camps}
    X = np.array([[1, diff[e["campaign"]] == "moderately", diff[e["campaign"]] == "very",
                   idx[e["campaign"]]] for e in ev], float)
    y = np.array([e["clicked"] for e in ev], float)
    r = logistic(X, y, ["c", "m", "v", "t"], clusters=[e["employee"] for e in ev])
    return r["t"]["p_value"]


ap = argparse.ArgumentParser()
ap.add_argument("--runs", type=int, default=200)
args = ap.parse_args()

camps = json.loads((ROOT / "campaigns" / "campaigns.json").read_text(encoding="utf-8"))
cfg = json.loads((ROOT / "config" / "simulation.json").read_text(encoding="utf-8"))
TRUE_OR = cfg["training_odds_ratio"]
# L'OR simulé est « individuel » (à susceptibilité égale). Une régression sans
# effet individuel estime l'OR « moyen de population », légèrement plus proche
# de 1 (approximation de Zeger et al., 1988).
_c = 16 * 3 ** 0.5 / (15 * np.pi)
PA_OR = float(np.exp(np.log(TRUE_OR) / np.sqrt(1 + _c ** 2 * cfg["individual_susceptibility_sd"] ** 2)))

naive_fp = trend_fp = trend_fp_emp = 0
cov_pa = cov_rob = cov_naive = signif_train = rep_detect = 0
ors = []
for seed in range(args.runs):
    emp, ev = simulate(camps, cfg, seed=10_000 + seed)
    emps = {e["employee"]: e for e in emp}
    rows = per_campaign(camps, ev)
    naive_fp += naive_trend(rows)["p_value"] < 0.05
    m = model(camps, emps, ev)
    trend_fp_emp += employee_level_trend(camps, emps, ev) < 0.05
    tr = trends(rows)
    trend_fp += tr["click"]["p_value"] < 0.05
    f, fn = m["robust"]["formation"], m["naive"]["formation"]
    ors.append(f["or"])
    cov_rob += f["or_ci"][0] <= TRUE_OR <= f["or_ci"][1]
    cov_naive += fn["or_ci"][0] <= TRUE_OR <= fn["or_ci"][1]
    cov_pa += f["or_ci"][0] <= PA_OR <= f["or_ci"][1]
    signif_train += f["or_ci"][1] < 1
    rep_detect += tr["report"]["or_ci"][0] > 1
    print(f"\r{seed + 1}/{args.runs}", end="", file=sys.stderr)
print(file=sys.stderr)

n = args.runs
res = {
    "runs": n,
    "raw_trend_declared_significant": naive_fp / n,
    "adjusted_trend_false_positive_employee_model": trend_fp_emp / n,
    "adjusted_trend_false_positive_campaign_level": trend_fp / n,
    "training_true_or": TRUE_OR,
    "training_mean_estimated_or": float(np.exp(np.mean(np.log(ors)))),
    "training_ci_coverage_robust": cov_rob / n,
    "training_ci_coverage_naive": cov_naive / n,
    "training_population_averaged_or": PA_OR,
    "training_ci_coverage_robust_vs_pa": cov_pa / n,
    "training_power": signif_train / n,
    "report_trend_power": rep_detect / n,
}
(ROOT / "report" / "validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
