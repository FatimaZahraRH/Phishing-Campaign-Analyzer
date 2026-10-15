"""Actions correctives déduites des résultats, en français et en anglais.

Chaque recommandation cite le chiffre qui la justifie. Aucune ne vise une
personne : on corrige des processus et des outils, on ne désigne pas de
« mauvais élèves » (voir docs/ethics.md).
"""
from __future__ import annotations


DEPT_EN = {"Conseil": "Consulting", "RH": "HR", "Juridique": "Legal", "Direction": "Management"}


def _pct(x):
    return f"{100 * x:.1f} %"


def recommendations(a: dict) -> list[dict]:
    recs = []
    rows, trend, m = a["campaigns"], a["naive_trend"], a["model"]["robust"]
    tr = a["training"]

    t = a["trends"]["click"]
    if trend["p_value"] < 0.05 and t["or_ci"][0] <= 1 <= t["or_ci"][1]:
        recs.append({
            "priority": 1,
            "fr": ("Ne pas annoncer de progrès. Le taux de clic brut passe de "
                   f"{_pct(trend['first'])} à {_pct(trend['last'])}, mais à difficulté égale "
                   f"(NIST Phish Scale) aucune baisse n'est démontrée (OR par campagne "
                   f"{t['or']:.2f}, IC 95 % {t['or_ci'][0]:.2f}–{t['or_ci'][1]:.2f}). "
                   "La baisse s'explique par des leurres plus faciles. Toujours publier les taux "
                   "avec la difficulté de chaque campagne."),
            "en": ("Do not report progress. The raw click rate drops from "
                   f"{_pct(trend['first'])} to {_pct(trend['last'])}, but at equal difficulty "
                   f"(NIST Phish Scale) no drop is demonstrated (OR per campaign {t['or']:.2f}, "
                   f"95% CI {t['or_ci'][0]:.2f}–{t['or_ci'][1]:.2f}). The drop is explained by "
                   "easier lures. Always report rates alongside each campaign's difficulty."),
        })

    f = m["formation"]
    if f["or_ci"][0] <= 1 <= f["or_ci"][1]:
        recs.append({
            "priority": 2,
            "fr": (f"La formation après clic n'a pas d'effet démontré (OR {f['or']:.2f}, IC 95 % "
                   f"{f['or_ci'][0]:.2f}–{f['or_ci'][1]:.2f}). Avec {tr['obs_per_group']} "
                   f"observations par groupe, il en faudrait au moins {tr['needed_per_group_for_1_7pt']} "
                   "pour détecter l'effet rapporté par Ho et al. (−1,7 point). Ne pas étendre "
                   "le dispositif sur cette base ; privilégier la formation interactive : dans cette "
                   "étude, c'est la seule associée à un bénéfice, une fois suivie jusqu'au bout."),
            "en": (f"Post-click training shows no demonstrated effect (OR {f['or']:.2f}, 95% CI "
                   f"{f['or_ci'][0]:.2f}–{f['or_ci'][1]:.2f}). With {tr['obs_per_group']} "
                   f"observations per group, at least {tr['needed_per_group_for_1_7pt']} would be "
                   "needed to detect the effect reported by Ho et al. (−1.7 points). Do not "
                   "scale it up on this basis; favour interactive training: in that study it is "
                   "the only kind associated with a benefit, once completed."),
        })

    hard = [r for r in rows if r["difficulty"] == "very"]
    if hard:
        worst = max(hard, key=lambda r: r["click"]["rate"])
        sub = sum(r["submit"]["k"] for r in rows) / sum(r["submit"]["n"] for r in rows)
        recs.append({
            "priority": 2,
            "fr": (f"Les leurres très difficiles piègent jusqu'à {_pct(worst['click']['rate'])} "
                   f"des employés ({worst['id']}), et {_pct(sub)} des destinataires ont saisi "
                   "des identifiants sur l'ensemble des campagnes. La formation ne suffira pas : "
                   "généraliser une MFA résistante au phishing (clés FIDO2 / passkeys) en "
                   "commençant par les comptes à privilèges, et ajouter un bandeau "
                   "« expéditeur externe »."),
            "en": (f"Very difficult lures catch up to {_pct(worst['click']['rate'])} of "
                   f"employees ({worst['id']}), and {_pct(sub)} of recipients entered "
                   "credentials across all campaigns. Training will not be enough: roll out "
                   "phishing-resistant MFA (FIDO2 keys / passkeys), privileged accounts first, "
                   "and add an 'external sender' banner."),
        })

    first, last = rows[0]["report"]["rate"], rows[-1]["report"]["rate"]
    rt = a["trends"]["report"]
    real = rt["or_ci"][0] > 1
    recs.append({
        "priority": 3,
        "fr": (f"Le signalement progresse ({_pct(first)} → {_pct(last)})"
               + (f", et pas seulement parce que les leurres étaient plus faciles (OR {rt['or']:.2f} "
                  "par campagne à difficulté égale)" if real else
                  ", mais cette hausse s'explique par la difficulté des leurres")
               + f". {_pct(rows[-1]['reports_within_30'])} des signalements arrivent en moins de "
               "30 minutes. Continuer à répondre à chaque signaleur (retour positif) et "
               "brancher la boîte « signalements » sur un triage automatique, pour que ces "
               "alertes humaines servent à bloquer les vraies campagnes."),
        "en": (f"Reporting is improving ({_pct(first)} → {_pct(last)})"
               + (f", and not only because lures got easier (OR {rt['or']:.2f} per campaign at "
                  "equal difficulty)" if real else
                  ", but the rise is explained by lure difficulty")
               + f". {_pct(rows[-1]['reports_within_30'])} of reports arrive within 30 minutes. "
               "Keep replying to every reporter (positive feedback) and connect the "
               "reporting mailbox to automated triage, so these human alerts help block "
               "real campaigns."),
    })

    rep = a["repeat"]
    recs.append({
        "priority": 3,
        "fr": (f"{_pct(rep['clicked_at_least_once'])} des employés ont cliqué au moins une fois "
               "en 8 campagnes : cliquer est la norme, pas l'exception. Communiquer sans "
               "culpabiliser, et ne jamais publier de résultats individuels."),
        "en": (f"{_pct(rep['clicked_at_least_once'])} of employees clicked at least once in "
               "8 campaigns: clicking is the norm, not the exception. Communicate without "
               "blame, and never publish individual results."),
    })

    for d in a["departments"]["rows"]:
        key = f"service : {d['department']}"
        if d.get("suppressed") or key not in m:
            continue
        o = m[key]
        if o["or_ci"][0] > 1:
            recs.append({
                "priority": 3,
                "fr": (f"Le service {d['department']} clique davantage que le service de "
                       f"référence à difficulté égale (OR {o['or']:.2f}, IC "
                       f"{o['or_ci'][0]:.2f}–{o['or_ci'][1]:.2f}) : proposer une session "
                       "courte adaptée à ses usages, sans désigner de personnes."),
                "en": (f"The {DEPT_EN.get(d['department'], d['department'])} department clicks more than the reference at "
                       f"equal difficulty (OR {o['or']:.2f}, CI {o['or_ci'][0]:.2f}–"
                       f"{o['or_ci'][1]:.2f}): offer a short session tailored to its work, "
                       "without singling anyone out."),
            })
    return sorted(recs, key=lambda r: r["priority"])
