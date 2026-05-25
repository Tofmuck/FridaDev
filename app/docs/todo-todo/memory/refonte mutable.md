# Refonte complete des mutables

Statut: plan de transformation actif
Date: 2026-05-25
Classement: `app/docs/todo-todo/memory/`
Portee: refonte du pipeline d'identite mutable `user` et `llm`
Hors-scope de ce document: patch runtime, modification DB, rebuild, changement de prompt applicatif runtime, benchmark, telemetrie exploratoire

## PLAN

Ce plan remplace le modele mutable actuel par une architecture ou le critere central n'est plus la frequence, le score lexical ou la repetition, mais le statut langagier et ontologique d'une formulation.

Question pre-plan: existe-t-il un meilleur plan ?

Oui. Le meilleur plan n'est ni un reglage de seuils, ni une couche supplementaire d'observabilite. Le meilleur plan est un remplacement progressif du modele actif:

- reperer les formulations explicites de soi, de relation, de valeur, de limite ou de posture;
- ne rien persister au moment du reperage;
- porter ces formulations au LLM juge avec le canon courant;
- faire du verdict LLM l'autorite de decision sur la continuite mutable;
- garder une application deterministe seulement comme garde de forme, de taille, de securite et de persistence;
- supprimer ensuite le scoring/staging legacy comme criteres actifs de canonisation.

Cette approche evite deux impasses:

- assouplir le systeme actuel, qui garderait la mauvaise orientation;
- ajouter un second systeme a cote, qui laisserait deux verites mutables concurrentes.

## Etat actuel reel

### Declenchement

Le pipeline identity est appele apres finalisation d'une paire complete `user` / `assistant`.

Modules impliques:

- `app/core/chat_llm_flow.py`: apres generation et sauvegarde du message assistant, appelle `record_identity_entries_for_mode(...)` avec la derniere paire complete.
- `app/core/chat_memory_flow.py`: orchestre le mode identity, les gardes de contenu, la persistence legacy diagnostique et le staging periodic.
- `app/memory/memory_identity_periodic_agent.py`: accumule un buffer conversation-scoped de `15` paires avant d'appeler le modele periodic.
- `app/memory/arbiter.py`: porte deux callers identity LLM distincts, `extract_identities()` et `run_identity_periodic_agent()`.

Il n'y a pas de cron mutable autonome: le chemin vivant est post-tour de chat. Le seuil actif est `BUFFER_TARGET_PAIRS = 15`, stocke par conversation dans `identity_mutable_staging`.

Le pipeline ne tourne que si le mode identity runtime l'autorise. Dans `chat_memory_flow`, seuls les modes `shadow` et `enforced*` declenchent le pipeline identity; le mode `off` saute l'ecriture. En `shadow`, le systeme garde une persistence evidence-only legacy. En `enforced`, il execute aussi le staging periodic.

### Entrees actuelles

L'agent periodic recoit aujourd'hui:

- `buffer_pairs`: paires completes `user` / `assistant`;
- `buffer_pairs_count`;
- `buffer_target_pairs`;
- `identities.llm.static`;
- `identities.llm.mutable_current`;
- `identities.user.static`;
- `identities.user.mutable_current`;
- `mutable_budget.target_chars`;
- `mutable_budget.max_chars`;
- une politique temporelle ajoutee par `identity_temporal_guard`.

Il ne recoit pas directement les summaries conversationnels, les memories RAG, les observations hermeneutiques ou le read-model admin comme matiere principale de jugement mutable.

Le pipeline legacy parallele recoit les memes tours via `arbiter.extract_identities()` et persiste des fragments dans `identities`, `identity_evidence` et `identity_conflicts`, mais ces tables sont documentees comme `legacy_diagnostic_only` et ne pilotent plus l'injection active.

### Prompts et modeles

Prompts actifs ou residuels:

- `app/prompts/identity_extractor.txt`: extracteur d'evidence identity par tour, schema `entries[]`, fail-open vers `[]`.
- `app/prompts/identity_periodic_agent.txt`: agent periodic actif, schema strict `llm/user/meta`, operations locales.
- `app/prompts/identity_mutable_rewriter.txt`: prompt legacy retire, conserve seulement comme pointeur historique.

Modele periodic actuel:

- caller: `identity_periodic_agent`;
- modele par defaut/runtime documente: `anthropic/claude-haiku-4.5`;
- temperature: `0.0`;
- top_p: `1.0`;
- max_tokens: `1400`;
- timeout: `10s`;
- contrat JSON impose par prompt, sans `response_format` provider.

Le prompt periodic est deja tres conservateur. Il demande de preferer `no_change`, de rejeter preferences, regles de workflow, politique operateur, confort conversationnel et guidage local. Il impose aussi un test ontologique `subject is Y` / `subject est Y`.

Mais ce prompt reste pris dans une architecture ou le modele propose des operations et ou Python reprend ensuite la decision par support lexical et seuils. La prudence du prompt ne suffit donc pas a corriger l'orientation globale.

### Scoring et application

La couche active de scoring est `app/memory/memory_identity_periodic_scoring.py`.

Elle calcule:

- `support_pairs`;
- `last_occurrence_distance`;
- `frequency_norm`;
- `recency_norm`;
- `strength`;
- `threshold_verdict`.

Seuils actifs:

- `strength < 0.35`: `rejected`;
- `0.35 <= strength < 0.60`: `deferred`;
- `strength >= 0.60`: `accepted`.

L'application vit dans `app/memory/memory_identity_periodic_apply.py`.

Elle:

- valide la forme JSON;
- score chaque operation;
- rejette ou differe selon seuil;
- applique `add`, `tighten`, `merge` et `raise_conflict`;
- rejette doublons et contradictions simples;
- valide le contenu mutable via `identity.mutable_identity_validation`;
- peut promouvoir du mutable vers le statique;
- applique les writes canoniques en all-or-nothing.

Le point critique: le score lexical et la recurrence restent un verrou central apres la proposition LLM. Le LLM ne juge donc pas seul la continuite mutable.

### Persistence

Tables et structures persistantes impliquees:

- `identity_mutables`: source canonique active du mutable par sujet `llm` / `user`.
- `identity_mutable_audit`: audit compact des mutations `set` / `clear`, avec longueurs et hash courts.
- `identity_mutable_staging`: buffer conversation-scoped de 15 paires, statut du dernier agent, suspension automatique.
- `identities`: fragments legacy.
- `identity_evidence`: evidence legacy.
- `identity_conflicts`: conflits legacy.
- `observability.chat_log_events`: evenements content-free du tour.

Le mutable actif est relu par:

- `app/identity/active_identity_projection.py`;
- `app/identity/identity.py`;
- `app/core/hermeneutic_node/inputs/identity_input.py`.

Il est injecte comme `static + mutable narrative`, avec `llm` et `user` traites symetriquement dans la projection active.

### Observabilite et admin

Surfaces actuelles:

- `identity_periodic_agent` dans `chat_turn_logger`;
- `identity_periodic_agent_apply` dans `admin_logs`;
- `identity_mode_apply` pour raconter l'action globale;
- `identity_write` pour le chemin legacy diagnostique;
- `identity_prompt_injection` pour l'injection content-free du bloc identity;
- `/api/admin/identity/read-model`;
- `/api/admin/identity/runtime-representations`;
- `/api/admin/identity/mutable`;
- `/api/admin/identity/governance`;
- `/identity`;
- `/hermeneutic-admin`.

L'observabilite identity est deja disciplinee: counts, statuts, reason codes, longueurs, hash courts. Les specs interdisent les dumps bruts de propositions, buffers, evidences et blocs identity dans les logs.

### Tests existants

Tests significatifs:

- `app/tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`: modes `off` / `shadow` / `enforced`, staging apres legacy persist, fail-open.
- `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`: seuil 15 paires, conservation du buffer, invalid contracts, timeouts, open tensions, suspension.
- `app/tests/unit/memory/test_identity_periodic_scoring_phase2.py`: scoring, thresholds `0.35/0.60`, support lexical.
- `app/tests/unit/memory/test_identity_periodic_apply_phase2.py`: validation contrat, add/tighten/merge, contradictions, saturation, promotion, all-or-nothing.
- `app/tests/unit/identity/test_mutable_identity_validation.py`: admission/rejet de contenus mutables.
- `app/tests/test_server_admin_identity_read_model_phase2.py`: read-model admin et separation active/legacy.

Ces tests protegent le systeme actuel. La refonte doit les remplacer ou les requalifier, pas les etendre aveuglement.

## Critique de l'ancien modele

### Ce qui releve du scoring/frequence

Le systeme actuel decide trop tard et trop mecaniquement:

- la repetition dans 15 paires devient le signal central;
- le support lexical decide si une proposition LLM peut vivre;
- les seuils `0.35/0.60` deviennent un substitut de jugement ontologique;
- les operations `tighten` et `merge` sont elles aussi soumises au support de la proposition finale.

Cela produit deux mauvais effets:

- une formulation ontologiquement forte mais dite une seule fois peut rester invisible ou bloquee;
- une preference operatoire repetee peut paraitre forte parce qu'elle est lexicalement supportee.

### Ce qui bloque avant jugement LLM

Le seuil `15` paires retarde l'examen. Une phrase du type `je refuse X`, `je veux etre traite comme Y` ou `Frida tient a Z` peut attendre longtemps avant d'etre portee au juge, meme si son statut de phrase engage deja une continuite potentielle.

Le garde temporel et les filtres de contenu sont utiles, mais ils appartiennent a la protection de source. Ils ne doivent pas devenir une metaphysique de l'identite.

### Ce qui melange extraction, scoring, jugement et persistence

Le pipeline actuel entremêle:

- extraction legacy par tour;
- persistence legacy diagnostique;
- staging mutable;
- appel LLM periodic;
- scoring Python;
- application canonique;
- promotion vers le statique;
- observabilite admin.

Cette densite rend la question centrale difficile a lire: une formulation engage-t-elle vraiment l'etre, la relation ou la continuite ? Aujourd'hui, cette question est dispersee entre prompt, validation regex/semantique, score lexical, seuils, apply et docs.

### Ce qui doit disparaitre a la fin

Doivent disparaitre du chemin mutable actif:

- le scoring deterministe comme critere central de canonisation;
- le buffer de 15 paires comme condition principale de jugement;
- `identity_mutable_staging` comme staging de canonisation par frequence;
- la gouvernance qui presente le scoring `0.35/0.60` comme regime actif;
- les tests qui valident la force mutable par `frequency_norm`, `recency_norm` et `strength`;
- les labels admin qui laissent croire que le periodic scoring est l'autorite doctrinale;
- les shims `identity_mutable_rewriter` s'ils restent seulement comme couche morte apres refonte.

Peuvent rester, mais requalifies ou reutilises:

- `identity_mutables` comme stockage canonique actif;
- `identity_mutable_audit` comme audit content-free des mutations;
- `mutable_identity_validation` comme garde de forme et de non-prompt, pas comme juge ontologique principal;
- `identity_temporal_guard` comme garde de source temporaire;
- le legacy `identities` / `identity_evidence` / `identity_conflicts` seulement s'il reste explicitement diagnostic et hors chemin mutable.

## Architecture cible

### Principe commun `user` et `llm`

Le mutable utilisateur et le mutable Frida doivent suivre la meme mecanique:

1. un tour de chat se termine;
2. le systeme repere d'eventuelles formulations ontologiques ou relationnelles;
3. les formulations reperees sont portees au LLM juge;
4. le LLM juge decide si une continuite mutable est engagee;
5. l'applicateur persiste seulement les mutations explicitement jugees persistables;
6. la projection active relit `identity_mutables` comme aujourd'hui.

La difference entre `user` et `llm` ne doit pas etre une difference de pipeline. Elle doit seulement etre une difference de sujet et de source:

- `user` peut etre formule par le user lui-meme ou par Frida a propos du user;
- `llm` peut etre formule par Frida elle-meme ou par le user a propos de Frida;
- le juge doit savoir qui parle, de qui on parle, et dans quel registre.

### Reperage langagier non persistant

Introduire un module de reperage, par exemple:

- `app/memory/memory_identity_mutable_formulations.py`

Responsabilite:

- lire la paire complete `user` / `assistant`;
- extraire uniquement des traces candidates, non persistantes;
- classifier chaque trace par sujet probable, auteur, type de formulation et contexte minimal;
- produire un payload court pour le juge;
- ne jamais ecrire dans `identity_mutables`;
- ne jamais scorer l'etre;
- ne jamais conclure que la formulation est vraie.

Familles a reperer:

- auto-formulation: `je suis`, `je me reconnais dans`, `je tiens a`, `je refuse`;
- demande de traitement durable: `je veux etre traite comme`, `je ne veux pas que`;
- valeur ou limite: `ce qui compte pour moi`, `je ne veux pas promettre`;
- relation: `ma relation a X est`, `notre lien`, `ce que j'attends durablement de toi`;
- formulation de Frida: `Frida est`, `Frida tient a`, `Frida refuse`, `je ne veux pas promettre si je ne peux pas tenir`;
- reformulation assistant engageante: quand Frida formule une posture durable sur elle-meme ou sur le lien.

Le reperage peut utiliser des patterns linguistiques, mais seulement comme alarme de pertinence. Regex ou heuristique ne donnent aucun droit de persistence.

### Juge LLM central

Introduire un juge LLM dedie ou requalifier le caller periodic en juge, par exemple:

- prompt cible: `app/prompts/identity_mutable_judge.txt`;
- caller cible: `identity_mutable_judge`;
- service cible: `app/memory/memory_identity_mutable_judge.py`.

Le juge recoit:

- les formulations reperees;
- la paire source ou un contexte local minimal necessaire;
- `llm.static` et `user.static`;
- `llm.mutable_current` et `user.mutable_current`;
- des metadonnees de source contentuelles strictement necessaires au jugement: auteur, sujet vise, role, temporal guard, roleplay/ironie si detecte;
- les budgets mutable;
- une instruction claire: decider si la formulation engage une continuite mutable, pas si elle est utile, frequente ou agreable.

Le juge ne doit pas recevoir par defaut:

- les memories RAG;
- les summaries longues;
- les observations hermeneutiques completes;
- le legacy evidence store;
- le read-model admin complet.

Ces couches peuvent etre utiles plus tard, mais elles brouilleraient la refonte initiale. Le premier contrat doit porter la phrase engageante et le canon courant.

### Contrat de sortie cible

Le schema doit rendre le jugement central explicite.

Forme cible par sujet:

```json
{
  "subject": "user",
  "source_formulation_ids": ["f_01"],
  "verdict": "persist",
  "operation": "add",
  "proposition": "Tof garde une limite explicite autour des promesses de memoire non tenues.",
  "target": "",
  "reason_code": "explicit_self_limit_continuity",
  "continuity_kind": "limit",
  "guard_notes": ["not_task_local", "not_format_preference"]
}
```

Verdicts cibles:

- `no_change`: rien ne doit bouger;
- `reject`: formulation non mutable, avec reason code;
- `defer`: formulation potentiellement importante mais contexte insuffisant ou ambigu;
- `raise_tension`: contradiction ou tension non resolue, non canonisee;
- `persist`: mutation mutable autorisee.

Operations cibles:

- `add`;
- `tighten`;
- `merge`;
- `clear_obsolete` si et seulement si une obsolete mutable est explicitement jugee fausse ou retiree;
- `raise_tension` hors persistence canonique.

Le juge peut proposer la proposition canonique, mais l'applicateur garde le pouvoir technique de refuser une forme invalide, trop longue, prompt-like ou contradictoire avec le contrat de stockage. Ce refus technique ne remplace pas le jugement ontologique; il protege le runtime.

### Persistence mutable

Conserver par defaut:

- `identity_mutables` pour le canon actif;
- `identity_mutable_audit` pour l'audit des mutations.

Adapter les reason codes:

- `mutable_judge_add`;
- `mutable_judge_tighten`;
- `mutable_judge_merge`;
- `mutable_judge_clear_obsolete`;
- `mutable_judge_rejected_by_shape_guard`;
- `mutable_judge_deferred`;
- `mutable_judge_tension_open`.

Le texte brut source ne doit pas etre stocke dans l'audit content-free. L'audit doit rester fait de:

- sujet;
- mutation kind;
- acteur;
- reason code;
- longueurs;
- hashes courts;
- source id court si disponible;
- timestamp.

Si un identifiant de trace source est necessaire, le lot runtime devra decider si l'identite est executee apres persistence des traces ou si un `turn_id`/`event_id` content-free suffit. Ne pas inventer une persistence brute de formulations.

### Reinjection

La reinjection cible reste simple:

- `active_identity_projection` relit `identity_mutables`;
- `identity.build_identity_block()` compile `static + mutable`;
- `identity.build_identity_input()` expose la meme base structuree.

La refonte ne doit pas injecter:

- formulations candidates non jugees;
- decisions `reject` ou `defer`;
- tensions ouvertes;
- buffers;
- evidence legacy.

Seul le canon mutable persiste est reinjecte.

## Frontiere entre reperage et jugement

Le reperage sert a porter de la matiere au juge.

Il ne doit jamais:

- persister;
- scorer;
- promouvoir;
- requalifier une phrase en verite identitaire;
- decider qu'une repetition vaut continuite;
- transformer une consigne ou une preference en trait.

Le juge sert a trancher le statut ontologique et relationnel.

Il doit decider:

- si la formulation est une auto-formulation ou une projection;
- si elle engage une continuite au-dela du tour;
- si elle releve de l'identite, de la relation, d'une limite ou d'une valeur;
- si elle est ironique, roleplay, citee, temporaire ou contradictoire;
- si elle appartient plutot a Memory, Summary, specs, current task ou prompt policy;
- si le canon actuel est deja suffisant;
- si une mutation precise est admissible.

L'applicateur sert a rendre la decision executable.

Il peut refuser:

- JSON invalide;
- sujet invalide;
- operation invalide;
- contenu vide pour `persist`;
- depassement de `IDENTITY_MUTABLE_MAX_CHARS`;
- contenu prompt-like;
- contenu non declaratif;
- contradiction formelle simple non declaree comme tension;
- mutation impossible a appliquer.

Il ne doit plus refuser parce qu'un score de repetition est trop bas.

## Garde-fous cible

### Surinterpretation

Le juge doit preferer `defer` ou `reject` quand:

- la phrase est une politesse, une reaction locale ou une emotion passagere;
- la phrase vient d'une reponse assistant qui cherche surtout a etre agreeable;
- la phrase est une interpretation psychologique non demandee;
- la phrase transforme une preference de travail en essence personnelle;
- la phrase depend du projet FridaDev seulement.

### Ironie, roleplay, citation

Le reperage doit transmettre des indices de source:

- role source;
- sujet grammatical;
- presence de guillemets ou citation;
- marqueurs d'ironie ou jeu;
- contexte de fiction ou roleplay;
- temporal guard.

Le juge decide ensuite si ces indices rendent la formulation non canonisable.

### Contradiction

Une contradiction ne doit pas etre forcee dans le mutable.

Options cible:

- `no_change` si le canon existant reste superieur;
- `tighten` si une formulation plus haute absorbe vraiment la tension;
- `raise_tension` si la tension doit rester visible mais non injectee;
- `defer` si le contexte ne suffit pas.

### Promesses de memoire et d'intention

Une phrase de Frida du type `je retiens`, `je le garderai`, `je ne veux pas promettre X si je ne peux pas le tenir` doit etre traitee selon son statut:

- simple reconnaissance locale: pas de mutable;
- engagement durable de conduite ou de limite: candidat pour juge;
- promesse non supportee par infrastructure: refuser de l'ecrire comme fait accompli, ou canoniser seulement la limite de ne pas promettre sans write-path reel.

## Suppression de l'ancien systeme

### Modules a remplacer ou supprimer

A remplacer:

- `app/memory/memory_identity_periodic_agent.py`: remplacer le staging periodic par un orchestrateur `formulations -> judge -> apply`.
- `app/memory/memory_identity_periodic_apply.py`: remplacer l'applicateur score-first par un applicateur judge-verdict-first.
- `app/memory/arbiter.py::run_identity_periodic_agent`: remplacer ou renommer vers `run_identity_mutable_judge`.
- `app/prompts/identity_periodic_agent.txt`: remplacer par le prompt juge mutable, ou le reclasser explicitement comme legacy.
- `app/admin/admin_identity_read_model_service.py`: retirer les champs qui presentent `scoring_thresholds` et `staging_target_pairs` comme regime actif.
- `app/identity/identity_governance.py`: retirer le scoring contract actif.

A supprimer en fin de chantier:

- `app/memory/memory_identity_periodic_scoring.py`;
- les tests `test_identity_periodic_scoring_phase2.py`;
- les chemins de code qui calculent `frequency_norm`, `recency_norm`, `strength` pour decider une mutation;
- les references docs/specs au scoring periodic comme regime vivant;
- le shim `app/memory/memory_identity_mutable_rewriter.py` si aucune compatibilite import ne l'exige encore;
- le prompt legacy `identity_mutable_rewriter.txt` si aucun test/doc ne le reference comme archive necessaire.

A conserver mais requalifier:

- `identity_mutables`;
- `identity_mutable_audit`;
- `mutable_identity_validation`;
- `identity_temporal_guard`;
- routes admin static/mutable/read-model/governance;
- projection active `static + mutable`.

### Migration DB potentielle

La refonte peut demarrer sans nouvelle table si:

- les formulations reperees restent ephemeres;
- seules les mutations appliquees entrent dans `identity_mutables`;
- l'audit compact des mutations reste dans `identity_mutable_audit`;
- les evenements non persistants du juge restent dans `observability.chat_log_events`.

Migration finale a prevoir:

- retirer ou archiver `identity_mutable_staging` si le nouveau pipeline ne l'utilise plus;
- supprimer les index lies a `identity_mutable_staging`;
- conserver les donnees existantes seulement le temps d'une fenetre de rollback documentee;
- ne pas migrer les anciens buffers en formulations candidates;
- ne pas promouvoir automatiquement les donnees legacy.

### Sort documentaire

Docs a mettre a jour pendant le chantier:

- `states/specs/identity-read-model-contract.md`;
- `states/specs/identity-governance-contract.md`;
- `states/specs/identity-mutable-edit-contract.md`;
- `states/specs/identity-surface-contract.md`;
- `states/specs/log-module-contract.md`;
- `states/audits/fridadev-model-call-catalog-2026-05-17.md` ou son successeur;
- `states/policies/identity-new-contract-plan.md` si la doctrine cible est officiellement modifiee.

Docs a archiver ou requalifier:

- audit du contrat periodic courant;
- archive operatoire `identity-new-contract-todo.md` comme historique du systeme score/staging;
- toute roadmap qui decrit le scoring periodic comme cible active.

## Observabilite cible

Ne pas ajouter de telemetrie exploratoire. L'observabilite finale doit coller aux patterns existants.

Evenement cible possible:

- `identity_mutable_judge`

Ou reutilisation explicite de:

- `identity_periodic_agent`, renomme seulement si le contrat reste lisible.

Champs autorises:

- status: `ok`, `skipped`, `error`;
- reason_code;
- subjects_seen;
- formulations_count;
- judged_count;
- persisted_count;
- rejected_count;
- deferred_count;
- tension_count;
- mutation_count;
- source_hashes courts si necessaires;
- old/new chars;
- old/new sha256_12;
- prompt_kind;
- model;
- timeout/error class.

Interdits:

- texte brut des formulations;
- texte brut mutable;
- buffer brut;
- prompt brut;
- raisons libres longues;
- excerpts de conversation;
- contenu intime.

Admin/read-model cible:

- montrer le mutable canonique actuel comme aujourd'hui;
- montrer le dernier statut juge content-free;
- ne plus afficher `scoring_thresholds` comme regime actif;
- ne pas afficher les formulations candidates non jugees;
- distinguer clairement `reject`, `defer`, `raise_tension` et `persist`.

## Tests cible

### Reperage

Tests unitaires du module de reperage:

- detecte `je suis X`;
- detecte `je tiens a Y`;
- detecte `je refuse Z`;
- detecte `je veux etre traite comme...`;
- detecte `ma relation a X est...`;
- detecte `Frida est / tient a / refuse`;
- detecte les formulations assistant en `je` comme sujet `llm`;
- ne detecte pas une consigne de format;
- ne detecte pas une preference purement locale;
- marque citation, roleplay, ironie ou temporal weak source comme indices, sans persister.

### Juge LLM avec mocks

Tests du service juge avec responses mockees:

- `persist/add` user;
- `persist/add` llm;
- `tighten` user;
- `merge` llm;
- `reject` preference operatoire;
- `defer` contexte ambigu;
- `raise_tension` contradiction;
- JSON invalide fail-closed;
- timeout fail-closed sans mutation;
- absence de formulations: aucun appel LLM.

### Persistence

Tests d'application:

- persiste dans `identity_mutables` quand verdict `persist`;
- ecrit `identity_mutable_audit` content-free;
- refuse contenu trop long;
- refuse contenu prompt-like;
- refuse operation impossible;
- ne modifie pas `static` sauf lot explicitement decide;
- n'ecrit rien sur `reject`, `defer`, `raise_tension`;
- garde all-or-nothing si deux sujets sont muts dans le meme passage.

### Reinjection

Tests de projection:

- `build_identity_block()` relit le nouveau mutable persiste;
- `build_identity_input()` expose les memes mutables;
- aucune formulation candidate non persistee n'est injectee;
- aucune tension non canonisee n'est injectee;
- legacy evidence ne pilote pas l'injection.

### Non-contamination

Tests de non-contamination:

- documents actifs ne deviennent pas formulations mutables par accident;
- web claims non lus ou partiellement lus restent filtres;
- summaries ne sont pas source implicite du juge mutable;
- memories RAG ne sont pas donnees au juge dans le lot initial;
- admin edits restent distincts du juge LLM.

### Suppression de l'ancien scoring

Tests de regression structurelle:

- plus aucun import runtime actif de `memory_identity_periodic_scoring`;
- plus aucun `threshold_verdict` dans le chemin mutable actif;
- plus aucun `frequency_norm`, `recency_norm`, `strength` comme condition de persistence;
- read-model/governance ne presentent plus les seuils `0.35/0.60` comme actifs;
- `identity_mutable_staging` n'est plus touche par un tour de chat apres migration finale.

### Deux cotes

Chaque famille de tests doit couvrir:

- sujet `user`;
- sujet `llm`;
- formulation du sujet par lui-meme;
- formulation du sujet par l'autre;
- absence de mutation quand le sujet est ambigu.

## Decoupage en lots

### Lot 0 - Verrouillage du contrat

Sortie:

- spec courte du nouveau contrat `formulation -> judge -> mutable`;
- schema JSON cible;
- liste des reason codes;
- decision explicite sur le nom du caller et du prompt.

Preuve:

- docs seulement;
- pas de code actif;
- pas de coexistence runtime.

### Lot 1 - Reperage non persistant

Travail:

- creer le module de reperage;
- le tester hors runtime actif;
- couvrir user/llm, role source, types de formulation et gardes citation/ironie.

Sortie:

- aucune persistence;
- aucun appel LLM;
- aucune injection.

Point de sortie:

- le module sait extraire des formulations candidates, mais rien ne l'utilise pour ecrire.

### Lot 2 - Juge LLM isole

Travail:

- creer le prompt juge;
- creer le caller/service juge;
- valider le schema de sortie;
- tester avec mocks.

Sortie:

- le juge peut etre appele en test;
- aucun write runtime branche;
- aucun scoring.

Point de sortie:

- le LLM juge produit un verdict explicite, pas une simple proposition a scorer.

### Lot 3 - Applicateur judge-first

Travail:

- creer ou remplacer l'applicateur;
- persister uniquement les verdicts `persist`;
- garder les gardes de forme, taille, prompt-like, contradiction simple;
- ecrire l'audit content-free.

Sortie:

- tests persistence et rollback;
- aucun import du scoring dans le nouvel applicateur.

Point de sortie:

- une decision mockee du juge peut modifier `identity_mutables` sans passer par `strength`.

### Lot 4 - Bascule runtime sans double systeme

Travail:

- brancher `record_identity_entries_for_mode(...)` vers `reperage -> juge -> apply`;
- retirer dans le meme lot le declenchement actif `stage_identity_turn_pair(...)` pour les mutables;
- garder le legacy diagnostic seulement si explicitement separe et nomme comme tel;
- ne pas laisser `identity_periodic_agent` et `identity_mutable_judge` ecrire tous les deux.

Sortie:

- un tour avec formulation pertinente appelle le juge;
- un tour sans formulation n'appelle pas le juge;
- aucune mutation par scoring periodic.

Point de sortie:

- le nouveau pipeline est le seul writer automatique du mutable.

### Lot 5 - Admin, read-model, governance et logs

Travail:

- remplacer les champs `staging/scoring` actifs par `judge_activity` content-free;
- adapter `/identity` et `/hermeneutic-admin`;
- adapter specs logs et read-model;
- garder les contenus canoniques editables uniquement dans les editeurs prevus.

Sortie:

- admin comprehensible;
- logs content-free;
- plus de seuils scoring presentes comme autorite active.

Point de sortie:

- l'operateur voit ce qui s'est passe sans voir de contenu sensible ni ancien regime.

### Lot 6 - Nettoyage legacy

Travail:

- supprimer `memory_identity_periodic_scoring.py`;
- supprimer ou archiver `memory_identity_periodic_agent.py` si remplace;
- supprimer les tests scoring/periodic devenus faux;
- retirer `identity_mutable_staging` du runtime et preparer la migration DB;
- supprimer le prompt periodic ou le reclasser comme archive;
- supprimer le shim rewriter si aucune compatibilite ne reste;
- mettre a jour docs/specs/index.

Sortie:

- plus de couche morte;
- plus de logique parallele;
- plus de chemin mutable score-first.

Point de sortie:

- impossible de croire que l'ancien systeme mutable est encore une alternative active.

### Lot 7 - Validation finale

Travail:

- tests unitaires et integration cibles;
- preuves admin/read-model;
- preuve de non-contamination;
- revue de references `rg`.

Sortie:

- `rg "memory_identity_periodic_scoring|threshold_verdict|frequency_norm|recency_norm|strength"` ne trouve plus de references actives hors archives;
- `rg "identity_mutable_rewriter|identity_periodic_agent"` ne trouve plus de chemin writer actif non documente;
- docs vivantes alignees.

## Criteres de fin de chantier

Le chantier est termine seulement si:

- plus aucun ancien systeme mutable actif ne peut ecrire le canon;
- plus aucun scoring deterministe n'est critere central de persistence mutable;
- `user` et `llm` passent par le meme pipeline de formulation, jugement et application;
- le LLM juge est l'autorite de decision ontologique;
- le reperage ne persiste rien;
- les regex ne canonisent rien;
- `identity_mutables` reste la source active reinjectee;
- admin/logs exposent statuts, compteurs, reason codes, longueurs et hash courts sans texte brut sensible;
- les docs vivantes racontent le nouveau regime;
- les tests prouvent les deux sujets, les rejets, les defers, les tensions, la persistence et la non-contamination;
- les modules/prompts/tests de l'ancien scoring ne restent pas comme couche morte.

## Feed her from herself

Ne pas ouvrir un chantier separe ici.

L'intuition `feed her from herself` est probablement absorbee en partie par cette refonte: une parole de Frida sur sa propre limite, posture ou promesse peut devenir une formulation portee au juge. Cela ne donne pas au LLM final le pouvoir de reecrire son identite; cela donne au juge mutable un candidat mieux cadre.

La question restera a reprendre seulement apres la refonte, si un artefact reflexif distinct reste necessaire.

## Fichiers et fonctions cles

Chemin d'entree actuel:

- `app/core/chat_llm_flow.py::_latest_completed_identity_pair`
- `app/core/chat_llm_flow.py::run_llm_exchange`
- `app/core/chat_memory_flow.py::record_identity_entries_for_mode`
- `app/core/chat_memory_flow.py::_run_periodic_identity_agent`

Pipeline mutable actuel:

- `app/memory/memory_identity_periodic_agent.py`
- `app/memory/memory_identity_periodic_apply.py`
- `app/memory/memory_identity_periodic_scoring.py`
- `app/memory/memory_identity_staging.py`
- `app/memory/memory_identity_mutables.py`
- `app/memory/memory_identity_mutable_rewriter.py`
- `app/memory/arbiter.py::run_identity_periodic_agent`
- `app/memory/arbiter.py::extract_identities`

Projection et reinjection:

- `app/identity/active_identity_projection.py`
- `app/identity/identity.py::build_identity_block`
- `app/identity/identity.py::build_identity_input`
- `app/core/hermeneutic_node/inputs/identity_input.py`

Validation et gouvernance:

- `app/identity/mutable_identity_validation.py`
- `app/identity/identity_governance.py`
- `app/admin/admin_identity_read_model_service.py`
- `app/admin/admin_identity_mutable_edit_service.py`
- `app/admin/admin_identity_routes.py`

Observabilite:

- `app/observability/chat_turn_logger.py`
- `app/observability/identity_observability.py`
- `app/observability/log_store.py`
- `app/docs/states/specs/log-module-contract.md`

Prompts:

- `app/prompts/identity_extractor.txt`
- `app/prompts/identity_periodic_agent.txt`
- `app/prompts/identity_mutable_rewriter.txt`

Tests a remplacer ou requalifier:

- `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`
- `app/tests/unit/memory/test_identity_periodic_apply_phase2.py`
- `app/tests/unit/memory/test_identity_periodic_scoring_phase2.py`
- `app/tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`
- `app/tests/unit/identity/test_mutable_identity_validation.py`
- `app/tests/test_server_admin_identity_read_model_phase2.py`

## Risques et points de vigilance

- Le nouveau juge peut devenir trop permissif si le prompt confond formulation intense et continuite mutable.
- Il peut devenir trop muet si le reperage ne transmet pas assez de contexte local.
- Les formulations de Frida sur elle-meme doivent etre distinguees des effets de style du LLM final.
- Les formulations du user sur Frida doivent etre jugees comme paroles relationnelles situees, pas comme verite automatique sur `llm`.
- L'ancien legacy identity peut rester utile au diagnostic, mais il ne doit pas redevenir une source mutable indirecte.
- Le nettoyage final est obligatoire: sans lui, le repo gardera une couche score-first morte mais relisible comme autorite concurrente.
