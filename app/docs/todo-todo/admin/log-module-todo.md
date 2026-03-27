# Log Module TODO (Frida)

## Objectif
Mettre en place un module de logs applicatifs consultables en UI pour suivre le pipeline chat par tour, sans melanger observabilite et memoire metier.

Contrat normatif de reference:
- `app/docs/states/specs/log-module-contract.md`

## Invariants
- Le module logs est un module d'observabilite, pas une source metier.
- `delete logs` ne supprime jamais conversations, traces, summaries, identities, context hints.
- La memoire metier continue de fonctionner meme si tous les logs sont supprimes.
- Les logs sont stockes a part de la memoire metier.
- Les logs sont chronologiques et relies a un tour (`conversation_id`, `turn_id`, `event_id`, `ts`).
- Statuts minimaux obligatoires: `ok`, `error`, `skipped`.
- Pas de dump massif brut par defaut (prompt complet, contexte complet, payloads LLM complets).
- Pas de dump massif des blocs identitaires (lecture ou ecriture): uniquement metadonnees sobres.
- Pour le contexte injecte, on logue les metadonnees utiles (`context_tokens`, `token_limit`, `truncated`, compteurs), pas le contenu integral.
- UI logs: reutilisation prioritaire du CSS admin (`app/web/admin.css`) et du langage de composants admin existant.
- Le module cible reste borne au pipeline chat par tour (pas de plateforme observabilite globale).

## TODO (executable par tranches)

### 0) Cadrage contractuel (avant code)
- [x] Valider la frontiere exacte memoire metier vs logs applicatifs (tables, routes, ownership).
- [x] Verrouiller la liste des champs communs obligatoires pour chaque evenement (`conversation_id`, `turn_id`, `event_id`, `ts`, `stage`, `status`).
- [x] Verrouiller le sous-contrat `status=skipped` avec des `reason_code` minimaux et stables.
- [x] Ajouter et verrouiller un champ explicite `prompt_kind` (taxonomie initiale fixee dans le contrat).
- [x] Verrouiller un evenement / sous-contrat explicite `web_search` (pas seulement un booleen dans `turn_start`).
- [x] Decider explicitement le scope de suppression MVP a supporter.
- [x] Decider explicitement que l'option `all_logs` n'est pas retenue pour le MVP.
- [x] Option `conversation_logs` (purge par conversation, retenue pour MVP)
- [x] Option `turn_logs` (purge par tour, retenue pour MVP)
- [x] Documenter la decision retenue et les options differees.

### 1) Stockage dedie logs (separe memoire metier)
- [x] Definir le support de stockage dedie logs (sans reemploi des tables memoire metier).
- [x] Definir le schema minimal par evenement (champs communs + metadata stage).
- [x] Ajouter les index minimaux pour lecture chrono, filtre conversation, filtre tour, filtre statut.
- [x] Verrouiller une regle de retention initiale simple (pas de retention automatique pour le MVP).

### 2) Instrumentation backend MVP (ecriture)
- [x] Instrumenter `turn_start` et `turn_end`.
- [x] Instrumenter `embedding`.
- [x] Instrumenter `memory_retrieve`.
- [x] Instrumenter `summaries`.
- [x] Instrumenter `identities_read` (sources `frida` vs `user`, compteurs, `keys`/`preview` sobres, hints utilises, `truncated`).
- [x] Instrumenter `identity_write` (avec `target_side=frida|user`; ce que l'arbitre retient pour inscription: actions `add|update|override|reject|defer`, compteurs, `keys`/`preview` sobres, sans dump brut).
- [x] Instrumenter `web_search` (activation, tentative, resultat ou `skipped`, erreurs).
- [x] Instrumenter `context_build`.
- [x] Instrumenter `prompt_prepared` avec `prompt_kind` et metriques non sensibles.
- [x] Instrumenter `llm_call`.
- [x] Instrumenter `arbiter`.
- [x] Instrumenter `persist_response`.
- [x] Instrumenter `error` explicite.
- [x] Instrumenter `branch_skipped` explicite.

### 3) Backend lecture logs (consultation)
- [x] Exposer une lecture chronologique paginee des logs.
- [x] Exposer les filtres minimaux (conversation, turn, stage, status, plage temporelle).
- [x] Verrouiller le format de reponse (stable, sans dump massif par defaut).

### 4) Backend suppression logs (sans effet metier)
- [x] Verrouiller que `all_logs` est non retenu MVP et explicitement non implemente.
- [x] Implementer la suppression `conversation_logs` (par `conversation_id`).
- [x] Implementer la suppression `turn_logs` (par `conversation_id` + `turn_id`).
- [x] Verrouiller contractuellement qu'aucune suppression logs ne touche la memoire metier.
- [x] Verifier qu'aucune reconstruction opportuniste des logs n'apparait apres suppression.

### 5) UI minimale
- [x] Ajouter un bouton `Log` a cote de `Admin` dans l'UI principale.
- [x] Ajouter une page dediee logs avec reutilisation prioritaire du socle CSS/composants admin existant (pas de charte parallele).
- [x] Poser le JS futur sous `app/web/log/`.
- [x] Afficher la timeline chronologique par tour avec badges `ok/error/skipped`.
- [x] Afficher les metadonnees utiles (tokens, limites, truncation, compteurs) sans dump brut.
- [x] Exposer les actions de suppression strictement alignees sur le scope decide.

### 6) Tests / preuves
- [x] Test contrat evenement: champs obligatoires et statuts `ok/error/skipped`.
- [x] Test `prompt_kind`: presence et valeurs attendues sur les evenements concernes.
- [x] Test `identities_read`: visibilite `frida` vs `user` + forme sobre (`keys`/`preview`/`count`) sans dump massif.
- [x] Test `identity_write`: `target_side` obligatoire (`frida|user`) + visibilite de la retention arbitre (`add|update|override|reject|defer`) + forme sobre (`keys`/`preview`/`count`).
- [x] Test `web_search`: couverture `ok/error/skipped` et metadonnees minimales.
- [x] Test redaction: absence de dump brut (contexte integral, prompt integral, payloads complets).
- [x] Test refus explicite `all_logs` (MVP non retenu) sans impact memoire metier.
- [x] Test suppression logs `conversation_logs` sans impact memoire metier.
- [x] Test suppression logs `turn_logs` sans impact memoire metier.
- [x] Test non-reconstruction: apres suppression, le viewer reste vide jusqu'a nouveaux tours.
- [x] Test pipeline non-regression memory/chat/admin (la memoire metier reste intacte).

## Hors scope (MVP)
- Logs admin detailles hors pipeline chat.
- Logs Docker/systeme/stdout.
- Live tail complexe en temps reel.
- Export avance.
- Dump complet des prompts/requetes/reponses.

## Risques / vigilance
- Confusion entre observabilite et persistance metier.
- Logs trop verbeux (cout/perf/bruit) ou trop pauvres (inutilisables en debug).
- Decoupage artificiel en cases trop grosses: chaque case doit rester cochable en une tranche fermee.
- Ambiguite sur `prompt_kind` si la taxonomie n'est pas verrouillee avant instrumentation.
- Oubli d'un vrai contrat `web_search` (avec `skipped`) si on reste sur un simple flag.
- Suppression faussement "reelle" si les logs reapparaissent par reconstruction depuis la memoire.
