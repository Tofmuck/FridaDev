# Log Module TODO (Frida)

## 1) Objectif
- Definir un module de logs applicatifs consultables en UI pour suivre un tour de chat.
- Garder un module simple, lisible, et strictement separe de la memoire metier.
- Eviter deux extremes: logs trop verbeux (dump brut) ou logs trop pauvres (inexploitables).

## 2) Invariants non negociables
- Le module de logs est un module d'observabilite, pas une source metier.
- Effacer les logs ne doit jamais supprimer conversations, traces, summaries, identities, context hints.
- La memoire metier doit continuer a fonctionner meme apres suppression totale des logs.
- Les logs doivent etre stockes a part de la memoire metier.
- Les logs sont chronologiques et relies a un tour (`conversation_id`, `turn_id`, `ts`).
- Statuts minimaux obligatoires: `ok`, `error`, `skipped`.
- Pas de dump massif par defaut (prompt complet, contexte complet, etc.).
- Pour le contexte: loguer metadonnees utiles (`tokens`, `limit`, `truncated`, compteurs), pas le contenu massif.
- UI cible: bouton `Log` a cote de `Admin`, page dediee, meme langage visuel global que l'admin, JS futur sous `app/web/log/`.
- Suppression reelle: si les logs sont supprimes, ils ne reapparaissent pas par reconstruction opportuniste depuis les conversations.

## 3) Frontiere memoire vs logs
- Memoire metier (source metier): conversations/messages, traces, summaries, identities, conflicts, arbiter_decisions.
- Logs applicatifs (source observabilite): evenements de pipeline, compteurs, statuts, erreurs, branches sautees.
- Interdiction: reutiliser les donnees metier pour "reconstruire" des logs effaces.
- Interdiction: utiliser les logs comme mecanisme de reprise metier.

## 4) MVP retenu (borne)
- Perimetre: pipeline chat par tour uniquement.
- Couverture MVP: creation de logs d'evenements, consultation simple en UI, suppression explicite des logs.
- Non couvert au MVP: logs admin detailles, logs Docker/systeme, live tail complexe, export avance, payloads complets.

## 5) Hors scope explicite
- Aucun changement des routes chat metier.
- Aucun changement du schema memoire metier.
- Aucun changement de la persistance conversationnelle.
- Aucune plateforme observabilite "globale" (ELK, OpenTelemetry complet, etc.) dans ce lot.

## 6) Catalogue initial des evenements (MVP)
Pour chaque evenement, le niveau de detail doit rester minimal utile.

### 6.1 Evenements obligatoires
- `turn_start`
  - Statut: `ok`
  - Champs mini: `conversation_id`, `turn_id`, `ts`, `user_msg_chars`, `web_search_enabled`
  - Interdit: dump du message utilisateur complet par defaut

- `embedding`
  - Statut: `ok|error|skipped`
  - Champs mini: `mode` (`query|passage`), `provider`, `dimensions`, `duration_ms`, `error_code`
  - Interdit: dump du vecteur

- `memory_retrieve`
  - Statut: `ok|error|skipped`
  - Champs mini: `top_k_requested`, `top_k_returned`, `duration_ms`, `error_code`
  - Interdit: dump complet des traces

- `summaries`
  - Statut: `ok|error|skipped`
  - Champs mini: `active_summary_present`, `summary_count_used`, `duration_ms`, `error_code`
  - Interdit: dump du contenu integral des summaries

- `identities_context_hints`
  - Statut: `ok|error|skipped`
  - Champs mini: `identities_used`, `context_hints_used`, `hints_truncated`, `duration_ms`, `error_code`
  - Interdit: dump brut des blocs identite/hints

- `context_build`
  - Statut: `ok|error|skipped`
  - Champs mini: `context_tokens`, `token_limit`, `truncated`, `duration_ms`, `error_code`
  - Interdit: dump du contexte complet (20k/35k tokens)

- `prompt_prepared`
  - Statut: `ok|error`
  - Champs mini: `messages_count`, `estimated_prompt_tokens`, `memory_items_used`, `duration_ms`
  - Interdit: payload complet prompt

- `llm_call`
  - Statut: `ok|error|skipped`
  - Champs mini: `model`, `mode` (`sync|stream`), `timeout_s`, `duration_ms`, `response_chars`, `error_code`
  - Interdit: dump complet requete/reponse

- `arbiter`
  - Statut: `ok|error|skipped`
  - Champs mini: `raw_candidates`, `kept_candidates`, `mode` (`shadow|enforced|off`), `duration_ms`, `error_code`
  - Interdit: dump integral des decisions texte

- `persist_response`
  - Statut: `ok|error|skipped`
  - Champs mini: `conversation_saved`, `messages_written`, `duration_ms`, `error_code`
  - Interdit: dump des messages persistes

- `turn_end`
  - Statut: `ok|error`
  - Champs mini: `conversation_id`, `turn_id`, `total_duration_ms`, `final_status`

- `error` (explicite)
  - Statut: `error`
  - Champs mini: `stage`, `error_code`, `error_class`, `message_short`
  - Interdit: stacktrace complete brute en UI par defaut

- `branch_skipped` (explicite)
  - Statut: `skipped`
  - Champs mini: `stage`, `reason_code`, `reason_short`

### 6.2 Identifiants minimaux communs
- `conversation_id`
- `turn_id` (ID unique par tour)
- `event_id`
- `ts` (timestamp ISO UTC)
- `stage` (nom evenement)
- `status` (`ok|error|skipped`)

## 7) Semantique de suppression
- Action utilisateur "effacer logs": suppression physique des enregistrements du module logs cible.
- La suppression n'impacte jamais les tables/fichiers metier.
- Aucune reconstruction automatique depuis conversations/traces/summaries.
- Verification explicite requise: apres suppression, le viewer reste vide jusqu'a nouveaux tours.

## 8) Decoupage d'implementation propose (petites tranches)
- Tranche A (contrat)
  - Definir schema d'evenements et enum statuts.
  - Definir API interne d'ecriture de log (sans dump brut).
  - Definir regles de redaction.

- Tranche B (persistence logs MVP)
  - Ajouter stockage dedie logs (separe memoire metier).
  - Ecriture des evenements `turn_start` a `turn_end` + `error` + `branch_skipped`.

- Tranche C (consultation backend)
  - Route(s) dediee(s) lecture paginee des logs par conversation/turn/date.
  - Route suppression logs (scope explicite, pas de side effect metier).

- Tranche D (UI minimale)
  - Bouton `Log` dans UI principale a cote de `Admin`.
  - Page dediee de consultation simple (liste chronologique, filtres de base).
  - Reutilisation du langage visuel admin; JS dans `app/web/log/`.

- Tranche E (preuves de non confusion)
  - Tests de non regression: suppression logs != suppression memoire.
  - Tests de non reconstruction apres suppression.
  - Tests `skipped` explicites.

## 9) Strategie de test / preuve
- Tests backend:
  - ecriture d'evenements par tour (ordre chrono et statuts)
  - suppression logs et verification qu'aucune donnee metier ne disparait
  - verification qu'aucune reconstruction opportuniste n'a lieu
- Tests UI:
  - navigation bouton `Log`
  - affichage des statuts `ok/error/skipped`
  - absence de contenu massif dump par defaut
- Garde-fous source:
  - assertions sur champs autorises par evenement
  - assertions d'absence de dump brut (prompt complet, contexte complet)

## 10) Risques et vigilances
- Risque de confusion logs vs memoire si noms de routes/tables ambigus.
- Risque de bruit excessif si chaque etape logue du contenu brut.
- Risque de logs trop pauvres si seuls des "ok" sans compteurs sont stockes.
- Risque de couplage artificiel avec `admin_logs` existant (JSONL technique) au lieu d'un module logs produit cible.
- Risque UX: suppression percue comme "cache vide" alors qu'elle doit etre reelle et irreversible pour les logs.
- Risque performance si la volumetrie n'est pas bornee (pagination, retention, niveau detail).

## 11) Decision documentaire
- Emplacement retenu: `app/docs/todo-todo/admin/log-module-todo.md`.
- Motif: chantier admin actif (UI + API de consultation), non archive, non spec stable finale.
