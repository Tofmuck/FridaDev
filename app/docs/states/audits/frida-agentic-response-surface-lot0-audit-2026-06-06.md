# Frida - Agentic Response Surface - Lot 0 audit

Date: 2026-06-06
Statut: audit docs-only, content-free
Portee: chemin actuel d'une reponse Biblio visible dans FridaDev

## Synthese

Le chemin actuel d'une reponse Biblio visible est deja un chemin de message
assistant normal quand le final lock Biblio est autorise.

Chemin court observe:

1. Biblio produit un `BiblioAnswerObject`.
2. Biblio rend un `BiblioRenderedAnswer`.
3. `BiblioFinalResponseLock` autorise ou bloque le contenu final.
4. `chat_service._biblio_assistant_response_override()` transforme le lock
   autorise en `AssistantResponseOverride`.
5. `chat_llm_flow.run_llm_exchange()` court-circuite le LLM principal si
   l'override contient un message.
6. `_run_assistant_response_override()` persiste ce contenu comme message
   assistant, avec timestamp, meta, observabilite, Memory et identite.

Donc la surface Biblio autorisee ne vit pas dans un canal visible parallele.
Elle devient `assistant_message.content` via le meme store conversationnel que
les autres reponses assistant.

Nuance importante: le message Biblio final est disponible pour les tours
suivants. Il ne peut pas etre dans le prompt LLM du tour courant, puisqu'il est
persisté apres la construction du prompt du tour courant.

## Reponse visible

| Zone | Role actuel | Statut audit |
| --- | --- | --- |
| `app/biblio/answer_object.py` | Projection du resultat Biblio en objet structure, rendu final, final lock. | Certain par code. |
| `app/biblio/answer_surface.py` | Formatage visible des extraits exacts deja autorises. | Certain par code. |
| `app/biblio/answer_resolution.py`, `answer_structure.py`, `answer_search.py`, `answer_extraction.py` | Formatage visible des familles non-extrait exact. | Certain par code, a couvrir en regression plus tard. |
| `app/biblio/chat_runtime.py` | Orchestration du tour Biblio et stockage du `final_response_lock` dans le resultat Biblio. | Certain par code. |
| `app/core/chat_service.py` | Conversion d'un lock autorise en `AssistantResponseOverride`. | Certain par code. |
| `app/core/chat_llm_flow.py` | Persistance du message assistant override et retour HTTP/stream. | Certain par code. |

`answer_surface.py` documente une frontiere utile: il formate des donnees deja
autorisees et ne choisit pas document, section, ancre ou pertinence. C'est le bon
principe a conserver.

Le futur `surface_intro` / `surface_outro` ne doit pas etre injecte dans le
prompt lane. Le meilleur point de branchement est avant le final lock visible:
dans la projection/rendu Biblio, puis verification par le lock, puis passage par
`AssistantResponseOverride`.

## Metas Biblio

Production observee:

- `BiblioFinalResponseLock.to_message_meta()` produit une meta compacte.
- `BiblioFinalResponseLock.to_observability()` produit une observabilite
  content-free.
- `chat_service._biblio_assistant_response_override()` transmet ces champs a
  `AssistantResponseOverride`.
- `_run_assistant_response_override()` passe `meta` a
  `conv_store.append_message()`.
- La table conversationnelle conserve `meta` en JSONB.

Les metas ne remplacent pas le contenu visible: l'override contient toujours un
`content` assistant distinct. Si le lock n'est pas autorise ou si le contenu est
vide, aucun override visible n'est produit.

## Timestamp et contexte LLM

Creation / persistence:

- `_run_assistant_response_override()` cree `updated_at = now_iso_func()`.
- Ce timestamp est passe a `append_message(..., timestamp=updated_at)`.
- `save_conversation(..., updated_at=updated_at)` persiste le tour.
- Le schema conversationnel stocke un timestamp non nul pour les messages.

Reprise dans le contexte:

- `conversations_prompt_window.build_prompt_messages()` selectionne les messages
  `user` / `assistant` eligibles.
- Le message assistant Biblio, une fois sauve, est eligible au tour suivant sauf
  coupure par resume.
- Le constructeur de fenetre ajoute les labels de silence et le label Delta-T
  a partir du timestamp du message.

Conclusion statique: le timestamp Biblio est disponible au LLM au tour suivant
quand le message reste dans la fenetre de contexte directe. Si le message est
couvert par un resume, la reprise depend du chemin resume / Memory. Cela doit
etre prouve plus tard en live, sans le deduire seulement de la DB.

## Memory, embeddings et resume

Ce qui est certain par code:

- `_run_assistant_response_override()` appelle
  `memory_store.save_new_traces(conversation)` apres la sauvegarde du message.
- `memory_traces_summaries._message_is_trace_eligible()` accepte les roles
  `user` et `assistant`, hors assistant interrompu, si le contenu est non vide.
- `save_new_traces()` insere les traces avec role, contenu, timestamp,
  embedding si disponible, et `summary_id`.
- `summarizer._raw_dialogue()` inclut les messages `user` / `assistant` non
  encore resumes.

Ce qui reste a prouver en live:

- que le message Biblio final est effectivement observe par Memory dans une
  conversation reelle apres ce chemin;
- que l'embedding est cree ou que l'echec embedding reste non bloquant selon la
  configuration runtime;
- que le resume reprend correctement la reponse Biblio quand elle sort de la
  fenetre directe;
- que le traitement temporel reste visible dans le payload LLM d'un tour de
  reprise, et pas seulement dans la ligne DB.

## Canal parallele et double reponse

Pas de double reponse visible observee dans le chemin final-lock:

- `run_llm_exchange()` retourne immediatement
  `_run_assistant_response_override()` quand l'override est present et non vide.
- Le LLM principal ne produit donc pas une seconde reponse visible dans ce cas.

Point de vigilance:

- `biblio_chat_runtime.inject_biblio_prompt_lane()` existe aussi.
- Sur les chemins sans final lock visible, cette lane peut informer le LLM
  principal.
- Le futur mecanisme de surface ne doit pas brancher l'enveloppe vernaculaire
  dans cette lane, sinon il pourrait recreer un canal parallele ou une voix
  indirecte.

## Surface visible technique

Etat observe:

- Le chemin exact autorise passe par `answer_surface.exact_excerpt_lines()`.
- Les metas techniques restent dans `message.meta` et observabilite.
- Les surfaces structurelles passent par les renderers par famille.

Risque restant:

- Un futur ajout fait trop haut dans `chat_service.py` pourrait reintroduire des
  reason codes, ids, modes ou statuts machine dans le visible.
- Un futur ajout fait trop bas dans `chat_llm_flow.py` modifierait tous les
  assistants, pas seulement Biblio.

## Point de branchement recommande

Brancher proprement:

- dans le contrat agentique Biblio, en ajoutant les champs de surface au resultat
  structure;
- dans le rendu Biblio, en assemblant intro, surface existante, limites et outro;
- avant `build_final_response_lock()`, afin que le contenu visible final reste
  verrouillable;
- en conservant `AssistantResponseOverride` comme chemin de persistance normal.

Ne pas brancher:

- dans `conversations_prompt_window.py`;
- dans `memory_store.py` ou les chemins Memory;
- dans le prompt lane Biblio;
- dans `chat_llm_flow.py` comme transformation stylistique globale;
- dans un validateur regex ou un filtre de voix.

## Mapping Lot 0

- Assemblage visible localise: oui.
- Metas Biblio localisees: oui.
- Message assistant DB verifie par code: oui.
- Contexte recent verifie par code: oui.
- Timestamp / Delta-T verifie par code: oui, preuve live future requise pour le
  payload observe.
- Memory verifie par code: oui, preuve live future requise.
- Embeddings verifies par code: eligible, preuve live future requise.
- Resume verifie par code: eligible, preuve live future requise.
- Diagnostic content-free produit: oui.
- Runtime modifie: non.

## Risques pour les lots suivants

- Confondre intro/outro avec un canal prompt supplementaire.
- Laisser le LLM principal reecrire ou completer un exact verrouille.
- Brancher une enveloppe visible apres final lock, donc hors garde-fou.
- Prouver seulement la DB et oublier le contexte LLM timestampé.
- Supposer Memory/embeddings/resume sans preuve live.
- Reintroduire une surface visible technique en assemblant trop pres de
  `chat_service.py`.
