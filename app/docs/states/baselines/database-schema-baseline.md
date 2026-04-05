# Baseline schema de base - FridaDev

Date de reference: 2026-03-29

## 1. Objet

Cette baseline decrit le schema physique observe dans le repo `FridaDev` a date.

Elle couvre:
- tables principales creees par le runtime;
- schema SQL utilise (`public` et `observability`);
- champs principaux et indexes notables;
- relations SQL explicites et relations metier non forcees en FK.

Elle ne couvre pas:
- le SQL exhaustif ligne par ligne;
- les scripts de migration executables;
- les conventions applicatives hors persistance.

## 2. Sources de verite

Sources lues pour cette baseline:
- `app/core/conv_store.py`
- `app/memory/memory_store_infra.py`
- `app/admin/sql/runtime_settings_v1.sql`
- `app/observability/log_store.py`

## 3. Pre-requis PostgreSQL

Extensions utilisees:
- `pgcrypto` (runtime settings + memory tables UUID/crypto);
- `vector` (pgvector, pour embeddings memoire).

Schemas:
- `public`: conversations, memoire/identite, runtime settings;
- `observability`: `chat_log_events`.

## 4. Vue d'ensemble

| Domaine | Schema | Table | Role principal | Source |
| --- | --- | --- | --- | --- |
| Conversations | `public` | `conversations` | Catalogue conversations (titre, dates, compteurs, suppression logique) | `app/core/conv_store.py` |
| Conversations | `public` | `conversation_messages` | Messages ordonnes par conversation | `app/core/conv_store.py` |
| Memoire | `public` | `traces` | Traces dialogue avec embedding | `app/memory/memory_store_infra.py` |
| Memoire | `public` | `summaries` | Resumes periodiques avec embedding | `app/memory/memory_store_infra.py` |
| Identite | `public` | `identity_mutables` | Source canonique mutable narrative, une ligne par sujet | `app/memory/memory_store_infra.py` |
| Identite | `public` | `identities` | Etat identitaire durable/dynamique fragmentaire (legacy) | `app/memory/memory_store_infra.py` |
| Identite | `public` | `identity_evidence` | Evidences identitaires horodatees | `app/memory/memory_store_infra.py` |
| Arbitrage memoire | `public` | `arbiter_decisions` | Decisions keep/reject sur traces | `app/memory/memory_store_infra.py` |
| Identite | `public` | `identity_conflicts` | Conflits inter-identites detectes | `app/memory/memory_store_infra.py` |
| Runtime admin | `public` | `runtime_settings` | Valeurs runtime sectionnees (JSONB) | `app/admin/sql/runtime_settings_v1.sql` |
| Runtime admin | `public` | `runtime_settings_history` | Historique des modifications runtime | `app/admin/sql/runtime_settings_v1.sql` |
| Observabilite | `observability` | `chat_log_events` | Evenements de tour chat (logs structurés) | `app/observability/log_store.py` |

## 5. Blocs par domaine

## 5.1 Conversations (`app/core/conv_store.py`)

Table `public.conversations`
- Champs principaux:
- `id` (UUID, PK)
- `title` (TEXT)
- `created_at`, `updated_at` (TIMESTAMPTZ)
- `message_count` (INTEGER)
- `last_message_preview` (TEXT)
- `deleted_at` (TIMESTAMPTZ, suppression logique)
- Index notables:
- `conversations_updated_idx (updated_at DESC)`
- `conversations_deleted_idx (deleted_at)`

Table `public.conversation_messages`
- Champs principaux:
- `conversation_id` (UUID, FK vers `conversations.id`)
- `seq` (INTEGER, ordre)
- `role`, `content`, `timestamp`
- `summarized_by`, `embedded`, `meta` (JSONB)
- Cle primaire:
- `(conversation_id, seq)`
- Index notable:
- `conversation_messages_conv_ts_idx (conversation_id, timestamp DESC)`

## 5.2 Memoire / identite (`app/memory/memory_store_infra.py`)

Table `public.traces`
- Champs principaux:
- `id` (UUID, PK)
- `conversation_id`, `role`, `content`, `timestamp`
- `embedding` (`vector(dim)`)
- `summary_id` (TEXT)
- Index notable:
- `traces_embedding_hnsw` (HNSW cosine)

Table `public.summaries`
- Champs principaux:
- `id` (UUID, PK)
- `conversation_id`, `start_ts`, `end_ts`
- `content`
- `embedding` (`vector(dim)`)
- Index notable:
- `summaries_embedding_hnsw` (HNSW cosine)

Table `public.identity_mutables`
- Champs principaux:
- `subject` (TEXT, PK, restreint a `llm|user`)
- `content`
- `source_trace_id` (UUID, non FK)
- `updated_by`, `update_reason`
- `created_ts`, `updated_ts`
- Index notable:
- `identity_mutables_updated_ts_idx`

Table `public.identities`
- Champs principaux:
- `id` (UUID, PK)
- `subject`, `content`, `weight`
- `created_ts`, `last_seen_ts`
- `source_trace_id` (UUID, non FK)
- Champs de qualification: `stability`, `utterance_mode`, `recurrence`, `scope`, `evidence_kind`, `confidence`, `status`
- Champs override: `override_state`, `override_reason`, `override_actor`, `override_ts`
- Index notables:
- `identities_subject_weight_idx`
- `identities_status_idx`
- `identities_content_norm_idx`
- `identities_created_ts_idx`

Table `public.identity_evidence`
- Champs principaux:
- `id` (UUID, PK)
- `conversation_id`
- `subject`, `content`, `content_norm`
- `stability`, `utterance_mode`, `recurrence`, `scope`, `evidence_kind`, `confidence`, `status`
- `reason`, `source_trace_id`, `created_ts`
- Index notables:
- `identity_evidence_conversation_created_idx`
- `identity_evidence_status_idx`
- `identity_evidence_content_norm_idx`

Table `public.arbiter_decisions`
- Champs principaux:
- `id` (UUID, PK)
- `conversation_id`, `candidate_id`
- donnees candidat: `candidate_role`, `candidate_content`, `candidate_ts`, `candidate_score`
- decision: `keep`, `semantic_relevance`, `contextual_gain`, `redundant_with_recent`, `reason`, `model`, `decision_source`
- `created_ts`
- Index notables:
- `arbiter_decisions_conversation_created_idx`
- `arbiter_decisions_keep_idx`

Table `public.identity_conflicts`
- Champs principaux:
- `id` (UUID, PK)
- `identity_id_a`, `identity_id_b` (UUID, non FK)
- `confidence_conflict`, `reason`
- `resolved_state`, `created_ts`, `resolved_ts`
- Index notables:
- `identity_conflicts_open_idx`
- `identity_conflicts_pair_idx`

## 5.3 Admin runtime (`app/admin/sql/runtime_settings_v1.sql`)

Table `public.runtime_settings`
- Champs principaux:
- `section` (TEXT, PK)
- `schema_version`, `updated_at`, `updated_by`
- `payload` (JSONB)
- Contraintes notables:
- sections autorisees via `runtime_settings_section_chk`
- sections runtime actuelles: `main_model`, `arbiter_model`, `summary_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`
- `payload` doit etre un objet JSON via `runtime_settings_payload_object_chk`
- Index notable:
- `runtime_settings_updated_at_idx`

Table `public.runtime_settings_history`
- Champs principaux:
- `id` (UUID, PK)
- `section`, `schema_version`
- `changed_at`, `changed_by`
- `payload_before`, `payload_after` (JSONB)
- Contraintes notables:
- section restreinte a la meme liste que `runtime_settings`
- `payload_before` et `payload_after` doivent etre des objets JSON
- Index notable:
- `runtime_settings_history_section_changed_at_idx`

## 5.4 Observabilite (`app/observability/log_store.py`)

Table `observability.chat_log_events`
- Champs principaux:
- `event_id` (TEXT, PK)
- `conversation_id`, `turn_id`
- `ts`, `stage`, `status`
- `duration_ms`
- `payload_json` (JSONB)
- `created_ts`
- Contraintes notables:
- `status` contraint a `ok|error|skipped`
- Index notables:
- `chat_log_events_ts_idx`
- `chat_log_events_conversation_ts_idx`
- `chat_log_events_conversation_turn_ts_idx`
- `chat_log_events_status_ts_idx`

## 6. Relations utiles

Relations SQL explicites:
- `conversation_messages.conversation_id` -> `conversations.id` (FK, `ON DELETE CASCADE`).

Relations metier non forcees en FK (etat actuel):
- `traces.summary_id` reference logiquement `summaries.id`.
- `identity_mutables.source_trace_id` reference logiquement `traces.id`.
- `identities.source_trace_id` reference logiquement `traces.id`.
- `identity_evidence.source_trace_id` reference logiquement `traces.id`.
- `arbiter_decisions.conversation_id` reference logiquement une conversation.
- `identity_conflicts.identity_id_a` / `identity_id_b` referencent logiquement `identities.id`.

## 7. Frontieres

Cette baseline est un document de lecture, pas une migration executable.

Regle de maintenance:
- toute evolution physique durable DB (table, colonne, index, schema, relation) doit mettre a jour cette baseline dans le meme patch.
