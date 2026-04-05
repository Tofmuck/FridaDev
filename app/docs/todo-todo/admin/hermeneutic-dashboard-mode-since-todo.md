# Hermeneutic Dashboard Mode Since TODO

Statut: actif
Classement: `app/docs/todo-todo/admin/`
Origine: reliquat extrait du follow-up d'audit `2026-04-04`, maintenant archive dans `app/docs/todo-done/audits/fridadev-audit-followup-2026-04-04.md`

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

- [ ] Trancher la source de verite de `mode depuis` / `derniere bascule`:
  - etat runtime derive,
  - historique settings,
  - ou autre source admin explicite si elle est plus honnete.
- [ ] Definir la semantique minimale a afficher dans le dashboard:
  - `mode depuis` seulement,
  - `derniere bascule` seulement,
  - ou les deux si la verite reste compacte et non ambigue.
- [ ] Ajouter l'indication dans `/hermeneutic-admin` et/ou `GET /api/admin/hermeneutics/dashboard` avec un contrat lisible et stable.
- [ ] Ajouter les preuves associees:
  - test backend de contrat dashboard,
  - test frontend/admin si l'UI affiche cette information,
  - verification live minimale de lisibilite.

## Hors scope

- replay complet de tout le rollout hermeneutique
- nouvelle campagne d'audit globale
- refonte large du dashboard admin
- nouvelle dette documentaire autour du follow-up d'audit clos
