"""Rapport au RSSI, en français et en anglais, avec figures."""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .actions import recommendations  # noqa: E402
from .analyze import MIN_GROUP  # noqa: E402
from .phishscale import LABEL_EN, LABEL_FR  # noqa: E402

# Palette catégorielle validée (3 premiers créneaux, contrôle daltonisme OK).
# L'aqua est sous 3:1 de contraste : étiquettes directes + tableau dans le rapport.
COLORS = {"least": "#1baf7a", "moderately": "#2a78d6", "very": "#eb6834"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

DEPT_EN = {"Audit": "Audit", "Conseil": "Consulting", "Finance": "Finance", "RH": "HR",
           "IT": "IT", "Juridique": "Legal", "Direction": "Management"}

T = {
    "fr": {
        "title": "Analyse des campagnes de phishing d'entraînement",
        "lead": "Rapport au RSSI. Données simulées (voir docs/simulation.md) ; aucun résultat "
                "individuel n'est publié.",
        "summary": "Ce qu'il faut retenir", "actions": "Actions correctives",
        "campaigns": "Résultats par campagne",
        "cols": "| Campagne | Mois | Thème | Difficulté (Phish Scale) | Clic | Saisie d'identifiants "
                "| Signalement | Signalements / clic | Signalements < 30 min |",
        "trend": "Le piège du taux brut", "model": "Analyse à difficulté égale",
        "training": "La formation après clic marche-t-elle ?", "dept": "Par service",
        "repeat": "Combien d'employés cliquent ?",
        "fig_click": "Taux de clic par campagne (IC 95 %), couleur = difficulté",
        "fig_report": "Taux de signalement par campagne (IC 95 %)",
        "fig_delay": "Délai de signalement (toutes campagnes)",
        "x_campaign": "Campagne", "y_click": "Taux de clic", "y_report": "Taux de signalement",
        "x_delay": "Minutes après l'envoi (échelle log)", "y_delay": "Part des signalements",
        "diff": LABEL_FR,
    },
    "en": {
        "title": "Phishing simulation campaign analysis",
        "lead": "Report to the CISO. Simulated data (see docs/simulation.md); no individual "
                "result is published.",
        "summary": "Key takeaways", "actions": "Corrective actions",
        "campaigns": "Results per campaign",
        "cols": "| Campaign | Month | Theme | Difficulty (Phish Scale) | Click | Credentials entered "
                "| Report | Reports / click | Reports < 30 min |",
        "trend": "The raw-rate trap", "model": "Analysis at equal difficulty",
        "training": "Does post-click training work?", "dept": "By department",
        "repeat": "How many employees click?",
        "fig_click": "Click rate per campaign (95% CI), colour = difficulty",
        "fig_report": "Report rate per campaign (95% CI)",
        "fig_delay": "Time to report (all campaigns)",
        "x_campaign": "Campaign", "y_click": "Click rate", "y_report": "Report rate",
        "x_delay": "Minutes after sending (log scale)", "y_delay": "Share of reports",
        "diff": LABEL_EN,
    },
}


def _p(x):
    return f"{100 * x:.1f} %"


def _pv(p):
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def _ci(r):
    return f"{_p(r['rate'])} [{100 * r['ci'][0]:.1f}–{100 * r['ci'][1]:.1f}]"


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def figures(a: dict, events: list[dict], out: Path, lang: str):
    t = T[lang]

    def _p(x):   # virgule décimale en français sur les figures aussi
        txt = f"{100 * x:.1f} %"
        return txt.replace(".", ",") if lang == "fr" else txt
    out.mkdir(parents=True, exist_ok=True)
    rows = a["campaigns"]
    xs = range(len(rows))

    fig, ax = plt.subplots(figsize=(8, 4), facecolor=SURFACE)
    _style(ax)
    seen = set()
    for x, r in zip(xs, rows):
        lo, hi = r["click"]["ci"]
        col = COLORS[r["difficulty"]]
        ax.plot([x, x], [lo, hi], color=col, linewidth=2, solid_capstyle="round")
        lab = t["diff"][r["difficulty"]] if r["difficulty"] not in seen else None
        seen.add(r["difficulty"])
        ax.scatter([x], [r["click"]["rate"]], s=60, color=col, edgecolor=SURFACE,
                   linewidth=2, zorder=3, label=lab)
        ax.annotate(_p(r["click"]["rate"]), (x, hi), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=8, color=INK2)
    ax.set_xticks(list(xs), [r["id"] for r in rows])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, max(r["click"]["ci"][1] for r in rows) * 1.18)
    ax.set_xlabel(t["x_campaign"], color=INK2)
    ax.set_ylabel(t["y_click"], color=INK2)
    ax.set_title(t["fig_click"], color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(out / f"click_by_campaign_{lang}.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    _style(ax)
    rr = [r["report"]["rate"] for r in rows]
    ax.fill_between(list(xs), [r["report"]["ci"][0] for r in rows],
                    [r["report"]["ci"][1] for r in rows], color="#2a78d6", alpha=0.15,
                    linewidth=0)
    ax.plot(list(xs), rr, color="#2a78d6", linewidth=2, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2)
    for x in (0, len(rows) - 1):
        ax.annotate(_p(rr[x]), (x, rr[x]), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9, color=INK2)
    ax.set_xticks(list(xs), [r["id"] for r in rows])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, max(r["report"]["ci"][1] for r in rows) * 1.2)
    ax.set_xlabel(t["x_campaign"], color=INK2)
    ax.set_ylabel(t["y_report"], color=INK2)
    ax.set_title(t["fig_report"], color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(out / f"report_by_campaign_{lang}.png", dpi=150)
    plt.close(fig)

    d = sorted(e["report_delay_min"] for e in events if e["reported"])
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    _style(ax)
    ax.plot(d, [(i + 1) / len(d) for i in range(len(d))], color="#2a78d6", linewidth=2)
    for m in (5, 30):
        share = sum(x <= m for x in d) / len(d)
        ax.axvline(m, color=GRID, linewidth=1, zorder=0)
        ax.annotate(f"{m} min : {_p(share)}", (m, share), textcoords="offset points",
                    xytext=(6, -14), fontsize=9, color=INK2)
    ax.set_xscale("log")
    ax.set_xticks([1, 5, 30, 60, 240, 1440, 4320], ["1", "5", "30", "60", "240",
                                                    "1 440", "4 320"])
    ax.minorticks_off()
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel(t["x_delay"], color=INK2)
    ax.set_ylabel(t["y_delay"], color=INK2)
    ax.set_title(t["fig_delay"], color=INK, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(out / f"report_delay_{lang}.png", dpi=150)
    plt.close(fig)


def markdown(a: dict, lang: str) -> str:
    t = T[lang]
    fr = lang == "fr"
    rows, nt, tr = a["campaigns"], a["naive_trend"], a["training"]
    m = a["model"]["robust"]
    form = m["formation"]
    tend, rt = a["trends"]["click"], a["trends"]["report"]
    recs = recommendations(a)
    L = [f"# {t['title']}", "", f"*{t['lead']}*", "", f"## {t['summary']}", ""]
    if fr:
        L += [f"- Le taux de clic brut baisse de **{_p(nt['first'])}** à **{_p(nt['last'])}**, "
              f"mais **à difficulté égale, aucune baisse n'est démontrée** (OR par campagne {tend['or']:.2f}, "
              f"IC 95 % {tend['or_ci'][0]:.2f}–{tend['or_ci'][1]:.2f}).",
              f"- La formation après clic n'a **pas d'effet démontré** (OR {form['or']:.2f}, "
              f"IC {form['or_ci'][0]:.2f}–{form['or_ci'][1]:.2f}) ; l'échantillon est trop petit "
              f"pour trancher ({tr['obs_per_group']} observations par groupe, "
              f"au moins {tr['needed_per_group_for_1_7pt']} nécessaires).",
              f"- Le **signalement progresse vraiment** : de {_p(rows[0]['report']['rate'])} à "
              f"{_p(rows[-1]['report']['rate'])}, et **même à difficulté égale** "
              f"(OR {rt['or']:.2f} par campagne, IC {rt['or_ci'][0]:.2f}–{rt['or_ci'][1]:.2f}).",
              f"- **{_p(a['repeat']['clicked_at_least_once'])}** des employés ont cliqué au moins "
              "une fois : la défense doit être technique autant qu'humaine."]
    else:
        L += [f"- The raw click rate drops from **{_p(nt['first'])}** to **{_p(nt['last'])}**, "
              f"but **at equal difficulty, no drop is demonstrated** (OR per campaign {tend['or']:.2f}, "
              f"95% CI {tend['or_ci'][0]:.2f}–{tend['or_ci'][1]:.2f}).",
              f"- Post-click training has **no demonstrated effect** (OR {form['or']:.2f}, "
              f"CI {form['or_ci'][0]:.2f}–{form['or_ci'][1]:.2f}); the sample is too small to "
              f"decide ({tr['obs_per_group']} observations per group, "
              f"at least {tr['needed_per_group_for_1_7pt']} needed).",
              f"- **Reporting is genuinely improving**: from {_p(rows[0]['report']['rate'])} to "
              f"{_p(rows[-1]['report']['rate'])}, **even at equal difficulty** "
              f"(OR {rt['or']:.2f} per campaign, CI {rt['or_ci'][0]:.2f}–{rt['or_ci'][1]:.2f}).",
              f"- **{_p(a['repeat']['clicked_at_least_once'])}** of employees clicked at least "
              "once: defence must be technical as much as human."]
    L += ["", f"## {t['actions']}", ""]
    L += [f"{i}. **P{r['priority']}** — {r[lang]}" for i, r in enumerate(recs, 1)]

    L += ["", f"## {t['campaigns']}", "", t["cols"], "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        theme = r["theme_fr"] if fr else r["theme_en"]
        ps = r["phishscale"]
        L.append(f"| {r['id']} | {r['month']} | {theme} | {t['diff'][r['difficulty']]} "
                 f"({ps['cues']} {'indices' if fr else 'cues'}, "
                 f"{'prétexte' if fr else 'premise'} {ps['premise_score']}) | {_ci(r['click'])} "
                 f"| {_p(r['submit']['rate'])} | {_ci(r['report'])} | "
                 f"{r['reports_per_click']:.1f} | {_p(r['reports_within_30'])} |")
    L += ["", f"![]({'figures/click_by_campaign_' + lang + '.png'})", "",
          f"## {t['trend']}", ""]
    if fr:
        L += [f"Comparer les 3 premières campagnes ({', '.join(nt['first_ids'])}) aux 3 "
              f"dernières ({', '.join(nt['last_ids'])}) donne une baisse spectaculaire et "
              f"« significative » : {_p(nt['first'])} → {_p(nt['last'])} (p < 0,001). "
              "Conclusion naïve : le programme fonctionne. Mais les premières campagnes étaient "
              "**très difficiles** et les dernières **plus faciles** (NIST Phish Scale). Ho et al. "
              "observent la même chose sur 19 789 employés : le taux d'échec dépend surtout "
              "du leurre (de 1,8 % à 30,8 %)."]
    else:
        L += [f"Comparing the first 3 campaigns ({', '.join(nt['first_ids'])}) with the last 3 "
              f"({', '.join(nt['last_ids'])}) shows a dramatic, 'significant' drop: "
              f"{_p(nt['first'])} → {_p(nt['last'])} (p < 0.001). Naive conclusion: the "
              "programme works. But the first campaigns were **very difficult** and the last "
              "ones **easier** (NIST Phish Scale). Ho et al. observe the same over 19,789 "
              "employees: failure depends mostly on the lure (1.8% to 30.8%)."]
    L += ["", f"## {t['model']}", "",
          ("Régression logistique par employé : clic ~ campagne (effets fixes) + formation + "
           "service. Formation et service sont comparés à l'intérieur de chaque campagne. "
           "Erreurs standard robustes par employé (chaque employé apparaît 8 fois)."
           if fr else "Per-employee logistic regression: click ~ campaign (fixed effects) + "
           "training + department. Training and department are compared within each "
           "campaign. Employee-clustered robust standard errors (each employee appears 8 "
           "times)."),
          "", "| " + ("Variable | OR | IC 95 % | p" if fr else "Variable | OR | 95% CI | p") + " |",
          "|---|---|---|---|"]
    for k, v in m.items():
        if k == "constante" or k.startswith("campagne"):
            continue
        L.append(f"| {k} | {v['or']:.2f} | {v['or_ci'][0]:.2f}–{v['or_ci'][1]:.2f} | "
                 f"{_pv(v['p_value']).lstrip('= ')} |")
    L += ["", ("Service de référence : " if fr else "Reference department: ")
          + a["model"]["reference_department"], ""]
    if fr:
        L += ["**Tendances, testées au niveau campagne** (logit du taux ~ difficulté + n° de "
              f"campagne, test t à {tend['df']} degrés de liberté). Chaque campagne a sa part "
              "d'aléa : avec 8 campagnes, c'est leur nombre, pas celui des employés, qui limite "
              "la précision. Un modèle par employé conclut à tort à une tendance dans ≈ 28 % des "
              "cas (voir la validation).", "",
              f"- Effet de la difficulté sur le clic : moyenne OR "
              f"{tend['moderately']['or']:.1f}, très difficile OR {tend['very']['or']:.1f} "
              "(contre peu difficile)",
              f"- Tendance du clic : OR {tend['or']:.2f} par campagne, IC 95 % {tend['or_ci'][0]:.2f}–"
              f"{tend['or_ci'][1]:.2f}, p {_pv(tend['p_value'])}",
              f"- Tendance du signalement : OR {rt['or']:.2f} par campagne, IC 95 % {rt['or_ci'][0]:.2f}–"
              f"{rt['or_ci'][1]:.2f}, p {_pv(rt['p_value'])}"]
    else:
        L += ["**Trends, tested at campaign level** (logit of rate ~ difficulty + campaign "
              f"number, t-test with {tend['df']} degrees of freedom). Each campaign has its own "
              "noise: with 8 campaigns, their number, not the number of employees, limits "
              "precision. A per-employee model wrongly finds a trend in ≈ 28% of cases (see "
              "validation).", "",
              f"- Effect of difficulty on clicks: moderate OR {tend['moderately']['or']:.1f}, "
              f"very difficult OR {tend['very']['or']:.1f} (vs least difficult)",
              f"- Click trend: OR {tend['or']:.2f} per campaign, 95% CI {tend['or_ci'][0]:.2f}–"
              f"{tend['or_ci'][1]:.2f}, p {_pv(tend['p_value'])}",
              f"- Report trend: OR {rt['or']:.2f} per campaign, 95% CI {rt['or_ci'][0]:.2f}–"
              f"{rt['or_ci'][1]:.2f}, p {_pv(rt['p_value'])}"]
    L += ["", f"## {t['training']}", ""]
    if fr:
        L += [f"Après la 1re campagne, la moitié des employés (tirée au sort) voit une page de "
              f"formation après un clic. Clic du groupe formé : {_ci(tr['formation'])} ; groupe "
              f"témoin : {_ci(tr['témoin'])}. Écart {100 * tr['diff']:+.1f} point(s), IC 95 % "
              f"{100 * tr['ci'][0]:+.1f} à {100 * tr['ci'][1]:+.1f}, p = {tr['p_value']:.2f}.",
              "", f"**Puissance.** Pour détecter l'effet observé par Ho et al. (−1,7 point), il "
              f"faudrait **au moins {tr['needed_per_group_for_1_7pt']} observations par groupe** "
              f"(puissance 80 %, en supposant des réponses indépendantes ; davantage en réalité, "
              f"puisque chaque employé répond 8 fois) ; on en a {tr['obs_per_group']}. Une organisation de cette "
              "taille ne peut pas prouver qu'une formation de ce type marche : il faut le dire "
              "avant de lancer l'expérience, pas après."]
    else:
        L += [f"After the 1st campaign, half of the employees (randomly assigned) see a training "
              f"page after a click. Trained group click rate: {_ci(tr['formation'])}; control: "
              f"{_ci(tr['témoin'])}. Difference {100 * tr['diff']:+.1f} point(s), 95% CI "
              f"{100 * tr['ci'][0]:+.1f} to {100 * tr['ci'][1]:+.1f}, p = {tr['p_value']:.2f}.",
              "", f"**Power.** Detecting the effect observed by Ho et al. (−1.7 points) would "
              f"need **at least {tr['needed_per_group_for_1_7pt']} observations per group** (80% "
              f"power, assuming independent answers; more in practice, since each employee "
              f"answers 8 times); we have {tr['obs_per_group']}. An organisation this size cannot prove "
              "that such training works: say so before running the experiment, not after."]
    L += ["", f"![]({'figures/report_by_campaign_' + lang + '.png'})", "",
          f"![]({'figures/report_delay_' + lang + '.png'})", "", f"## {t['dept']}", "",
          (f"Groupes de moins de {MIN_GROUP} personnes masqués. Intervalles robustes par "
           "employé (8 réponses d'une même personne ne valent pas 8 personnes)." if fr else
           f"Groups under {MIN_GROUP} people are hidden. Employee-clustered intervals "
           "(8 answers from one person are not 8 people)."), "",
          "| " + ("Service | Effectif | Clic | Signalement" if fr else
                  "Department | Headcount | Click | Report") + " |", "|---|---|---|---|"]
    for d in a["departments"]["rows"]:
        if d["suppressed"]:
            L.append(f"| {d['department']} | < {MIN_GROUP} | — | — |")
        else:
            L.append(f"| {d['department']} | {d['headcount']} | {_ci(d['click'])} | "
                     f"{_ci(d['report'])} |")
    rp = a["repeat"]
    dist = rp["distribution"]
    L += ["", f"## {t['repeat']}", ""]
    L.append(("Employés ayant cliqué 0 / 1 / 2 / 3+ fois sur 8 campagnes : "
              if fr else "Employees who clicked 0 / 1 / 2 / 3+ times over 8 campaigns: ")
             + f"{dist[0]} / {dist[1]} / {dist[2]} / {dist[3]}. "
             + (f"Les employés à 3 clics ou plus représentent {_p(rp['share_clicks_from_3plus'])} "
                "des clics : un accompagnement individuel, proposé en privé, peut se discuter, "
                "mais jamais de liste nominative diffusée."
                if fr else
                f"Employees with 3+ clicks account for {_p(rp['share_clicks_from_3plus'])} of "
                "clicks: private, individual support can be considered, but never a "
                "circulated list of names."))
    text = "\n".join(L) + "\n"
    if not fr:
        for a_, b_ in DEPT_EN.items():
            text = text.replace(f"service : {a_}", f"department: {a_}") \
                       .replace(f"| {a_} |", f"| {b_} |").replace(f": {a_}\n", f": {b_}\n")
        text = text.replace("department: ", "department: ").replace("| formation |",
                                                                     "| training |")
        for a_, b_ in DEPT_EN.items():
            text = text.replace(f"department: {a_}", f"department: {b_}")
        text = text.replace(" %", "%")
    if fr:   # virgule décimale en français (hors noms de fichiers)
        text = "\n".join(line if line.startswith("![") else
                         re.sub(r"(?<=\d)\.(?=\d)", ",", line) for line in text.split("\n"))
    return text
