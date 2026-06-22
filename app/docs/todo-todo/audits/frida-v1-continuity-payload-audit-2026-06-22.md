# Frida V1 - Audit continuité conversationnelle et payload modèle - 2026-06-22

## Verdict court

Frida V1 dispose deja d'une charpente forte pour produire une reponse coherente dans une conversation longue: prompt systeme augmente, identite statique et mutable, memoire semantique, resumes, fenetre recente, garde hermeneutique, lanes Documents/Notes/Biblio/Agenda/Web et observabilite content-free.

En revanche, le depot ne contient pas encore de surface durable explicite qui porte la continuite de ton, methode, relation, presence et habitudes dialogiques entre une conversation terminee et une nouvelle conversation. Aujourd'hui, une nouvelle conversation recupere surtout le prompt statique, l'identite statique/mutable et une selection de memoire factuelle; elle ne recupere pas un "profil de continuite" dedie.

L'audit ne conclut pas a un bug runtime immediat. Il conclut a un manque produit/architecture pour Frida V1: la continuite inter-conversations est emergente, fragile et non testee comme telle.

## Périmètre

Audit read-only du payload logique envoye aux modeles et des surfaces qui influencent la continuite conversationnelle Frida V1:

- chat principal et modele visible;
- arbitres, agents secondaires, memoire, identite, resumes;
- contexte conversationnel, nouvelle conversation vs conversation longue;
- lanes Documents, Notes, Exports, Images, Biblio, Agenda, Web, Adobe docs;
- runtime settings, feature flags, budgets, exclusions, ordre d'injection;
- tests existants qui prouvent ou ne prouvent pas ces contrats.

## Non-objectifs

- Pas de patch runtime.
- Pas de capsule de continuité.
- Pas de provider live.
- Pas de dump de payload brut.
- Pas de spec normative nouvelle.
- Pas de rebuild Docker.
- Pas de migration, reset, purge, backfill ou modification DB.
- Pas de lecture de contenu utilisateur brut, document brut, note Markdown reelle, passage Biblio reel, export reel ou image/base64 reelle.

## Méthode

1. Verification de branche et etat Git.
2. Creation immediate du fichier d'audit demande.
3. Relecture des documents d'ancrage imposes.
4. Recherche large par `rg` sur les termes payload/prompt/messages/model/memory/identity/summary/lane.
5. Relecture ciblee du code qui construit les appels modele et les lanes.
6. Relecture ciblee de tests chat, memory, identity, agenda, biblio, documents, notes, images.
7. Cartographie logique content-free, sans capture runtime et sans payload brut.
8. Formulation des findings et lots suivants sans patch runtime.

Question pre-patch obligatoire: existe-t-il un meilleur plan ? Non. Le plan minimal, plus sur et conforme a la consigne etait de creer uniquement ce fichier d'audit puis d'executer l'audit read-only.

## Sources relues

Documents principaux:

- `AGENTS.md`
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/todo-done/audits/model-prompt-payload-interpretation-audit-2026-05-16.md`
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`
- `app/docs/states/specs/mutable-identity-judge-contract.md`
- `app/docs/states/policies/identity-new-contract-plan.md`
- `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- `app/docs/states/specs/frida-v1-agentic-observability-contract.md`

Specs V1 relues pour influence prompt/lanes:

- `app/docs/states/specs/active-conversation-documents-contract.md`
- `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- `app/docs/states/specs/frida-v1-exports-contract.md`
- `app/docs/states/specs/frida-v1-generated-images-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-agenda-agent-contract.md`

Code relu:

- `app/core/chat_service.py`
- `app/core/chat_session_flow.py`
- `app/core/chat_prompt_context.py`
- `app/core/chat_llm_flow.py`
- `app/core/llm_client.py`
- `app/core/conversations_prompt_window.py`
- `app/core/chat_memory_flow.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/workspace_folder_notes_prompt_lane.py`
- `app/core/adobe_docs_prompt_lane.py`
- `app/memory/summarizer.py`
- `app/memory/arbiter.py`
- `app/memory/memory_identity_periodic_agent.py`
- `app/memory/mutable_identity_judge_v2.py`
- `app/identity/identity.py`
- `app/identity/active_identity_projection.py`
- `app/biblio/chat_runtime.py`
- `app/biblio/prompt_lane.py`
- `app/biblio/librarian_agent_openrouter.py`
- `app/biblio/librarian_agent_runtime.py`
- `app/biblio/librarian_agent_bridge.py`
- `app/agenda/chat_runtime.py`
- `app/agenda/agent_openrouter.py`
- `app/tools/web_search.py`
- `app/tools/web_search_discovery.py`
- `app/tools/image_generation.py`
- `app/core/stimmung_agent.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/config.py`
- `app/server.py`

Tests relus ou inventories:

- `app/tests/unit/chat/test_chat_session_flow.py`
- `app/tests/unit/chat/test_chat_prompt_context.py`
- `app/tests/unit/chat/test_chat_llm_flow.py`
- `app/tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py`
- `app/tests/unit/chat/test_chat_workspace_folder_notes_prompt.py`
- `app/tests/unit/chat/test_chat_service_biblio_recent_dialogue.py`
- `app/tests/unit/core/test_active_document_prompt_lane.py`
- `app/tests/unit/core/test_workspace_folder_notes_prompt_lane.py`
- `app/tests/test_server_chat_biblio_contract.py`
- `app/tests/test_server_chat_agenda_contract.py`
- `app/tests/test_server_chat_adobe_docs_contract.py`
- inventaire des tests chat/memory/identity/agenda/biblio/documents/notes/exports/images via `find` et `rg`.

## Carte des appels modèle

| Chemin | Module/fonction | Provider/client | Messages envoyes | Source des donnees | Observabilite | Influence reponse visible |
| --- | --- | --- | --- | --- | --- | --- |
| Chat principal | `core.chat_llm_flow.run_llm_exchange` via `llm_client.build_payload` | OpenRouter chat completions | `messages` complet du prompt chat, roles system/user/assistant et multimodal possible | `chat_service.chat_response`, conversation, lanes, runtime settings | `llm_payload`, `llm_call`, `llm_provider_response`, `AssistantText`, content-free | Oui, sauf override Agenda/Biblio |
| Resume conversation | `memory.summarizer.summarize_conversation` | OpenRouter via caller `resumer` | system resume + user dialogue a resumer | anciens tours non resumes de la conversation | logs provider et logs summarize, pas prompt brut attendu | Oui indirectement: resume remplace l'historique ancien dans le prompt |
| Arbiter memoire | `memory.arbiter.filter_traces_with_diagnostics` | OpenRouter via caller `arbiter` | system arbiter + user payload structure de traces candidates et contexte recent | retrieval semantique + tours recents | decisions persistantes et events content-free | Oui indirectement; en mode `enforced_all`, filtre la memoire injectee |
| Extracteur identite | `memory.arbiter.extract_identity_entries` | OpenRouter via caller `identity_extractor` | system extraction + user paire(s) recentes | dernier couple user/assistant admissible | events identity write content-free | Oui au tour suivant si ecriture retenue |
| Juge identite mutable | `memory.mutable_identity_judge_v2` | OpenRouter strict JSON | system juge + user JSON borne de 5 paires completes et identites courantes | buffer conversationnel post-reponse, statique/mutable actuel | `mutable_identity_judge_apply`, payloads d'observation content-free | Oui aux tours suivants via `identity_mutables` |
| Stimmung | `core.stimmung_agent.build_affective_turn_signal` | OpenRouter primary/fallback | system prompt dedie + user avec fenetre recente compacte et tour courant compacte | message courant + recent window | `stimmung_prompt_prepared`, content-free | Oui indirectement via inputs hermeneutiques/validation |
| Validation agent | `core.hermeneutic_node.validation.validation_agent.build_validated_output` | OpenRouter primary/fallback | system prompt dedie + user avec primary verdict, justifications, contextes compactes, hard guards | canonical inputs hermeneutiques, contexte recent, memoire, web, identity, time | `validation_prompt_prepared`, provider metadata, content-free | Oui: injecte le jugement hermeneutique final dans le systeme |
| Web reformulation | `tools.web_search.reformulate` | OpenRouter via caller `web_reformulation` | system reformulation + user question courante | tour utilisateur | `web_reformulation_prompt_prepared`, hashes/chars | Oui indirectement: construit recherche web |
| Web discovery Exa | `tools.web_search_discovery._build_openrouter_exa_payload` | OpenRouter server tool web search | system discovery + user requete; tool server-side | requete web reformulee/specialisee | observabilite web discovery content-free | Oui indirectement: URLs/sources lues alimentent contexte Web |
| Biblio agent bibliothecaire | `biblio.librarian_agent_openrouter.OpenRouterBiblioLibrarianAgentClient` | OpenRouter strict JSON | system planificateur Biblio + user JSON borne | message courant, dialogue recent, etat Biblio, plan deterministe | comparaison content-free; pas de prompt brut retenu par le resultat | Oui indirectement; peut autoriser agent-first et lock final |
| Agenda agent | `agenda.agent_openrouter.OpenRouterAgendaAgentClient` | OpenRouter strict JSON | system planificateur Agenda + user JSON borne | message courant, dialogue recent, time windows, etat pending | payload Agenda content-free | Oui si toggle active et lock final produit |
| Image generation V0/V1 tool | `tools.image_generation.handle_generation_request` | OpenRouter image | user prompt image seul + config image | formulaire outil, pas chat principal | logs generation sans prompt brut attendu | Non pour le chat principal; produit une image/outillage lateral |
| Embeddings/memoire | `memory_store` et config embeddings | service embedding | texte a indexer/retrouver | traces/memoire | selon memory observability | Oui indirectement via retrieval; pas un modele generatif chat |
| Admin/runtime helpers | `admin.runtime_settings*`, read-models admin | pas d'appel LLM principal detecte | n/a | settings | logs admin | Influence via runtime settings, pas par prompt direct |

Note: plusieurs chemins auxiliaires recoivent du contenu utilisateur borne ou compacte. Ils ne sont pas visibles comme reponse finale, mais ils modifient les decisions injectees ensuite.

## Carte du payload chat principal

Payload logique du chat principal, tel que reconstruit par code:

| Composant | Source technique | Persistance | Nouvelle conversation | Conversation existante | Budget/limite | Exclusions | Risque continuite |
| --- | --- | --- | --- | --- | --- | --- | --- |
| System prompt backend | `prompt_loader.get_main_system_prompt()` via `chat_prompt_context.resolve_backend_prompts` | fichier prompt/runtime | oui | oui | pas de budget dedie observe | absent si prompt manquant | Porte la personnalite statique, mais pas les preferences inter-conversations individuelles |
| Prompt hermeneutique | `get_main_hermeneutical_prompt()` | fichier prompt/runtime | oui | oui | pas de budget dedie observe | absent si prompt manquant | Porte methode generale, pas historique relationnel |
| Reference temporelle | `build_augmented_system` + `time_input` | transitoire | oui | oui | compact | timezone invalide peut degrader | Aide les reprises apres ecart temporel |
| Identite stable | `identity.load_llm_identity`, `load_user_identity` | fichiers statiques configures | oui | oui | troncature interne possible | lecture manquante -> section absente | Fort support doctrinal; non personnalise par conversation |
| Identite mutable | `active_identity_projection.resolve_active_identity_projection` | table/read model `identity_mutables` | oui | oui | cible/max mutable dans config | si juge n'a rien ajoute | Support inter-conversation durable, mais cible identitaire, pas style/methode fine |
| Memoire semantique | `chat_memory_flow.prepare_memory_context` | traces/memory store | oui si retrieval trouve | oui si retrieval trouve | `MEMORY_TOP_K`, selection basket, contexte parent | no data, retrieval error, mode off | Peut porter faits/projets; pas garantie de ton ou relation |
| Context hints | `get_recent_context_hints` | memoire/context hints | oui si presents | oui si presents | max items, age, confidence, token budget | trop vieux/faible confiance | Surface utile mais petite et factuelle |
| Resume actif | `conversations_prompt_window.get_active_summary` | table `summaries` par conversation | non pour nouvelle conversation sans meme id | oui si resume existe | summary target tokens | absent si pas de resume | Porte continute intra-conversation, pas inter-conversation |
| Dialogue recent | `conversation["messages"]` | conversation JSON/DB | seulement le nouveau tour | tous les tours apres resume actif | soft max seulement; pas de troncation dure observee | assistant interrompu exclu | Source principale du ton local; perdue en nouvelle conversation |
| Silences et Delta-T | `conversations_prompt_window` | transitoire | a partir du premier tour | oui | labels courts | timestamp absent | Bon support local de temporalite |
| Documents actifs | `active_document_prompt_lane` | conversation active docs / workspace selections | seulement si selection dans conversation | oui si actifs/selectionnes | max tokens si > 0; images/PDF max bytes/pages/model support | trop gros, vide, unsupported, erreur lecture | Courant-turn; pas continuite personnelle |
| Notes preparees | `workspace_folder_notes_prompt_lane` | Nextcloud-read current turn; pas corps local durable | seulement si demande explicite | oui si demande explicite | 1 note injectee/tour, 5 demandes max, char budget | folder/note absent, trop gros, over limit | Courant-turn; pas memoire/style |
| Exports reutilises | specs Exports + routes services | durable Nextcloud/read-model | pas auto-injecte | pas auto-injecte | reuse borne md/txt | formats non reutilisables | Source de contenu seulement si action explicite |
| Images generees | generated images V1 | durable Nextcloud/read-model | pas auto-injecte | pas auto-injecte | formats/stockage | prompt brut non stocke | N'influence pas la voix chat sauf selection explicite future |
| Web | `tools.web_search.build_context` puis `inject_web_context` | transitoire par tour | si `web_search`/auto | si `web_search`/auto | runtime services, crawl max chars/results | no data/error/Adobe skip | Peut fortement orienter reponse factuelle; pas continuite relationnelle |
| Biblio | `biblio.chat_runtime` + prompt lane/lock | etat Biblio conversationnel + Catalogue | si toggle/signaux | oui, avec etat conversationnel Biblio | passages max chars, tools, model settings agent | disabled/not selected/error | Peut modifier voix via lane ou lock final |
| Agenda | `agenda.chat_runtime` | pending state conversationnel | si toggle | oui, avec pending state | agent settings, max tools, secrets/runtime | disabled/off/not_configured/error | Peut bypasser modele principal via lock final |
| Adobe docs | `adobe_docs_prompt_lane` | transitoire par tour | si mode Adobe | si mode Adobe | passages limites upstream | non demande/error | Peut orienter reponse documentaire, pas continuite |
| Runtime settings | `admin.runtime_settings` | DB/env fallback | oui | oui | section-specific | DB/secret indisponible | Change modele, temperature, tools, flags et donc voix |
| Assistant override | Agenda/Biblio locks | transitoire puis assistant persiste | si lock | si lock | lock autorise | aucun LLM principal | Voix visible contourne le modele principal |

## Ordre réel d’injection

Ordre reconstruit du chat principal:

1. `resolve_backend_prompts` charge systeme backend et prompt hermeneutique.
2. `resolve_chat_session` cree une nouvelle conversation si aucun `conversation_id` normalise n'est fourni, ou charge une conversation existante si l'id est valide.
3. Le message utilisateur courant est ajoute a la conversation avec timestamp.
4. `summarizer.maybe_summarize` peut resumer les anciens tours non resumes avant la construction finale du prompt.
5. `build_augmented_system` compose system prompt, prompt hermeneutique, reference temporelle et bloc identite.
6. `prepare_memory_context` recupere memoire semantique, contexte parent de resumes et context hints.
7. Les canonical inputs sont prepares: summary, identity, recent context, recent window, user turn, stimmung, web.
8. Web/Biblio/Agenda/Adobe runtime sont resolus avant la construction finale du payload.
9. Le noeud hermeneutique primaire et le validation agent produisent le jugement final; les guards sont ajoutes au systeme.
10. `build_prompt_messages` construit la base: systeme augmente, resume actif, context hints, contexte memoire parent, traces memoire, dialogue apres resume, labels Delta-T/silence.
11. `inject_web_context` modifie le dernier message utilisateur en lui prepandant le contexte Web si actif.
12. `inject_workspace_folder_notes_prompt_lane` insere la lane Notes avant le premier message de dialogue.
13. `inject_active_document_prompt_lane` insere la lane Documents avant le premier message de dialogue restant; si Notes a deja insere un message user de contenu, Documents se place avant ce contenu Notes.
14. `inject_biblio_prompt_lane` insere la lane Biblio avant le dernier message user.
15. Si Biblio read-passages le demande, une enveloppe intro/outro peut entourer la reponse du modele principal.
16. Si Biblio produit un final response lock, `AssistantResponseOverride` peut court-circuiter le modele principal.
17. Agenda final response lock a priorite sur Biblio pour l'override final.
18. `inject_adobe_prompt_lane` insere Adobe avant le dernier message user si active.
19. `run_llm_exchange` appelle le modele principal, sauf override autorise.
20. La reponse est persistee, les traces sont sauvegardees, puis l'identite mutable peut etre mise a jour pour les tours suivants.

Point important: Web est calcule avant plusieurs lanes, mais vit dans le dernier user message. Les lanes Documents/Notes/Biblio/Adobe sont des messages separes inserees autour du dialogue. L'ordre logique exact est donc plus subtil que l'ordre des appels dans `chat_service.py`.

## Nouvelle conversation vs conversation longue

Conversation deja longue:

- conserve l'historique local jusqu'au resume;
- beneficie du resume actif par conversation;
- conserve les silences et labels Delta-T sur les messages persistants;
- peut porter l'etat Biblio/Agenda attache a des messages;
- reconstruit une tonalite locale depuis le dialogue recent;
- a plus de matiere pour le stimmung, validation agent et agents de lane.

Nouvelle conversation:

- demarre avec systeme, prompt hermeneutique, temps, identite statique/mutable, memoire semantique et context hints;
- ne charge pas le resume d'une autre conversation;
- ne charge pas l'etat Biblio/Agenda d'une autre conversation;
- ne conserve pas les rituels locaux, seuils de proactivite ou style d'explication d'une ancienne conversation sauf s'ils sont devenus identite/memoire retrievable;
- perd la nuance relationnelle portee par les derniers tours.

Conversation avec memoire:

- peut recuperer des faits utilisateur/projet et certains fragments assistant;
- depend du retrieval, de `MEMORY_TOP_K`, de la qualite des traces, du basket pre-arbiter et du mode hermeneutique;
- ne garantit pas que les souvenirs recuperes soient les bons souvenirs de style ou de methode.

Conversation sans memoire:

- depend presque entierement du prompt statique, de l'identite statique/mutable et du message courant;
- risque de redevenir generique, meme si le systeme reste "Frida".

Conversation avec lanes desactivees ou non selectionnees:

- Biblio/Agenda/Web/Documents/Notes n'ajoutent pas de contexte;
- l'observabilite marque disabled/not_selected/not_configured selon contrat;
- la voix depend du chat principal et non des renderers de lanes.

Conversation apres resume:

- les anciens tours bruts couverts par le resume sortent de la fenetre principale;
- le resume devient un system message de synthese;
- la nuance de ton, d'humour, d'hesitation, de conflit ou de methode peut etre aplatie si le resume ne la preserve pas explicitement.

Conversation apres reset/absence de contexte:

- il reste le socle prompt + identite statique/mutable + runtime settings;
- toute continuite relationnelle recente disparait si elle n'a pas ete ecrite durablement;
- les docs doctrine archivees ne sont pas automatiquement injectees comme memoire active.

Ce que Frida perd typiquement en nouvelle conversation:

- faits utilisateur non retenus comme memoire ou identite;
- tonalite locale et niveau d'humour/sobriete negocie;
- methode de travail apprise dans un fil particulier;
- rituels d'audit/prompt lies a un chantier;
- seuil de proactivite et facon de cadrer les risques;
- historique de decisions ou arbitrages qui n'ont pas ete documentes dans le repo ou retenus en memoire;
- preferences d'explication et niveau de detail;
- continuite critique/politique locale;
- maniere de dire non faconnee par le dialogue recent.

## Identité stable

L'identite stable vit dans les fichiers statiques resolus par `identity.static_identity_content` et injectes via `identity.build_identity_block`.

Elle est presente en nouvelle conversation et en conversation existante. Elle porte la posture profonde de Frida et de l'utilisateur telle que configuree. Selon `identity-new-contract-plan.md`, elle ne doit pas devenir un fourre-tout de preferences conversationnelles, memoires recentes ou consignes operationnelles.

Risque: si la continuite de style/methode est encodee abusivement dans l'identite stable, la doctrine identitaire devient confuse. Si elle n'y est pas encodee, une nouvelle conversation ne la retrouve pas.

## Identité mutable

L'identite mutable active vit dans `identity_mutables` et est injectee par `active_identity_projection.resolve_active_identity_projection`.

Pipeline actuel:

- les paires user/assistant completes sont bufferees apres reponse;
- seuil courant: 5 paires completes;
- le juge mutable v2 recoit une fenetre bornee, les identites courantes et une schema JSON stricte;
- les ajouts valides sont appliques en add-only dans `identity_mutables`;
- pas de promotion static, pas de scoring runtime actif, pas de maintenance automatique du canon existant.

Elle soutient la continuite inter-conversations pour des traits identitaires ou dispositions fortes. Elle ne constitue pas une memoire de style conversationnel. Les micro-preferences de ton, niveau d'explication, humour, proactivite ou maniere de travailler ne sont retenues que si le juge les qualifie comme identitaires, ce qui n'est pas le meme objet produit.

## Mémoire

La memoire injectee vient de `chat_memory_flow.prepare_memory_context`.

Sur un tour:

- retrieval semantique par message courant;
- enrichissement possible par resumes parents;
- construction d'un `memory_retrieved` canonique;
- construction d'un basket pre-arbiter;
- appel arbiter en modes `shadow`, `enforced_identities`, `enforced_all`;
- injection effective selon mode.

Point d'architecture majeur: en mode `shadow`, l'arbiter est appele et observe, mais la memoire injectee au prompt reste issue du pre-arbiter basket. Seul `enforced_all` applique les decisions arbitrees a la memoire de prompt. C'est comprehensible historiquement, mais important pour l'audit payload: le modele principal peut voir des souvenirs que l'arbiter n'aurait pas retenus.

La memoire peut porter des faits utilisateur, projet, historiques de decisions et fragments relationnels. Elle n'est pas specialement structuree pour porter une continuite de voix ou de methode.

## Résumés

Les resumes vivent dans la table `summaries`, par conversation.

Generation:

- `summarizer.maybe_summarize` estime les tokens des messages non resumes;
- au-dela du seuil, les tours anciens sauf les derniers tours gardes sont envoyes au modele de resume;
- un resume textuel est persiste;
- les messages couverts sont marques `summarized_by`.

Injection:

- `conversations_prompt_window.get_active_summary` lit le dernier resume de la conversation courante;
- le resume est ajoute comme system message avant le dialogue restant;
- les messages avant le cutoff ne sont plus injectes comme dialogue brut.

Risque continuite: le resume conserve probablement le fond mieux que la maniere. Rien dans le contrat relu ne prouve que le resume preserve explicitement la tonalite relationnelle, les micro-methodes de travail, les preferences de refus/cadrage ou les rituels d'audit.

## Lanes agentiques

Les lanes agentiques influencent la reponse visible de deux manieres:

- injection de contexte dans le prompt principal;
- final response lock / assistant override, qui bypass le modele principal.

Biblio:

- si `biblio_enabled` est faux, disabled content-free;
- si actif mais non selectionne, not_selected content-free;
- si selectionne, peut injecter des passages Biblio comme system lane;
- l'agent bibliothecaire peut construire un plan JSON strict;
- certains chemins agent-first ou rendu exact produisent un final response lock;
- les tests prouvent que le lock controle le message assistant et que le texte final peut ne pas venir du modele principal.

Agenda:

- si `agenda_enabled` est absent/faux, disabled content-free;
- si active mais runtime off/non configure, noop/fallback observe;
- si active et validee, l'agent peut produire une lecture/proposition et un final response lock;
- les tests prouvent qu'un lock Agenda persiste comme message assistant normal.

Stimmung et validation agent:

- ne produisent pas de reponse visible directement;
- influencent le jugement hermeneutique et donc les instructions finales ajoutees au systeme;
- recoivent des contextes bornes/compactes, pas le payload complet.

Risque voix: quand une lane produit une reponse verrouillee, la continuite de voix depend du renderer/agent de la lane, pas seulement du prompt principal Frida.

## Documents / Notes / Exports / Images

Documents actifs et workspace files:

- source: documents actifs de conversation + fichiers de dossier explicitement selectionnes;
- injection: lane separee avant le dialogue;
- texte injecte en entier si budget ok; sinon signal de non-injection;
- images/PDF visuels peuvent etre envoyes en multimodal selon support modele et limites provider;
- distinct de memoire/resume/identity/Web/Biblio.

Notes:

- source: notes Markdown de dossier explicitement demandees;
- le corps Markdown est lu pour le tour courant et injecte dans une lane user separee;
- limite observee: 1 note injectee par tour, jusqu'a 5 demandes reportees content-free;
- pas d'ecriture du corps Markdown localement, pas de Memory/RAG/Identity/Summary.

Exports:

- source durable Nextcloud/read-model;
- creation/reuse explicites;
- pas d'injection automatique dans le chat principal;
- reutilisation comme source bornee surtout pour formats texte admissibles.

Images generees:

- read-model dedie et stockage Nextcloud-first;
- generation via outil lateral;
- prompt brut non durable selon contrat;
- pas d'injection automatique dans chat, memoire, identity ou summary.

Risque continuite: ces surfaces portent du contenu de travail, pas une personnalite durable. Elles peuvent cependant dominer localement le ton par charge contextuelle et ordre d'injection.

## Biblio / Agenda / Web

Biblio:

- Catalogue est GET-only cote FridaDev;
- lane de passages injectee si resolution/extraction;
- etat conversationnel Biblio attache aux messages pour follow-up;
- agent bibliothecaire configurable, strict JSON, outils GET-only;
- product controller encore largement deterministe selon les chemins, mais agent-first/lock existe.

Agenda:

- toggle `agenda_enabled`;
- runtime off/disabled observe comme no-op content-free;
- mode active peut appeler un agent JSON strict;
- lecture/proposition/pending state restent bornes et content-free;
- post-V1 dormant selon contrat observabilite, a ne pas rouvrir ici.

Web:

- activation manuelle/auto selon runtime;
- reformulation LLM possible;
- recherche SearXNG/Crawl4AI et discovery OpenRouter Exa possible;
- contexte Web prepende au dernier user message;
- guard Web ajoute au systeme pour ne pas surestimer la lecture.

Web et Biblio peuvent apporter du contenu externe tres saillant. Cela aide la justesse factuelle mais peut concurrencer la continuite de voix si le systeme ne rappelle pas explicitement la posture relationnelle.

## Runtime settings et feature flags

Surfaces runtime qui modifient le comportement:

- main model, temperature, top_p, response max tokens;
- modeles et budgets summary, arbiter, identity extractor, mutable judge, stimmung, validation agent;
- `HERMENEUTIC_MODE` et gouvernance des modes;
- embedding top_k, context hints max items/age/confidence;
- Web services settings: resultats, crawl top_n, max chars, discovery provider;
- `biblio_enabled` par payload, plus settings agent bibliothecaire;
- `agenda_enabled` par payload, plus settings Agenda agent/secrets;
- support multimodal par modele principal;
- limites Documents/Notes/Images/Exports;
- assistant output policy et final response locks.

Ces settings sont persistants via runtime settings DB/env fallback. Ils peuvent changer la voix sans changement de code, surtout modele principal, temperature, agents secondaires et toggles de lanes.

## Observabilité et traces

Points forts:

- contrat agentic observability content-free;
- statuses normalises: ok, skipped, disabled, not_selected, not_configured, not_applicable, refused, failed, error;
- logs de payload secondaire majoritairement hashes/chars/counts;
- Tests de non-contamination pour Biblio, Agenda, Documents, Notes, provider reasoning.

Limites:

- pas de snapshot content-free unique du payload final ordonne;
- l'observabilite permet de savoir qu'une surface existe et combien elle pese, pas de verifier qualitativement la continuite de ton;
- un final response lock peut produire une reponse sans `llm_payload` principal, ce qui est correct mais doit etre distingue dans les audits de voix;
- les logs ne doivent pas etre utilises pour reconstruire des contenus bruts.

## Ce qui soutient déjà la continuité

- Prompt systeme et prompt hermeneutique centraux.
- Identite statique Frida/utilisateur toujours injectee si disponible.
- Identite mutable add-only durable et reinjectee en nouvelle conversation.
- Memoire semantique inter-conversations.
- Context hints recents.
- Resume actif intra-conversation.
- Fenetre recente complete apres resume, sans troncation dure observee.
- Labels temporels et silences.
- Guards de voix, lecture vocale, revelation identitaire, Web, plain text.
- Observabilite content-free qui evite de polluer les logs par du contenu sensible.
- Tests de lanes et de final response override.

## Ce qui casse ou fragilise la continuité

- Absence de surface durable dediee a la continuite de ton/methode/relation.
- Nouvelle conversation sans resume inter-fil.
- Memoire semantique orientee retrieval factuel, pas style relationnel.
- Identite mutable trop noble/ontologique pour porter toutes les micro-preferences.
- Resume conversationnel susceptible d'aplatir la nuance du dialogue ancien.
- Lanes externes tres saillantes pouvant dominer la reponse.
- Biblio/Agenda locks qui contournent le modele principal.
- Mode `shadow` memoire qui observe l'arbiter sans forcement appliquer ses choix au prompt.
- Pas de test produit "nouvelle conversation garde la posture Frida".
- Pas de snapshot content-free du payload final ordonne.

## Findings

### P1

P1-CONT-01 - Pas de Continuity Capsule ni surface equivalente injectee en nouvelle conversation.

Le code injecte identite statique/mutable, memoire semantique, context hints et prompt systeme, mais aucune surface dediee ne conserve les preferences de ton, methode, relation, presence, seuil de proactivite, humour/sobriete ou maniere de cadrer les refus entre conversations. La continuite inter-conversations est donc emergente, dependante du retrieval et de l'identite, et non garantie.

Aucun autre P1 identifie dans le perimetre read-only.

### P2

P2-PAYLOAD-01 - Pas de preuve snapshot content-free du payload final ordonne.

L'ordre peut etre reconstruit par code, mais l'audit ne peut pas prouver un payload final exact sans instrumentation fake/snapshot. Inventer ce payload serait contraire a la consigne.

P2-SUMMARY-01 - Le resume intra-conversation peut ecraser la nuance de continuite.

Le resume remplace les anciens tours bruts dans le prompt apres seuil. Le contrat actuel ne prouve pas que le resume preserve la voix relationnelle, les rituels, la methode, les preferences d'explication ou la politique de cadrage.

P2-LANES-01 - Biblio/Agenda peuvent produire une reponse visible hors modele principal.

Les final response locks sont utiles et testes, mais ils deplacent la responsabilite de voix vers les renderers/agents de lane. Une future continuite doit couvrir ces chemins, pas seulement le prompt principal.

P2-MEMORY-01 - En mode `shadow`, l'arbiter memoire ne controle pas la memoire injectee.

Le prompt peut recevoir le pre-arbiter basket alors que les decisions arbitrees restent observees. Cela fragilise l'explication "ce qui influence la reponse" si les audits lisent seulement les decisions arbiter.

Aucun autre P2 identifie dans le perimetre read-only.

### P3

P3-DOC-01 - Certaines cartes historiques sont partiellement stale.

Le catalogue d'appels modele du 2026-05-17 et certains commentaires de module restent utiles, mais ne decrivent plus completement Biblio agent-first, les lanes V1 Documents/Notes/Images/Exports et les final response locks.

P3-TEST-01 - Les tests prouvent les contrats structurels, pas la continuite qualitative.

Les tests couvrent injection, non-contamination, no-op, overrides et settings. Aucun test lu ne prouve qu'une nouvelle conversation conserve la posture Frida, le style relationnel ou la methode de travail.

P3-OBS-01 - L'observabilite content-free ne suffit pas a juger la presence.

Les hashes/chars/counts sont necessaires pour la securite, mais ne permettent pas de mesurer la continuite de ton. Il faudra une instrumentation content-free specialisee ou des fixtures artificielles.

Aucun autre P3 identifie dans le perimetre read-only.

## Proposition de modèle cible

Sans ecrire de spec maintenant, le modele cible devrait etre une surface de continuite separee des objets existants:

- pas une identite stable;
- pas une memoire factuelle;
- pas un resume de conversation;
- pas une observabilite;
- pas une lane documentaire.

Elle pourrait etre un bloc court, versionne, content-free en observabilite mais textuel dans le prompt, portant:

- posture relationnelle durable;
- methode de travail preferee;
- preferences de densite/explication;
- niveau d'humour/sobriete;
- facon de cadrer les risques et de dire non;
- rituels de reprise apres interruption;
- separation claire entre faits utilisateur et style de presence.

Elle devrait etre injectee en nouvelle conversation et en conversation existante, apres l'identite mais avant la memoire ou avec un emplacement explicite a specifier. Elle devrait aussi couvrir les renderers Biblio/Agenda quand ils verrouillent la reponse.

## Lots recommandés

Lot 1 docs-only - Spec "Continuity Capsule" ou equivalent.

- definir l'objet, son emplacement, ses non-objectifs;
- clarifier difference avec identite/memoire/resume;
- definir observabilite content-free;
- definir injection en nouvelle conversation et conversation longue;
- definir interaction avec Biblio/Agenda locks.

Lot 2 instrumentation/fake payload snapshot content-free.

- ajouter un snapshot de structure ordonnee sans contenu brut;
- prouver presence/ordre/roles/budgets/hashes seulement;
- inclure cas nouvelle conversation, longue conversation, resume, lanes activees/desactivees, override.

Lot 3 runtime injection eventuelle.

- injecter la capsule si Lot 1/2 prouvent le besoin;
- garder limite stricte de taille et conflit avec identite/memoire;
- ne pas toucher providers live dans le lot de dev.

Lot 4 tests/smokes de continuite.

- fixtures artificielles sans contenu utilisateur reel;
- tests nouvelle conversation vs longue conversation;
- tests de non-regression Biblio/Agenda lock;
- tests content-free observability.

Lot Z validation.

- relire docs/code/tests;
- scan anti-fuite;
- smoke runtime borne si autorise;
- decision explicite avant activation OVH.

## No-go avant runtime

- Ne pas injecter une capsule sans spec separee.
- Ne pas utiliser les logs existants pour reconstruire du contenu brut.
- Ne pas melanger continuity capsule avec identity mutable sans decision doctrinale.
- Ne pas supposer que le prompt final exact est prouve sans snapshot fake.
- Ne pas activer de provider live pour "voir" le payload.
- Ne pas corriger Biblio/Agenda/Web dans ce lot.
- Ne pas toucher DB, reset, purge, backfill ou Docker.
- Ne pas ecrire de contenu utilisateur/document/note/passage/export/image dans les tests ou logs.

## Commandes exécutées

Commandes deja executees pendant l'audit:

- `git status --short --branch`
- `git fetch origin main`
- `git pull --ff-only origin main`
- `git log -8 --oneline --decorate`
- `find app/docs/todo-todo -maxdepth 2 -type d | sort`
- `wc -l` sur les documents obligatoires
- recherches `rg` larges sur model/prompt/messages/payload/memory/identity/summary/lane/context/conversation
- recherches `rg` ciblees sur Documents/Notes/Exports/Images/Biblio/Agenda/Web
- lectures `sed` des modules et tests listes dans `Sources relues`

Tests executables: non lances pour ce lot docs-only. Les tests existants ont ete relus.

Checks pre-commit executes:

- `git status --short --branch` : fichier d'audit nouveau uniquement dans `app/docs/todo-todo/audits/`.
- `git diff --check` : OK.
- `find app -path "*__pycache__*" -o -name "*.pyc"` : aucune sortie.
- `find app -type f \( -name "utils.py" -o -name "helpers.py" \)` : aucune sortie.
- grep anti-fuite cible de la consigne sur ce fichier : aucune sortie.

## Checks anti-fuite

Etat de redaction avant checks pre-commit:

- pas de prompt brut reproduit;
- pas de dialogue brut utilisateur reel;
- pas de memoire brute reelle;
- pas de contenu document/note/export/passage Biblio/image;
- pas de data URL ni contenu multimodal;
- pas de secret ni token;
- pas de provider live appele.

Resultat du grep anti-fuite cible: aucune sortie.

## Limites de l’audit

- Audit read-only par lecture code/docs/tests, sans instrumentation runtime.
- Aucun payload final brut n'a ete capture, affiche ou commite.
- Les contenus exacts de prompts systeme/agents n'ont pas ete recopies dans ce document.
- Les logs runtime reels n'ont pas ete inspectes en contenu.
- La carte d'ordre est logique et issue du code; elle doit etre confirmee par un lot snapshot content-free si elle devient base de correction runtime.
- Les findings portent sur continuite/payload; ils ne constituent pas une demande de correction immediate.
