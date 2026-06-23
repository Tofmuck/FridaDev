# Frida V1 - Continuity Payload Contract

Date: 2026-06-22

Statut: contrat source-of-truth Continuity Payload. Lot 1 a defini le contrat;
Lot 2 a livre le manifeste runtime content-free sans capsule. Lot 3 a livre la
garde writer-side d'observabilite, durcie en Lots 3.1, 3.2 et 3.3 en politique
schema-first/default-deny stricte. Lot 4 a etendu le manifeste aux fenetres de
continuite content-free: summary, memory observee vs injectee, hermeneutic node,
Biblio, Agenda, identity staging et soft-limit final. Lot 4.1 preserve les
payloads d'observabilite content-free legitimes sous cette garde stricte et
reduit l'estimation de tokens du manifeste a un calcul prompt-level unique.
Lot 4.2 supprime le hash stable court du bloc de prompt hermeneutique et refuse
toute valeur renseignee sous cle generique `sha256_12` cote writer-side.
Lot 5 clarifie les conflits de lanes, final locks Agenda/Biblio et no-op
Documents/Notes/Exports/Images dans le manifeste, sans capsule runtime.
Lot 5.1 classe `final_lock_priority_unexpected` en `failed` quand un conflit
Agenda/Biblio selectionne une source non-Agenda malgre la politique courante.
Lot 6 ajoute des fixtures qualitatives artificielles, content-free et sans
provider live, pour prouver ce qu'une future capsule devra preserver avant tout
runtime. Lot 7 livre une Continuity Capsule runtime bornee, desactivee par
defaut/configurable sans DB, injectee seulement quand le modele principal est
appele, et observee content-free par `main_payload_manifest_v1`. Lot 7.1 durcit
l'entree de capsule contre les marqueurs de contenu unsafe et clarifie que la
non-souverainete du message `system` est une contrainte produit explicite, pas
une garantie mecanique du provider. Lot 7.2 etend ce durcissement aux variantes
credential-like avec `:` ou `=`, aux URL-like `www.` en milieu de phrase et aux
chemins prives/absolus evidents en milieu de phrase.

Ce contrat definit deux objets cibles:

- `main_payload_manifest_v1`, le manifeste content-free du payload logique final
  envoye au modele principal Frida.
- `Continuity Capsule`, la surface courte de continuite de ton,
  methode, relation et presence entre conversations.

Decision dure: le manifeste precede la capsule. Aucune injection runtime de
Continuity Capsule ne peut partir tant que `main_payload_manifest_v1` n'est pas
livre, teste, relu et prouve content-free sur le payload final apres injections
tardives.

## Sources normatives

- TODO active: `app/docs/todo-todo/product/frida-v1-continuity-payload-todo.md`
- Audit principal:
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-audit-2026-06-22.md`
- Contre-audit:
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`
- Doctrine voix et reprise:
  `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Identite mutable active:
  `app/docs/states/specs/mutable-identity-judge-contract.md`
- Doctrine identite:
  `app/docs/states/policies/identity-new-contract-plan.md`
- Archive identite:
  `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Observabilite agentique:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`

## Non-objectifs du Lot 1

- Pas de patch runtime Python ou JavaScript.
- Pas d'instrumentation du payload.
- Pas d'appel provider live.
- Pas de capture, dump, export ou commit de prompt brut.
- Pas de dialogue brut, message utilisateur brut, contenu document, note,
  passage Biblio, contenu Adobe, contenu Web, export, image, bytes, base64 ou
  data URL.
- Pas de migration, reset, purge, backfill ou lecture de donnees runtime
  sensibles.
- Pas d'activation ou injection de Continuity Capsule.

## Definition: payload final principal

Le payload final principal est la sequence logique des messages et options qui
alimente le modele de chat principal apres toutes les injections tardives du
tour courant. Dans le code actuel, cette frontiere se situe apres la construction
de la fenetre de prompt conversationnelle, puis apres les injections Web, Notes,
documents actifs, Biblio, Agenda, Adobe et les gardes de sortie, et juste avant
l'appel principal ou son contournement par final response lock.

Le manifeste ne doit pas etre un payload provider serialise. Il doit etre une
projection content-free, assez precise pour prouver l'ordre, les roles, les
origines, les budgets et les exclusions, sans permettre de reconstruire le
contenu envoye au modele.

## `main_payload_manifest_v1`

### Objet

`main_payload_manifest_v1` est le contrat d'observabilite content-free du payload
final envoye au modele principal Frida, ou du contournement de cet appel quand
un final response lock produit directement la reponse visible.

Il doit repondre a quatre questions sans fuite:

- Qu'est-ce qui aurait ete envoye au modele principal, dans quel ordre final?
- Quels roles provider et roles logiques Frida chaque bloc porte-t-il?
- Quelle lane ou sous-systeme a contribue, ete exclu, ete desactive ou ete
  contourne?
- Le modele principal a-t-il ete appele, ou une reponse verrouillee a-t-elle
  remplace l'appel?

### Champs top-level requis

Un manifeste valide doit contenir au minimum:

| Champ | Regle |
| --- | --- |
| `schema_version` | Valeur exacte `main_payload_manifest_v1`. |
| `scope` | Valeur `main_chat`. |
| `turn_id_present` | Booleen. Pas d'identifiant brut obligatoire. |
| `conversation_id_present` | Booleen. Si une empreinte est ajoutee, elle doit respecter la politique de hachage ci-dessous. |
| `conversation_state` | Presence d'id conversation, presence d'id de tour, etat `conversation_state_kind`, message count conversationnel et rattachement dossier content-free. |
| `main_model_called` | Booleen. Faux si final response lock remplace l'appel principal. |
| `provider` | Nom de provider ou famille non secrete, sans cle ni URL sensible. |
| `runtime_settings` | Reglages utiles content-free: modele exact non sensible ou empreinte approuvee, temperature, top_p, max_tokens, stream, reasoning envoye ou non, stop_count. |
| `assistant_output_policy` | Presence, kind, reason codes, flags de garde. Pas de texte de politique brute si elle contient des instructions completes. |
| `final_response_lock` | Presence, source, reason_code, priorite effective, main model bypassed. Pas de contenu de reponse. |
| `lane_conflicts` | Synthese content-free des conflits de lanes et final locks: candidats, priorite effective, source selectionnee, source supprimee, mismatch d'injection implicite. |
| `continuity_capsule` | Statut runtime content-free de la capsule: presence, enabled, version, reason_code, taille, injection count, flags raw/fingerprint a false. Pas de contenu de capsule. |
| `messages` | Tableau ordonne des entrees content-free du payload final. |
| `lane_statuses` | Presence/absence/no-op de chaque lane attendue. |
| `windows` | Compteurs des fenetres reconstruites par prompt final, memory, hermeneutic node, Biblio, Agenda et autres sous-systemes. |
| `budgets` | Limites, compteurs, soft-limit, exclusions et truncations connues. |
| `raw_flags` | Tous les flags anti-fuite obligatoires a `false`. |

### Entree `messages[]`

Chaque entree de `messages[]` doit decrire un bloc final sans contenu brut:

| Champ | Regle |
| --- | --- |
| `index` | Position finale zero-based apres injections tardives. |
| `provider_role` | Role provider effectif: `system`, `user`, `assistant`, `tool` ou autre role supporte si ajoute plus tard. |
| `logical_roles` | Liste des roles logiques internes. Exemples: `system_prompt`, `developer_prompt`, `time_reference`, `identity_stable`, `identity_mutable`, `summary`, `memory`, `context_hints`, `user_turn`, `assistant_turn`, `web_lane`, `note_lane`, `document_lane`, `biblio_lane`, `agenda_lane`, `adobe_lane`, `continuity_capsule`, `assistant_output_policy`. |
| `origin` | Module, sous-systeme ou lane source, sous forme allowlistee. |
| `origin_stage` | Etape d'injection: base prompt, web late injection, note lane, active document lane, biblio lane, agenda lane, adobe lane, output guard, final lock. |
| `content_kind` | Type abstrait: instruction, resume, trace memoire, dialogue, lane contract, lane content, guard, tool evidence, override metadata. |
| `content_present` | Booleen. |
| `content_chars` | Nombre de caracteres du bloc, pas le contenu. |
| `estimated_tokens` | Estimation si disponible; sinon `null`. |
| `excluded` | Booleen si le bloc candidat a ete exclu. |
| `exclusion_reason_code` | Raison allowlistee si exclu. |
| `raw_content_included` | Toujours `false`. |

La version livree en Lot 2 ne contient pas de champ `hash_12` dans
`messages[]`. Elle expose seulement des compteurs, roles, origines et flags.

### Politique de hachage et empreintes

Le finding P2 Lot 1.1 est valide: un hash court stable comme `sha256[:12]`
calcule sur un texte sensible court n'est pas content-free par defaut. Il peut
etre retrouve par dictionnaire, par comparaison d'hypotheses ou par correlation
inter-runs.

`hash_12` ne doit donc pas etre presente comme non reversible par defaut. Une
empreinte courte est une aide de comparaison, pas une garantie de confidentialite.
La version Lot 2 evite ce champ dans le manifeste runtime et expose seulement
`stable_text_hashes_included=false`,
`short_stable_text_hashes_included=false` et `fingerprints_included=false`.

Aucun hash stable non sale, non secret ou non HMAC-like ne doit etre calcule sur:

- prompt brut;
- message utilisateur;
- reponse assistant;
- contenu de lane;
- texte de policy;
- contenu de Continuity Capsule;
- contenu documentaire;
- passage Biblio;
- contenu Web;
- contenu Adobe;
- contenu de note;
- contenu de document actif;
- contenu d'export;
- contenu ou metadonnees sensibles d'image.

Pour les contenus textuels sensibles, le manifeste doit preferer:

- compteurs;
- longueurs;
- presence ou absence;
- reason codes;
- IDs opaques techniques deja non sensibles;
- index local du bloc;
- fingerprints ephemeres non correlables si une comparaison locale est
  absolument necessaire.

Si une comparaison entre runs est necessaire, elle doit etre explicitement
bornee par l'une de ces conditions:

- comparaison sur donnees synthetiques non sensibles;
- methode approuvee dans la spec ou le patch Lot 2;
- HMAC ou hash sale avec secret non expose, rotation documentee et absence
  d'affichage de la valeur si le risque de correlation reste trop fort.

Meme dans ces cas, le manifeste doit rester content-free face aux textes courts.
Une implementation qui ajoute une empreinte stable sur du contenu textuel
sensible doit etre refusee.

### Roles logiques minimaux

La premiere version doit reconnaitre au moins:

- `system_prompt`
- `developer_prompt`
- `time_reference`
- `identity_stable`
- `identity_mutable`
- `summary`
- `memory`
- `context_hints`
- `hermeneutic_node`
- `user_turn`
- `assistant_turn`
- `web_lane`
- `note_lane`
- `document_lane`
- `export_lane`
- `image_lane`
- `biblio_lane`
- `agenda_lane`
- `adobe_lane`
- `continuity_capsule`
- `assistant_output_policy`
- `final_response_lock`

Si un sous-systeme injecte aujourd'hui son contexte comme provider role `user`,
le manifeste doit conserver deux plans distincts:

- `provider_role=user`
- `logical_roles=[..., "<lane>_lane"]`

Cette distinction est obligatoire pour resoudre le risque de provenance entre
parole humaine et contexte outille.

### Provenance structuree obligatoire

Le manifeste ne doit jamais attribuer `note_lane`, `document_lane`,
`biblio_lane` ou `adobe_lane` par simple inspection du texte final du message.
Les libelles visibles tels que `[NOTES DE DOSSIER ...]`,
`[DOCUMENTS ACTIFS ...]`, `[ADOBE DOCS ...]` ou
`PASSAGES DE BIBLIOTHEQUE ...` sont des details de rendu prompt, pas une preuve
de provenance.

La provenance souveraine pour ces lanes doit etre capturee autour de
l'injection reelle sous forme content-free: index ou reference locale du bloc,
role logique attendu, origine allowlistee, etape d'injection et type abstrait de
contenu. Un message utilisateur contenant une fausse balise de lane doit rester
`logical_roles=["user_turn"]` si aucune injection structuree ne l'a produit.

`web_lane` est le cas separe: la lane peut etre portee par le dernier message
provider `user` seulement si le contexte Web a reellement ete injecte par le
runtime Web, selon un payload structure indiquant une activation `manual` ou
`auto` et une injection effective.

Les roles `identity_stable` et `identity_mutable` ne doivent etre portes par le
message systeme que si les lanes d'identite correspondantes sont selectionnees
dans les donnees structurees du tour. Le manifeste ne doit pas dire a la fois
qu'un message contient une identite et que la lane identity est `not_selected`.

### Lanes et statuts requis

`lane_statuses` doit contenir une entree pour chaque lane connue, meme quand elle
ne contribue pas:

- Web
- Notes
- Documents actifs
- Exports reutilises
- Images ou contexte multimodal
- Biblio
- Agenda
- Adobe Docs
- Memory
- Summary
- Identity stable
- Identity mutable
- Hermeneutic node

Chaque entree doit exposer au minimum:

- `selected`
- `enabled`
- `status`
- `reason_code`
- `input_count`
- `injected_count`
- `excluded_count`
- `content_chars`
- `estimated_tokens`
- `raw_lane_content_included=false`

Les statuts doivent rester compatibles avec la taxonomie agentique:
`ok`, `skipped`, `disabled`, `not_selected`, `not_configured`,
`not_applicable`, `refused`, `failed`, `error`.

### Budgets, limites et exclusions

Le manifeste doit prouver sans contenu:

- soft token limit observe;
- hard limit si un lot futur en ajoute un;
- `prompt_soft_limit_exceeded`;
- `dialogue_messages_truncated`;
- nombre de messages candidats;
- nombre de messages retenus;
- fenetre de dialogue retenue apres summary;
- fenetre memory;
- fenetre hermeneutic node;
- fenetre Biblio;
- fenetre Agenda;
- budgets de notes, documents, Biblio, Agenda, Adobe et Web;
- exclusions par budget;
- exclusions par selection absente;
- exclusions par feature flag;
- exclusions par erreur, refusal ou configuration manquante.

Un soft limit observe mais non impose doit etre visible comme tel. Il ne peut pas
etre presente comme une preuve de truncation effective.

### Fenetres de continuite Lot 4

`windows` est une carte content-free des sous-fenetres qui peuvent porter ou
casser la continuite de ton, methode, relation et presence. Chaque entree de
fenetre doit exposer au minimum:

- `status`;
- `reason_code`;
- `source`;
- `origin_stage`;
- `selected`;
- `raw_content_included=false`;
- compteurs ou flags propres a la fenetre.

Les statuts de fenetre peuvent utiliser `not_available` quand un signal n'est
pas disponible au point final du manifeste. Ce statut ne doit pas etre confondu
avec les statuts d'evenement agentique; il documente une absence de preuve au
moment du payload final.

Fenetres requises en Lot 4:

- `prompt_final`: ordre final, roles provider, nombre de messages, caracteres
  et estimation de tokens apres injections tardives;
- `conversation`: compteurs d'historique persistant, par role;
- `recent_context`: messages recents visibles au noeud hermeneutique;
- `recent_window`: tours retenus, tours complets, in-progress et assistant-only;
- `summary`: presence, periode, taille et statut explicite de nuance de voix;
- `memory`: retrieval, arbitration observee, injection effective et source
  d'injection;
- `hermeneutic_node`: presence du payload primaire, validation et bloc injecte;
- `identity_staging`: statut conversation-scoped avant canonisation;
- `biblio_recent_dialogue`: fenetre recente envoyee a Biblio, sans contenu;
- `agenda_recent_dialogue`: fenetre recente envoyee a Agenda, sans contenu.

La fenetre `memory` doit distinguer:

- `retrieved_count`;
- `basket_candidates_count`;
- `arbiter_decisions_count`;
- `arbiter_observed_count`;
- `prompt_injected_count`;
- `context_hint_count`;
- `injection_source`;
- `arbiter_controls_injection`.

En mode `shadow`, `arbiter_controls_injection=false` et
`injection_source=pre_arbiter_basket_shadow`: le juge observe mais ne controle
pas forcement la memoire injectee. En mode `enforced_all`,
`arbiter_controls_injection=true`.

La fenetre `summary` doit rester honnete: elle peut prouver presence, taille et
periode, mais elle ne prouve pas a elle seule que les nuances de voix, humour,
hesitations, rituels d'audit ou methode relationnelle sont preserves. Tant qu'un
test qualitatif artificiel n'existe pas, le manifeste doit exposer
`voice_continuity_status=not_available` et
`voice_continuity_reason_code=summary_style_not_scored`.

La fenetre `identity_staging` doit rappeler que la mutable identity staging est
conversation-scoped et post-reponse avant canonisation. Au point du payload
principal, elle ne doit pas etre vendue comme identite canonisee ni comme
continuite trans-conversation disponible.

`budgets.prompt` doit exposer pour le prompt final:

- `soft_limit_configured`;
- `prompt_soft_token_limit`;
- `prompt_soft_limit_exceeded`;
- `dialogue_messages_truncated`;
- `excluded_count`;
- `truncated_count`;
- `soft_limit_stage`;
- `soft_limit_policy`;
- `soft_limit_reason_code`.

La politique actuelle est `observability_only_no_prompt_exclusion`: un
depassement du soft limit est observable, mais ne prouve pas une exclusion ou
troncation effective.

L'estimation de tokens du manifeste doit rester content-free et sobre. Quand un
compteur est disponible, Lot 4.1 impose une estimation globale du prompt final,
calculee une seule fois au point du manifeste et reutilisee dans
`messages[]`, `windows.prompt_final` et `budgets.prompt`. Le manifeste ne doit
pas multiplier les appels au compteur par message si une estimation prompt-level
suffit a prouver les budgets et la fenetre finale.

### Runtime settings content-free

Le manifeste peut exposer les reglages utiles au diagnostic:

- slot appelant: `main_chat`;
- provider family;
- modele exact si non sensible, ou empreinte conforme a la politique de hachage
  si la politique operateur le decide;
- temperature;
- top_p;
- max_tokens;
- stream active ou non;
- stop sequence count seulement;
- reasoning envoye ou non, effort normalise si present;
- response_format presence/type si un lot futur l'ajoute;
- feature flags de lanes;
- version de contrat et version de code si disponible.

Il ne doit jamais exposer de cle, valeur secrete, URL sensible, contenu d'en-tete
provider ou payload provider brut.

### Final response locks

Le manifeste doit representer les final response locks comme une decision de
surface visible, meme si le modele principal n'est pas appele.

Champs requis:

- `final_response_lock.present`
- `final_response_lock.source`
- `final_response_lock.reason_code`
- `final_response_lock.priority_policy`
- `final_response_lock.main_model_bypassed`
- `final_response_lock.content_present`
- `final_response_lock.content_chars`
- `final_response_lock.raw_content_included=false`

La priorite actuelle Agenda puis Biblio doit etre documentee par le manifeste.
Si la priorite change, le champ `priority_policy` doit changer explicitement.

Depuis Lot 5, le manifeste doit aussi exposer `lane_conflicts`:

- `priority_policy=agenda_over_biblio`;
- presence de lock Agenda et Biblio;
- `candidate_count` et `candidate_sources` sans contenu de reponse;
- `selected_source` et, en cas de conflit, `suppressed_source`;
- `agenda_selected` / `biblio_selected`;
- `conflict_present`;
- `message_lane_status_mismatch_count`;
- `implicit_injection_detected`;
- `raw_content_included=false`.

Le cas de conflit courant est borne ainsi: si Agenda et Biblio produisent tous
deux un final lock valide, Agenda est la source selectionnee et Biblio reste
visible comme candidat supprime par priorite. Cette regle est une observation du
runtime courant, pas une doctrine de voix: Lot 6 reste responsable des tests
qualitatifs de presence.

Si Agenda et Biblio produisent tous deux un final lock mais que la source
selectionnee n'est pas Agenda, `lane_conflicts.status` doit etre `failed`,
`reason_code=final_lock_priority_unexpected`, `selected_source` doit rester
content-free, et la source attendue ou supprimee doit etre visible sans contenu
de reponse. Cette branche defensive ne doit jamais etre classee `ok`.

### Assistant output policy

La politique de sortie assistant doit etre visible sans recopier le prompt brut:

- presence de la policy;
- policy id ou kind;
- reason codes;
- flags de plain text guard;
- contraintes de format sous forme de codes allowlistes;
- `raw_policy_text_included=false`.

### Flags anti-fuite obligatoires

`raw_flags` doit contenir exactement ces garanties, toutes a `false`:

- `raw_prompt_included=false`
- `raw_message_included=false`
- `raw_content_included=false`
- `raw_lane_content_included=false`
- `raw_provider_payload_included=false`
- `raw_secret_included=false`

Si une future implementation ne peut pas garantir un de ces flags, le manifeste
doit etre refuse et le lot runtime bloque.

### Interdictions absolues

Le manifeste, ses logs, ses tests et ses fixtures ne doivent jamais contenir:

- prompt brut;
- dialogue brut;
- message utilisateur brut;
- reponse assistant brute;
- contenu de document actif;
- corps de note Markdown;
- passage Biblio;
- contenu Adobe;
- contenu Web;
- export brut;
- image, bytes, base64 ou data URL;
- payload provider brut;
- valeur secrete;
- URL sensible, DAV brute, chemin distant sensible ou en-tete sensible.

## Garde writer-side d'observabilite

Depuis le Lot 3, `chat_turn_logger` doit appliquer une garde avant toute
ecriture d'evenement dans `log_store`. Cette garde est distincte de la projection
admin: elle empeche l'entree du contenu dangereux dans le stockage, au lieu de
compter seulement sur une redaction de lecture.

La garde doit refuser ou remplacer avant stockage tout payload contenant:

- cles brutes exactes ou equivalents non qualifies: `messages`, `message`,
  `prompt`, `content`, `text`, `payload`, `provider_payload`, `raw`,
  `raw_payload`, `base64`, `data_url`, `image_data_url`, `secret`, `token`,
  `password`, `cookie`, `authorization`, `header`, `url`, `path`, `dav`, `xml`,
  `etag`;
- variantes raw/request/response payload non qualifiees;
- URL, DAV/XML, ETag brut, header, bearer/token-like, cookie, credential,
  path sensible, base64 ou data URL, meme sous une cle apparemment safe;
- payloads imbriques dangereux.

Restent autorises quand ils sont content-free:

- compteurs, longueurs, boolens, statuts, reason codes, stages et index locaux;
- IDs opaques techniques non sensibles;
- flags qualifies explicitement faux, par exemple
  `raw_prompt_included=false`, `raw_message_included=false`,
  `raw_content_included=false`, `raw_provider_payload_included=false`,
  `raw_lane_content_included=false`, `raw_secret_included=false`;
- `main_payload_manifest_v1`, seulement s'il respecte son schema content-free et
  ne contient ni champ brut inattendu ni raw flag vrai.

Depuis le Lot 3.1, cette garde est default-deny. Elle ne doit pas accepter une
chaine libre parce que sa cle n'est pas connue comme dangereuse. Pour les
payloads generaux:

- une cle inconnue avec valeur string doit etre refusee;
- une cle inconnue avec mapping ou liste doit etre refusee, meme si ses valeurs
  paraissent content-free;
- les strings ne sont admises que sous cles textuelles explicites et sous forme
  de code safe, statut, reason code, modele non secret ou equivalent borne;
- les valeurs numeriques, booleennes et nulles ne sont admises que sous cles
  metriques ou scalaires content-free explicitement reconnues;
- les flags `raw_*_included` qualifies ne sont admis que s'ils valent `false`.

Pour `main_payload_manifest_v1`, chaque mapping connu doit etre schema-first:
`runtime_settings`, `assistant_output_policy`, `final_response_lock`,
`conversation_state`, `hash_policy`, `raw_flags`, `budgets.prompt`,
`windows.*`, `messages[]` et `lane_statuses.*` ont des cles attendues. Les noms
dynamiques de lanes restent possibles dans `lane_statuses`, mais leur valeur
doit respecter le schema de statut de lane. Aucun sous-mapping du manifeste ne
doit retomber sur une logique "si ce n'est pas dangereux connu, on accepte".

Comportement requis en cas de rejet:

- l'evenement original dangereux n'est pas stocke;
- l'evenement stocke porte un payload de garde content-free avec
  `reason_code=observability_payload_rejected`;
- un evenement demande en `status=ok` ne doit pas rester un succes normal: il
  devient `status=refused`;
- un evenement deja non-OK peut garder son statut pour preserver la visibilite
  de la panne, mais son payload reste remplace par la garde;
- la garde ne doit pas exposer la valeur interdite ni la cle brute sensible:
  elle expose seulement compteurs et classes de rejet.

## Continuity Capsule

### Objet

La Continuity Capsule est une surface courte, versionnee et contestable
destinee a porter ce que ni identity, ni memory, ni summary ne portent proprement
aujourd'hui: une continuite de ton, methode, relation et presence entre
conversations.

Elle n'a pas ete implementee par le Lot 1. Elle devient runtime en Lot 7, apres
preuve du payload final, de la garde writer-side, des fenetres, des locks/lanes
et des tests qualitatifs sans contenu utilisateur reel.

### Ce que la capsule peut decrire

Une capsule cible peut decrire, de facon courte et non souveraine:

- posture dialogique habituelle;
- niveau de proactivite attendu;
- densite d'explication preferee;
- maniere de cadrer un refus ou une incertitude;
- sobriete ou humour habituel;
- rituels de travail explicites, par exemple audit, no-go, content-free;
- preference de reprise apres interruption ou nouvelle conversation;
- attention a la continuite critique et politique.

Elle doit rester un aide-memoire de conduite, pas une preuve factuelle et pas une
identite.

### Distinctions obligatoires

| Dimension | Difference avec la capsule |
| --- | --- |
| Identite stable | Decrit le noyau identitaire profond et durable. La capsule ne modifie pas ce noyau. |
| Identite mutable | Decrit des enonces d'etre admis par le juge mutable. La capsule ne doit pas y ecrire ni etre canonisee comme mutable sans decision doctrinale explicite. |
| Memory | Stocke et retrouve des traces factuelles ou contextuelles. La capsule ne remplace pas les souvenirs. |
| Summary | Compresse une conversation donnee. La capsule traverse les conversations et ne doit pas aplatir le dialogue recent. |
| Observabilite | Prouve des evenements content-free. La capsule n'est pas une trace technique. |
| Lanes | Apportent des preuves ou outils de domaine. La capsule ne prime jamais sur une lane probante. |

### Proprietes obligatoires

La capsule doit etre:

- courte;
- versionnee;
- contestable;
- desactivable;
- rollbackable;
- content-free observable;
- non souveraine;
- separee de l'identite mutable;
- jamais melangee a memory ou summary sans champ explicite et decision
  doctrinale.

Non souveraine signifie:

- le tour courant prime;
- les preuves injectees priment;
- les garde-fous produit priment;
- les refus et limites de securite priment;
- l'utilisateur peut corriger ou contester la capsule;
- une contradiction doit etre resolue par prudence, pas par autorite de la
  capsule.

### Non-objectifs de la capsule

- Pas de simulation d'intimite.
- Pas de fossilisation de personnalite.
- Pas de remplacement de la memoire.
- Pas de transformation de la relation en scoring.
- Pas de capture de dialogue utilisateur reel pour imiter le ton.
- Pas de souverainete sur le tour courant.
- Pas de promotion automatique vers identity mutable.
- Pas de doctrine cachee dans une surface runtime.

### Preuve qualitative Lot 6

Le Lot 6 ne cree pas de Continuity Capsule runtime. Il cree une preuve
deterministe test-only, sur fixtures artificielles, que la continuite de
presence peut etre jugee sans provider live et sans contenu utilisateur reel.

Les fixtures doivent rester content-free:

- traits qualitatifs sous forme de codes, par exemple methode, presence
  relationnelle, reprise apres ecart, proactivite bornee, cadrage de refus et
  sobriete/humour;
- compteurs, statuts, booleens et reason codes;
- aucun prompt, dialogue, summary, memory, document, note, passage, export,
  image, URL, payload provider, secret ou hash stable de texte sensible.

La preuve Lot 6 distingue quatre carriers:

- `identity`: noyau ou faits identitaires, pas surface de methode
  conversationnelle;
- `memory`: faits ou decisions recuperables, pas posture qualitative complete;
- `summary`: condensation d'une conversation donnee, susceptible d'aplatir la
  nuance de voix;
- `continuity_capsule_candidate`: objet test-only non injecte, distinct,
  qualitatif, court et non souverain.

Scenarios minimaux prouves par Lot 6:

- conversation longue: le dialogue recent peut porter les traits qualitatifs
  sans capsule candidate;
- nouvelle conversation sans memoire: identity seule ne suffit pas a porter la
  presence qualitative complete;
- lanes non selectionnees: les no-op n'apportent pas de continuite implicite;
- apres resume: summary seul peut conserver le fond tout en aplatissant les
  traits relationnels et methodologiques;
- capsule candidate: restaure les traits minimaux dans la fixture sans devenir
  identity, memory ou summary, et sans etre injectee dans le prompt.

Cette preuve ferme les findings de test et d'observabilite qualitative
pre-runtime. A l'issue du Lot 6, elle ne fermait pas a elle seule l'absence de
surface durable runtime: `P1-CONT-01` restait conditionne a Lot 7 ou a un report
post-V1 explicite. Le Lot 7 ferme ensuite ce point par une surface runtime
bornee.

### Injection runtime Lot 7

La position retenue en Lot 7 est tardive et bornee: apres les lanes Web, Notes,
Documents, Biblio, Agenda, Adobe et apres le choix effectif du final response
lock Agenda/Biblio, juste avant `main_payload_manifest_v1` et
`run_llm_exchange`.

La capsule runtime Lot 7 doit:

- etre bornee en taille;
- etre versionnee;
- etre desactivee par defaut et activable par config/env sans DB;
- etre rollbackable sans migration destructive;
- apparaitre dans `main_payload_manifest_v1`;
- exposer presence, enabled, version, `content_chars`, `max_chars`,
  `injected_count`, `status` et `reason_code`;
- garder `raw_content_included=false`, `raw_prompt_included=false`,
  `raw_capsule_content_included=false` et `fingerprint_included=false`;
- ne pas utiliser de hash stable naif sur capsule, prompt, message ou lane;
- ne pas etre injectee si `final_response_lock.present=true`;
- ne jamais ecrire dans identity mutable sans decision doctrinale separee.

Les statuts runtime attendus sont:

- `disabled` / `continuity_capsule_disabled`: defaut, rollback simple, aucune
  injection;
- `ok` / `continuity_capsule_ready`: capsule valide, message systeme tardif
  injecte avec `logical_roles=["continuity_capsule"]`;
- `not_configured` / `continuity_capsule_missing`: flag actif sans texte,
  aucune injection;
- `refused` / `continuity_capsule_too_large`: texte trop long, aucune
  troncation silencieuse;
- `refused` / `continuity_capsule_unsafe_content`: texte contenant un marqueur
  unsafe evident, aucune injection provider;
- `not_selected` / `continuity_capsule_final_lock_bypass`: final lock
  Agenda/Biblio, modele principal bypass, aucune injection.

Validation safety Lots 7.1 et 7.2:

- le texte de capsule est refuse avant injection s'il contient URL ou `://`,
  `Bearer`, `Authorization`, `Cookie`, `Set-Cookie`, `token=`, `api_key=`,
  `password=`, `secret=`, data URL/base64 evident, XML/DAV/CALDAV/WebDAV,
  chemin absolu/prive evident ou bloc de cle privee;
- les variantes credential-like avec separateur `:` ou `=` sont refusees:
  `token:`, `secret:`, `password:`, `api_key:`, `api-key:`, `x-api-key:`,
  `authorization:`, `cookie:` et `set-cookie:`;
- `www.` est refuse meme au milieu d'une phrase;
- les chemins prives/absolus evidents sont refuses meme au milieu d'une phrase,
  notamment `/Users/...`, `/home/...`, `/root/...`, `/opt/...`, `/var/...`,
  `/etc/...`, `/tmp/...`, `~/...` et chemins Windows absolus;
- le refus expose seulement `status=refused`,
  `reason_code=continuity_capsule_unsafe_content`, compteurs et flags raw a
  false;
- le texte refuse ne doit jamais apparaitre dans manifest, projection admin,
  garde writer-side, logs, tests ou artefacts;
- aucun hash stable court n'est calcule sur la capsule.

Provider role et non-souverainete:

- Lot 7.1 conserve `provider_role=system` parce que ce flux utilise deja des
  messages systeme pour plusieurs lanes de contexte tardives;
- la non-souverainete n'est donc pas presentee comme une garantie mecanique du
  provider, mais comme une contrainte produit: capsule desactivee par defaut,
  texte court, clause interne de priorite, bypass sous final lock, aucune
  ecriture identity/memory/summary, projection content-free, rollback simple et
  tests dedies;
- le manifeste doit classer ce message avec
  `logical_roles=["continuity_capsule"]` seulement, jamais avec
  `identity_stable`, `identity_mutable`, `memory` ou `summary`.

## Ordre obligatoire des lots

1. Lot 1 peut specifier ensemble `main_payload_manifest_v1` et Continuity
   Capsule. C'est le role du present contrat.
2. Lot 2 doit livrer et tester `main_payload_manifest_v1` sur le payload final,
   apres toutes les injections tardives.
3. Lot 3 livre la garde writer-side qui empeche les payloads dangereux dans
   l'observabilite.
4. Lots 4 et 5 doivent clarifier les fenetres, summary, memory, staging et
   conflits de lanes.
5. Lot 6 doit prouver la continuite qualitative avec fixtures artificielles,
   sans contenu utilisateur reel.
6. Lot 7 livre une Continuity Capsule runtime bornee si les conditions
   precedentes sont satisfaites.
7. Lot Z ne peut cloturer que si les preuves content-free, tests et docs sont
   coherents, et si chaque finding est clos ou reporte explicitement.

No-go absolu: aucune capsule runtime avant livraison et test de
`main_payload_manifest_v1`. No-go chantier: aucune capsule runtime avant que les
lots 1 a 6 ne soient relus et acceptes.

## Rattachement des findings vivants

| Finding | Apport du present contrat | Statut courant apres lots livres |
| --- | --- | --- |
| P1-CONT-01 | Definit la Continuity Capsule comme surface distincte, courte, non souveraine; Lot 6 prouve une candidate test-only et Lot 7 livre la surface runtime bornee. | Clos Lot 7 par capsule runtime desactivee par defaut/configurable, observable content-free, non souveraine et testee. |
| P1-PAYLOAD-01 | Definit `main_payload_manifest_v1` et en fait le gate avant capsule runtime. | Clos Lot 2 par manifeste runtime content-free du payload final apres injections tardives. |
| P2-SUMMARY-01 | Separe summary et capsule, expose summary comme fenetre Lot 4, et exige que les tests detectent l'aplatissement de voix. | Clos Lot 6 par fixture post-resume summary seul vs capsule candidate. |
| P2-LANES-01 | Etend la continuite aux final response locks et renderers de lanes. | Clos Lot 5 pour le bornage content-free des locks; preuve qualitative pre-runtime couverte par Lot 6. |
| P2-MEMORY-01 | Distingue decision arbiter, memory injectee et contenu reellement vu par le modele. | Clos Lot 4 par fenetre `memory`. |
| P2-WINDOWS-01 | Exige des compteurs separes pour prompt final, memory, hermeneutic node, Biblio et Agenda. | Clos Lot 4 par `windows`. |
| P2-IDENTITY-STAGING-01 | Interdit de confondre staging mutable conversation-scoped et capsule trans-conversation. | Clos Lot 4 par fenetre `identity_staging`. |
| P2-LANE-PROVENANCE-01 | Oblige la separation `provider_role` / `logical_roles` pour les lanes injectees comme `user`. | Clos Lot 2.1 par provenance structuree capturee autour des injections reelles. |
| P2-FINAL-LOCK-POLICY-01 | Oblige un champ de priorite effective des final locks. | Clos Lot 5 par `lane_conflicts` et tests Agenda/Biblio/conflit. |
| P2-NOTES-UI-01 | Exige un statut Notes meme quand la lane est non selectionnee ou non envoyee par le frontend. | Clos Lot 5: backend Notes selection-only visible; frontend courant non branche documente. |
| P2-OBS-WRITER-01 | Definit les flags et interdictions que la garde writer-side devra proteger. | Clos par Lot 3. |
| P3-SOFT-LIMIT-01 | Rend visible la difference soft-limit observee et truncation effective. | Clos Lot 4 par `budgets.prompt`. |
| P3-NOOP-LANES-01 | Exige des no-op observables pour chaque lane connue. | Clos Lot 5 pour Documents/Notes/Exports/Images. |
| P3-DOC-01 | Requalifie la source-of-truth active sans rouvrir les archives identity. | Prepare, non clos. |
| P3-TEST-01 | Pose les criteres des tests qualitatifs artificiels Lot 6. | Clos Lot 6 par fixtures nouvelle conversation, longue conversation, post-resume, sans memoire et lanes non selectionnees. |
| P3-OBS-01 | Dit que le manifeste est necessaire mais pas suffisant pour juger la presence. | Clos Lot 6 par observation qualitative content-free acceptee par la garde writer-side. |
| P3-OFFLINE-PAYLOAD-EXPORT-01 | Encadre les exports/audits locaux: non-runtime, non-bruts, content-free, non committes si artefacts. | Prepare, non clos. |

## Criteres d'acceptation du Lot 2

Le Lot 2 ne sera recevable que si une preuve content-free montre:

- schema `main_payload_manifest_v1`;
- ordre final des messages apres injections tardives;
- roles provider;
- roles logiques;
- presence/absence/no-op de chaque lane connue;
- origins allowlistes;
- budgets, limites et exclusions;
- final response lock present ou absent;
- modele principal appele ou bypass explicite;
- assistant output policy presente ou absente;
- raw flags obligatoires tous faux;
- absence de hash stable naif sur contenu textuel sensible;
- tests/fakes sans provider live;
- aucun contenu brut dans logs, fixtures, commits ou exports.

Statut Lot 2 au 2026-06-22: livre par
`app/observability/main_payload_manifest.py`, emis au stage
`main_payload_manifest` via `chat_turn_logger` depuis `app/core/chat_service.py`
juste avant `run_llm_exchange`, et projete en admin par allowlist de schema
`main_payload_manifest_v1`. Le manifeste couvre aussi le contournement du modele
principal par final response lock avec `main_model_called=false`.

Correctif Lot 2.1 au 2026-06-22: la provenance des lanes Notes, Documents,
Biblio et Adobe est fondee sur des sources structurees capturees autour des
injections reelles, et non sur des marqueurs textuels spoofables. Les roles
`identity_stable` et `identity_mutable` du premier message systeme suivent les
statuts structuraux d'identite.

Tests de reference Lot 2:

- `app/tests/unit/logs/test_main_payload_manifest.py`
- `app/tests/unit/chat/test_chat_workspace_folder_notes_prompt.py`

Limite volontaire: `app/scripts/export_main_prompt_payload.py` reste un outil
offline historique trop riche pour servir de preuve content-free de continuite;
le manifeste runtime le remplace pour ce chantier sans supprimer le script.

## Criteres d'acceptation du Lot 3

Le Lot 3 est recevable seulement si:

- un payload avec `messages`, `prompt`, `content`, `payload`,
  `provider_payload`, `raw`, base64/data URL ou secret est remplace avant
  stockage;
- une valeur URL/token/DAV/XML/ETag/path sensible sous cle allowlistee ne passe
  pas;
- un `status=ok` dangereux ne reste pas un succes normal;
- un `main_payload_manifest_v1` valide passe;
- la projection admin et l'export Markdown ne reexposent aucune sentinelle de
  test.

Statut Lot 3 au 2026-06-22: livre par
`app/observability/observability_payload_guard.py`, branche dans
`app/observability/chat_turn_logger.py` avant l'appel a `log_store`, et teste par
`app/tests/unit/logs/test_observability_payload_guard.py` et
`app/tests/unit/logs/test_chat_turn_logger_core_contract.py`.

Correctif Lot 3.1 au 2026-06-22: la garde est schema-first/default-deny pour les
payloads generaux et pour `main_payload_manifest_v1`. Une cle neutre contenant
une string libre est refusee. Un manifeste forge avec une string libre dans
`budgets.prompt`, `windows.recent_context` ou `runtime_settings` est refuse. Le
manifeste reel produit par `build_main_payload_manifest()` reste accepte s'il
respecte le schema content-free.

Correctif Lot 3.2 au 2026-06-22: la politique default-deny reste en vigueur,
mais les schemas content-free existants doivent rester observables sans bruit de
rejet. `context_build` peut exposer ses compteurs et booleens de soft limit.
`web_search` peut conserver `query_preview=""` comme compatibilite vide, mais
toute valeur non vide de preview doit etre refusee ou remplacee par des
compteurs tels que `query_present` et `query_chars`. Les erreurs doivent
conserver `error_code` et `error_class` content-free; le detail textuel court
`message_short` ne doit pas etre stocke brut et doit etre remplace par longueur
et flags, par exemple `message_short_chars`,
`message_short_included=false` et `raw_error_message_included=false`.
Les anciens champs d'observabilite Web fondes sur URL brute ou hash stable de
requete/prompt/message ne doivent pas etre reenregistres dans l'evenement
writer-side: utiliser domaines, compteurs, `*_hash_included=false`,
`*_url_included=false`, `*_chars` et `*_present`.

Correctif Lot 3.3 au 2026-06-22: les cles textuelles du writer guard doivent
etre explicitement allowlistees. Une cle inconnue ne doit pas etre acceptee
simplement parce qu'elle se termine par un suffixe safe-code tel que `_code`,
`_reason`, `_status`, `_mode` ou `_requested`. Les familles legitimes doivent
etre ajoutees comme cles explicites ou schemas bornes.

Correctif Lot 4.1 au 2026-06-22: la garde reste schema-first/default-deny, mais
les schemas content-free existants exposes par Lot 4 doivent etre acceptes sans
bruit de rejet: `prompt_prepared`, `hermeneutic_node_insertion`,
`validation_agent`, `stimmung_agent`, Biblio, Agenda, summaries et `llm_call`.
Les champs bruts residuels de ces payloads doivent etre remplaces par presence,
longueur, domaine, compteurs, reason codes et flags `*_included=false`.
Exemples interdits: `arbiter_reason` brut, URL explicite brute, prompt/message
ou provider payload. Exemples autorises: `arbiter_reason_present`,
`arbiter_reason_chars`, `arbiter_reason_included=false`, `source_domain`,
`url_present`, `url_chars`, `url_included=false`.

Correctif Lot 4.2 au 2026-06-22: `hermeneutic_prompt_injection` ne doit pas
contenir de `sha256_12` calcule sur le bloc hermeneutique injecte dans le
prompt. Le payload doit conserver les compteurs utiles (`present`, `chars`,
posture, regime, source, reason codes) et declarer l'absence d'empreinte par
des flags tels que `fingerprint_present=false`, `fingerprint_included=false`,
`prompt_block_hash_included=false` et `raw_content_included=false`. La garde
writer-side doit refuser une valeur renseignee sous cle generique `sha256_12`;
seules des cles qualifiees, explicitement justifiees et non contradictoires avec
cette politique peuvent rester hors scope de ce correctif. Les placeholders
vides historiques ne doivent pas creer de bruit de rejet.

## No-go et gardes runtime capsule

Une Continuity Capsule runtime etait interdite tant que toutes les conditions
suivantes n'etaient pas remplies; Lot 7 ne peut rester valide que si ces gardes
continuent a etre respectees:

- `main_payload_manifest_v1` livre et teste;
- garde writer-side anti-fuite livree;
- fenetres memory/summary/hermeneutic/lane documentees par preuve content-free;
- politique de final locks clarifiee;
- Notes, Documents, Biblio, Agenda, Web et Adobe representes dans le manifeste;
- tests qualitatifs artificiels nouvelle conversation vs conversation longue;
- separation doctrinale identity/memory/summary/capsule relue;
- rollback et feature flag definis;
- aucun contenu utilisateur reel utilise pour imiter le ton.

Gardes Lot 7 actives:

- capsule desactivee par defaut;
- activation par config/env sans DB, migration, purge ou backfill;
- refus propre si texte absent ou trop long;
- refus propre si le texte contient URL, credentials/token-like, data
  URL/base64, XML/DAV/CALDAV/WebDAV, chemin prive/absolu ou bloc de cle privee;
- aucune injection sous final response lock;
- aucune ecriture identity mutable ou memory;
- aucune projection du contenu de capsule dans manifest, admin logs ou tests;
- aucun hash stable court de capsule.

## Limites assumees

Ce contrat reste normatif jusqu'a Lot Z. Depuis les Lots 2 a 7, le payload
runtime courant est prouve par un manifeste content-free borne, protege par une
garde writer-side, enrichi par les fenetres/locks/lanes, et dispose d'une
Continuity Capsule runtime bornee. Les limites restantes portent sur la
validation Lot Z, la relecture globale des docs/tests et les findings
explicitement encore ouverts ou reportables post-V1.
