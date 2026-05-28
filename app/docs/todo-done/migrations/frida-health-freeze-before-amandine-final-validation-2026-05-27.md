# Validation finale freeze sante Frida avant duplication Amandine

Statut: freeze sante Frida valide; GO Amandine historique supersede le 2026-05-28
Date: 2026-05-27
Branche: `migration`
Commit runtime valide: `b489ed2 Fix mutable judge primary user name detection`
Roadmap archivee: `app/docs/todo-done/migrations/frida-health-freeze-before-amandine-todo.md`

Note de mise a jour 2026-05-28: le plan de duplication Amandine ouvert apres
ce freeze a ete annule par decision produit, car Amandine ne souhaite pas de
Frida separee. Cette validation reste une baseline utile de sante Frida, mais
elle ne doit plus etre lue comme une action a executer, a reporter ou a confier
a Sauron. Aucune DB, aucun conteneur, aucun secret/token et aucun `state/`
Amandine ne doivent etre crees.

## Decision historique du 2026-05-27

Decision au moment du freeze: **GO** pour ouvrir un plan separe de duplication Amandine depuis le repository FridaDev, avec DB neuve, `state/` propre et runtime settings reseedes.

Cette validation ne cree pas Amandine, ne purge rien, ne copie aucune DB et ne modifie pas la plateforme. La duplication reste interdite dans ce lot et doit faire l'objet d'un GO utilisateur separe.

## Base validee

Pipeline produit retenu:

```text
FridaDev repository sain
+ DB neuve
+ state propre
+ runtime settings reseedes
-> future instance Amandine separee
```

Etat Frida valide:

- app live healthy;
- `/admin` protege par Authelia et repond en `HTTP/2 302`, cookies filtres;
- admin/runtime settings lisibles et secrets masques;
- juge mutable actif: `mutable_identity_judge_v2_add_only`;
- contrat mutable actif: `mutable_judge_v2`;
- modele juge mutable: `openai/gpt-5.2`;
- slot runtime conserve par compatibilite: `identity_periodic_model`;
- pipeline mutable: 5 paires completes -> juge v2 -> add/no_change -> applicateur add-only -> `identity_mutables`;
- aucun ancien writer mutable score-first actif;
- aucune promotion mutable -> static automatique.

## Tests et smokes finaux

Preuves finales executees le 2026-05-27:

| Preuve | Resultat |
| --- | --- |
| `git status --short --branch` avant cloture | branche `migration`, clean avant patch docs Lot 6 |
| `git log --oneline -10` | lots 0 a 5 visibles jusqu'a `b489ed2` |
| `git diff --check` avant patch | OK |
| `docker exec platform-fridadev python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply tests.unit.chat.test_mutable_identity_judge_final_validation` | OK, 32 tests |
| `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2 tests.test_minimal_validation_phase4` | OK, 35 tests |
| `docker ps --filter name=platform-fridadev` | `platform-fridadev` healthy, Postgres healthy |
| `curl -sSI https://fridadev.frida-system.fr/admin` | `HTTP/2 302` vers Authelia, cookies filtres |
| preuve mutable user-name content-free | `active_llm_names ['Frida']`, `active_user_names ['Tof']`, `mentions_tof True`, `mentions_amandine True` |

La preuve mutable confirme que l'instance Frida courante garde `Tof` comme nom principal actif du sujet `user`, meme si `Amandine` est mentionnee comme tiers/relation dans l'identite.

## Inventaire DB / state

Le Lot 3 a valide un inventaire content-free, lecture seule:

| Famille | Decision Amandine |
| --- | --- |
| conversations / messages | repartir vide, archive Frida a ne pas copier |
| traces / summaries / arbiter decisions | repartir vide, archive Frida a ne pas copier |
| identity mutables / audit / staging | repartir vide ou reseed explicite, ne pas copier Frida/Tof |
| identity legacy/evidence/conflicts | archive Frida a ne pas copier |
| runtime settings | reseed obligatoire, secrets hors Git |
| active documents / workspace files | repartir vide sauf seed produit explicite |
| observability events / dashboard projections | repartir vide; logs Frida a ne pas copier |
| `state/conv` / uploads | repartir propre |
| `state/logs` | ne pas copier; archive Frida seulement |
| `state/data/identity` | seed Amandine explicite requis, ne pas copier tel quel |

La checklist future backup/purge est prete dans la roadmap archivee, mais aucune action destructive n'a ete executee.

## P0 / P1 / P2 restants

Aucun P0/P1/P2 ouvert au moment du GO.

Les P2 trouves pendant le freeze ont ete corriges avant cloture:

- export Markdown chat: label user runtime `Tof` remplace par un label export generique;
- juge mutable v2: validation du nom user actif corrigee pour suivre le nom principal d'identite active et refuser les simples mentions de tiers.

## P3 acceptes

P3 acceptes et non bloquants pour ouvrir un plan Amandine:

- les referers/hostnames FridaDev devront etre reseedes lors de la creation Amandine;
- la surface `/log` separe encore les sources: `mutable_identity_judge` cote chat events et `mutable_identity_judge_apply` cote admin logs/filesystem;
- les logs Frida et `state/` Frida ne doivent pas etre copies vers Amandine;
- le futur seed Amandine doit commencer par une formulation principale claire du sujet user, par exemple `Amandine est...` ou `Amandine tient...`, avant toute mention historique ou relationnelle de tiers;
- certaines preuves working-copy montee Memory/RAG ou web-search peuvent necessiter DB/settings live; le conteneur live est sain.

## Non-actions confirmees

Ce lot n'a pas:

- cree Amandine;
- purge, copie ou migre la DB;
- modifie `state/`;
- change le modele, le prompt ou le runtime;
- touche Caddy, Authelia, Docker global, reseaux, hostnames ou secrets;
- affiche de secret, `.env`, DSN complet, token, cookie, payload brut, conversation brute, prompt complet ou identite brute.

## Statut apres decision produit 2026-05-28

Il n'y a plus de prochaine action de duplication Amandine. Le plan ouvert apres
ce freeze est archive comme annule dans
`app/docs/todo-done/migrations/amandine-duplication-annulee-2026-05-28.md`.
Le freeze reste une baseline utile pour Frida et pour de futures verifications
de sante, sans creation de DB, conteneur, secret/token ou `state/` Amandine.
