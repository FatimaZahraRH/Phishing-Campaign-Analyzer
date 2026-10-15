#!/usr/bin/env python3
"""Analyse data/ et produit report/report_fr.md, report/report_en.md et les figures.

L'analyse ne lit QUE les événements et la description des campagnes ;
elle ignore tout des paramètres de simulation.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from phishcamp.analyze import analyze, load  # noqa: E402
from phishcamp.i18n import landing_page  # noqa: E402
from phishcamp.report import figures, markdown  # noqa: E402

camps, emps, events = load(ROOT / "data", ROOT / "campaigns" / "campaigns.json")
a = analyze(camps, emps, events)
for lang in ("fr", "en"):
    figures(a, events, ROOT / "report" / "figures", lang)
    (ROOT / "report" / f"report_{lang}.md").write_text(markdown(a, lang), encoding="utf-8")
for c in camps:
    for lang in ("fr", "en"):
        (ROOT / "i18n" / f"{c['id']}_{lang}.md").write_text(landing_page(c, lang),
                                                          encoding="utf-8")
summary = {"naive_trend": a["naive_trend"], "training": a["training"],
           "trends": a["trends"], "model": a["model"]["robust"], "repeat": a["repeat"]}
(ROOT / "report" / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False,
                                                         default=str), encoding="utf-8")
print("report/report_fr.md, report/report_en.md, report/figures/, i18n/")
