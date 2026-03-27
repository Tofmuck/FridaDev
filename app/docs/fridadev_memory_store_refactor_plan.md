# FridaDev Memory Store Refactor Plan (Phase 8 bis)

## 1) Contexte et objectif
- `app/memory/memory_store.py` reste le principal hotspot monolithique (1831 lignes, ~41 fonctions).
- Cette phase prépare un découpage **pipeline-first** sans changement métier:
  - même contrat chat/admin herméneutique,
  - même persistance SQL,
  - même grammaire de patch (logger `frida.*`, typage cohérent, pas de format global).

## 2) Pipeline actuel (cartographie de responsabilités)

| Bloc pipeline | Fonctions principales dans `memory_store.py` | Appelants clés |
| --- | --- | --- |
| Infra mémoire | `_conn`, `_runtime_database_*`, `_runtime_embedding_*`, `init_db`, `embed` | bootstrap `server.py`, tous les blocs mémoire |
| Traces + summaries | `save_new_traces`, `retrieve`, `save_summary`, `update_traces_summary_id`, `get_summary_for_trace`, `enrich_traces_with_summaries` | `chat_llm_flow`, `chat_memory_flow`, `summarizer` |
| Lecture contexte | `get_identities`, `get_recent_context_hints` | `chat_memory_flow`, `admin_hermeneutics_service` |
| Audit arbitre | `record_arbiter_decisions`, `get_arbiter_decisions`, `get_hermeneutic_kpis` | `chat_memory_flow`, `admin_hermeneutics_service` |
| Identities write path | `record_identity_evidence`, `add_identity`, `set_identity_override`, `relabel_identity`, `persist_identity_entries` | `chat_memory_flow`, `admin_hermeneutics_service` |
| Identity dynamics | `preview_identity_entries`, `detect_and_record_conflicts`, `_apply_defer_policy_for_content`, `_expire_stale_deferred_global`, `decay_identities`, `reactivate_identities` | `chat_memory_flow`, flux identité |

## 3) Pourquoi le module reste monolithique
- Mélange dans un seul fichier de:
  - infra DB/runtime,
  - lecture/écriture métier,
  - règles de policy identité,
  - audit arbitre,
  - dynamique d’état identité.
- Couplage fort entre write path identité et dynamics (conflits/defer/promote), ce qui rend les modifications locales risquées.
- Surface d’import unique pratique, mais charge cognitive trop élevée pour un contributeur humain.

## 4) Découpage cible retenu (pipeline-first)

### 4.1 Modules cibles
- `memory_store_infra.py`
  - connexion DB runtime, accès settings runtime embedding, bootstrap schéma, adapter embedding.
- `memory_traces_summaries.py`
  - traces retrieval/persistence, summaries persistence/enrichment.
- `memory_context_read.py`
  - lecture identities et sélection context hints.
- `memory_arbiter_audit.py`
  - persistance/lecture décisions arbitre + KPI herméneutiques.
- `memory_identity_write.py`
  - evidence + add/relabel/override + orchestration persist identity entries.
- `memory_identity_dynamics.py`
  - preview policy, conflits, defer/promote/reject, decay/reactivation.

### 4.2 Façade de transition
- `memory_store.py` reste **façade publique** pendant la migration:
  - exports stables pour les appelants existants (`chat_memory_flow`, `admin_hermeneutics_service`, etc.),
  - composition explicite vers les sous-modules,
  - pas de logique métier nouvelle dans la façade.

## 5) Variantes rejetées
- Découpage “par table SQL uniquement”:
  - rejeté car ne suit pas le pipeline réel côté chat/admin.
- Découpage “read/write” binaire:
  - rejeté car masque les frontières critiques (audit arbitre vs dynamics identité).
- Module générique `utils/helpers`:
  - rejeté pour éviter un nouveau fourre-tout.

## 6) Invariants de grammaire à préserver
- Namespace logger: `frida.*` uniquement.
- Typage harmonisé localement, sans passe globale.
- Pas de commit “format global”.
- Pas de sous-module fourre-tout.
- Lisibilité humaine prioritaire: frontières explicites et stables.

## 7) Ordre d’exécution recommandé (tranches)
1. Cartographie figée + façade publique explicite (sans extraction comportementale).
2. Extraction infra mémoire.
3. Extraction traces + summaries.
4. Extraction lecture contexte + audit arbitre.
5. Extraction identities write path.
6. Extraction identity dynamics + réduction finale de la façade.
7. Consolidation tests ciblés memory/chat/admin herméneutique.

## 8) Critères de fermeture de la phase
- `memory_store.py` n’est plus un god module.
- Les contrats métier sont inchangés et couverts par tests de non-régression.
- Les nouveaux modules suivent la grammaire Phase 8 (conventions + lisibilité).
