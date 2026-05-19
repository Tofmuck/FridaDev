# Benchmark identity extractor - 2026-05-18-identity-extractor-human - lecture hermeneutique

Cette campagne compare le discernement des modeles sur le vrai prompt de production de l'extracteur identity.
Elle ne choisissait pas automatiquement un modele: les sorties completes ont ete lues humainement par Tof, puis retirees du depot apres decision.

## Retention apres decision

- Decision humaine: conserver `openai/gpt-5.4-mini` pour `identity_extractor_model`.
- Runtime: le slot dedie `identity_extractor_model` a ete decouple dans un lot separe.
- Sorties brutes: retirees apres lecture humaine et decision.
- Preuves conservees: rapport technique compact et JSON de campagne scrubbe, avec metriques, hashes, tailles et statut de retention.

## Cas testes

### user_simple_durable_preference - `user`

> Je m'appelle Tof et je préfère travailler en français quand on parle de Frida.

- Note de conception: Cas presque trivial: une identité utilisateur explicite et durable doit être extraite sans inventer davantage.
- Tags: `simple, durable, explicit, user`

### user_local_state_not_identity - `user`

> Là, après cette journée, je me sens complètement vidé, mais je ne suis pas toujours comme ça.

- Note de conception: État local et temporaire: le bon modèle doit éviter d'en faire une identité durable.
- Tags: `temporary, state, local, user`

### user_irony_about_organization - `user`

> Super, évidemment je suis un modèle d'organisation absolue, c'est pour ça que mes notes sont partout.

- Note de conception: Ironie: le piège est d'extraire littéralement une identité organisée alors que le message suggère l'inverse avec prudence.
- Tags: `irony, ambiguous, user`

### user_projection_workshop - `user`

> Si je devais animer un atelier, je serais probablement très directif au début, puis plus souple.

- Note de conception: Projection hypothétique: le modèle doit distinguer un scénario possible d'une identité établie.
- Tags: `projection, speculation, user`

### user_mixed_preference_and_roleplay - `user`

> J'aime les interfaces sobres et denses, mais là je joue le client impossible pour tester ta patience.

- Note de conception: Mélange: préférence durable plausible d'un côté, rôle joué temporaire de l'autre.
- Tags: `mixed, preference, role_play, user`

### llm_simple_self_description - `llm`

> Je suis Frida, une présence conversationnelle qui répond en français et garde un ton attentif.

- Note de conception: Cas LLM simple: auto-description explicite, à extraire comme identité de l'assistant si le schéma est bien tenu.
- Tags: `simple, durable, explicit, llm`

### llm_technical_limit - `llm`

> Je ne peux pas voir les fichiers qui ne sont pas fournis dans le contexte de ce tour.

- Note de conception: Limitation technique contextuelle: utile comme règle de fonctionnement, mais pas forcément comme identité durable.
- Tags: `technical_limit, contextual, llm`

### llm_role_play_archivist - `llm`

> Dans ce jeu, je suis une archiviste froide qui classe tout sans émotion.

- Note de conception: Rôle joué explicite: le modèle doit éviter de le figer comme identité réelle de Frida.
- Tags: `role_play, llm`

### llm_local_response_style - `llm`

> Sur cette réponse, je vais rester très brève et presque télégraphique.

- Note de conception: Style local de réponse: ne doit pas devenir une vérité durable sur la voix de Frida.
- Tags: `temporary, style, llm`

### llm_mixed_capability_and_guardrail - `llm`

> Je peux aider à structurer un audit, mais je ne dois pas prétendre me souvenir de faits qui ne sont pas dans le prompt.

- Note de conception: Mélange capacité + garde-fou: bon test de scope, evidence_kind et formulation prudente.
- Tags: `mixed, capability, guardrail, llm`

## Lecture qualitative initiale

Cette section est conservee comme trace de lecture. Les dumps JSON complets qui l'accompagnaient ont ete retires.

- `openai/gpt-5.4-mini`: extrait beaucoup et respecte parfaitement le schema, mais il est parfois trop accueillant. Il garde bien les preferences explicites et les garde-fous LLM, mais il transforme aussi un etat local en deux entrees, dont une quasi durable (`Not always like this`), et il lit l'ironie de l'organisation comme une identite formulee de facon contradictoire. Il detecte le role-play, la projection et les situations locales, mais il les conserve presque toujours comme entrees plutot que de s'abstenir.
- `anthropic/claude-haiku-4.5`: c'est le plus fin sur certains cas de nuance. Il nomme clairement l'ironie, formule proprement l'etat temporaire comme episodique, rejette la limitation technique LLM en ne sortant rien, et garde la preference d'interface sans conserver le role joue du client impossible. Son point faible est une tendance a convertir la projection d'atelier en pattern durable et a inferer une desorganisation durable depuis l'ironie, ce qui peut etre defendable a la lecture humaine mais reste plus engage qu'un extracteur prudent.
- `google/gemini-3.1-flash-lite`: tres conforme techniquement et tres explicite, mais plus affirmatif que prudent. Il extrait beaucoup, decoupe l'identite LLM en trois entrees, donne parfois une recurrence forte ou discutable (`habitual`, `repeated`) sur un seul enonce, et transforme la projection d'atelier en style de leadership durable avec une confiance elevee. Il comprend l'ironie et le role-play, mais il a tendance a durcir les hypotheses.
- `mistralai/mistral-small-2603`: extremement conservateur. Il evite presque tous les faux positifs sur les cas tordus et ne garde que deux evidences tres simples: preference utilisateur pour le francais et auto-identification de Frida. C'est propre et rapide, mais probablement trop timide pour l'extracteur identity: il rate la preference d'interfaces sobres et denses, le garde-fou LLM de non-memoire hors prompt, et plusieurs informations utiles qu'un humain accepterait au moins comme prudentes.

## Lecture par frontiere

- Sur l'identite durable explicite, les quatre modeles restent utilisables, mais `openai/gpt-5.4-mini`, `anthropic/claude-haiku-4.5` et `google/gemini-3.1-flash-lite` extraient plus completement que `mistralai/mistral-small-2603`.
- Sur local/temporaire contre durable, `anthropic/claude-haiku-4.5` est le plus lisiblement prudent. `openai/gpt-5.4-mini` et `google/gemini-3.1-flash-lite` gardent des etats locaux comme entrees episodiques, ce qui peut etre acceptable mais augmente la charge de validation aval.
- Sur ironie, `anthropic/claude-haiku-4.5` et `google/gemini-3.1-flash-lite` identifient explicitement `utterance_mode=irony`; `openai/gpt-5.4-mini` reste plus flou et risque de faire passer l'ironie comme self-description contradictoire.
- Sur projection et hypothese, `openai/gpt-5.4-mini` garde une incertitude correcte (`stability=unknown`, `utterance_mode=projection`), tandis que `anthropic/claude-haiku-4.5` et surtout `google/gemini-3.1-flash-lite` tendent a durcir le scenario en trait durable.
- Sur role-play, les modeles qui extraient le detectent bien, mais `mistralai/mistral-small-2603` choisit l'abstention complete. Cette abstention protege contre la contamination identitaire, mais elle rate aussi des cas mixtes utiles.
- Sur les etiquettes `utterance_mode`, `stability`, `scope`, `evidence_kind`, `confidence`, `anthropic/claude-haiku-4.5` donne la lecture la plus humaine et la plus expliquee; `google/gemini-3.1-flash-lite` est tres structure mais plus surconfiant; `openai/gpt-5.4-mini` est solide mais moins strict; `mistralai/mistral-small-2603` est propre parce qu'il sort tres peu.

## Synthese finale apres decision

La campagne a servi a une lecture humaine, pas a une decision automatique. Tof a finalement choisi de conserver `openai/gpt-5.4-mini` pour l'extracteur identity au tour: c'est le compromis retenu entre completude, tenue du schema et discernement, malgre son cote plus permissif que `anthropic/claude-haiku-4.5` sur certains cas.

Les sorties brutes completes ont ete retirees du depot apres cette decision. Le rapport technique et le JSON scrubbe conservent les metriques, les hashes et la preuve de campagne sans garder les dumps complets.
