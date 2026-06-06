# Frida Biblio Last Chance - archive de nettoyage TODO

Date: 2026-06-06
Classement: `app/docs/todo-done/product/`

Cette note archive le nettoyage docs-only de
`app/docs/todo-todo/product/frida-biblio-last-chance.md` apres fermeture live de
la checklist BIB-01 -> BIB-33.

Le fichier actif faisait 3217 lignes et contenait:

- les anciens plans Lot 0 -> Lot 4;
- des diagnostics et micro-lots devenus historiques;
- des matrices requalifiees par la checklist canonique;
- des preuves partielles conservees ensuite par les artefacts JSONL;
- des sections de pilotage deja absorbees par les BIB fermees.

Decision:

- ne pas dupliquer ces 3000 lignes dans une seconde archive Markdown;
- conserver l'historique complet via Git, commit pre-nettoyage `645f108`;
- conserver les preuves produit via les artefacts JSONL cites dans la TODO
  active;
- garder dans la TODO active seulement l'etat courant, les invariants, la
  checklist 33/33, le journal compact, Lot 5, Lot 6 et les risques utiles.

La TODO active apres nettoyage est:
`app/docs/todo-todo/product/frida-biblio-last-chance.md`.
