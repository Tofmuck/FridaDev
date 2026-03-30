# FridaDev - conv_store structural refactor TODO

## 1) Objet
Ce document prepare un refactor structurel de `app/core/conv_store.py`.

But:
- separer des responsabilites metier aujourd'hui entassees;
- garder un pipeline lisible d'un seul regard;
- rester strictement neutre sur la doctrine du noeud hermeneutique.

Ce document ne lance pas le refactor: il fixe un plan executable, ferme, et reversible.

## 2) Diagnostic (etat reel du code)
`conv_store.py` melange aujourd'hui plusieurs familles metier dans le meme module:

1. Persistance conversation DB-first:
- creation/lecture/ecriture conversation (`new_conversation`, `load_conversation`, `save_conversation`, `append_message`);
- catalogue et messages DB (`conversations`, `conversation_messages`, upsert/list/read/rename/soft delete).

2. Assemblage prompt conversationnel:
- fenetre glissante token (`build_prompt_messages`);
- injection resume actif, contexte souvenir, traces memoire, indices contextuels.

3. Temporalite de tour:
- labels Delta-T (`delta_t_label`);
- marqueurs de silence (`_silence_label`).

4. Operations de maintenance/lifecycle:
- init schema conversations/messages;
- sync legacy JSON -> DB, inventaire stockage;
- suppression forte conversation et donnees associees (`delete_conversation`).

Impact:
- charge cognitive elevee;
- frontieres de responsabilite floues;
- surface de regression plus large que necessaire;
- terrain moins lisible pour les prochains lots (notamment autour du point d'insertion du futur noeud, deja fixe dans `chat_service`).

## 3) Principes de refactor
- Decoupage par logique metier, pas par convenance technique.
- Premier passage sans changement comportemental (contrats et sorties stables).
- `conv_store.py` reste facade de compatibilite pendant la transition.
- Pas de reouverture doctrinale (noeud, regimes, directives): refactor purement structurel.
- Pas d'eclatement excessif: cible 3 fichiers extraits.
- Etape 0 bloquante: cartographier symboles publics, appelants reels et facade de transition avant toute extraction.
- Reference Etape 0: `app/docs/todo-todo/refactors/fridadev-conv-store-symbols-cartography.md`.

## 4) Decoupage cible propose (3 fichiers)
### A. `app/core/conversations_store.py`
Role:
- coeur persistence conversation/catalog/messages.

Responsabilites:
- normalisation conversation/message utile a la persistence;
- CRUD conversation DB-first et catalogue (`load/read/save/list/get_summary/rename/soft_delete`);
- lecture/ecriture `conversation_messages`.

Pourquoi ce groupe va ensemble:
- meme frontiere metier: etat conversationnel durable.
- meme dependance dominante: acces DB runtime.

Ce qui sort de `conv_store.py`:
- fonctions persistence/conversation/catalog/messages.

Ce qui reste ailleurs:
- assemblage prompt (fichier B), maintenance destructive/legacy (fichier C).

### B. `app/core/conversations_prompt_window.py`
Role:
- reconstruction du prompt conversationnel a partir de l'etat et du contexte.

Responsabilites:
- `build_prompt_messages`;
- selection fenetre token;
- injection resume actif, contexte souvenirs, traces memoire, context hints;
- labels temporels et marqueurs de silence (`delta_t_label`, `_silence_label`) utilises a l'assemblage.

Pourquoi ce groupe va ensemble:
- meme sortie metier: messages prompt finalises pour le LLM.
- temporalite Delta/silence est consommee ici, donc lisibilite meilleure si locale au builder.

Ce qui sort de `conv_store.py`:
- bloc prompt + helpers de formatage associes.

Ce qui reste ailleurs:
- persistence DB (fichier A), maintenance/lifecycle (fichier C).

### C. `app/core/conversations_maintenance.py`
Role:
- operations operateur et lifecycle non nominal.

Responsabilites:
- init schema conversations/messages;
- sync legacy JSON -> DB + inventaire stockage;
- suppression forte conversation (`delete_conversation`) et nettoyage des tables liees.

Pourquoi ce groupe va ensemble:
- operations admin/maintenance distinctes du flux nominal chat;
- responsabilites potentiellement destructives ou de migration, a isoler du path runtime principal.

Ce qui sort de `conv_store.py`:
- init/sync/inventory/delete fort.

Ce qui reste ailleurs:
- persistence nominale (fichier A), prompt window (fichier B).

## 5) Ordre d'extraction recommande
0. Valider la cartographie bloquante (`fridadev-conv-store-symbols-cartography.md`).
1. Figer la facade de transition dans `conv_store.py` (surface publique explicite + sections metier lisibles, sans extraction).
2. Extraire fichier B (`conversations_prompt_window.py`) avec wrappers de compatibilite dans `conv_store.py`. *(realisee)*
3. Extraire fichier A (`conversations_store.py`) en gardant les symboles publics actuels exposes via `conv_store.py`.
4. Extraire fichier C (`conversations_maintenance.py`) et isoler les operations destructives/legacy.
5. Nettoyer `conv_store.py` en facade explicite de delegation (imports + forwarding), sans rupture d'API.

## 6) Garde-fous (runtime et regression)
- Aucun changement de contrat public `conv_store` au premier passage.
- Aucune modification de schema DB dans ce refactor.
- Conserver exactement:
  - ordre d'assemblage prompt;
  - formats Delta-T/silence;
  - semantics de soft delete vs delete fort.
- Eviter les dependances circulaires entre A/B/C.
- Garder un point d'entree unique lisible: `conv_store.py` facade.

Couverture minimale a verifier a chaque etape:
- `app/tests/unit/core/test_conv_store_time_labels.py`
- `app/tests/unit/chat/test_chat_session_flow.py`
- `app/tests/unit/chat/test_chat_llm_flow.py`
- `app/tests/test_conv_store_phase4_database.py`
- `app/tests/test_server_phase13.py`

## 7) Lien explicite avec le chantier hermeneutic node
- Ce refactor est un assainissement structurel prealable.
- Il ne modifie pas les 9 lots du TODO noeud.
- Il ne change pas le point d'insertion deja fixe (`prepare_memory_context(...)` puis `build_prompt_messages(...)`).
- Il ne change aucune doctrine (regimes, jugements, validation).
- Il rend simplement les surfaces plus lisibles pour brancher la suite proprement.

## 8) Checklist executable du chantier
- [x] Etape 0 bloquante: cartographier les symbols publics `conv_store`, les appelants reels et la facade de transition (`todo-todo/refactors/fridadev-conv-store-symbols-cartography.md`).
- [x] Etape 1: figer la facade de transition dans `conv_store.py` (surface publique explicite + sections metier; pas d'extraction).
- [x] Extraire `conversations_prompt_window.py` sans changer les sorties de `build_prompt_messages`.
- [x] Re-router `delta_t_label` et `_silence_label` via la nouvelle unite sans changer les chaines.
- [ ] Extraire `conversations_store.py` et garder les routes/chat flows inchanges.
- [ ] Extraire `conversations_maintenance.py` avec `init_*`, `sync_*`, `get_storage_counts`, `delete_conversation`.
- [ ] Conserver `conv_store.py` comme facade de delegation (imports explicites, pas de logique remelangee).
- [ ] Executer la batterie minimale de tests a chaque etape d'extraction.
- [ ] Finaliser un patch neutre doctrinalement et sans changement comportemental observable.
