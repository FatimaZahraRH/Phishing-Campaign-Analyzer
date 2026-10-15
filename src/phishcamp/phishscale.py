"""NIST Phish Scale : noter la difficulté de détection d'un e-mail d'exercice.

Dawkins & Jacobs, *NIST Phish Scale User Guide*, NIST TN 2276, 2023.

Deux mesures, combinées dans une matrice :
  1. le nombre d'INDICES visibles (fautes, domaine étrange, urgence…),
     comptés sur cinq types ; peu d'indices = plus difficile ;
  2. l'ALIGNEMENT DU PRÉTEXTE avec le quotidien des destinataires : cinq
     éléments notés 0/2/4/6/8 ; note = (E1 + E2 + E3 + E4) - E5.

Pourquoi c'est indispensable : comparer le taux de clic de deux campagnes
sans tenir compte de leur difficulté ne veut rien dire. Ho et al. (IEEE S&P
2025) observent de 1,8 % à 30,8 % d'échec selon le leurre, dans la même
population.
"""
from __future__ import annotations

CUE_TYPES = ("error", "technical_indicator", "visual_presentation", "language_content",
             "common_tactic")
PREMISE_ELEMENTS = ("mimics_workplace_process", "has_workplace_relevance",
                    "aligns_with_other_situations", "engenders_concern",
                    "prior_training_or_warnings")      # E5 : fait BAISSER la note
ALLOWED_SCORES = {0, 2, 4, 6, 8}

# Table 7 du guide. La case « Some / Weak » est une plage : on retient le
# niveau le plus difficile (« moderately ») par prudence, et on le signale.
MATRIX = {
    ("few", "strong"): "very", ("few", "medium"): "very", ("few", "weak"): "moderately",
    ("some", "strong"): "very", ("some", "medium"): "moderately",
    ("some", "weak"): "moderately",
    ("many", "strong"): "moderately", ("many", "medium"): "moderately",
    ("many", "weak"): "least",
}
LABEL_FR = {"least": "peu difficile", "moderately": "moyennement difficile",
            "very": "très difficile"}
LABEL_EN = {"least": "least difficult", "moderately": "moderately difficult",
            "very": "very difficult"}


def cue_category(cues: dict) -> tuple[int, str]:
    unknown = set(cues) - set(CUE_TYPES)
    if unknown:
        raise ValueError(f"types d'indices inconnus : {unknown}")
    n = sum(len(v) for v in cues.values())
    return n, ("few" if n <= 8 else "some" if n <= 14 else "many")


def premise_alignment(elements: dict) -> tuple[int, str]:
    if set(elements) != set(PREMISE_ELEMENTS):
        raise ValueError("les cinq éléments du prétexte doivent être notés")
    if any(v not in ALLOWED_SCORES for v in elements.values()):
        raise ValueError("chaque élément se note 0, 2, 4, 6 ou 8")
    score = sum(elements[k] for k in PREMISE_ELEMENTS[:4]) - elements[PREMISE_ELEMENTS[4]]
    return score, ("weak" if score <= 10 else "medium" if score <= 17 else "strong")


def rate(campaign: dict) -> dict:
    n_cues, cue_cat = cue_category(campaign["cues"])
    pa, pa_cat = premise_alignment(campaign["premise"])
    diff = MATRIX[(cue_cat, pa_cat)]
    return {"cues": n_cues, "cue_category": cue_cat, "premise_score": pa,
            "premise_category": pa_cat, "difficulty": diff,
            "range_cell": (cue_cat, pa_cat) == ("some", "weak")}
