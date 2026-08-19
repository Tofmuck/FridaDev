# Audits actifs et pieces historiques

Statut Lot 8 du mega-audit code + stack.

Ce dossier peut contenir a la fois des TODO actives et des pieces d'audit
conservees comme preuves contradictoires. Une checkbox dans une piece
historique n'est pas une tache active par defaut: la TODO canonique ci-dessous
decide ce qui reste executable.

## Source active

- `frida-v1-mega-audit-code-stack-todo.md`: registre canonique actif du
  mega-audit.

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

## Pieces d'entree du mega-audit courant

- `frida-v1-mega-audit-code-stack-2026-06-24.md`: audit source du mega-audit.
  Ses constats initiaux peuvent etre supersedes par les lots documentes dans la
  TODO canonique.
- `frida-v1-mega-audit-code-stack-counter-audit-2026-06-24.md`: contre-audit
  conserve comme piece de validation contradictoire. Il n'est pas une checklist
  active autonome.

## Pieces superseded conservees provisoirement

Ces fichiers portent deja un en-tete `superseded` et restent ici seulement pour
ne pas casser les pointeurs pendant le mega-audit. Les sources courantes sont
les archives `todo-done/product/` citees dans leurs en-tetes.

- `frida-v1-continuity-payload-audit-2026-06-22.md`
- `frida-v1-continuity-payload-counter-audit-2026-06-22.md`
- `frida-v1-final-global-audit-2026-06-23.md`
- `frida-v1-final-global-counter-audit-2026-06-23.md`

Lot Z pourra deplacer ou archiver ces pieces si la TODO canonique est elle-meme
archivee.
