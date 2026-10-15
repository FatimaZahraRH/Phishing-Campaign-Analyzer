# Le modèle de simulation

Aucun résultat réel de campagne n'est public : ce sont des données
personnelles d'employés. Les données de `data/` sont donc **simulées**, avec
un modèle explicite. Tous les paramètres sont dans
[`config/simulation.json`](../config/simulation.json).

**Règle :** l'analyse (`scripts/analyze.py`) ne lit **jamais** ce fichier. Elle
ne voit que les événements et la description des campagnes, comme elle le
ferait avec des données réelles.

## Organisation

1 200 employés répartis en 7 services. La moitié, tirée au sort, est dans le
groupe « formation » (page de formation après un clic, à partir de la 2e
campagne), l'autre dans le groupe « témoin ».

## Clic

Pour l'employé *i* et la campagne *c* :

```
logit P(clic) = logit(taux de base selon la difficulté)   # 3 %, 9 %, 25 %
              + aléa de la campagne       ~ N(0 ; 0,15)
              + susceptibilité de i       ~ N(0 ; 0,9)    # certains cliquent plus
              + effet du service                          # ex. Finance +0,25, IT −0,40
              + log(0,905) si formé                       # Ho et al.
```

Les taux de base encadrent la plage observée par Ho et al. (1,8 % à 30,8 %).
Aucune tendance dans le temps n'est simulée : **toute « amélioration » du
taux brut vient donc du choix des leurres.**

## Saisie d'identifiants

45 % des cliqueurs saisissent leurs identifiants. C'est une hypothèse ; elle
n'influence aucune conclusion.

## Signalement

Probabilité de 15 % à la 1re campagne, +2 points par campagne (effet du retour
positif, Lain et al.), multipliée par 0,8 / 1 / 1,15 selon la difficulté
(très / moyen / peu difficile) et par 0,4 si l'employé a cliqué. Le délai
suit une loi log-normale (médiane 60 min, σ = 1,8, plafonné à 3 jours),
calée pour obtenir environ 10 % des signalements en moins de 5 minutes et
30 à 40 % en moins de 30 minutes, comme chez Lain et al.

## Ce que la simulation permet

Comme les vrais paramètres sont connus, `scripts/validate.py` vérifie sur 200
simulations que l'analyse les retrouve (voir le README).
