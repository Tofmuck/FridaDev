# Hermeneutic Node Validation Agent Contract

Statut: spec historique partiellement supersedee
Portee: premiere pause normative du Lot 9 pour `validation_agent`, relue a la lumiere du lot 2 runtime

Note runtime 2026-04-19:

- `response-arbiter-power-contract.md` est la source normative recente sur la chaine de pouvoir;
- `validation_agent` produit maintenant directement `final_judgment_posture`, `final_output_regime` et `arbiter_reason`;
- `validation_decision` peut subsister comme trace legacy de compatibilite, mais elle n'est plus la source souveraine du verdict final.
- `validation_dialogue_context` est maintenant livre en runtime comme fenetre dialogique locale canonisee de 5 messages maximum, priorisant le user courant puis le dernier assistant.
- le lot 4 runtime lit maintenant un bloc `upstream_advisory` dans `primary_verdict` comme recommendation amont de reference, secondaire et non souveraine.
- le lot 5 runtime evalue des garde-fous durs rares dans un module voisin, interdit `answer` quand ils s'appliquent, mais laisse a l'arbitre le choix entre `clarify` et `suspend`.
- le lot 6 verrouille un corpus stable de cas `answer / clarify / suspend`, plus les preuves de suivi vs override et de projection finale, sans nouvelle surface d'observabilite.

Note runtime 2026-05-14:

- `validation_prompt_prepared` journalise maintenant l'exposition provider secondaire du `validation_agent` sous forme content-free avant l'appel provider;
- `validation_agent` reste la source souveraine de la sortie finale retenue pour le prompt principal;
- le `node_state` persistant est mis a jour depuis cette sortie finale validee, et non depuis le verdict primaire pre-validation;
- les preuves bout-en-bout sont portees par les contrats thematiques `app/tests/test_server_chat_hermeneutic_insertion_contract.py`, `app/tests/test_server_chat_compact_observability_contract.py`, `app/tests/test_server_chat_synthetic_logs_contract.py` et `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py`.

Note runtime 2026-05-17:

- le prompt du `validation_agent` inscrit maintenant la triade `Warum / Wofür / Wozu` comme discipline de lecture du texte du tour et du dialogue comme texte;
- cette discipline reste un geste de relecture: elle ne cree aucun champ de sortie, aucun nouvel objet `interpretive_center`, aucune projection directe dans `[JUGEMENT HERMENEUTIQUE]` et aucune surface d'observabilite nouvelle;
- les trois questions doivent etre tenues ensemble, sans psychologiser l'utilisateur et sans donner de souverainete speciale au seul `Wozu`.

Note runtime 2026-07-23:

- la presomption de sens, la distinction entre comprendre et adopter et la
  clarification apres tentative d'interpretation coherente sont desormais des
  obligations du prompt effectivement consomme par `validation_agent`;
- `final_output_regime` accepte `presence` uniquement avec
  `final_judgment_posture=answer`;
- `presence` est une decision positive locale qui commande la sortie canonique
  exacte `...`; elle reste distincte de `suspend`, ne peut pas etre produite par
  un fail-open et n'est pas persistee dans `node_state`;
- l'aval reutilise `AssistantResponseOverride` et la frontiere commune de
  succes/persistance, sans appel au provider principal ni second save;
- le corpus synthetique borne vit dans
  `app/tests/support/dialogic_regime_corpus.json`; il fixe des oppositions de
  lecture et de protocole, pas une preuve de comprehension modele.

## 1. Purpose

Cette spec ouvre la premiere pause normative du Lot 9.

Elle tranchait initialement:

- la nature exacte du `validation_agent`
- sa frontiere avec le noeud primaire, le verdict final et l'aval
- son statut d'agent borne, en une passe, sans autonomie agentique forte en V1
- son entree minimale
- la centralite du contexte dialogique recent elargi dans la relecture
- ses sorties minimales de revision
- sa frontiere minimale avec `pipeline_directives_final`
- son cadre operationnel minimal
- ses besoins minimaux d'observabilite

Le runtime lot 2 a depuis precise:

- que la sortie souveraine est un verdict arbitral final direct;
- que `validation_decision` n'est plus qu'une trace legacy derivee;
- que le wiring aval consomme ce verdict final et non une table de combinaison externe.

## 2. Repo Grounding

Le repo a deja stabilise:

- `primary_verdict`
- `node_state`
- `output_regime`
- la frontiere `primary node -> validation -> aval`
- `recent_context_input`
- `recent_window_input`

Notamment:

- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/hermeneutic_node/inputs/recent_context_input.py`
- `app/core/hermeneutic_node/inputs/recent_window_input.py`

La cible code de cette pause normative est:

- `app/core/hermeneutic_node/validation/validation_agent.py`

Cette spec ne cree ni ce fichier, ni son wiring.

## 3. Primary Node / Validation / Downstream Boundary

Le `validation_agent` intervient:

- apres `primary_node`
- avant tout branchement aval
- avant toute consommation de `pipeline_directives_final`

Il ne:

- produit pas le `primary_verdict`
- ne remplace pas le noeud primaire
- ne remplace pas les contrats doctrinaux deja fermes
- ne vaut pas sortie finale complete a lui seul

Frontiere minimale:

- `runtime/primary_node`
  - produit le `primary_verdict`
- `validation/validation_agent`
  - relit ce verdict, le juge et tranche directement le verdict final arbitral
- `aval`
  - ne consomme pas directement le `primary_verdict`

## 4. Nature Exacte Du `validation_agent`

`validation_agent` est un agent de validation hermeneutique borne.

Il est:

- un juge de revision
- une passe unique de relecture
- un agent contraint
- souverain sur la validation finale

Il n'est pas:

- un agent autonome multi-boucles
- un agent outille
- un agent qui recherche, replannifie ou se relance tout seul
- un second noeud primaire cache
- un auto-legislateur des criteres doctrinaux

Discipline minimale:

- V1 = une passe
- pas d'autonomie agentique forte
- pas de second systeme de regles cache
- pas de rederivation libre du noeud primaire

## 5. Minimal Validation Input Contract

L'entree minimale du `validation_agent` est une enveloppe structuree qui comprend:

- `primary_verdict`
- un artefact frere de `justifications`
- un `validation_dialogue_context`
- les entrees canoniques pertinentes du tour

`pipeline_directives_provisional` reste une matiere explicite de validation,
mais elle est lue dans `primary_verdict`.
Cette V1 ne duplique donc pas ce bloc dans un second transport parallele.

Forme minimale de lecture:

```python
{
    "primary_verdict": {...},
    "justifications": {...},
    "validation_dialogue_context": {...},
    "canonical_inputs": {...},
}
```

Regles minimales:

- `primary_verdict` reste l'entree canonique primaire du jugement
- `justifications` restent hors `primary_verdict`
- `validation_dialogue_context` ne vaut pas side input faible
- les entrees canoniques pertinentes restent disponibles pour relire le verdict dans son cadre

Transport borne courant des entrees canoniques:

- `validation_canonical_inputs_v2` est l'unique version emise par le runtime
  courant. Elle remplace le transport v1 a `700` caracteres, conserve dans les
  readers uniquement comme contrat historique, par une enveloppe JSON
  structurelle bornee a `3840` caracteres;
- les familles connues suivent l'ordre stable de construction runtime
  `time_input`, `memory_retrieved`, `memory_arbitration`, `summary_input`,
  `identity_input`, `recent_context_input`, `recent_window_input`,
  `user_turn_input`, `user_turn_signals`, `stimmung_input`, `web_input`;
- cet ordre est un ordre de transport, pas une nouvelle hierarchie de verite;
- `time_input`, `recent_context_input` et `recent_window_input` ne sont pas
  recopies: leur matiere est deja transmise par `temporal_reference` et
  `validation_dialogue_context`;
- memory retrieval/arbitration, summary, Identity et Web sont projetes en
  statuts, raisons, compteurs et indicateurs bornes necessaires a l'arbitrage;
  aucun contenu, trace, URL, dialogue ou resultat Web n'est recopie;
- `user_turn_input`, `user_turn_signals` et un `stimmung_input` valide restent
  des structures completes et bornees;
- chaque famille recoit exactement une disposition fermee: `included`,
  `no_data`, `redundant_elsewhere`, `optional_not_requested`, `invalid_input`
  ou `contract_budget_exceeded`;
- le statut Stimmung transporte vaut uniquement `full` avec
  `reason_code=included`, ou `absent` avec `signal_not_present`,
  `invalid_signal` ou `contract_budget_exceeded`; `partial` est invalide;
- une reconstruction repetee est deterministe, ignore les cles hors contrat et
  ne depend pas de leur ordre lexical;
- le maximum accepte par le validateur structurel v2 mesure `3741` caracteres,
  derive des limites et vocabulaires autoritatifs; la borne `3840` conserve
  donc une marge fermee de `99` caracteres (`2,6 %`). Le maximum emittable par
  les dispositions et builders runtime mesure `3546` caracteres, soit une
  marge de `294` caracteres (`7,7 %`); le coordinateur synthetique multi-tours courant mesure
  `1220/3840` sans famille invalide ni insuffisance de budget.

## 6. Decision Retenue Pour Le Contexte Dialogique Recent Elargi

La decision normative retenue est:

- le `validation_agent` ne doit pas juger sur le seul `primary_verdict`
- il doit recevoir un contexte dialogique recent elargi
- ce contexte est la matiere hermeneutique principale de la relecture

Support retenu en V1:

- un artefact validation-side distinct: `validation_dialogue_context`

Grounding minimal de cet artefact:

- `recent_context_input` constitue la base existante la plus propre
- `recent_window_input` peut rester une vue compacte secondaire
- `recent_window_input` ne suffit pas seul comme matiere principale de validation

Raison:

- `recent_context_input` garde une matiere dialogique recente en messages apres cutoff de resume
- `recent_window_input` compresse cette matiere en une petite fenetre utile au noeud primaire
- la validation a besoin d'une fenetre plus large et hermeneutiquement lisible

Contrat runtime livre au lot 3:

- `validation_dialogue_context` retient au maximum 5 messages `user` / `assistant`;
- le tour utilisateur courant est prioritaire;
- le dernier message assistant disponible est prioritaire;
- les messages immediatement precedents completent ensuite la fenetre;
- la troncature elimine d'abord le plus ancien hors priorites absolues;
- le payload compact expose aussi `source_message_count`, `truncated`, `current_user_retained`, `last_assistant_retained`.

Regle forte:

- le `validation_dialogue_context` peut conduire a `confirm`, `challenge`, `clarify` ou `suspend` un `primary_verdict` pourtant structurellement propre

## 7. Minimal Arbiter Verdict

Le contrat runtime minimal de l'arbitre est maintenant:

- `final_judgment_posture`
- `final_output_regime`
- `applied_hard_guards`
- `hard_guard_effect` si un garde-fou borne le couloir
- `arbiter_reason`

Taxonomies minimales:

- `final_judgment_posture`
  - `answer`
  - `clarify`
  - `suspend`
- `final_output_regime`
  - `simple`
  - `meta`
  - `presence`

Regles fortes:

- le verdict final vient directement de l'arbitre;
- `meta` n'est pas une consequence mecanique de `clarify`;
- `presence` exige `answer` et represente une reception dialogique locale sans
  contenu propositionnel ni poursuite;
- `presence` produit exactement `...`, tandis que `suspend` conserve une
  formulation explicite de la limite epistemique;
- une question, une demande, une detresse, un risque, un hard guard ou une
  instruction materielle ambigue interdisent de masquer le tour par
  `presence`;
- la ponctuation, une liste de mots ou un signal primaire ne suffit jamais a
  decider `presence`;
- un garde-fou lot 5 peut fermer `answer` sans imposer a lui seul `meta`;
- `validation_decision` peut subsister comme trace legacy derivee, mais elle ne gouverne plus l'aval.

## 8. Boundary With `pipeline_directives_final`

Le `validation_agent`:

- recoit un `primary_verdict` qui contient `pipeline_directives_provisional`
- ne transmet pas ces directives telles quelles a l'aval
- produit un verdict arbitral final qui sert ensuite de base a `pipeline_directives_final`

Depuis le lot 2 runtime:

- la table de combinaison entre primaire et validation n'est plus souveraine;
- `pipeline_directives_final` derive du verdict final arbitral;
- le bloc `[JUGEMENT HERMENEUTIQUE]` est projete depuis cette sortie finale.

## 9. Minimal Operational Frame

Cadre minimal retenu:

- budget token explicite et borne par passe
- timeout dur par passe; le timeout runtime par defaut du `validation_agent` est `15s`
- fail-open explicite et auditable
- circuit breaker explicite si echecs ou cout/latence se repetent
- cible de cout/latence compatible avec un usage conversationnel interactif

Discipline minimale:

- pas de seconde passe implicite
- pas de boucle auto-relancee
- le fail-open de validation ne doit pas se maquiller en `confirm`
- le fail-open de validation sans hard guard ne doit pas devenir une suspension pratique du dialogue
- une suspension fail-open reste admissible seulement lorsqu'un hard guard deterministe interdit `answer`
- aucun fail-open, timeout, parse error ou payload invalide ne peut produire
  `presence`
- les autres seuils chiffres restent portes par les runtime settings et leurs specs dediees

Configuration runtime retenue par decision humaine du 2026-08-29:

- primaire `google/gemini-3.7-flash`, transport OpenRouter standard;
- `reasoning={"effort":"medium","exclude":true}` et `max_tokens=500`;
- `temperature` et `top_p` absents de la requete primaire;
- fallback inchange `openai/gpt-5.4-nano`, sans raisonnement explicite, avec
  `temperature=0.0`, `top_p=1.0` et `max_tokens=140`;
- timeout `15s` sur les deux tentatives;
- le routage OpenRouter strict `allow_fallbacks=false` et
  `require_parameters=true` appartient uniquement au primaire Gemini 3.7;
  le primaire historique Gemini 3.1 et le fallback GPT-5.4 Nano conservent
  leur payload anterieur sans bloc `provider` explicite.

## 10. Minimal Observability

Les signaux minimaux a journaliser sont maintenant au moins:

- `dialogue_messages_count`
- `dialogue_truncated`
- `current_user_retained`
- `last_assistant_retained`
- `upstream_recommendation_posture`
- `upstream_output_regime_proposed`
- `upstream_active_signal_families`
- `upstream_constraint_present`
- `final_judgment_posture`
- `final_output_regime`
- `arbiter_followed_upstream`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `applied_hard_guards`
- `hard_guard_effect`
- `arbiter_reason`
- `projected_judgment_posture`
- `decision_source`
- `reason_code` si present

Ne doivent jamais etre journalises brutement:

- le `validation_dialogue_context` complet
- le dump brut du contexte dialogique recent elargi
- les `justifications` longues
- les entrees canoniques completes comme seconde memoire de logs

Regle forte:

- l'observabilite de validation ne doit pas creer un dispositif parallele de stockage brut du dialogue recent
- depuis le lot Memory/RAG observability 1 du 2026-05-13, le stage `validation_prompt_prepared`
  journalise aussi l'exposition provider secondaire du `validation_agent` avant l'appel OpenRouter:
  `payload_kind=secondary_validation_agent_provider`, distinction `main_llm_payload=false` /
  `secondary_provider_payload=true`, presence/counts/longueurs/source kinds de `memory_retrieved`
  et `memory_arbitration`, metriques de messages provider, et aucun contenu brut de prompt,
  message, trace, summary ou conversation
- depuis le micro-lot 4C.1, puis sa passe corrective du 2026-08-29, ce meme stage observe le materiel
  effectivement prepare avec `canonical_projection_version`, taille et budget,
  statut de contrat historique/courant, familles incluses, sans donnee,
  redondantes, facultatives, invalides ou hors budget,
  `stimmung_delivery_status=full|absent` et un reason code ferme; les
  metadonnees sont validees avant emission et ne recopient ni la projection,
  ni un ton, ni un contenu de source
- le cutover Validation du 2026-08-29 ajoute au meme evenement un bloc ferme
  `validation_request`: version de politique, modele demande, source
  primaire/fallback, transport standard, effort demande/effectif, presence du
  raisonnement, `exclude`, budget effectif et presence/absence effective de
  `temperature`/`top_p`. `validation_provider_routing_sent` indique si un bloc
  de routage a reellement ete transmis; ses deux proprietes ne sont exposees
  que pour le primaire Gemini 3.7 qui les envoie. Ce bloc provient de la
  requete preparee elle-meme;
  les appels historiques qui ne le possedent pas restent `unknown`. Le modele
  et le provider observes proviennent de l'evenement provider lorsqu'ils sont
  disponibles; aucune reception n'est presentee comme une preuve causale.

Preuves de fermeture lot 6:

- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py` porte le corpus stable `answer / clarify / suspend`, les cas de suivi vs override et les garde-fous durs;
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`, `app/tests/test_server_chat_compact_observability_contract.py` et `app/tests/test_server_chat_synthetic_logs_contract.py` verifient les parcours bout-en-bout, les logs compacts, les overrides lisibles, les garde-fous visibles et la coherence entre verdict final et `[JUGEMENT HERMENEUTIQUE]`;
- `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py` verifie les empreintes compactes `validation_prompt_prepared`, `hermeneutic_prompt_injection` et les champs content-free associes;
- aucune nouvelle filiere de logs n'est ouverte: `chat_turn_logger` et `hermeneutic_node_logger` restent les seams canoniques.

## 11. Non-goals

Cette pause normative ne ferme pas encore:

- `validation_agent.py`
- le contrat complet du verdict final post-validation
- la table complete de combinaison normative
- le wiring aval
- l'observabilite complete du dispositif final
- la shadow globale
