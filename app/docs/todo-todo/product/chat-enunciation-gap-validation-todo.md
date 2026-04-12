# Chat - Validation doctrine enonciation / identite / gap

Statut: suivi post-implementation prompt-first
Classement: `app/docs/todo-todo/product/`
Portee: verification legere apres implementation du prompt principal

Reference stable:

- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`

## Objectif

Garder un mini-support de suivi jusqu'a stabilisation du lot `prompt-first` sur la voix, la coherence identitaire posturale/affective et la reprise apres ecart temporel.

## Etat apres implementation prompt-first (`2026-04-12`)

- [x] La doctrine source-of-truth a ete validee humainement.
- [x] Le prompt principal a ete aligne sur `je` par defaut, le glissement meta explicite systeme / instance / artefact, la reprise sobre et non rituelle apres gap, la coherence identitaire forte `statique -> base` / `mutable -> nuance`, le refus du faux affect revendique et la priorite maintenue de la demande courante.
- [x] Aucun complement runtime n'a ete juge necessaire pour ce lot borne.

## TODO

- [x] Valider la formulation courte retenue et la liste des interdits.
- [x] Verrouiller un petit jeu d'exemples canoniques pour la validation produit: voix dialogique ordinaire, pas de cote systeme, pas de cote artefact, reprise sobre, reprise relationnelle legere, cas sans mention du gap.
- [x] Valider des exemples acceptables de posture, de tonalite et de coloration affective exprimee coherentes avec l'identite active.
- [x] Valider des exemples explicitement inacceptables de faux affect revendique comme fait interieur.
- [x] Verifier l'articulation attendue entre socle statique, modulation mutable et priorite de la demande courante.
- [x] Trancher le lot d'implementation: `prompt-first`, sans ajout runtime.
- [ ] Confirmer apres deploiement que le comportement observe reste sobre sur les reprises avec silence et n'introduit pas de faux affect revendique.
- [ ] Archiver ce mini-suivi quand cette verification post-implementation n'appelle plus de reformulation de prompt.

## Hors scope de ce TODO

- aucun patch runtime
- aucune nouvelle brique runtime pour ce lot
- aucun seuil de temps en production
