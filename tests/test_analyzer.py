import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phishcamp.actions import recommendations  # noqa: E402
from phishcamp.analyze import MIN_GROUP, analyze, departments, load  # noqa: E402
from phishcamp.i18n import CUE_EN, landing_page  # noqa: E402
from phishcamp.phishscale import cue_category, premise_alignment, rate  # noqa: E402
from phishcamp.report import markdown  # noqa: E402
from phishcamp.stats import (campaign_level_trend, clustered_rate, logistic,  # noqa: E402
                             sample_size_two_proportions, wilson)

CAMPS = json.loads((ROOT / "campaigns" / "campaigns.json").read_text(encoding="utf-8"))


def _camp(n_cues, premise):
    keys = ["mimics_workplace_process", "has_workplace_relevance",
            "aligns_with_other_situations", "engenders_concern", "prior_training_or_warnings"]
    return {"cues": {"error": ["x"] * n_cues, "technical_indicator": [],
                     "visual_presentation": [], "language_content": [], "common_tactic": []},
            "premise": dict(zip(keys, premise))}


# --- NIST Phish Scale -------------------------------------------------------

def test_cue_thresholds_follow_the_guide():
    assert cue_category(_camp(8, [0] * 5)["cues"])[1] == "few"
    assert cue_category(_camp(9, [0] * 5)["cues"])[1] == "some"
    assert cue_category(_camp(14, [0] * 5)["cues"])[1] == "some"
    assert cue_category(_camp(15, [0] * 5)["cues"])[1] == "many"


def test_premise_rating_subtracts_prior_training():
    assert premise_alignment(_camp(1, [8, 8, 2, 0, 8])["premise"]) == (10, "weak")
    assert premise_alignment(_camp(1, [8, 8, 2, 0, 0])["premise"])[1] == "strong"
    assert premise_alignment(_camp(1, [6, 6, 6, 0, 0])["premise"]) == (18, "strong")
    assert premise_alignment(_camp(1, [6, 6, 4, 0, 0])["premise"]) == (16, "medium")


def test_difficulty_matrix_corners():
    assert rate(_camp(3, [8, 8, 4, 4, 0]))["difficulty"] == "very"
    assert rate(_camp(20, [0, 0, 2, 0, 0]))["difficulty"] == "least"


def test_invalid_premise_score_is_rejected():
    with pytest.raises(ValueError):
        premise_alignment(_camp(1, [5, 0, 0, 0, 0])["premise"])


# --- Statistiques -----------------------------------------------------------

def test_wilson_zero_successes_has_nonzero_upper_bound():
    p, lo, hi = wilson(0, 10)
    assert p == 0 and lo == 0 and hi == pytest.approx(0.2775, abs=1e-3)


def test_sample_size_matches_textbook_value():
    assert sample_size_two_proportions(0.5, 0.4) == pytest.approx(388, abs=3)


def test_logistic_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    x = rng.normal(size=20000)
    y = (rng.random(20000) < 1 / (1 + np.exp(-(-1 + 0.7 * x)))).astype(float)
    r = logistic(np.column_stack([np.ones_like(x), x]), y, ["c", "x"])
    assert r["x"]["coef"] == pytest.approx(0.7, abs=0.05)
    assert r["x"]["or_ci"][0] < np.exp(0.7) < r["x"]["or_ci"][1]


def test_clustered_interval_is_wider_when_people_repeat_themselves():
    # 50 personnes qui cliquent toujours, 50 jamais : 800 réponses, mais 100 personnes.
    k = [8] * 50 + [0] * 50
    n = [8] * 100
    _, lo_c, hi_c = clustered_rate(k, n)
    _, lo_w, hi_w = wilson(sum(k), sum(n))
    assert (hi_c - lo_c) > 2 * (hi_w - lo_w)


def test_campaign_level_trend_detects_a_real_trend_only():
    diff = ["least", "moderately", "very", "least", "moderately", "very", "least", "moderately"]
    flat = campaign_level_trend([(100, 1000), (200, 1000), (400, 1000), (105, 1000),
                                 (190, 1000), (410, 1000), (98, 1000), (205, 1000)], diff)
    assert flat["or_ci"][0] < 1 < flat["or_ci"][1]
    rising = campaign_level_trend([(50 + 30 * i + {"least": 0, "moderately": 60, "very": 150}[d],
                                    1000) for i, d in enumerate(diff)], diff)
    assert rising["or_ci"][0] > 1


# --- Analyse sur les données du dépôt -------------------------------------

@pytest.fixture(scope="module")
def result():
    camps, emps, events = load(ROOT / "data", ROOT / "campaigns" / "campaigns.json")
    return analyze(camps, emps, events), emps, events


def test_raw_trend_is_a_trap(result):
    a, _, _ = result
    assert a["naive_trend"]["p_value"] < 0.001            # baisse brute « significative »
    lo, hi = a["trends"]["click"]["or_ci"]
    assert lo < 1 < hi                                     # rien à difficulté égale


def test_reporting_trend_survives_difficulty_adjustment(result):
    assert result[0]["trends"]["report"]["or_ci"][0] > 1


def test_first_action_warns_against_announcing_progress(result):
    recs = recommendations(result[0])
    assert recs[0]["priority"] == 1 and "Ne pas annoncer" in recs[0]["fr"]


def test_small_departments_are_hidden(result):
    _, emps, events = result
    emps = {k: dict(v) for k, v in emps.items()}
    for k in list(emps)[:MIN_GROUP - 1]:
        emps[k]["department"] = "Petit service"
    rows = {r["department"]: r for r in departments(emps, events)["rows"]}
    assert rows["Petit service"]["suppressed"] is True


def test_reports_never_contain_employee_identifiers(result):
    a, emps, _ = result
    text = markdown(a, "fr") + markdown(a, "en")
    assert not any(e in text for e in emps)


# --- Traduction -------------------------------------------------------------

def test_every_cue_has_an_english_translation():
    for c in CAMPS:
        for items in c["cues"].values():
            assert all(x in CUE_EN for x in items)
    page = landing_page(CAMPS[0], "en")
    assert "This was an exercise" in page and "Report" in page
