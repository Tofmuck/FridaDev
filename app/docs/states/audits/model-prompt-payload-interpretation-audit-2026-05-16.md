# Audit - Contrat semantique entre payloads modele et prompts - 2026-05-16

Statut: audit transverse read-only
Portee: modele principal, prompts effectifs, payloads secondaires quand ils portent leur propre contrat d'interpretation
Hors-scope: patch correctif de prompt, refonte runtime, dashboard, documents actifs de conversation

## EXECUTIVE SUMMARY

Verdict court: FridaDev possede deja un contrat d'interpretation substantiel pour le modele principal. Le fichier `app/prompts/main_hermeneutical.txt` n'est pas un simple prompt de ton: il declare explicitement les briques runtime attendues, leur priorite relative, leur usage et leurs limites. Le systeme ne se contente donc pas d'envoyer des blocs au modele en esperant qu'il devine leur sens.

Ce contrat est toutefois incomplet sur trois points importants:

- le modele principal voit une fenetre conversationnelle selectionnee, mais il ne recoit pas un marqueur explicite disant que cette fenetre peut etre tronquee par budget token ou remplacee partiellement par le resume actif;
- certains formats visibles ont evolue plus vite que le contrat statique, surtout l'identite active actuelle en sections `[STATIQUE]` / `[MUTABLE]`;
- les resumes parents associes aux traces memoire sont injectes avant les traces, mais le lien trace -> parent_summary reste semantiquement implicite pour le modele principal.

Reponse a la question centrale:

Quand Frida recoit quelque chose dans son payload principal, elle sait en general ce que c'est et quoi en faire au niveau bloc. Elle doit encore deviner certains details de limites, de provenance fine et de relation entre blocs. Le danger n'est pas l'absence totale de contrat; le danger est de confondre "bloc interpretable" avec "composition complete et limites parfaitement explicites".

## VERDICT GLOBAL

### Modele principal

Le contrat semantique principal est globalement solide pour:

- la question utilisateur finale;
- le cadre de reponse en texte brut;
- le repere temporel `NOW` / `TIMEZONE`;
- les labels Delta-T et marqueurs de silence;
- le bloc identite;
- le resume actif de conversation;
- les indices contextuels recents;
- les traces memoire et leurs contextes;
- le contexte web;
- le jugement hermeneutique valide;
- les gardes de lecture vocale, web, identitaire et sortie texte.

Il est partiel pour:

- la forme exacte actuelle du bloc identite;
- les limites de la fenetre conversationnelle recente;
- le couplage exact entre parent summaries et traces memoire;
- la distinction entre ce que le pipeline a exclu avant prompt et ce que le modele ne voit simplement pas.

### Providers secondaires

Les providers secondaires audites ont, pour la plupart, un contrat propre suffisant:

- `stimmung_agent`: contrat clair, local au tour courant, sans psychologie durable;
- `validation_agent`: contrat fort, avec priorite explicite au `validation_dialogue_context`;
- `arbiter`: contrat explicite sur recent context, candidates, scores et schema de sortie;
- `web_reformulation`: contrat minimal mais adapte a sa tache etroite;
- `summary_system`: contrat minimal acceptable pour une synthese conversationnelle;
- `identity_extractor` et `identity_periodic_agent`: contrats stricts de schema, prudence et non-generalisation.

## METHODE

Question de methode posee avant conclusion: existe-t-il un meilleur plan d'audit ?

Oui: le bon plan n'etait pas de relire seulement les textes de prompts ni seulement les payloads. J'ai suivi le flux inverse:

1. identifier le payload final du modele principal depuis le point d'appel OpenRouter;
2. remonter les builders qui ajoutent chaque bloc;
3. comparer la forme reelle injectee aux instructions statiques et dynamiques qui expliquent cette forme;
4. verifier les tests/specs qui figent les contrats;
5. separer le modele principal des providers secondaires.

Ce plan evite la confusion entre:

- presence d'un bloc;
- preuve qu'il est injecte;
- intelligibilite effective du bloc pour le modele.

## CARTOGRAPHIE DES PAYLOADS

### Payload principal

Chemin runtime:

- `app/core/chat_service.py:403-414`: fixe `now_iso_value`, construit le system prompt augmente avec system prompt, contrat hermeneutique, reference temporelle et identite.
- `app/core/chat_service.py:417-460`: prepare memoire, resume, identite, contexte recent, user turn, stimmung et web.
- `app/core/chat_service.py:462-499`: execute le noeud hermeneutique, valide le resultat, puis injecte `[JUGEMENT HERMENEUTIQUE]`.
- `app/core/chat_service.py:501-531`: injecte les gardes runtime.
- `app/core/chat_service.py:535-551`: construit les messages finaux et injecte eventuellement le contexte web dans le dernier message utilisateur.
- `app/core/chat_llm_flow.py:127-144`: construit le payload OpenRouter depuis `prompt_messages` et journalise `provider_caller=llm`.

Le payload principal contient donc:

- un message `system` augmente;
- des messages `system` supplementaires pour resume actif, indices, contexte de souvenirs, traces memoire;
- la fenetre conversationnelle recente selectionnee;
- le dernier message utilisateur, eventuellement precede du contexte web et de `Question :`.

### Payloads secondaires audites

- `stimmung_agent`: `app/core/stimmung_agent.py:211-231`
- `validation_agent`: `app/core/hermeneutic_node/validation/validation_agent.py:825-875`
- `memory arbiter`: `app/memory/arbiter.py:322-349`
- `web_reformulation`: `app/prompts/web_reformulation.txt`
- `summary_system`: `app/prompts/summary_system.txt`
- `identity_extractor`: `app/prompts/identity_extractor.txt`
- `identity_periodic_agent`: `app/prompts/identity_periodic_agent.txt`

## MATRICE ELEMENT -> PROMPT -> INTERPRETATION

| Element recu par le modele principal | Source code / builder | Forme reellement injectee | Prompt ou instruction qui l'explique | Interpretation attendue par le modele | Implicite / ambigu / mal specifie |
| --- | --- | --- | --- | --- | --- |
| Cadre de reponse | `prompt_loader.get_main_system_prompt()`, `chat_prompt_context.resolve_backend_prompts()` | Debut du message system: cadre de reponse, texte brut, sobriete, pas de markdown par defaut | `app/prompts/main_system.txt`; renforce par `chat_prompt_context.build_plain_text_guard_block()` | Repondre en texte brut sobre, adapter la structure seulement si utile ou demande | Pas d'ambiguite majeure |
| Contrat hermeneutique global | `prompt_loader.get_main_hermeneutical_prompt()` puis `build_augmented_system()` | Bloc statique "Contrat d'interpretation du prompt augmente" dans le system | `app/prompts/main_hermeneutical.txt:1-157` | Lire les briques comme des apports secondaires, prioriser la question finale, respecter les limites | Ce contrat reste texte statique; il peut devenir legerement stale si les builders changent |
| Question utilisateur finale | Conversation courante, puis `build_prompt_messages()` | Dernier message user, ou `context web + Question : + message user` | `main_hermeneutical.txt:142-146` | Centre de gravite de la reponse, dominant sauf contradiction avec system prompt | Si web est injecte dans le meme message user, la separation role/contexte repose sur la balise `Question :` |
| Repere temporel | `time_input.build_time_reference_block()`, appele par `chat_prompt_context.build_augmented_system()` | `[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`, phrase humaine | `main_hermeneutical.txt:45-60`; `chat-time-grounding-contract.md` | Utiliser NOW pour les relatifs, ne pas pretendre ne pas avoir de temps de reference | Contrat fort; pas de trou majeur |
| Labels Delta-T | `conversations_prompt_window.delta_t_label()` et builders de messages | Prefixes tels que `[il y a ...]`, `[aujourd'hui ...]` | `main_hermeneutical.txt:62-66` | Lire comme deltas relatifs conversationnels | Le modele ne voit pas la classe stable, seulement le rendu humain |
| Marqueurs de silence | `conversations_prompt_window.silence_label()` dans `build_prompt_messages()` | Messages system `[-- silence de X --]` entre messages selectionnes | `main_hermeneutical.txt:68-72` | Reprise sobre si utile, pas de psychologie du silence | Pas de trou majeur |
| Identite active | `identity.build_identity_block()` -> `active_identity_projection.resolve_active_identity_projection()` | `[IDENTITÉ DU MODÈLE]`, `[IDENTITÉ DE L'UTILISATEUR]`, sous-sections actuelles `[STATIQUE]` / `[MUTABLE]` | `main_hermeneutical.txt:32-43`, `74-84`; specs identity | Garder coherence relationnelle et contextuelle; statique comme socle, mutable comme nuance; ne pas ecraser la demande | La section "Briques" ne nomme pas explicitement les sous-balises `[STATIQUE]` / `[MUTABLE]`; elle mentionne encore des lignes dynamiques `stability/recurrence/confidence` qui ne sont pas la forme active principale |
| Lignes dynamiques d'identite | Ancien/chemin interne `_format_identity_line()`, non forme principale actuelle du bloc actif | Si utilisees: `- [stability=...; recurrence=...; confidence=...] ...` | `main_hermeneutical.txt:86-93` | Traiter comme indices de ponderation, pas preuves fortes | Contrat partiellement stale par rapport a la projection active `[STATIQUE]` / `[MUTABLE]` |
| Resume actif de conversation | `conversations_prompt_window.get_active_summary()` + `make_summary_message()` | Message system `[Résumé de la période ...]` puis contenu du resume | `main_hermeneutical.txt:95-100`; `memory-rag-summaries-lane-contract.md` | Memoire du passe, continuite generale, moins fort qu'un souvenir specifique | Le modele ne voit pas explicitement que les messages avant cutoff ont ete exclus/remplaces par ce resume |
| Fenetre conversationnelle recente | `conversations_prompt_window.build_prompt_messages()` | Messages user/assistant selectionnes apres cutoff summary et limites token | `main_hermeneutical.txt:62-72`, `142-146`; contrat temporel | Lire les messages visibles comme contexte conversationnel recent, avec deltas/silences | Aucun marqueur visible ne dit "fenetre selectionnee/tronquee"; le modele peut croire que l'historique visible est naturellement complet |
| Indices contextuels recents | `make_context_hints_message()` | `[Indices contextuels recents]`, lignes avec scope et confidence | `main_hermeneutical.txt:102-107` | Indices faibles, non decisifs | Contrat suffisant |
| Traces memoire injectees | `prepare_memory_context()` puis `make_memory_message()` | `[Mémoire -- souvenirs pertinents]`, lignes avec role et contenu | `main_hermeneutical.txt:116-121`; `memory-rag-current-pipeline-cartography.md` | Utiliser seulement si lien utile avec demande courante; plus fort qu'indice contextuel, moins fort que demande finale | Le modele ne voit pas les scores, decisions arbitre, rejected candidates ni limites du panier; cela est volontaire mais doit rester compris comme limite |
| Resumes parents de traces memoire | `memory_store.enrich_traces_with_summaries()`, `make_memory_context_message()` | `[Contexte du souvenir — résumé ...]` avant les traces | `main_hermeneutical.txt:109-114`; spec summaries lane | Contexte de cadrage pour mieux comprendre la portee du souvenir | Le lien exact entre chaque trace et son parent summary reste implicite; pas de mapping visible par trace |
| Contexte web | `web_search.build_context_payload()` + `chat_prompt_context.inject_web_context()` | `[RECHERCHE WEB — date]`, sources, URLs, contenu utilise, `[FIN DES RÉSULTATS WEB]`, puis `Question :` | `main_hermeneutical.txt:123-133`; `build_web_reading_guard_block()` si `read_state` explicite | Lire comme contexte externe pour la question courante; prioritaire sur memoire pour faits externes recents | Le bloc est place dans le message user et parle parfois en "J'ai effectue"; le contrat le couvre, mais la forme role/user reste moins propre qu'une lane system dediee |
| Garde de lecture web | `chat_prompt_context.build_web_reading_guard_block()` | `[GARDE DE LECTURE WEB]`, `read_state`, interdits de lecture directe selon cas | `chat_prompt_context.py:212-249`; tests web runtime | Ne pas pretendre lire une page si seulement snippets/fallback ou erreur | S'applique surtout aux URLs explicites; pour recherche simple, le contrat general web porte l'essentiel |
| Jugement hermeneutique valide | `validation_agent.build_validated_output()` puis `build_hermeneutic_judgment_block()` | `[JUGEMENT HERMENEUTIQUE]`, posture finale, regime, consigne, directives | `main_hermeneutical.txt:135-140`; `hermeneutic-node-validated-output-contract.md` | Consigne aval normative deja resolue; ne pas re-deduire primary verdict ou validation decision | Le detail source_priority/source_conflicts du noeud n'est pas expose au modele principal; seule la projection finale compacte l'est |
| Node state | `read_hermeneutic_node_state()` dans le noeud primaire | Pas injecte directement dans le prompt principal | `hermeneutic-node-state-persistence-contract.md`; indirectement via jugement final | Le modele principal n'a pas a interpreter le node_state brut | Si un operateur s'attend a le voir dans le prompt principal, il faut corriger l'attente: ce n'est pas une brique visible |
| Stimmung | `stimmung_agent` puis `stimmung_input` pour le noeud | Pas injecte directement dans le prompt principal | Prompt `stimmung_agent`, puis jugement hermeneutique eventuel | Signal amont pour posture, pas information visible brute | Pas un trou principal; c'est volontairement amont |
| Garde vocale | `build_voice_transcription_guard_block()` | `[GARDE DE LECTURE VOCALE]` si input voice | `chat_prompt_context.py:166-180` | Tolerance locale aux scories de transcription | Contrat clair |
| Garde revelation identitaire | `build_direct_identity_revelation_guard_block()` | `[GARDE DE REVELATION IDENTITAIRE]` dans des cas bornes | `chat_prompt_context.py:129-153` | Traiter une revelation identitaire explicite comme operative sans bureaucratie | Contrat clair |
| Garde sortie texte | `assistant_output_contract` via `build_plain_text_guard_block()` | `[CONTRAT TEXTE BRUT]` selon politique | `main_system.txt` et contrat runtime | Respecter format de sortie attendu | Contrat clair |
| Documents actifs de conversation | Aucun code runtime actuel lu dans ce chemin | Non injecte aujourd'hui | Docs produit en chantier separe | Non applicable au payload courant | Ne pas supposer une lane documentaire tant qu'elle n'est pas implementee |

## CE QUE LE MODELE SAIT INTERPRETER EXPLICITEMENT

Le modele principal sait explicitement:

- que la question finale domine;
- que les autres briques servent a eclairer, situer, nuancer ou verifier;
- que le web est prioritaire pour les faits externes recents quand il est injecte;
- que les souvenirs pertinents doivent etre utiles a la demande, pas surinterpretes;
- que le resume actif est une synthese moins fine que des extraits specifiques;
- que les indices contextuels sont faibles;
- que l'identite cadre la coherence mais n'est pas un ordre absolu;
- que le jugement hermeneutique est la brique aval validee;
- qu'il ne voit pas les evenements internes non textuellement exposes.

Cette derniere phrase est importante: `main_hermeneutical.txt:148-152` dit explicitement au modele qu'il ne voit pas les sorties brutes de l'identity extractor, les evenements internes, les scores de retrieval ou des metadonnees non ecrites dans le prompt final.

## CE QU IL DOIT ENCORE DEVINER

Le modele doit encore deviner ou inferer:

- que la sequence conversationnelle visible est une fenetre selectionnee, possiblement tronquee par budget;
- que le resume actif remplace une partie de l'historique et que l'absence de messages plus anciens n'est pas une absence de conversation;
- quel resume parent correspond a quelle trace memoire quand plusieurs traces et plusieurs contextes sont presents;
- la forme exacte actuelle de l'identite active quand elle arrive sous `[STATIQUE]` / `[MUTABLE]`;
- quels candidats memoire ont ete rejetes et pourquoi, car seuls les souvenirs injectes sont visibles;
- si le contexte web provient d'une lane system ou d'une transformation du message utilisateur; le contrat explique le bloc, mais la forme role/user peut rester legerement ambigue.

## CONTRADICTIONS / AMBIGUITES / TROUS

### 1. Fenetre conversationnelle tronquee sans marqueur explicite

`conversations_prompt_window.build_prompt_messages()` selectionne les messages visibles sous contrainte de cutoff summary et de budget token (`app/core/conversations_prompt_window.py:253-299`). Cette selection est saine techniquement, mais le modele ne recoit pas un marqueur du type "historique recent selectionne, possiblement tronque".

Effet: il peut interpreter correctement les messages visibles, mais il ne sait pas explicitement quelles limites respecter sur l'absence des messages non visibles.

### 2. Contrat identity partiellement stale

Le bloc actif actuel est compose par `active_identity_projection.resolve_active_identity_projection()` en sections `[STATIQUE]` et `[MUTABLE]` (`app/identity/active_identity_projection.py:41-49`, `52-80`).

Le contrat hermeneutique explique bien statique vs mutable dans sa discipline d'enonciation (`main_hermeneutical.txt:38-40`), mais la matrice "Briques a interpreter" met surtout en avant les balises top-level et les anciennes lignes dynamiques `stability/recurrence/confidence` (`main_hermeneutical.txt:74-93`).

Effet: le modele peut comprendre l'intention generale, mais le contrat visible n'est pas parfaitement aligne sur la forme active exacte.

### 3. Parent summaries injectes sans mapping explicite par trace

Les resumes parents sont deduples puis injectes avant les traces (`app/core/conversations_prompt_window.py:274-287`). Le contrat dit qu'ils resituent un souvenir, mais le prompt final ne materialise pas une relation trace -> parent_summary.

Effet: avec un seul parent summary, c'est lisible. Avec plusieurs summaries et plusieurs traces, le modele peut seulement inferer la relation par proximite et par contenu.

### 4. Web context place dans le message user

Le contexte web est prepende au dernier message utilisateur (`app/core/chat_prompt_context.py:294-303`). Le contrat l'explique (`main_hermeneutical.txt:123-133`), mais la forme visible parle parfois en premiere personne: "J'ai effectue une recherche...".

Effet: le modele a assez d'instructions pour le lire comme contexte externe injecte, mais cette lane est moins nette qu'un message system dedie.

### 5. Projection hermeneutique aval compacte

Le modele principal ne voit pas `primary_verdict`, `validation_dialogue_context`, `source_priority` ou `source_conflicts` bruts. Il voit seulement `[JUGEMENT HERMENEUTIQUE]`, ce qui est conforme au contrat aval. Cela evite le dump technique mais rend impossible pour le modele principal de relire lui-meme les arbitrages de source fins.

Effet: ce n'est pas un bug, mais c'est une limite explicite: la comprehension fine est dans le pipeline amont, pas dans le prompt principal.

## PROVIDERS SECONDAIRES

### Stimmung agent

Le provider recoit une fenetre conversationnelle courte et le tour courant, construits par `app/core/stimmung_agent.py:180-231`. Son prompt (`app/prompts/stimmung_agent.txt:1-47`) explique:

- qu'il est un classificateur affectif minimal;
- que le centre est le tour courant;
- que la fenetre courte est seulement contextuelle;
- qu'il ne doit pas produire de psychologie durable;
- qu'il doit sortir un JSON strict.

Verdict: contrat suffisant pour sa tache.

### Validation agent

Le provider recoit un user payload explicitement structure:

- `validation_dialogue_context`;
- `primary_verdict`;
- `justifications`;
- `canonical_inputs`;
- `hard_guards`;
- tache et schema.

`app/core/hermeneutic_node/validation/validation_agent.py:825-875` nomme clairement la priorite: le dialogue local est la matiere principale, les autres inputs sont secondaires. Le prompt statique (`app/prompts/validation_agent.txt:1-26`) renforce cette doctrine.

Verdict: contrat fort. Limite: les canonical inputs sont volontairement compacts/tronques pour le provider; il ne faut pas croire que le validation agent relit tous les contenus bruts.

### Memory arbiter

L'arbitre recoit recent context et candidate memories (`app/memory/arbiter.py:322-349`). Son prompt (`app/prompts/arbiter.txt:1-49`) explique le sens de `retrieval_score`, `semantic_score`, la discipline de rejet et le schema de sortie.

Verdict: contrat fort pour le tri memoire.

### Web reformulation

Le provider recoit une tache tres etroite: transformer un message en requete web courte (`app/prompts/web_reformulation.txt:1`). Le contrat est minimal mais suffisant.

Verdict: suffisant.

### Summary system

Le summarizer recoit un dialogue et doit produire une synthese concise/exhaustive utile a la suite (`app/prompts/summary_system.txt:1`). Le contrat est court mais coherent avec sa fonction.

Verdict: acceptable. Limite: il ne formalise pas finement la gestion d'incertitude ou de contenu contradictoire; ce serait un futur durcissement possible, pas un trou bloquant pour le modele principal.

### Identity extractor et periodic identity agent

`identity_extractor` a un schema strict et des labels epistemiques (`app/prompts/identity_extractor.txt:1-46`). `identity_periodic_agent` a un contrat plus riche sur les deux identites canoniques, le rejet des signaux faibles et les operations locales (`app/prompts/identity_periodic_agent.txt:1-71`).

Verdict: suffisant pour leurs payloads propres.

## FINDINGS P0/P1/P2/P3

### P0

Aucun P0 trouve. Aucun bloc majeur du payload principal n'est totalement non explique.

### P1 - La fenetre conversationnelle recente n'expose pas clairement ses limites au modele principal

Preuve:

- `build_prompt_messages()` applique cutoff summary et budget token sans ajouter de marqueur de fenetre/troncature au prompt final (`app/core/conversations_prompt_window.py:253-299`).
- Le contrat explique les labels temporels, le silence et le resume, mais pas explicitement que les messages visibles sont une selection possiblement incomplete.

Impact:

- Le modele interprete les messages visibles, mais peut devoir deviner les limites de l'historique disponible.
- Cela touche directement la question "quelles limites respecter ?".

Recommandation:

- Dans un futur lot prompt-first, ajouter une brique courte de type "Fenetre conversationnelle visible" ou un marqueur de selection/troncature quand applicable.

### P2 - Le contrat identity ne colle plus parfaitement a la forme active

Preuve:

- La projection active compose `[STATIQUE]` et `[MUTABLE]` (`app/identity/active_identity_projection.py:41-49`).
- Le contrat explique statique/mutable dans la discipline generale, mais la liste des formes visibles met encore l'accent sur des lignes dynamiques `stability/recurrence/confidence` (`app/prompts/main_hermeneutical.txt:86-93`).

Impact:

- Le modele comprend probablement l'intention, mais l'audit ne peut pas dire que la forme active est integralement enseignee.

Recommandation:

- Aligner la section "Bloc identites" avec la forme `[STATIQUE]` / `[MUTABLE]`, et conserver les lignes dynamiques seulement comme forme legacy/eventuelle.

### P2 - Le lien trace memoire -> parent summary reste implicite

Preuve:

- Les parent summaries sont collectes/dedupliques avant injection (`app/core/conversations_prompt_window.py:274-284`).
- Les traces sont injectees ensuite dans un bloc separe (`app/core/conversations_prompt_window.py:285-287`).
- Le contrat explique la fonction generale du contexte de souvenir (`app/prompts/main_hermeneutical.txt:109-114`) mais pas de mapping par trace.

Impact:

- Avec plusieurs traces et plusieurs summaries, la relation exacte peut etre inferee mais pas lue structurellement.

Recommandation:

- Si cette precision devient importante pour la reponse, rendre la relation visible par groupement ou reference compacte dans le prompt.

### P2 - Le contexte web est semantiquement explique mais transporté dans le message utilisateur

Preuve:

- `inject_web_context()` remplace le dernier message user par `ctx + "\n\nQuestion : " + content` (`app/core/chat_prompt_context.py:294-303`).
- Le contrat web explique cette forme (`app/prompts/main_hermeneutical.txt:123-133`).

Impact:

- Le modele a la consigne d'interpretation, mais la lane reste conceptuellement plus propre dans le contrat que dans la forme role/message.

Recommandation:

- Ne pas corriger en urgence; si un futur lot de prompt hygiene existe, envisager une lane system ou une annotation encore plus explicite.

### P3 - Quelques libelles du contrat statique ne sont pas strictement identiques aux balises runtime

Preuve:

- Le builder produit des balises accentuees comme `[Résumé de la période ...]` et `[Contexte du souvenir — résumé ...]` (`app/core/conversations_prompt_window.py:41-51`, `107-123`).
- Le prompt statique utilise parfois une forme ASCII ou approximative (`Resume`, `-- resume`, `RESULTATS`) dans la description.

Impact:

- Faible pour le modele, car les formes restent humainement equivalentes.
- Moyen pour la maintenabilite de contrat exact.

Recommandation:

- Aligner les libelles statiques lors d'un futur lot docs/prompt.

## RECOMMANDATIONS

1. Ne pas refaire tout le prompt: le contrat principal existe et fait deja beaucoup de travail utile.
2. Ajouter d'abord un marqueur de fenetre/troncature conversationnelle, car c'est le trou le plus proche d'une mauvaise interpretation.
3. Mettre a jour le contrat identity pour decrire explicitement `[STATIQUE]` et `[MUTABLE]`.
4. Clarifier le groupement parent summary -> traces si les reponses futures doivent s'appuyer sur cette relation.
5. Garder la projection `[JUGEMENT HERMENEUTIQUE]` compacte; ne pas dumper `primary_verdict` dans le prompt principal sans besoin prouve.
6. Pour les futurs documents actifs de conversation, creer une lane prompt explicitement contractee des le premier lot runtime, au lieu de reproduire les ambiguities de fenetre ou web.

## PREUVES / FICHIERS LUS / COMMANDES

Commandes initiales:

- `git fetch origin main`
- `git pull --ff-only origin main`
- `git status --short`

Fichiers runtime principaux lus:

- `AGENTS.md`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/core/conversations_prompt_window.py`
- `app/core/conv_store.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_turn_runtime_inputs.py`
- `app/core/chat_memory_flow.py`
- `app/core/hermeneutic_node/inputs/time_input.py`
- `app/core/hermeneutic_node/inputs/summary_input.py`
- `app/core/hermeneutic_node/inputs/memory_retrieved_input.py`
- `app/core/hermeneutic_node/inputs/memory_arbitration_input.py`
- `app/core/hermeneutic_node/inputs/recent_context_input.py`
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
- `app/core/hermeneutic_node/inputs/web_input.py`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/core/stimmung_agent.py`
- `app/memory/arbiter.py`
- `app/identity/identity.py`
- `app/identity/active_identity_projection.py`
- `app/tools/web_search.py`

Prompts lus:

- `app/prompts/main_system.txt`
- `app/prompts/main_hermeneutical.txt`
- `app/prompts/stimmung_agent.txt`
- `app/prompts/validation_agent.txt`
- `app/prompts/web_reformulation.txt`
- `app/prompts/summary_system.txt`
- `app/prompts/arbiter.txt`
- `app/prompts/identity_extractor.txt`
- `app/prompts/identity_periodic_agent.txt`

Docs/specs relues:

- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- `app/docs/states/specs/chat-time-grounding-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/memory-rag-summaries-lane-contract.md`
- `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- `app/docs/states/specs/hermeneutic-node-validated-output-contract.md`
- `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/docs/states/specs/dashboard-long-term-observability-contract.md`

Tests et preuves contractuelles inspectes par recherche:

- `app/tests/test_prompt_loader_phase13.py`
- `app/tests/unit/chat/test_chat_prompt_context.py`
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`
- `app/tests/test_server_chat_web_runtime_contract.py`
- tests unitaires autour de memory summaries, prompt window, dashboard read-models et observability.

Preuve content-free:

- Aucun contenu brut de conversation, prompt utilisateur live, secret, DSN ou token n'a ete affiche ni requis pour cet audit.
