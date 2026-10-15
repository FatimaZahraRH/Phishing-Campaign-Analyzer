# De la recherche aux choix de conception

## NIST Phish Scale — noter la difficulté avant de comparer

*S. Dawkins, J. Jacobs, NIST Phish Scale User Guide, NIST TN 2276, 2023.*

Deux mesures :
- **Indices** visibles, comptés sur 5 types (erreurs, indices techniques,
  présentation, langage, ressorts de manipulation) : 1–8 = *few*,
  9–14 = *some*, 15+ = *many*. Peu d'indices = plus difficile.
- **Alignement du prétexte** : 5 éléments notés 0/2/4/6/8 ;
  note = E1 + E2 + E3 + E4 − E5 (E5 = formation ou alerte récente sur ce
  type de message). ≤ 10 faible, 11–17 moyen, ≥ 18 fort.

Une matrice (table 7 du guide) combine les deux : peu / moyennement / très
difficile. La case « some × weak » est une plage dans le guide ; l'outil
retient « moyennement » par prudence (`phishscale.py`).

**Usage ici** : chaque campagne est notée, la difficulté entre dans toutes
les comparaisons, et le rapport affiche la note à côté de chaque taux.

## Ho et al., IEEE S&P 2025 — la formation, mesurée honnêtement

*G. Ho et al., Understanding the Efficacy of Phishing Training in Practice.*
19 789 employés de UC San Diego Health, 8 mois, 10 leurres, essai randomisé.

- Le taux d'échec par leurre va de **1,82 %** à **30,80 %** : le leurre compte
  plus que tout le reste.
- Les groupes formés échouent **1,7 point** de moins que le témoin
  (OR 0,905), un effet faible.
- La formation interactive, suivie jusqu'au bout, est associée à 19 % d'échec
  en moins ; la formation statique, à aucun bénéfice.
- Plus de 75 % des sessions de formation durent moins d'une minute.
- **56 %** des employés ont échoué au moins une fois en 8 mois.

**Usage ici** : paramètres de simulation (taux par difficulté, OR 0,905) ;
groupe témoin tiré au sort ; calcul de la taille d'échantillon nécessaire
pour détecter −1,7 point ; pages de sensibilisation courtes ; message
« cliquer est la norme, pas l'exception ».

## Lain et al., IEEE S&P 2022 — le signalement comme indicateur

*D. Lain, K. Kostiainen, S. Čapkun, Phishing in Organizations.*
14 733 employés, 15 mois.

- Environ 10 % des signalements arrivent en moins de 5 minutes, 30 à 40 % en
  moins de 30 minutes ; pas de lassitude sur 15 mois.
- Le retour positif encourage à signaler davantage.
- Les signalements ont révélé 252 vraies campagnes en 5 mois.

**Usage ici** : taux de signalement, délai (< 5 min, < 30 min) et rapport
signalements/clics suivis pour chaque campagne ; la hausse du signalement
est testée à difficulté égale.

## Zeger, Liang & Albert, Biometrics 1988 — quel effet estime-t-on ?

Une régression logistique sans effet individuel estime un effet « moyen de
population », plus proche de 1 que l'effet « individuel » simulé :
OR_moyen ≈ exp(log OR / √(1 + c²σ²)), c = 16√3 / (15π). Avec σ = 0,9 :
0,905 → 0,916. `scripts/validate.py` vérifie la couverture contre cette cible.

## Deux pièges statistiques corrigés

1. **Les 8 réponses d'un employé ne sont pas indépendantes.** Sans
   correction, l'IC de l'effet de la formation ne couvre la vraie valeur que
   87 % du temps. Avec des erreurs standard robustes par employé : 93,5 %.
2. **Une tendance se teste avec le bon nombre d'unités.** Chaque campagne a
   sa part d'aléa ; avec 8 campagnes, une tendance testée dans un modèle par
   employé (9 600 lignes) donne 27,5 % de faux positifs. Testée au niveau
   campagne (8 points, 4 degrés de liberté) : 6,5 %.
