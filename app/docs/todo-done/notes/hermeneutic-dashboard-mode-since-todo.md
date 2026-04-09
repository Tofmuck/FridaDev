# Hermeneutic Dashboard Mode Since TODO

Statut: archive
Classement: `app/docs/todo-done/notes/`
Origine: reliquat extrait du follow-up d'audit `2026-04-04`, maintenant archive dans `app/docs/todo-done/audits/fridadev-audit-followup-2026-04-04.md`
Archivage: mini-lot termine, archive dans `app/docs/todo-done/notes/hermeneutic-dashboard-mode-since-todo.md`

## Objectif

Rendre le dashboard hermeneutique plus lisible en exposant au minimum:
- `mode depuis`
- et/ou `derniere bascule`

Le but est de pouvoir comprendre depuis quand `HERMENEUTIC_MODE=enforced_all` est en vigueur, ou quand la derniere transition de mode a eu lieu, sans replay documentaire manuel.

## Pourquoi ce point vit maintenant a part

- Le follow-up d'audit du `2026-04-04` est boucle sur son perimetre principal.
- Ce reliquat n'est pas un blocker d'audit ni un correctif runtime urgent.
- Le sujet releve d'une surface admin / observabilite, pas d'un TODO produit generaliste.

## Travail actif borne

- [x] Trancher la source de verite de `mode depuis` / `derniere bascule`:
  - source retenue: observations `hermeneutic_mode` conservees dans les logs admin retenus;
  - `runtime_settings_history` n'est pas retenu, car `HERMENEUTIC_MODE` n'y vit pas;
  - l'etat runtime derive seul n'est pas suffisant pour dater une observation.
- [x] Definir la semantique minimale a afficher dans le dashboard:
  - semantique retenue: `premiere observation du segment courant du mode` + `derniere observation`;
  - la `derniere bascule exacte` reste explicitement inconnue;
  - le dashboard ne forge donc pas un faux `mode depuis`.
- [x] Ajouter l'indication dans `/hermeneutic-admin` et dans `GET /api/admin/hermeneutics/dashboard` avec un contrat lisible et stable.
- [x] Ajouter les preuves associees:
  - test backend de contrat dashboard,
  - test frontend/admin si l'UI affiche cette information,
  - verification live minimale de lisibilite.

## Hors scope

- replay complet de tout le rollout hermeneutique
- nouvelle campagne d'audit globale
- refonte large du dashboard admin
- nouvelle dette documentaire autour du follow-up d'audit clos
