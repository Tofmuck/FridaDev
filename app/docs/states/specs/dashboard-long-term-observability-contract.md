# Dashboard Long Term Observability Contract

Statut: spec vivante
Source: Lot 1 du chantier `app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md`
Date: 2026-05-15
Portee: contrat fondateur du futur dashboard long terme FridaDev
Hors-scope: implementation backend/frontend, schema SQL final, migration, backfill, endpoints, stockage de contenu, rebuild

## 1. But

Ce contrat fixe la promesse produit du futur dashboard long terme avant toute implementation.

Le dashboard doit permettre deux lectures distinctes:

1. une lecture humaine par defaut, claire, traduite et intelligible pour un non-technicien;
2. la capacite de comprendre vraiment ce que le modele a recu, puis d'ouvrir volontairement le contenu complet sur demande explicite.

Regle forte:

> Le dashboard ne doit jamais pretendre comprendre le contexte modele si la seule preuve disponible est `present=true`, une longueur, un hash ou un count.

Les hashes, longueurs et empreintes prouvent l'existence, la taille et la stabilite d'un bloc. Ils ne prouvent pas son sens.

## 2. Validation de l'etat courant

### Ce que les logs actuels prouvent deja

Les logs compacts et read-models actuels prouvent correctement:

- qu'un tour existe dans `observability.chat_log_events`;
- quels stages ont ete observes;
- les statuts `ok`, `skipped`, `error`;
- des durees, counts, timestamps, modeles et provider callers;
- la presence de `prompt_prepared`;
- la presence et la taille des blocs identity, memory, hermeneutic et web quand les fingerprints existent;
- la presence d'un `llm_call[provider_caller=llm]`;
- la separation entre provider principal et providers secondaires;
- la persistence assistant finale via `persist_response.persist_phase=assistant_final`;
- la chaine RAG compacte via `memory_chain_snapshot` quand elle existe;
- les statuts compacts du `node_state`;
- les erreurs, skips, fallbacks et reason codes compacts;
- l'absence de payload brut dans les projections cockpit existantes.

Ces preuves sont utiles pour la sante systeme et la supervision.

### Ce que les logs actuels permettent seulement d'inferer

Les logs actuels permettent d'inferer:

- qu'un bloc identite, memoire ou hermeneutique a probablement atteint le prompt final;
- qu'un certain nombre d'elements memoire ont ete retrouves, gardes, rejetes ou injectes;
- qu'une recherche web a ete demandee, ignoree, reussie ou injectee;
- qu'un provider secondaire a ete prepare ou appele;
- que le prompt avait une certaine taille estimee.

Ces inferences doivent rester etiquetees comme inferences de forme ou de pipeline. Elles ne doivent pas etre presentees comme une comprehension substantielle du contenu.

### Ce que l'etat courant ne reconstruit pas

L'etat courant ne permet pas de reconstruire fidelement, a lui seul:

- le prompt principal exact recu par le modele;
- le payload complet du modele principal;
- les payloads complets des providers secondaires;
- le texte exact des blocs memory, identity, hermeneutic ou web injectes;
- le sens substantiel porte par un bloc au-dela de sa presence, de sa taille et de son hash;
- ce qui a ete transforme, resume ou exclu avant l'appel modele;
- le contenu exact d'une query web, de resultats web ou d'un contexte lu;
- la totalite des decisions de prompt quand seuls des counters ou hashes sont presents.

Conclusion normative:

- l'audit initial et les lots `/log` ont correctement stabilise une lecture compacte recente;
- ils ne suffisent pas a tenir seuls la promesse "comprendre vraiment ce que le modele a recu";
- toute implementation future doit ajouter des faits, references ou contenus gates lorsque cette comprehension fidele est requise.

## 3. Les quatre niveaux de lecture

### Niveau 1 - Lecture cockpit

But: donner le pouls du systeme sans jargon.

Exemples de lectures autorisees:

- Tours reussis;
- Reponses degradees;
- Memoire utilisee;
- Recherche web utile;
- Problemes rencontres;
- Latence inhabituelle;
- Conversation a inspecter.

Ce niveau est toujours content-free. Il ne doit jamais afficher prompt, message, identity brute, memoire brute, web query brute ou payload fournisseur.

### Niveau 2 - Lecture traduite conversation / tour

But: expliquer ce qui s'est passe en francais clair.

Exemples:

- La memoire a trouve 8 elements, en a garde 3, en a injecte 2.
- Le modele principal a recu un bloc identite, un bloc memoire et un jugement hermeneutique.
- 25 embeddings ont ete demandes, 25 ont reussi.
- La recherche web a ete demandee mais aucun contenu lisible n'a ete injecte.
- Le node_state hermeneutique a ete relu et mis a jour.

Ce niveau peut utiliser:

- counts;
- statuts;
- reason codes traduits;
- source kinds;
- timestamps;
- latences;
- hashes courts;
- longueurs;
- references d'artefacts non affichees.

Ce niveau ne doit pas dire que le contenu est compris si seuls count/hash/length existent.

### Niveau 3 - Comprehension fidele de ce que le modele a recu

But: permettre a un humain de comprendre le contexte effectif du modele sans ouvrir automatiquement tout le brut.

Ce niveau doit expliquer:

- quels blocs ont compose le contexte effectif;
- de quelles sources ils venaient;
- quelle information substantielle ils portaient;
- ce qui a ete inclus;
- ce qui a ete exclu;
- ce qui a ete transforme, resume, tronque ou reformule avant l'appel modele;
- quels blocs sont des preuves exactes, quels blocs sont des resumes et quels blocs sont des inferences.

Ce niveau ne peut pas etre reduit a:

- `chars`;
- `sha256_12`;
- `present=true`;
- `injected=true`;
- `messages_count`;
- `estimated_prompt_tokens`;
- `source_kind`;
- autres seules metadonnees compactes.

Champs ou faits futurs necessaires:

- manifeste de composition du prompt, avec ordre des blocs, role et source;
- references stables vers les contenus sources ou artefacts gates;
- resume humain de chaque bloc, genere ou derive de facon auditable;
- liste des inclusions et exclusions par module;
- trace de transformation: brut source -> resume -> bloc injecte -> payload modele;
- indication explicite des parties non reconstructibles;
- version de calcul du resume humain;
- lien vers les events sources;
- lien vers le contenu complet gate quand disponible.

Si un bloc ne possede qu'un hash et une longueur, l'UI doit dire par exemple:

- "Bloc observe, contenu non reconstructible depuis les donnees compactes actuelles."

Elle ne doit pas dire:

- "Le dashboard sait ce que contenait ce bloc."

### Niveau 4 - Contenu complet volontaire

Le besoin d'acces au contenu complet est confirme. Il n'est pas optionnel.

Le contenu complet doit etre accessible uniquement par une action volontaire, par exemple:

- `Afficher le contenu complet`.

Regles:

- aucun contenu complet n'est affiche par defaut;
- aucun contenu complet n'est precharge dans le DOM par commodite;
- l'action est explicite et visible;
- l'acces est garde cote frontend et backend;
- l'action est idealement auditee sans contenu brut dans l'audit;
- l'UI affiche une indication claire de sensibilite avant ouverture;
- le contenu complet reste separe de la lecture cockpit;
- l'absence de contenu complet disponible doit etre indiquee franchement.

Classes de contenu complet a distinguer:

- prompt principal;
- payload modele principal;
- payloads providers secondaires;
- contenu memoire;
- identity;
- web;
- node_state si un futur detail textuel existe;
- documents;
- images;
- autres modules futurs.

## 4. Couches de verite

Le dashboard long terme repose sur quatre couches distinctes.

### Logs compacts

Role: verite evenementielle detaillee.

Source actuelle principale:

- `observability.chat_log_events`.

Utilisation:

- debug technique;
- preuve de sequence;
- preuve de statut;
- source de materialisation;
- lien vers l'evenement source.

Limite:

- les logs compacts ne doivent pas devenir une source de comprehension substantielle quand ils ne portent que des fingerprints.

### Agregats persistants

Role: verite analytique longue periode.

Utilisation:

- fenetres 24 h / 7 j / 30 j / 90 jours;
- courbes;
- tendances;
- comparaisons conversationnelles;
- p50 / p95;
- taux de degradation;
- erreurs par module.

Limite:

- les agregats ne stockent pas de contenu brut;
- les courbes longues ne doivent jamais etre calculees depuis un simple `event_limit=2000`.

### Read-models humains

Role: traduction operateur.

Utilisation:

- lecture cockpit;
- explication par conversation;
- explication par tour;
- resume humain par module;
- etats et causes probables.

Limite:

- ils doivent indiquer leurs sources et leurs limites;
- ils ne doivent pas masquer une absence de preuve substantielle.

### Contenu complet gate

Role: preuve textuelle ou media ouverte volontairement.

Utilisation:

- inspection fine;
- comprehension exacte du prompt ou payload;
- comparaison entre source, transformation et injection.

Limite:

- jamais charge par defaut;
- jamais inclus dans les agregats;
- jamais expose dans les vues cockpit;
- acces explicite et garde.

## 5. Matrice sources -> champs -> vues -> gate eventuel

Cette matrice rend explicite la frontiere entre:

- les sources disponibles ou a creer;
- les champs exposables par defaut;
- les vues qui peuvent les consommer;
- les contenus qui exigent l'action `Afficher le contenu complet`.

| Source | Champs exposables par defaut | Vues consommatrices | Gate `Afficher le contenu complet` |
| --- | --- | --- | --- |
| `observability.chat_log_events` | `conversation_id`, `turn_id`, timestamps, stage, status, duration, provider caller, model name, counts, reason codes, hashes, longueurs, truncation flags, event id. | `/log`, dashboard overview, inspection technique liee a un tour, materialisation future. | Tout prompt, message, payload brut, query web, contenu memoire, identity brute, resultat web ou texte libre absent des logs compacts actuels mais reference par artefact futur. |
| `turn_pipeline_read_model` | classification, score/checklist compact, persistence assistant finale, provider principal, providers secondaires, RAG compact, identity status, hermeneutic status, web status, node_state status, errors/fallbacks, source_kind, events_truncated. | Dashboard premier ecran, table conversations/tours, `/log` compact, inspection traduite de tour. | Aucun contenu brut dans les champs actuels; seuls des liens futurs vers artefacts de prompt/payload/blocs peuvent ouvrir le gate. |
| `full_turn_metrics_snapshot` | statuts, timings, provider lanes, counts, persistence finale, erreurs/skips/fallbacks, version de calcul si disponible. | Courbes recentes/long terme apres materialisation, synthese tour, comparaison conversations. | Aucun contenu complet; les champs analytiques restent content-free. |
| `turn_observability_checklist` | checklist, score de completude, checks presents/absents, reason codes compacts, statut legacy/incomplet. | Classification cockpit, explication courte d'un tour, tests de materialisation. | Aucun contenu complet; si un check pointe vers un bloc textuel, seul l'artefact gate futur peut l'ouvrir. |
| `memory_chain_snapshot` | retrieved, basket, kept, rejected, injected, context hints, source/status, candidate ids hashes, timings, errors compacts. | Module memory du dashboard, Memory Admin, inspection traduite RAG, courbes funnel memoire. | Contenu exact des souvenirs, traces, summaries, bloc memoire injecte et transformations vers le prompt. |
| Read-models Memory Admin | embeddings count, dimensions, couverture, erreurs, latest update, provenance, health compact, counts durables/historiques. | Memory Admin, module memory du dashboard, diagnostic compact embeddings. | Extraits de trace, summaries, textes de souvenirs, payloads de retrieval ou arbitration. |
| Identity observability / read-models diagnostic | bloc present, `chars`, `sha256_12`, statut, subject, reason_code, counts de conflits, longueurs et hashes de raisons libres. | Module identity du dashboard, Identity pilotage compact, Hermeneutic Admin diagnostic. | Contenu identity exact injecte, raisons libres brutes, conflits bruts; l'edition canonique explicite reste une surface separee, pas une vue cockpit. |
| Hermeneutic node observability | mode, regime, directives_count, node_state read/write status, fail-open/fallback, `chars`, `sha256_12`, timings, errors compacts. | Module hermeneutic du dashboard, Hermeneutic Admin diagnostic, inspection traduite de tour. | Jugement hermeneutique textuel exact, runtime replies longues, payloads de stage, bloc injecte complet. |
| Web/search observability | requested/skipped/success/error, injected, counts, timings, reason_code, provider/status compact. | Module web du dashboard, `/log`, inspection traduite de tour, courbes web utile. | Query brute, resultats web bruts, extraits injectes, payloads de reformulation. |
| Provider observability | provider_caller, provider principal/secondaire, model, status, duration, response_chars, prepared event present/absent, error code compact. | Module providers du dashboard, table tours, latences p50/p95 par provider. | Payload complet envoye au provider, reponse complete, prompts secondaires et contenus produits par agents secondaires. |
| Agregats persistants futurs | buckets horaires/journaliers, counts, rates, p50/p95, materialization status, calculation_version, source window, lag. | Courbes 24 h / 7 j / 30 j / 90 jours, pouls global, comparaison conversations. | Aucun contenu complet; les agregats ne doivent jamais contenir de brut. |
| Artefacts gates futurs | disponibilite, type de contenu, classe de sensibilite, source event id, taille, hash, retention, audit id d'ouverture. | Bouton `Afficher le contenu complet`, inspection volontaire conversation/tour/module. | Le contenu lui-meme: prompt principal, payload modele principal, payloads providers secondaires, memoire, identity, web, documents, images et modules futurs. |

Regles de lecture:

- une vue cockpit ne consomme que les champs exposables par defaut;
- une vue d'inspection traduite peut consommer des resumes humains et references d'artefacts, mais pas precharger le contenu complet;
- une vue debug technique peut afficher des ids, stages et reason codes, mais pas de contenu brut hors gate;
- un champ libre, une query, un prompt, un message, une identity brute ou un contenu memoire ne devient jamais exposable par defaut parce qu'il est utile au diagnostic;
- si une source ne porte que `chars` et `hash`, la vue doit dire que le contenu exact n'est pas reconstructible depuis cette source.

## 6. Faits et agregats a definir

Ce contrat fixe les familles de faits necessaires. Le Lot 2 livre un premier schema analytique persistant v1, encore sans frontend ni endpoints dashboard.

Implementation v1:

- facade publique: `app/observability/dashboard_analytics.py`;
- projection pure: `app/observability/dashboard_analytics_projection.py`;
- stockage / materialisation: `app/observability/dashboard_analytics_storage.py`;
- bootstrap DB: `log_store.init_log_storage()` cree aussi les tables analytiques;
- materialiseur: `materialize_dashboard_analytics_window()`;
- version de calcul: `dashboard_analytics_v1`;
- retention cible: 90 jours;
- granularite recente: buckets horaires pour les 30 derniers jours;
- granularite ancienne: buckets journaliers jusqu'a 90 jours;
- aucune dependance a `event_limit`;
- aucun backfill massif automatique;
- aucun contenu brut stocke dans les facts, syntheses ou buckets.

Tables persistantes v1:

- `observability.dashboard_turn_facts`;
- `observability.dashboard_conversation_summaries`;
- `observability.dashboard_metric_buckets`;
- `observability.dashboard_materialization_status`.

Ces tables sont un socle analytique, pas une nouvelle source de contenu complet. Elles gardent des liens vers les logs sources et des references content-free, mais le besoin "comprendre vraiment ce que le modele a recu" reste rattache aux futurs manifestes et artefacts gates.

Doctrine de materialisation v1:

- une fenetre de materialisation selectionne les tours touches, puis relit tous les events de ces tours afin de ne pas remplacer un fact complet par un fact tronque;
- les `dashboard_turn_facts` peuvent etre mis a jour pour une fenetre arbitraire;
- les `dashboard_conversation_summaries` ne sont jamais reconstruites depuis la seule petite fenetre courante: elles sont regenerees depuis les facts deja persistants des conversations touchees;
- les `dashboard_metric_buckets` ne sont jamais remplaces par les seuls facts d'une sous-fenetre: les buckets affectes sont regenerees depuis tous les facts persistants du bucket complet;
- une materialisation 24 h ou intrajournaliere ne doit donc pas faire regresser des syntheses ou buckets deja materialises sur une fenetre plus large;
- si aucune materialisation large n'existe encore, la petite fenetre produit seulement le meilleur etat connu depuis les facts persistants disponibles, sans pretendre couvrir l'horizon long complet.

### Faits par tour

Chaque fait par tour devra porter au minimum:

- conversation_id;
- turn_id;
- timestamps debut / fin / derniere observation;
- classification globale;
- score ou statut de completude;
- persistence assistant finale;
- provider principal;
- providers secondaires;
- RAG;
- identity;
- hermeneutic;
- web;
- node_state;
- erreurs, skips et fallbacks;
- latences;
- flags legacy / truncation / source incomplete;
- liens vers events sources;
- version de calcul.

Le Lot 2 persiste ces facts dans `dashboard_turn_facts` avec:

- cle `(conversation_id, turn_id)`;
- `source_event_ids`, `source_first_event_id`, `source_latest_event_id`;
- JSON compacts par module: persistence, providers, RAG, identity, hermeneutic, web, node_state, latencies, errors, stage_counts;
- `content_availability_json` indiquant explicitement que le contenu complet et le manifeste de prompt ne sont pas encore materialises;
- `raw_event_payloads_included = false` impose par contrainte SQL.

Pour la comprehension fidele, il devra aussi pouvoir porter ou referencer:

- manifeste de composition du prompt;
- references d'artefacts gates;
- resumes humains par bloc;
- inclusions / exclusions / transformations;
- statut "contenu complet disponible / non disponible".

### Synthese conversation

Chaque synthese conversation devra porter:

- titre si disponible;
- sinon date / heure lisible;
- derniers tours observes;
- taux de tours reussis / degrades / partiels;
- modules les plus impliques;
- dernier probleme visible;
- usage memoire;
- usage web;
- tendance recente;
- source et version de calcul.

Le Lot 2 persiste ces syntheses dans `dashboard_conversation_summaries`.

Le label conversation reste content-free:

- titre explicite si un futur fait fiable et autorise existe;
- sinon date / heure lisible;
- jamais uniquement un identifiant opaque dans les futures vues.

En v1, le label est un fallback date / heure afin de ne pas inventer un titre depuis du contenu utilisateur.

### Buckets horaires / journaliers

Les buckets doivent permettre:

- fenetres 24 h;
- 7 j;
- 30 j;
- 90 jours;
- granularite plus fine sur le recent;
- granularite plus compacte sur l'ancien;
- pas de retention sans limite.

Chaque bucket devra porter:

- window_start;
- window_end;
- granularity;
- module_key;
- counts;
- rates;
- p50 / p95 si la source le permet;
- erreurs et reason codes;
- version de calcul;
- statut de materialisation.

Le Lot 2 persiste les buckets dans `dashboard_metric_buckets`.

Modules bucketises v1:

- pipeline;
- persistence;
- memory;
- web;
- providers;
- identity;
- hermeneutic;
- node_state;
- errors.

Les courbes futures 24 h / 7 j / 30 j / 90 jours doivent lire ces buckets ou des agregats equivalents, pas recalculer une fenetre longue depuis `event_limit=2000`.

### Statut de materialisation

Le dashboard doit exposer ou pouvoir exposer:

- dernier event traite;
- dernier timestamp source traite;
- retard de materialisation;
- erreurs de materialisation;
- version du calcul;
- fenetre couverte;
- indication de backfill absent ou incomplet.

Le Lot 2 persiste ce statut dans `dashboard_materialization_status`:

- `last_event_id`;
- `last_event_ts`;
- `lag_seconds`;
- `turns_materialized_count`;
- `conversations_materialized_count`;
- `buckets_materialized_count`;
- `source_events_truncated = false`;
- `event_limit_dependency = false`;
- code, hash court et longueur d'erreur, sans message brut;
- `backfill_status` pour distinguer la fenetre de retention materialisee d'une fenetre custom.

La presence du materialiseur ne declenche pas de backfill historique massif. Un backfill reste une action operateur explicite.

## 7. API admin dashboard v1

Le Lot 4 expose une API admin dediee au futur dashboard, sans demander au navigateur de parser `/log`.

Implementation v1:

- module de lecture: `app/observability/dashboard_read_model.py`;
- routes HTTP minces dans `app/server.py`;
- source principale: tables analytiques persistantes `observability.dashboard_*`;
- catalogue modules: `build_dashboard_module_catalog()`;
- pas d'endpoint contenu complet dans ce lot.

Endpoints v1:

- `GET /api/admin/dashboard/overview`;
- `GET /api/admin/dashboard/conversations`;
- `GET /api/admin/dashboard/conversations/<conversation_id>/turns`;
- `GET /api/admin/dashboard/turns/<turn_id>/inspection`.

Parametres communs:

- `window=24h|7d|30d|90d|today|yesterday`;
- ou fenetre custom avec `ts_from` et `ts_to`;
- `limit` / `offset` sur les listes;
- `conversation_id` obligatoire en query pour une inspection de tour si le `turn_id` est ambigu.

Contrat:

- les endpoints exposent des labels francais, counts, statuts, timestamps, reason codes, versions et references compactes;
- les endpoints exposent toujours le statut de source: fenetre, retention, materialisation, troncature, dependance event_limit, version de calcul;
- les endpoints exposent toujours la couverture de fenetre: fenetre demandee, fenetre materialisee, couverture `complete` / `partial` / `absent`;
- `source.status=ok` est autorise seulement si la materialisation couvre toute la fenetre demandee, sans troncature ni dependance `event_limit`;
- les endpoints ne lisent pas `/api/admin/logs/chat` et ne dependent pas de `event_limit=2000`;
- les endpoints n'exposent aucun prompt, message, query web, payload provider, contenu memoire, identity brute, summary brute, token, DSN ou traceback brut;
- l'inspection de tour est traduite module par module et reste content-free;
- si les tables analytiques sont indisponibles, les read-models renvoient un etat degrade compact plutot qu'un faux resultat complet.

## 8. Modules observables

Chaque module observable doit declarer conceptuellement:

- `module_key`;
- libelle francais;
- metriques globales;
- resume conversation;
- resume tour;
- detail humain;
- etats `success`, `degraded`, `error`, `skipped`, `not_applicable`;
- contenu complet optionnel;
- regles content-free;
- version de calcul;
- sources;
- limites;
- liens vers events sources;
- liens vers artefacts gates.

Convention v1 livree au Lot 3:

- module: `app/observability/dashboard_observable_modules.py`;
- facade publique: exports depuis `app/observability/dashboard_analytics.py`;
- catalogue content-free: `build_dashboard_module_catalog()`;
- cles bucketisables: `observable_module_keys()`;
- explication humaine des degradations: `explain_module_degradation()`;
- contrat de module: `ObservableModule`;
- reduction de metriques par module: `bucket_metrics_reducer`;
- finalisation optionnelle de metriques par module: `bucket_metrics_finalizer`;
- resume humain de tour par module: `turn_summary_renderer`;
- extraction optionnelle de cause compacte par module: `turn_degradation_reason_resolver`;
- version de contrat: `dashboard_observable_modules_v1`.

Chaque `ObservableModule` declare:

- `module_key`: cle stable;
- `label_fr`: libelle francais court pour les vues operateur;
- `description_fr`: role humain du module;
- `global_metrics`: metriques globales exposees par cle stable et libelle francais;
- `conversation_summary`: champs de synthese conversation;
- `turn_summary`: champs de synthese tour;
- `human_detail`: points de detail traduits;
- `states`: etats communs `success`, `degraded`, `error`, `skipped`, `not_applicable`;
- `content_free_rules`: regles de non-affichage de brut;
- `sources`: sources evenementielles, facts ou artefacts attendus;
- `limits`: limites explicites de preuve et reconstruction;
- `degradation_reasons`: reason codes compacts traduits en francais;
- `gated_content`: classes de contenus complets eventuellement ouvrables plus tard;
- `calculation_version`: version du calcul ou du contrat.
- `bucket_metrics_reducer`: hook optionnel qui reduit les facts du module en metriques de bucket;
- `bucket_metrics_finalizer`: hook optionnel qui finalise les metriques derivees, par exemple p50 / p95.
- `turn_summary_renderer`: hook optionnel qui produit le resume humain content-free d un tour.
- `turn_degradation_reason_resolver`: hook optionnel qui extrait le reason code compact d un tour pour le traduire ensuite.

Modules initiaux actuels:

- pipeline;
- persistence;
- memory;
- web;
- providers;
- identity;
- hermeneutic;
- node_state;
- errors.

Modules futurs branchables:

- documents;
- images.

Regle d'extension:

- ajouter `documents` ou `images` ne doit pas exiger de refaire le dashboard;
- un nouveau module doit pouvoir declarer ses metriques, son resume humain et ses contenus gates selon le meme contrat.
- les buckets analytiques lisent les cles depuis le registre des modules observables, au lieu de porter une liste de modules hard-codee dans la projection;
- la projection de buckets appelle le reducer declare par le module, sans chaine centrale `if module_key == ...`;
- l'inspection de tour appelle le resume humain declare par le module, sans chaine centrale `if module_key == ...`;
- l'inspection de tour appelle aussi l'extracteur de cause declare par le module, sans dispatch central par module;
- un module futur sans metriques specialisees peut deja produire un bucket content-free avec `turn_count` et `event_count`;
- un module futur avec metriques specialisees ajoute son reducer dans sa declaration de module, sans modifier la projection centrale.
- un module futur avec resume humain specialise ajoute son renderer dans sa declaration de module, sans modifier le read-model dashboard.

Regle de degradation:

- la lecture principale affiche une explication francaise courte;
- le reason code compact peut rester disponible dans le detail technique;
- si un reason code n'est pas encore traduit, la vue doit dire que la cause exacte demande le detail technique, sans afficher le code brut comme explication principale.

## 9. Vocabulaire humain

Le langage de premier niveau est un langage produit en francais.

Exemples attendus:

- `complete` -> Tours reussis;
- `degraded` -> Reponses degradees;
- `partial` -> Tours partiels;
- `legacy_incomplete` -> Historique incomplet;
- `llm_call[provider_caller=llm]` -> Modele principal;
- providers secondaires -> Agents secondaires;
- `memory_chain_snapshot` -> Chaine memoire;
- `node_state` -> Etat de suivi hermeneutique;
- `fallback_fail_open` -> Reponse avec garde degradee;
- `persist_response.assistant_final` -> Reponse finale sauvegardee.

Regles:

- les noms de stages backend ne doivent pas structurer la lecture principale;
- les noms techniques peuvent rester dans les details debug;
- les reason codes doivent etre traduits ou accompagnes d'une explication courte;
- le dashboard doit expliquer avant d'alerter.

## 10. Interdits

Sont interdits:

- une lecture principale composee de noms de stages backend;
- des courbes 30 / 90 jours calculees depuis `event_limit=2000`;
- l'affichage brut par defaut;
- le prechargement invisible de contenu complet;
- le faux "contenu compris" reduit a hash + longueur;
- la creation d'une seconde observabilite incoherente quand l'existant peut etre reutilise;
- la fusion du provider principal et des providers secondaires;
- la presentation d'un signal legacy comme signal fiable non etiquete;
- les labels derives de texte libre utilisateur comme labels de courbes;
- l'inclusion de contenu brut dans les agregats;
- l'affaiblissement du content gate pour accelerer le frontend.

## 11. Duplication et recouvrement

Doctrine retenue:

- duplication confuse a eviter;
- recouvrement transitoire acceptable;
- nettoyage progressif ensuite;
- pas de dogme "zero recouvrement immediat".

Definitions:

- duplication confuse: deux surfaces affichent des chiffres ou statuts proches avec sources ou semantiques differentes sans l'expliquer;
- recouvrement transitoire: une information existe a la fois dans `/log`, une surface domaine et le dashboard pendant la stabilisation;
- nettoyage progressif: replier, renommer ou deplacer une lecture seulement quand le dashboard a prouve une lecture plus claire sans perte diagnostic.

## 12. Matrice produit fondatrice

| Question produit | Reponse par defaut | Reponse sur action explicite |
| --- | --- | --- |
| Le modele a-t-il recu de la memoire ? | Statut oui/non/degrade, counts RAG, source `memory_chain_snapshot` ou fallback legacy, sans contenu brut. | Detail des elements memoire injectes si un artefact gate existe, avec contenu complet ou indication "non disponible". |
| Que contenait reellement le contexte modele ? | Resume traduit des blocs, sources, inclusions/exclusions et limites de preuve. Si seuls hash/longueur existent, dire que le contenu n'est pas reconstructible. | Ouverture du prompt/payload complet et des blocs sources via `Afficher le contenu complet`, sous garde. |
| Que peut-on prouver aujourd'hui ? | Presence de stages, statuts, counts, tailles, hashes, provider lanes, persistence finale, RAG compact, web compact, node_state compact. | Les contenus metier deja exposes par des surfaces explicites d'edition ou de detail peuvent etre ouverts selon leurs propres gardes; le prompt modele exact n'est pas garanti reconstructible depuis les logs actuels. |
| Que faudra-t-il persister demain ? | Facts par tour, syntheses conversation, buckets horaires/journaliers, materialisation, manifests de prompt, resumes humains par bloc, references d'artefacts. | Artefacts gates pour prompt principal, payload modele principal, providers secondaires, memoire, identity, web, documents, images et autres modules futurs. |

## 13. Acceptance criteria du Lot 1

Le Lot 1 est ferme quand:

- ce contrat existe dans `app/docs/states/specs/`;
- le TODO actif pointe vers ce contrat;
- les niveaux cockpit / lecture traduite / comprehension fidele / contenu complet sont definis;
- la limite hash + longueur est explicite;
- les couches de verite sont definies;
- les faits et agregats futurs sont cadres sans schema SQL final;
- la matrice sources -> champs -> vues -> gate eventuel est explicite;
- les modules observables sont cadres;
- le vocabulaire humain est cadre;
- les interdits sont cadres;
- les lots backend/frontend suivants ne peuvent pas confondre content-free et comprehension suffisante.
