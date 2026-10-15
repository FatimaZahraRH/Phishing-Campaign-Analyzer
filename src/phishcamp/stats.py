"""Outils statistiques, écrits à la main (numpy seulement) pour rester lisibles.

- intervalle de Wilson : un taux sans intervalle de confiance n'est pas un résultat ;
- test de deux proportions ;
- régression logistique (IRLS) avec erreurs standard et rapports de cotes ;
- taille d'échantillon nécessaire pour détecter un écart donné.
"""
from __future__ import annotations

import math

import numpy as np

Z95 = 1.959963984540054


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float, float]:
    """Taux et intervalle de confiance à 95 % (Wilson), robuste aux petits effectifs."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def two_proportions(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Écart p1 - p2, IC 95 % et p-valeur bilatérale (test z)."""
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se0 = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z = (p1 - p2) / se0 if se0 else 0.0
    return {"diff": p1 - p2, "ci": (p1 - p2 - Z95 * se, p1 - p2 + Z95 * se),
            "p_value": 2 * (1 - norm_cdf(abs(z)))}


def logistic(X: np.ndarray, y: np.ndarray, names: list[str], clusters=None,
             iters: int = 50) -> dict:
    """Régression logistique par moindres carrés repondérés (IRLS).

    Renvoie, pour chaque variable : coefficient, erreur standard, rapport de
    cotes (OR) et son IC 95 %, p-valeur (test de Wald).

    `clusters` (identifiant d'employé par ligne) active des erreurs standard
    ROBUSTES par grappe (sandwich). Indispensable ici : un même employé
    apparaît dans toutes les campagnes, ses réponses ne sont pas indépendantes.
    Sans correction, les intervalles sont trop étroits (voir scripts/validate.py).
    """
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        w = mu * (1 - mu)
        H = X.T @ (X * w[:, None]) + 1e-9 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - mu))
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    mu = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
    H = X.T @ (X * (mu * (1 - mu))[:, None]) + 1e-9 * np.eye(X.shape[1])
    bread = np.linalg.inv(H)
    if clusters is None:
        cov = bread
    else:
        eta = np.clip(X @ beta, -30, 30)
        score = X * (y - 1 / (1 + np.exp(-eta)))[:, None]
        _, inv = np.unique(np.asarray(clusters), return_inverse=True)
        g = np.zeros((inv.max() + 1, X.shape[1]))
        np.add.at(g, inv, score)
        G = g.shape[0]
        cov = bread @ (g.T @ g) @ bread * G / (G - 1)
    se = np.sqrt(np.diag(cov))
    out = {}
    for i, name in enumerate(names):
        b, s = float(beta[i]), float(se[i])
        out[name] = {"coef": b, "se": s, "or": math.exp(b),
                     "or_ci": (math.exp(b - Z95 * s), math.exp(b + Z95 * s)),
                     "p_value": 2 * (1 - norm_cdf(abs(b / s))) if s else float("nan")}
    return out


def sample_size_two_proportions(p1: float, p2: float, alpha: float = 0.05,
                                power: float = 0.8) -> int:
    """Observations nécessaires PAR GROUPE pour détecter p1 ≠ p2."""
    z_a = Z95 if alpha == 0.05 else _inv_norm(1 - alpha / 2)
    z_b = _inv_norm(power)
    pbar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar))
           + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(num / (p1 - p2) ** 2)


def _inv_norm(p: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clustered_rate(k_by_unit: list[int], n_by_unit: list[int]) -> tuple[float, float, float]:
    """Taux et IC 95 % quand chaque personne contribue plusieurs observations.

    Estimateur de ratio avec variance robuste par personne : les 8 réponses
    d'un même employé ne comptent pas comme 8 personnes indépendantes.
    """
    K, N, G = sum(k_by_unit), sum(n_by_unit), len(n_by_unit)
    if N == 0 or G < 2:
        return (float("nan"),) * 3
    p = K / N
    var = G / (G - 1) * sum((k - p * n) ** 2 for k, n in zip(k_by_unit, n_by_unit)) / N ** 2
    half = Z95 * math.sqrt(var)
    return p, max(0.0, p - half), min(1.0, p + half)


def campaign_level_trend(rates: list[tuple[int, int]], difficulty: list[str],
                         levels=("moderately", "very")) -> dict:
    """Tendance au niveau CAMPAGNE : logit(taux) ~ difficulté + n° de campagne.

    Pourquoi pas au niveau employé ? Chaque campagne a sa part d'aléa propre
    (le jour, l'actualité, la formulation). Avec 8 campagnes, c'est le nombre
    de campagnes, pas le nombre d'employés, qui limite la précision d'une
    tendance. Un modèle par employé l'ignore et conclut trop souvent à une
    tendance (≈ 28 % de faux positifs au lieu de 5 % : voir scripts/validate.py).
    Ici : moindres carrés sur les 8 logits, test t à (8 - 4) degrés de liberté.
    """
    from scipy import stats as sst
    y = np.array([math.log((k + 0.5) / (n - k + 0.5)) for k, n in rates])
    X = np.array([[1] + [d == lv for lv in levels] + [i] for i, d in enumerate(difficulty)],
                 float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    df = len(y) - X.shape[1]
    s2 = float(resid @ resid) / df
    cov = s2 * np.linalg.inv(X.T @ X)
    q = sst.t.ppf(0.975, df)
    out = {"df": df}
    for i, name in enumerate(["constante"] + list(levels) + ["trend"]):
        b, se = float(beta[i]), math.sqrt(cov[i, i])
        out[name] = {"or": math.exp(b), "or_ci": (math.exp(b - q * se), math.exp(b + q * se)),
                     "p_value": float(2 * sst.t.sf(abs(b / se), df))}
    # raccourcis pour la tendance (usage le plus fréquent)
    out.update(out["trend"])
    return out
