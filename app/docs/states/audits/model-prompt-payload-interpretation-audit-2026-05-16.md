# Audit - Contrat semantique entre payloads modele et prompts - 2026-05-16

Statut: audit transverse read-only
Portee: modele principal, prompts effectifs, payloads secondaires quand ils portent leur propre contrat d'interpretation
Hors-scope: patch correctif de prompt, refonte runtime, dashboard, documents actifs de conversation

## EXECUTIVE SUMMARY

Verdict court: FridaDev possede deja un contrat d'interpretation substantiel pour le modele principal. Le fichier `app/prompts/main_hermeneutical.txt` n'est pas un simple prompt de ton: il declare explicitement les briques runtime attendues, leur priorite relative, leur usage et leurs limites. Le systeme ne se contente donc pas d'envoyer des blocs au modele en esperant qu'il devine leur sens.

Relecture ciblee du 2026-05-16: plusieurs formulations du premier audit etaient trop larges. Le constat solide n'est pas "tout est tronque": il faut distinguer le remplacement explicite par resume actif et l'exclusion budgetaire silencieuse des messages plus anciens. De meme, l'identite `[STATIQUE]` / `[MUTABLE]` est la forme active normale et deja expliquee dans le prompt; seul un reliquat de vocabulaire sur les anciennes lignes dynamiques reste a nettoyer. Le web transporte bien son contexte dans le dernier message utilisateur, mais le contrat prompt couvre cette forme assez clairement: ce n'est pas un finding semantique demontre, seulement une note d'architecture.

Les deux points qui restent vraiment solides sont:

- la selection budgetaire de la fenetre conversationnelle peut exclure des messages visibles sans marqueur explicite dans le prompt final;
- les resumes parents associes aux traces memoire sont injectes avant les traces, mais le lien trace -> parent_summary reste semantiquement implicite pour le modele principal.

Mise a jour corrective du 2026-05-16:

- le finding P1 de selection budgetaire silencieuse est ferme cote runtime: `build_prompt_messages()` conserve desormais tous les messages `user` + `assistant` eligibles apres le cutoff du resume actif;
- `FRIDA_MAX_TOKENS` / `config.MAX_TOKENS` n'est plus un mecanisme normal de coupe de dialogue recent, mais un soft limit d'observabilite du prompt complet;
- si le prompt complet depasse ce soft limit, l'evenement `token_window` le signale sans retirer de messages dialogiques recents;
- le risque residuel n'est plus une troncature silencieuse normale, mais l'eventuelle impossibilite physique provider, qui devra rester une garde explicite si elle se manifeste.

Reponse a la question centrale:

Quand Frida recoit quelque chose dans son payload principal, elle sait en general ce que c'est et quoi en faire au niveau bloc. Elle doit encore deviner certains details de limites, de provenance fine et de relation entre blocs. Le danger n'est pas l'absence totale de contrat; le danger est de confondre "bloc interpretable" avec "composition complete et limites parfaitement explicites", ou de maquiller une exclusion budgetaire de messages en simple question de prompt.

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

- les limites exactes de la fenetre conversationnelle recente quand le budget prompt exclut des messages plus anciens;
- le couplage exact entre parent summaries et traces memoire;
- la distinction entre ce que le pipeline a exclu avant prompt et ce que le modele ne voit simplement pas.

Il n'est plus considere partiel pour l'interpretation principale de l'identite `[STATIQUE]` / `[MUTABLE]`: cette coexistence est bien la forme active normale et le prompt l'explique deja. Le reliquat identity est une dette de hygiene du contrat statique, pas un trou semantique majeur.

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

## RELECTURE CIBLEE DU 2026-05-16

Objet de la relecture: mettre a l'epreuve les findings initiaux avant toute correction runtime/prompt.

Existe-t-il un meilleur plan que corriger directement les findings tels qu'ils ont ete formules ?

Oui. Le meilleur plan est de ne pas corriger mecaniquement les findings initiaux, mais de les reclassifier depuis le code courant:

1. verifier la composition effective du payload;
2. verifier le contrat prompt qui explique cette composition;
3. separer probleme de composition runtime, probleme de contrat prompt et simple remarque d'architecture;
4. ne garder comme findings que les risques d'interpretation demontres.

| Point relu | Statut apres relecture | Nature retenue | Preuves courtes | Decision |
| --- | --- | --- | --- | --- |
| Fenetre recente / historique tronque | Confirme, requalifie, puis corrige runtime le 2026-05-16 | Ancien probleme de composition payload/runtime pour l'exclusion budgetaire; le cutoff par resume reste une substitution explicite distincte | `build_prompt_messages()` applique toujours le cutoff apres resume actif, mais conserve maintenant tous les candidats posterieurs au cutoff et journalise seulement le soft limit (`app/core/conversations_prompt_window.py`) | P1 ferme cote runtime; surveiller seulement les impossibilites provider explicites |
| Identite active `[STATIQUE]` / `[MUTABLE]` | Requalifie a la baisse | Hygiene de contrat prompt, pas trou semantique principal | `active_identity_projection` compose explicitement `[STATIQUE]` et `[MUTABLE]` (`app/identity/active_identity_projection.py:41-49`); le prompt explique le socle statique et la modulation mutable (`app/prompts/main_hermeneutical.txt:38-40`, `74-84`) | Remplacer le P2 initial par un P3 sur les lignes dynamiques legacy encore decrites |
| Lien trace memoire -> resume parent | Confirme | Probleme semantique de composition du payload prompt | Les parent summaries sont deduples puis injectes avant les traces (`app/core/conversations_prompt_window.py:274-287`); les traces elles-memes ne portent pas de reference visible au resume parent (`app/core/conversations_prompt_window.py:159-181`) | Garder en P2 solide |
| Contexte web dans message utilisateur | Invalide comme finding semantique demontre; conserve comme note architecture | Remarque d'architecture | `inject_web_context()` prepend le contexte au dernier message user (`app/core/chat_prompt_context.py:294-303`), mais le bloc porte `[RECHERCHE WEB]`, `[FIN DES RÉSULTATS WEB]`, `Question :`, et le prompt explique cette forme (`app/prompts/main_hermeneutical.txt:123-133`) | Ne pas le traiter comme dette urgente; eventuellement nettoyer la lane plus tard si un lot prompt hygiene existe |
| NOW | Confirme complet | Pas de finding | `time_input.build_time_reference_block()` injecte `NOW` / `TIMEZONE` et l'interdit de pretendre ne pas avoir le temps (`app/core/hermeneutic_node/inputs/time_input.py:68-86`); le prompt le couvre (`app/prompts/main_hermeneutical.txt:45-60`); tests contractuels existent (`app/tests/unit/chat/test_chat_prompt_context.py:80-110`) | Conserver comme chaine payload -> prompt -> usage complete |

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
| Question utilisateur finale | Conversation courante, puis `build_prompt_messages()` | Dernier message user, ou `context web + Question : + message user` | `main_hermeneutical.txt:142-146` | Centre de gravite de la reponse, dominant sauf contradiction avec system prompt | Le cas web est explique par le contrat; il reste une forme de transport moins propre architecturalement qu'une lane system dediee, sans risque semantique concret demontre |
| Repere temporel | `time_input.build_time_reference_block()`, appele par `chat_prompt_context.build_augmented_system()` | `[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`, phrase humaine | `main_hermeneutical.txt:45-60`; `chat-time-grounding-contract.md` | Utiliser NOW pour les relatifs, ne pas pretendre ne pas avoir de temps de reference | Contrat fort; pas de trou majeur |
| Labels Delta-T | `conversations_prompt_window.delta_t_label()` et builders de messages | Prefixes tels que `[il y a ...]`, `[aujourd'hui ...]` | `main_hermeneutical.txt:62-66` | Lire comme deltas relatifs conversationnels | Le modele ne voit pas la classe stable, seulement le rendu humain |
| Marqueurs de silence | `conversations_prompt_window.silence_label()` dans `build_prompt_messages()` | Messages system `[-- silence de X --]` entre messages selectionnes | `main_hermeneutical.txt:68-72` | Reprise sobre si utile, pas de psychologie du silence | Pas de trou majeur |
| Identite active | `identity.build_identity_block()` -> `active_identity_projection.resolve_active_identity_projection()` | `[IDENTITÉ DU MODÈLE]`, `[IDENTITÉ DE L'UTILISATEUR]`, sous-sections actuelles `[STATIQUE]` / `[MUTABLE]` | `main_hermeneutical.txt:32-43`, `74-84`; specs identity | Garder coherence relationnelle et contextuelle; statique comme socle, mutable comme nuance; ne pas ecraser la demande | La coexistence statique/mutable est bien enseignee; le contrat pourrait seulement lister les sous-balises visibles plus explicitement |
| Lignes dynamiques d'identite | Chemin interne `_format_identity_line()`, pas la forme principale actuelle du bloc actif | Si un ancien chemin les utilisait: `- [stability=...; recurrence=...; confidence=...] ...` | `main_hermeneutical.txt:86-93` | Traiter comme indices de ponderation, pas preuves fortes | Reliquat legacy/provisoire dans le prompt statique; dette de hygiene P3, pas preuve d'un payload actif mal explique |
| Resume actif de conversation | `conversations_prompt_window.get_active_summary()` + `make_summary_message()` | Message system `[Résumé de la période ...]` puis contenu du resume | `main_hermeneutical.txt:95-100`; `memory-rag-summaries-lane-contract.md` | Memoire du passe, continuite generale, moins fort qu'un souvenir specifique | Le modele voit le resume et sait que c'est une synthese; il ne voit pas les messages exacts remplaces par ce resume, ce qui est une limite assumee de fidelity, pas la meme chose qu'une troncature silencieuse |
| Fenetre conversationnelle recente | `conversations_prompt_window.build_prompt_messages()` | Messages user/assistant eligibles posterieurs au cutoff summary, conserves integralement; le budget complet est seulement observe | `main_hermeneutical.txt:62-72`, `142-146`; contrat temporel; `memory-rag-summaries-lane-contract.md` | Lire les messages visibles comme contexte conversationnel recent complet depuis le dernier resume actif | P1 ferme cote runtime le 2026-05-16: les couches non dialogiques ne coupent plus silencieusement ce dialogue recent |
| Indices contextuels recents | `make_context_hints_message()` | `[Indices contextuels recents]`, lignes avec scope et confidence | `main_hermeneutical.txt:102-107` | Indices faibles, non decisifs | Contrat suffisant |
| Traces memoire injectees | `prepare_memory_context()` puis `make_memory_message()` | `[Mémoire -- souvenirs pertinents]`, lignes avec role et contenu | `main_hermeneutical.txt:116-121`; `memory-rag-current-pipeline-cartography.md` | Utiliser seulement si lien utile avec demande courante; plus fort qu'indice contextuel, moins fort que demande finale | Le modele ne voit pas les scores, decisions arbitre, rejected candidates ni limites du panier; cela est volontaire mais doit rester compris comme limite |
| Resumes parents de traces memoire | `memory_store.enrich_traces_with_summaries()`, `make_memory_context_message()` | `[Contexte du souvenir — résumé ...]` avant les traces | `main_hermeneutical.txt:109-114`; spec summaries lane | Contexte de cadrage pour mieux comprendre la portee du souvenir | Le lien exact entre chaque trace et son parent summary reste implicite; pas de mapping visible par trace |
| Contexte web | `web_search.build_context_payload()` + `chat_prompt_context.inject_web_context()` | `[RECHERCHE WEB — date]`, sources, URLs, contenu utilise, `[FIN DES RÉSULTATS WEB]`, puis `Question :` dans le dernier message user | `main_hermeneutical.txt:123-133`; `build_web_reading_guard_block()` si `read_state` explicite | Lire comme contexte externe injecte pour la question courante; prioritaire sur memoire pour faits externes recents | Relecture: le risque de confusion avec la parole utilisateur n'est pas demontre, car la forme est explicitement decrite; la remarque restante est architecturale |
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
- que l'identite cadre la coherence mais n'est pas un ordre absolu, avec un socle statique et un mutable de modulation;
- que le contexte web prepende au dernier message utilisateur doit etre lu comme contexte externe injecte, distinct de la question apres `Question :`;
- que le jugement hermeneutique est la brique aval validee;
- que `NOW` et `TIMEZONE` donnent bien le temps de reference du tour;
- qu'il ne voit pas les evenements internes non textuellement exposes.

Cette derniere phrase est importante: `main_hermeneutical.txt:148-152` dit explicitement au modele qu'il ne voit pas les sorties brutes de l'identity extractor, les evenements internes, les scores de retrieval ou des metadonnees non ecrites dans le prompt final.

## CE QU IL DOIT ENCORE DEVINER

Le modele doit encore deviner ou inferer:

- que le resume actif represente des messages anterieurs sans permettre de relire leur texte exact;
- quel resume parent correspond a quelle trace memoire quand plusieurs traces et plusieurs contextes sont presents;
- quels candidats memoire ont ete rejetes et pourquoi, car seuls les souvenirs injectes sont visibles.

Points requalifies:

- l'identite active `[STATIQUE]` / `[MUTABLE]` n'est plus consideree comme un point que le modele doit deviner: le prompt explique deja statique comme socle et mutable comme nuance;
- le contexte web dans le dernier message user n'est plus conserve comme ambiguite semantique demontree: le prompt le decrit comme contexte externe injecte et indique la forme `Question :`.
- la selection budgetaire silencieuse du dialogue recent n'est plus conservee comme comportement runtime courant: le builder preserve la continuite recente et journalise seulement le soft limit.

## CONTRADICTIONS / AMBIGUITES / TROUS

### 1. Fenetre conversationnelle: substitution par resume vs exclusion budgetaire

`conversations_prompt_window.build_prompt_messages()` applique deux mecanismes distincts (`app/core/conversations_prompt_window.py:253-299`):

- si un resume actif existe, les candidats sont limites aux messages apres le cutoff du resume, et le resume est injecte explicitement avant la fenetre recente;
- depuis le correctif du 2026-05-16, les candidats recents posterieurs au cutoff sont conserves integralement; le prompt complet est seulement estime et compare a `FRIDA_MAX_TOKENS` comme soft limit d'observabilite.

Requalification: le cutoff par resume n'est pas une "troncature silencieuse" au meme sens, car le modele voit bien un `[Résumé ...]` et sait qu'il s'agit d'une synthese. L'ancienne selection budgetaire pouvait, elle, exclure des messages plus anciens sans marqueur visible. Ce point a ete corrige cote runtime: les blocs non dialogiques ne rabotent plus la continuite recente directe.

Effet residuel: le modele ne voit toujours pas le texte exact remplace par un resume actif, par definition du resume glissant. Si le prompt complet depasse un jour la capacite physique du provider, cela doit etre gere comme garde explicite, pas comme fenetre normale silencieuse.

### 2. Contrat identity: forme active bien comprise, reliquat dynamique legacy

Le bloc actif actuel est compose par `active_identity_projection.resolve_active_identity_projection()` en sections `[STATIQUE]` et `[MUTABLE]` (`app/identity/active_identity_projection.py:41-49`, `52-80`).

Le contrat hermeneutique explique deja la coexistence statique/mutable: "le socle statique donne la base" et "le mutable peut seulement la moduler" (`app/prompts/main_hermeneutical.txt:38-40`), puis la section "Bloc identites" redit cette interpretation (`app/prompts/main_hermeneutical.txt:74-84`).

Requalification: le finding initial etait trop fort. La forme `[STATIQUE]` / `[MUTABLE]` n'est pas une forme ancienne mal remplacee; c'est la forme active normale. Le vrai reliquat est seulement que le prompt conserve une section sur les lignes dynamiques `stability/recurrence/confidence` (`app/prompts/main_hermeneutical.txt:86-93`), alors que ce n'est pas la forme principale du bloc actif injecte par `identity.build_identity_block()`.

Effet: pas d'impact semantique principal demontre pour le modele. Dette de hygiene P3: clarifier que les lignes dynamiques sont legacy/eventuelles ou les retirer si elles ne sont plus exposees.

### 3. Parent summaries injectes sans mapping explicite par trace

Les resumes parents sont deduples puis injectes avant les traces (`app/core/conversations_prompt_window.py:274-287`). Le contrat dit qu'ils resituent un souvenir, mais le prompt final ne materialise pas une relation trace -> parent_summary.

Effet: avec un seul parent summary, c'est lisible. Avec plusieurs summaries et plusieurs traces, le modele peut seulement inferer la relation par proximite et par contenu.

### 4. Web context place dans le message user: note architecture, finding semantique invalide

Le contexte web est prepende au dernier message utilisateur (`app/core/chat_prompt_context.py:294-303`). Le contrat l'explique (`main_hermeneutical.txt:123-133`), mais la forme visible parle parfois en premiere personne: "J'ai effectue une recherche...".

Requalification: le risque concret de confusion avec la parole utilisateur n'est pas demontre dans l'etat courant. Le bloc runtime porte `[RECHERCHE WEB ...]`, une fin de resultats, puis `Question :`; le prompt dit explicitement que cette forme se trouve dans le dernier message utilisateur et doit etre lue comme contexte externe injecte.

Effet: il reste une remarque d'architecture sur la proprete de la lane, mais pas un P2 semantique a corriger par inertie.

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

### P1 - CONFIRME, REQUALIFIE, PUIS CORRIGE - La selection budgetaire pouvait exclure des messages sans marqueur visible

Preuve:

- `build_prompt_messages()` applique d'abord un cutoff lie au resume actif, puis une selection budgetaire sur les candidats recents (`app/core/conversations_prompt_window.py:253-299`).
- Le cutoff lie au resume n'est pas une perte muette: le prompt contient le resume actif via `make_summary_message()`.
- Avant correctif, la selection budgetaire cassait la boucle quand `estimated_trial_tokens > max_tokens` sans ajouter de marqueur au prompt final sur les messages candidats exclus.
- Depuis le correctif du 2026-05-16, le builder conserve tous les candidats dialogiques posterieurs au resume actif et journalise `prompt_soft_limit_exceeded` sans couper le dialogue recent.

Impact:

- Le comportement runtime courant ne demande plus au modele de deviner une coupe budgetaire silencieuse du dialogue recent.
- La limite restante concerne seulement les anciens messages remplaces par resume actif et les impossibilites provider explicites futures.

Recommandation:

- Conserver l'invariant dans les tests et la spec summaries: `SUMMARY_THRESHOLD_TOKENS` decide le resume sur dialogue direct; `FRIDA_MAX_TOKENS` n'est pas un ciseau de dialogue.
- Si une vraie garde provider est ajoutee plus tard, elle doit etre visible, explicite et separee de la memoire dialogique normale.

### P2 - CONFIRME - Le lien trace memoire -> parent summary reste implicite

Preuve:

- Les parent summaries sont collectes/dedupliques avant injection (`app/core/conversations_prompt_window.py:274-284`).
- Les traces sont injectees ensuite dans un bloc separe (`app/core/conversations_prompt_window.py:285-287`).
- Les lignes de traces ne portent pas de reference visible au parent summary (`app/core/conversations_prompt_window.py:159-181`).
- Le contrat explique la fonction generale du contexte de souvenir (`app/prompts/main_hermeneutical.txt:109-114`) mais pas de mapping par trace.

Impact:

- Avec plusieurs traces et plusieurs summaries, la relation exacte peut etre inferee mais pas lue structurellement.
- Impact semantique reel: le modele peut appliquer un contexte de periode a une trace voisine ou pertinente par contenu sans preuve explicite du lien.

Recommandation:

- Si cette precision devient importante pour la reponse, rendre la relation visible par groupement ou reference compacte dans le prompt.

### P2 initial INVALIDÉ - Le contexte web est explique mais transporte dans le message utilisateur

Preuve:

- `inject_web_context()` remplace le dernier message user par `ctx + "\n\nQuestion : " + content` (`app/core/chat_prompt_context.py:294-303`).
- Le contexte produit des balises `[RECHERCHE WEB ...]` et `[FIN DES RÉSULTATS WEB]` (`app/tools/web_search.py:407-417`, `522-545`).
- Le contrat web explique explicitement cette forme "dans le dernier message utilisateur", la phrase `Question :`, sa fonction de contexte externe et ses limites (`app/prompts/main_hermeneutical.txt:123-133`).

Requalification:

- Le transport dans le message `user` est materiellement vrai.
- Le risque semantique concret de confusion avec la parole utilisateur n'est pas demontre dans l'etat courant.
- Ce point devient une remarque d'architecture/lane hygiene, pas un P2.

Recommandation:

- Ne pas corriger en urgence. Si un futur lot de prompt hygiene existe, une lane system web plus explicite peut etre etudiee, mais elle ne doit pas etre priorisee comme trou d'interpretation prouve.

### P3 - REQUALIFIE - Reliquat identity sur les lignes dynamiques legacy

Preuve:

- La projection active compose `[STATIQUE]` et `[MUTABLE]` (`app/identity/active_identity_projection.py:41-49`).
- `identity.build_identity_block()` utilise cette projection active (`app/identity/identity.py:323-368`).
- Le contrat explique statique/mutable dans la discipline generale et dans la section bloc identites (`app/prompts/main_hermeneutical.txt:38-40`, `74-84`).
- Une section separee conserve toutefois les lignes dynamiques `stability/recurrence/confidence` (`app/prompts/main_hermeneutical.txt:86-93`), qui ne sont pas la forme principale actuelle.

Impact:

- Pas de trou semantique principal demontre: le modele sait lire statique + mutable.
- Dette de hygiene: le contrat statique peut laisser croire que les lignes dynamiques sont une forme active courante.

Recommandation:

- Aligner la section identity du prompt en declarant explicitement `[STATIQUE]` / `[MUTABLE]` comme forme active, et reclasser les lignes dynamiques comme legacy/eventuelles si elles restent utiles.

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
2. Traiter d'abord la selection budgetaire silencieuse de la fenetre conversationnelle: c'est le trou le plus proche d'une contradiction produit/runtime.
3. Clarifier le groupement parent summary -> traces si les reponses futures doivent s'appuyer sur cette relation.
4. Mettre a jour le contrat identity a faible risque: declarer `[STATIQUE]` / `[MUTABLE]` comme forme active et reclasser les lignes dynamiques en legacy/eventuel.
5. Ne pas ouvrir de correction NOW: la chaine payload -> prompt -> usage attendu est complete.
6. Ne pas prioriser le web comme finding semantique: garder seulement la possibilite d'une lane system plus propre si un futur lot de prompt hygiene le justifie.
7. Garder la projection `[JUGEMENT HERMENEUTIQUE]` compacte; ne pas dumper `primary_verdict` dans le prompt principal sans besoin prouve.
8. Pour les futurs documents actifs de conversation, creer une lane prompt explicitement contractee des le premier lot runtime, au lieu de reproduire l'ambiguite de selection de fenetre.

## PREUVES / FICHIERS LUS / COMMANDES

Commandes initiales:

- `git fetch origin main`
- `git pull --ff-only origin main`
- `git status --short`

Commandes de relecture ciblee du 2026-05-16:

- `nl -ba app/core/conversations_prompt_window.py | sed -n '1,330p'`
- `nl -ba app/prompts/main_hermeneutical.txt | sed -n '1,190p'`
- `nl -ba app/identity/active_identity_projection.py | sed -n '1,180p'`
- `nl -ba app/identity/identity.py | sed -n '1,420p'`
- `nl -ba app/core/chat_prompt_context.py | sed -n '1,360p'`
- `grep -R "parent_summary\\|summary_id\\|make_memory_context_message\\|make_memory_message\\|build_prompt_messages" -n app/core app/memory app/observability app/tests tests`
- `grep -R "build_context_payload\\|\\[RECHERCHE WEB\\|FIN DES RESULTATS WEB\\|Question :" -n app/core app/tools app/tests tests`
- `grep -R "NOW:\\|RÉFÉRENCE TEMPORELLE\\|build_time_reference_block\\|build_time_input" -n app/core app/prompts app/docs/states/specs app/tests tests`

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
