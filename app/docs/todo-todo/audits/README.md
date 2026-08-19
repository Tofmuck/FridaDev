# Audits - index actif et archives historiques

Statut Lot Z du mega-audit code + stack, 2026-08-19.

Ce dossier peut contenir a la fois des TODO actives et des pieces d'audit
conservees comme preuves contradictoires. Une checkbox dans une piece
historique n'est pas une tache active par defaut. Aucun chantier du mega-audit
code + stack ne reste actif dans ce dossier apres sa cloture Lot Z.

## Archive globale du mega-audit code + stack

- `../../todo-done/audits/frida-v1-mega-audit-code-stack-todo.md`: registre
  canonique ferme et archive; il porte les registres finaux P1/P2/P3, les
  quatre passes Lot Z et le verdict `met_with_documented_limits`.
- Artefact final content-free:
  `../../states/baselines/mega-audit-smokes/frida-v1-mega-audit-lotz-final-20260819T094412Z.jsonl`.

## Archive de remediation Lot 10

- `../../todo-done/audits/frida-v1-mega-audit-code-only-remediation-2026-07-15-todo.md`:
  sous-TODO Lot 10 archivee le 2026-07-22 apres fermeture ou requalification
  prouvee des lots 10A-10G. Elle ne remplace pas le registre canonique; la
  dette de complexite a ete absorbee puis traitee dans la roadmap Lot 9
  archivee sous `../../todo-done/refactors/`.

## Source d'audit code-only du Lot 10

- `../../states/audits/frida-v1-mega-audit-code-only-2026-07-15.md`: audit
  source de la seconde passe autocritique code-only. Il confirme cinq P2 et
  trois P3, sans P0/P1, et ne constitue pas une checklist executable sans la
  sous-TODO de remediation.

## Pieces d'entree archivees du mega-audit

- `../../todo-done/audits/frida-v1-mega-audit-code-stack-2026-06-24.md`:
  audit source historique du mega-audit.
- `../../todo-done/audits/frida-v1-mega-audit-code-stack-counter-audit-2026-06-24.md`:
  contre-audit historique conserve comme validation contradictoire.

## Pieces superseded archivees

Ces fichiers portent un en-tete `superseded`. Le Lot Z les a deplaces hors du
dossier actif; leurs sources courantes restent les archives
`todo-done/product/` citees dans leurs en-tetes.

- `../../todo-done/audits/frida-v1-continuity-payload-audit-2026-06-22.md`
- `../../todo-done/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`
- `../../todo-done/audits/frida-v1-final-global-audit-2026-06-23.md`
- `../../todo-done/audits/frida-v1-final-global-counter-audit-2026-06-23.md`

Une reouverture exige un finding courant prouve et une nouvelle TODO explicite;
aucune checkbox de ces archives ne redevient executable par simple lecture.
