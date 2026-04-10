# Memory RAG Relevance - baseline Phase 0 - 2026-04-10

Statut: reference active
Classement: `app/docs/states/baselines/`
Portee: baseline read-only du retrieval memoire actuel avant tout lot V2
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`

## 1. Objet

Cette baseline ferme la Phase 0 du chantier `memory-rag-relevance`.

Elle fige:
- un corpus canonique de probes;
- une taxonomy simple et stable de faux positifs;
- un snapshot exploitable du retrieval actuel;
- un verdict borne sur ce que la Phase 0 permet deja de conclure.

Elle ne lance pas:
- de patch runtime;
- de changement de recall;
- de redesign de l'arbitre;
- de lot `summaries`;
- de decision reranker.

## 2. Methodologie

Sources et methode retenues:
- runtime OVH actif, en lecture seule;
- vrai chemin de retrieval via `memory_store.retrieve(query)`;
- vrai enrichissement aval via `memory_store.enrich_traces_with_summaries(rows)`;
- aucune modification de settings;
- aucune ecriture metier;
- aucune generation de bruit volontaire dans l'observabilite live.

Mesure anti-pollution appliquee pour les probes:
- dans le process Python de probe uniquement, `observability.chat_turn_logger.emit` a ete no-op pour ne pas emettre d'evenements `memory_retrieve` parasites;
- le retrieval lui-meme est reste le retrieval runtime reel.

Limites assumees:
- `summaries=0` sur le runtime actif, donc aucune evaluation live de la voie `summaries` n'est possible a cette date;
- `arbiter_decisions` peut servir de baseline historique complementaire, mais pas de substitut au corpus canonique car il ne porte pas l'intention initiale des probes.

## 3. Snapshot runtime et DB

Constats figes pour cette baseline:
- `MEMORY_TOP_K=5`
- `ARBITER_MAX_KEPT_TRACES=3`
- `ARBITER_MIN_SEMANTIC_RELEVANCE=0.62`
- `ARBITER_MIN_CONTEXTUAL_GAIN=0.55`
- `traces=224` dont `224` avec `embedding IS NOT NULL`
- `summaries=0` dont `0` avec `embedding IS NOT NULL`
- `traces_with_summary_id=0`
- repartition `traces`: `assistant=112`, `user=112`
- `arbiter_decisions=551` dont `32` keep et `519` reject

Consequences directes pour la baseline:
- le retrieval live interroge `traces` seulement;
- tous les probes de cette phase reviennent sans `summary_id`;
- tous les probes de cette phase reviennent sans `parent_summary`.

## 4. Corpus canonique de probes

Le corpus retenu contient `6` probes. Il couvre les cinq familles minimales demandees et ajoute un probe de stress sur la saturation identitaire par doublons exacts.

### Probe 1 - architecture / modules externes

- Formulation exacte: `architecture modules externes arbiter STT TTS`
- Raison: verifier si le retrieval retrouve des souvenirs techniques de structure applicative et de modules externes, plutot que des reponses assistant generiques.
- Type de souvenir attendu: architecture produit, frontieres de modules, references a l'arbitre, STT/TTS, web tools, embeddings, services externes.
- Faux positifs typiques: assistant generique, item procedural, item stale hors axe, contenu OVH trop large sans information modulaire.
- Resultat acceptable: la majorite du top-k nomme des composants ou interfaces techniques utiles au chantier.
- Resultat mauvais: le top-k est surtout compose de reponses assistant vagues, de meta-discours ou de traces sans granularite modulaire.

### Probe 2 - memoire / identite durable

- Formulation exacte: `memoire identite durable episodique utilisateur`
- Raison: verifier si la memoire remonte des faits durables sur l'utilisateur ou sa relation a Frida, au lieu de capter des traces lexicalement proches mais semantiquement plates.
- Type de souvenir attendu: identite durable, recurrence utilisateur, faits memorisables sur le sujet, distinction durable vs episodique.
- Faux positifs typiques: duplication exacte, quasi-doublon, item lexicalement voisin mais plat, assistant procedural.
- Resultat acceptable: au moins une partie du top-k contient des traces sur l'identite utilisateur ou des faits durables.
- Resultat mauvais: le top-k est sature par des questions scolaires ou techniques sans rapport avec l'identite durable.

### Probe 3 - OVH / migration / exploitation

- Formulation exacte: `OVH migration Authelia Caddy Docker`
- Raison: verifier si le retrieval retrouve la memoire d'exploitation OVH et les briques de plateforme vraiment utiles au contexte FridaDev.
- Type de souvenir attendu: migration OVH, stack Docker, Authelia, Caddy, contraintes d'exploitation.
- Faux positifs typiques: item parasite court, assistant generique, salutations, validation trop vague sans contenu operatoire.
- Resultat acceptable: le top-k contient surtout des traces parlant explicitement de la migration OVH et des services cites.
- Resultat mauvais: un item parasite ou des generalites prennent la tete du recall et les items operatoires sont repousses.

### Probe 4 - preferences utilisateur durables

- Formulation exacte: `preferences utilisateur durables style reponse`
- Raison: verifier si le retrieval distingue une preference durable de style d'une instruction locale ou d'un test de sante ponctuel.
- Type de souvenir attendu: preferences de ton, longueur, simplicite, niveau de detail, style de reponse durable.
- Faux positifs typiques: instruction circonstancielle, item lexicalement voisin, quasi-doublon, plainte contextuelle hors preference.
- Resultat acceptable: le top-k contient des instructions de style stables ou repetitives et pas seulement des demandes ponctuelles.
- Resultat mauvais: le top-k melange tests de sante, items didactiques generiques et contextes sans valeur durable.

### Probe 5 - contexte circonstanciel recent

- Formulation exacte: `contexte circonstanciel recent ce soir fatigue`
- Raison: verifier si le retrieval remonte du contexte recent et utile, sans se perdre dans du contenu voisin mais hors axe.
- Type de souvenir attendu: contexte recent, etat du moment, temporalite proche, signaux de fatigue ou de circonstance immediate.
- Faux positifs typiques: item de presse hors axe, assistant generique, contenu de contexte large sans mention de l'etat vise.
- Resultat acceptable: le top-k contient des traces recentes utiles au tour en cours ou a la circonstance immediate.
- Resultat mauvais: le top-k remonte surtout des discussions de presse ou de contexte macro.

### Probe 6 - stress test identite durable par doublons exacts

- Formulation exacte: `qui suis-je pour toi maintenant identite durable`
- Raison: verifier si le panier brut se laisse saturer par des doublons exacts sur une requete identitaire pourtant legitime.
- Type de souvenir attendu: identite durable utilisateur, relation memorisee, reponse identitaire deja stabilisee.
- Faux positifs typiques: duplication exacte, quasi-doublon, assistant trop bavard, saturation mono-conversation.
- Resultat acceptable: un faible nombre d'items identitaires vraiment distincts occupe le top-k.
- Resultat mauvais: plusieurs copies du meme item absorbent l'essentiel du recall.

## 5. Taxonomy simple et stable des faux positifs

Cette taxonomy est retenue comme base de comparaison pour les lots suivants.

- `assistant generique`: reponse assistant large, polie ou meta, avec peu de valeur memoire exploitable.
- `duplication exacte`: meme contenu texte present plusieurs fois et captant plusieurs places du top-k.
- `quasi-doublon`: meme idee ou meme famille d'item, avec variation mineure de formulation.
- `item circonstanciel sans utilite`: trace liee a un moment local, mais qui n'aide pas la question actuelle.
- `item lexicalement voisin mais semantiquement plat`: partage des mots avec la query sans apporter le souvenir attendu.
- `item stale / procedural / hors axe`: contenu perime, purement procedural, ou tourne autour du sujet sans porter l'information utile.

## 6. Baseline observee par probe

Convention:
- `summary_id`: `none` signifie absent;
- `parent_summary`: `no` signifie absent;
- `apercu`: extrait court du contenu reel observe;
- tous les probes ont retourne `5` items.

### Probe 1 - `architecture modules externes arbiter STT TTS`

Observation synthetique:
- roles: `assistant=5`, `user=0`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: composition trop plate, pas manque clair de profondeur de recall

Top-k observe:
- `#1` assistant `0.836838` | `summary_id=none` | `parent_summary=no` | apercu: `Je ne peux pas identifier ce que tu attends a partir de la seule chaine codex-8192-live-1775296899...`
- `#2` assistant `0.833704` | `summary_id=none` | `parent_summary=no` | apercu: `Tu touches un point tres concret... Frida n'est plus hebergee chez toi...`
- `#3` assistant `0.832845` | `summary_id=none` | `parent_summary=no` | apercu: `Je vais repondre en restant dans le cadre que tu poses...`
- `#4` assistant `0.827785` | `summary_id=none` | `parent_summary=no` | apercu: `DB, embedding et web tools sont verifies cote OVH...`
- `#5` assistant `0.827381` | `summary_id=none` | `parent_summary=no` | apercu: `Je peux reformuler ta demande en requete de recherche...`

Lecture:
- un seul item du top-k touche directement un souvenir modulaire utile;
- le recall favorise des reponses assistant generiques et procedurales;
- `top_k=5` ne semble pas trop court ici: le probleme principal est la composition.

### Probe 2 - `memoire identite durable episodique utilisateur`

Observation synthetique:
- roles: `user=4`, `assistant=1`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: duplication exacte et quasi-doublons sur une question scolaire hors cible

Top-k observe:
- `#1` user `0.868279` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`
- `#2` user `0.861034` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`
- `#3` user `0.861034` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`
- `#4` user `0.861034` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`
- `#5` assistant `0.842576` | `summary_id=none` | `parent_summary=no` | apercu: `Je peux reformuler ta demande en requete de recherche...`

Lecture:
- la query active surtout une proximite lexicale autour du mot `memoire`;
- aucun souvenir identitaire ou durable utile n'entre dans le top-k;
- le probleme principal est la composition, pas la seule taille du recall.

### Probe 3 - `OVH migration Authelia Caddy Docker`

Observation synthetique:
- roles: `user=1`, `assistant=4`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: recall parasite et trop plat

Top-k observe:
- `#1` user `0.816378` | `summary_id=none` | `parent_summary=no` | apercu: `codex-8192-live-1775296899`
- `#2` assistant `0.814624` | `summary_id=none` | `parent_summary=no` | apercu: `DB, embedding et web tools sont verifies cote OVH...`
- `#3` assistant `0.813497` | `summary_id=none` | `parent_summary=no` | apercu: `VALIDATIONFRIDADEVOVHFINAL20260407...`
- `#4` assistant `0.807235` | `summary_id=none` | `parent_summary=no` | apercu: `Salut Tof... Tu veux bosser sur quoi aujourd'hui ?`
- `#5` assistant `0.803728` | `summary_id=none` | `parent_summary=no` | apercu: `Frida n'est plus hebergee chez toi...`

Lecture:
- un item parasite ultra-court prend la premiere place;
- les items OVH existent, mais ils sont melanges a des generalites et salutations;
- `top_k=5` n'est pas le probleme primaire: la composition est trop bruitee.

### Probe 4 - `preferences utilisateur durables style reponse`

Observation synthetique:
- roles: `user=5`, `assistant=0`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: confusion entre preference durable et instruction ponctuelle

Top-k observe:
- `#1` user `0.855255` | `summary_id=none` | `parent_summary=no` | apercu: `Test de sante minimal. Reponds en une phrase courte.`
- `#2` user `0.850597` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`
- `#3` user `0.850566` | `summary_id=none` | `parent_summary=no` | apercu: `Tu as aussi recupere le temps qui s'ecoule`
- `#4` user `0.849895` | `summary_id=none` | `parent_summary=no` | apercu: `Ce qui est triste c'est que mon systeme de recherche web ne fonctionne pas bien...`
- `#5` user `0.848879` | `summary_id=none` | `parent_summary=no` | apercu: `Explique simplement la difference entre la memoire vive et le disque dur.`

Lecture:
- le top-k trouve des formulations proches du champ lexical `style/reponse`, mais pas des preferences durables fiables;
- les instructions ponctuelles dominent;
- `top_k=5` ne semble pas trop court tant que la composition reste aussi plate.

### Probe 5 - `contexte circonstanciel recent ce soir fatigue`

Observation synthetique:
- roles: `assistant=4`, `user=1`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: contenu circonstanciel hors axe et voisinage semantique trop large

Top-k observe:
- `#1` assistant `0.858267` | `summary_id=none` | `parent_summary=no` | apercu: `Lecture politique de la guerre Iran/Etats-Unis/Israel telle qu'elle apparait dans ce moment de presse...`
- `#2` assistant `0.847265` | `summary_id=none` | `parent_summary=no` | apercu: `Tu me donnes un paquet d'acces presse comme si j'ouvrais le kiosque du jour...`
- `#3` assistant `0.842847` | `summary_id=none` | `parent_summary=no` | apercu: `Il s'est ecoule un peu plus de 2 heures entre mon dernier message et votre question actuelle.`
- `#4` assistant `0.842620` | `summary_id=none` | `parent_summary=no` | apercu: `Tu es en fin d'apres-midi qui bascule vers le debut de soiree...`
- `#5` user `0.842581` | `summary_id=none` | `parent_summary=no` | apercu: `Il te faut du contexte pour comprendre. Tu veux bien regarder la presse du jour ?`

Lecture:
- quelques items portent bien une temporalite recente, mais le coeur du top-k reste tire vers la presse plutot que vers l'etat circonstanciel vise;
- le recall montre un voisinage semantique large plutot qu'une voie specialisee;
- `top_k=5` ne semble pas le frein principal.

### Probe 6 - `qui suis-je pour toi maintenant identite durable`

Observation synthetique:
- roles: `user=4`, `assistant=1`
- `summary_id`: `0/5`
- `parent_summary`: `0/5`
- probleme dominant: saturation par duplication exacte

Top-k observe:
- `#1` user `0.878721` | `summary_id=none` | `parent_summary=no` | apercu: `Qui suis-je pour toi maintenant ?`
- `#2` user `0.878721` | `summary_id=none` | `parent_summary=no` | apercu: `Qui suis-je pour toi maintenant ?`
- `#3` user `0.878721` | `summary_id=none` | `parent_summary=no` | apercu: `Qui suis-je pour toi maintenant ?`
- `#4` user `0.878721` | `summary_id=none` | `parent_summary=no` | apercu: `Qui suis-je pour toi maintenant ?`
- `#5` assistant `0.873942` | `summary_id=none` | `parent_summary=no` | apercu: `Tu es, pour moi maintenant, quelqu'un qui se presente comme Christophe Muck...`

Lecture:
- ce probe confirme qu'un top-k plat peut etre sature par des doublons exacts;
- le premier vrai item de reponse identitaire utile n'arrive qu'en cinquieme position;
- `top_k=5` pourra etre reevalue apres dedup, mais le probleme primaire actuel reste la composition du panier brut.

## 7. Doublons exacts confirmes en base

Exemples confirmes en lecture SQL exacte:
- `Je suis Christophe Muck` -> `6`
- `Tu peux le trouver et le lire là : https://blogs.mediapart.fr/christophe-muck/blog/030426/apres-la-garde-vue-de-rima-hassan-ce-que-l-occident-refuse-de-voir` -> `6`
- `Bonsoir Frida` -> `5`
- `Qui suis-je ?` -> `5`
- `Qui suis-je pour toi maintenant ?` -> `4`
- `Explique simplement la différence entre la mémoire vive et le disque dur.` -> `3`

Utilite pour la suite:
- ces doublons confirment qu'un futur lot de panier devra traiter la dedup comme un sujet central;
- ils expliquent deja une partie du bruit observe dans les probes identitaires et `memoire`.

## 8. Ce que dit la baseline sur `top_k=5`

Constat borne a cette phase:
- aucun probe ne prouve que `top_k=5` est le probleme principal du systeme actuel;
- tous les probes montrent au moins un probleme de composition du recall avant meme qu'un manque de profondeur devienne la cause dominante;
- le probe `qui suis-je pour toi maintenant identite durable` montre toutefois qu'une reevaluation de `top_k` redeviendra utile apres dedup, car quatre places sont occupees par le meme item.

Decision de Phase 0:
- probes ou `top_k=5` parait trop court comme probleme primaire: aucun, a ce stade;
- probes ou la composition du recall est le probleme primaire: les six probes du corpus.

## 9. Ce que `arbiter_decisions` apporte deja

Lecture read-only complementaire utile:
- les lignes recentes de `arbiter_decisions` montrent deja des motifs `duplicate`, `procedural`, `redundant with recent`, `context-specific and not useful`;
- cette couche confirme que plusieurs faux positifs identifies ici existent deja dans le panier vu par l'arbitre.

Limite:
- `arbiter_decisions` reste une source aval, post-selection, sans corpus canonique de questions;
- elle peut donc completer la baseline, pas la remplacer.

## 10. Verdict de cloture Phase 0

La Phase 0 est fermable proprement au `2026-04-10` car:
- le corpus canonique de probes est fige;
- la taxonomy de faux positifs est ecrite;
- un snapshot reutilisable existe pour chaque probe;
- la baseline est datee et rangee dans `states/baselines/`;
- aucun choix d'implementation retrieval/RAG n'a encore ete engage.

Ce que la Phase 0 tranche deja:
- le retrieval live actuel est trop plat et trop sensible aux doublons;
- la voie `summaries` est hors evaluation live tant que `summaries=0`;
- le prochain travail doit porter sur la composition du panier avant tout debat reranker.
