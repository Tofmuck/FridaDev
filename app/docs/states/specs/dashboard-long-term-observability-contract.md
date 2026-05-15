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

Ce contrat ne fixe pas le schema SQL final. Il fixe les familles de faits necessaires.

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

### Statut de materialisation

Le dashboard doit exposer ou pouvoir exposer:

- dernier event traite;
- dernier timestamp source traite;
- retard de materialisation;
- erreurs de materialisation;
- version du calcul;
- fenetre couverte;
- indication de backfill absent ou incomplet.

## 7. Modules observables

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

Modules initiaux:

- pipeline;
- memory;
- identity;
- hermeneutic;
- providers;
- web;
- node_state.

Modules futurs branchables:

- documents;
- images.

Regle d'extension:

- ajouter `documents` ou `images` ne doit pas exiger de refaire le dashboard;
- un nouveau module doit pouvoir declarer ses metriques, son resume humain et ses contenus gates selon le meme contrat.

## 8. Vocabulaire humain

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

## 9. Interdits

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

## 10. Duplication et recouvrement

Doctrine retenue:

- duplication confuse a eviter;
- recouvrement transitoire acceptable;
- nettoyage progressif ensuite;
- pas de dogme "zero recouvrement immediat".

Definitions:

- duplication confuse: deux surfaces affichent des chiffres ou statuts proches avec sources ou semantiques differentes sans l'expliquer;
- recouvrement transitoire: une information existe a la fois dans `/log`, une surface domaine et le dashboard pendant la stabilisation;
- nettoyage progressif: replier, renommer ou deplacer une lecture seulement quand le dashboard a prouve une lecture plus claire sans perte diagnostic.

## 11. Matrice produit fondatrice

| Question produit | Reponse par defaut | Reponse sur action explicite |
| --- | --- | --- |
| Le modele a-t-il recu de la memoire ? | Statut oui/non/degrade, counts RAG, source `memory_chain_snapshot` ou fallback legacy, sans contenu brut. | Detail des elements memoire injectes si un artefact gate existe, avec contenu complet ou indication "non disponible". |
| Que contenait reellement le contexte modele ? | Resume traduit des blocs, sources, inclusions/exclusions et limites de preuve. Si seuls hash/longueur existent, dire que le contenu n'est pas reconstructible. | Ouverture du prompt/payload complet et des blocs sources via `Afficher le contenu complet`, sous garde. |
| Que peut-on prouver aujourd'hui ? | Presence de stages, statuts, counts, tailles, hashes, provider lanes, persistence finale, RAG compact, web compact, node_state compact. | Les contenus metier deja exposes par des surfaces explicites d'edition ou de detail peuvent etre ouverts selon leurs propres gardes; le prompt modele exact n'est pas garanti reconstructible depuis les logs actuels. |
| Que faudra-t-il persister demain ? | Facts par tour, syntheses conversation, buckets horaires/journaliers, materialisation, manifests de prompt, resumes humains par bloc, references d'artefacts. | Artefacts gates pour prompt principal, payload modele principal, providers secondaires, memoire, identity, web, documents, images et autres modules futurs. |

## 12. Acceptance criteria du Lot 1

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
