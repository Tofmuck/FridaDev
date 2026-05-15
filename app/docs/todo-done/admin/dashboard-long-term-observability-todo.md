# Dashboard long terme observabilite - TODO

Statut: clos, archive le 2026-05-15
Source: audit / cadrage read-only du futur dashboard long terme FridaDev du 2026-05-15
Classement initial: `app/docs/todo-todo/admin/`
Classement archive: `app/docs/todo-done/admin/`
Portee: dashboard produit/admin/frontend long terme, metriques persistantes, inspection traduite, architecture modulaire observable
Hors-scope du commit de creation: patch runtime, frontend, route, migration DB, backfill, rebuild, nettoyage immediat des surfaces existantes, redesign global
Spec fondatrice: `app/docs/states/specs/dashboard-long-term-observability-contract.md`

## 0. Note de cloture

Chantier clos le 2026-05-15 apres livraison et validation des Lots 1 a 9.

Les recouvrements restants entre `/dashboard`, `/log`, Memory Admin, Hermeneutic Admin et Identity sont documentes comme recouvrements utiles assumes: le dashboard porte la lecture globale, `/log` reste le debug technique, et les surfaces domaine conservent leurs diagnostics ou editions specialisees.

Aucun lot actif ne justifie de garder ce TODO ouvert. Les futurs nettoyages de doublons devront etre ouverts comme chantiers separes seulement s'ils deviennent reellement utiles.

Note corrective post-cloture du 2026-05-15:

- un defaut P1 a ete confirme apres cloture: les agregats persistants du dashboard ne se rematerialisaient pas automatiquement apres de nouveaux tours;
- correctif livre dans `app/observability/dashboard_materialization_runtime.py` et `app/server.py`;
- chaque fin de tour planifie une materialisation recente bornee sur 24 h;
- les lectures dashboard declenchent aussi un rattrapage borne si des events sources existent apres la derniere fenetre materialisee;
- les horizons 7 j / 30 j / 90 j restent honnetement marques partiels tant qu'un backfill ou scheduler longue periode explicite ne les couvre pas;
- aucun contenu brut n'est stocke dans les agregats par ce correctif.

## 1. Intention

Ce TODO ouvre le chantier actif du futur dashboard long terme FridaDev.

Le besoin n'est pas d'ajouter une cinquieme surface opaque ni de refaire l'observabilite existante. FridaDev possede deja des logs compacts, des read-models, des snapshots et des surfaces admin riches:

- `/log`;
- Memory Admin;
- Hermeneutic Admin;
- Identity;
- `observability.chat_log_events`;
- `full_turn_metrics_snapshot`;
- `turn_observability_checklist`;
- `turn_pipeline_read_model`;
- `memory_chain_snapshot`;
- read-models Memory, Identity et Hermeneutic.

Le besoin est de construire une lecture long terme, lisible par un non-technicien, capable de montrer en un ecran:

- le pouls global du systeme;
- la lecture comparative des conversations;
- les courbes fiables sur de vraies fenetres temporelles;
- l'inspection exhaustive mais traduite d'une conversation et d'un tour;
- l'acces volontaire au contenu complet quand il est explicitement demande.

## 2. Emplacement retenu

Emplacement initial: `app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md`.
Emplacement archive: `app/docs/todo-done/admin/dashboard-long-term-observability-todo.md`.

Raison:

- le chantier n'est plus une remediation d'audit;
- il ouvre une vraie surface produit/admin/frontend;
- il touche la lecture operateur, les routes admin futures, la persistence analytique et la coherence visuelle;
- `app/docs/todo-todo/audits/` serait moins juste, car le but n'est pas seulement de fermer des findings mais de cadrer puis construire un nouveau produit admin.

## 3. Direction d'architecture retenue

La source de verite du dashboard doit etre une combinaison explicite:

- logs compacts existants = verite evenementielle detaillee;
- agregats persistants = verite analytique longue periode;
- read-models modulaires = lecture humaine et inspection traduite;
- `/log` = outil de debug technique, pas dashboard long terme;
- le futur dashboard = couche de lecture et de decision, construite au-dessus de l'observabilite existante sans la reimplementer aveuglement.

Le dashboard ne doit pas recalculer 30 ou 90 jours de courbes a partir d'un `event_limit` court. Les lectures actuelles de `/api/admin/logs/chat/metrics` restent utiles comme semantique et preuve recente, mais ne suffisent pas comme socle industriel longue periode lorsque `source.events_truncated=true`.

## 4. Duplication, recouvrement et nettoyage

Ne pas transformer la non-duplication en dogme rigide.

Regle:

- eviter la duplication confuse: deux surfaces qui racontent la meme chose avec des nombres ou mots differents sans source claire;
- accepter le recouvrement transitoire lorsqu'il permet de construire proprement le dashboard sans casser `/log`, Memory Admin, Hermeneutic Admin ou Identity;
- nettoyer progressivement les surfaces devenues redondantes une fois le dashboard stabilise et prouve.

On ne cherche pas zero recouvrement immediat; on cherche une observabilite de mieux en mieux maitrisee, avec nettoyage progressif des duplications inutiles au fil du chantier.

## 5. Page dediee et structure frontend cible

Hypothese de structure a verifier au debut du lot d'implementation:

- `app/web/dashboard.html`;
- `app/web/dashboard/`;
- route statique dediee `/dashboard`;
- endpoints admin sous `/api/admin/dashboard/...`.

Cette structure suit le rangement actuel:

- `app/web/log.html` + `app/web/log/`;
- `app/web/memory-admin.html` + `app/web/memory_admin/`;
- `app/web/hermeneutic-admin.html` + `app/web/hermeneutic_admin/`;
- `app/web/identity.html` + `app/web/identity/`.

Chaque lot doit relire l'etat courant avant patch, car le depot peut evoluer avant l'ouverture du code.

## 6. Premiere vue cible

L'ecran d'ouverture doit mettre a egalite:

- le pouls global du systeme;
- la lecture comparative des conversations.

Il ne faut pas imposer un mode "global d'abord, conversations ensuite". Les deux lectures doivent etre visibles sans choix prealable.

Les conversations doivent etre identifiees par:

- leur titre si disponible;
- sinon une date / heure lisible;
- jamais uniquement par un identifiant opaque.

## 7. Fenetres temporelles et retention

Fenetres visibles d'abord:

- 24 h;
- 7 j;
- 30 j.

Options secondaires:

- aujourd'hui;
- hier;
- 90 jours;
- personnalisee.

Cible initiale:

- profondeur 90 jours;
- granularite plus fine sur le recent si utile;
- granularite plus compacte sur l'ancien;
- pas de retention sans limite a ce stade;
- pas de backfill massif sans decision separee.

## 8. Langage humain obligatoire

Le dashboard doit parler francais simple.

Exemples de vocabulaire principal:

- Tours reussis;
- Reponses degradees;
- Memoire utilisee;
- Recherche web utile;
- Problemes rencontres;
- Contenu complet;
- Conversation active;
- Dernier probleme visible.

Les termes techniques peuvent rester accessibles dans les details, mais ne doivent pas structurer la lecture principale:

- `legacy_incomplete`;
- `provider_caller`;
- `fallback_fail_open`;
- `memory_chain_snapshot`;
- `node_state`;
- noms de stages bruts.

## 9. Content-free par defaut et contenu complet volontaire

Par defaut, le dashboard reste content-free:

- counts;
- statuts;
- booleens;
- durees;
- timestamps;
- dimensions;
- rates;
- reason codes;
- error codes;
- noms de modules;
- hashes courts;
- longueurs;
- references techniques non sensibles.

Interdit par defaut:

- contenu brut de conversation;
- prompt;
- messages;
- memory trace brute;
- summary brute;
- identity brute;
- query web brute;
- result snippet;
- canonical input dump;
- DSN;
- token;
- cle;
- traceback brut.

Le besoin d'acces au contenu complet est confirme.

Il doit etre traite comme un lot explicite:

- action volontaire de type `Afficher le contenu complet`;
- aucun brut charge ou affiche par defaut;
- separation claire entre lecture humaine et contenu complet;
- garde frontend et backend;
- idealement audit de l'action;
- indication claire du niveau de sensibilite;
- pas d'elargissement implicite aux vues cockpit.

## 10. Architecture modulaire cible

Le dashboard doit accueillir des modules actuels et futurs.

Chaque module observable doit pouvoir declarer:

- metriques globales;
- resume conversation;
- resume tour;
- detail humain;
- etats succes / degrade / erreur;
- contenu complet optionnel;
- regles content-free;
- version de calcul;
- sources evenementielles ou tables d'agregats;
- points d'extension.

Modules initiaux:

- pipeline;
- memory;
- identity;
- hermeneutic;
- providers;
- web;
- node_state.

Modules futurs a prevoir explicitement:

- documents;
- images;
- autres outils ou agents.

## 11. Coherence visuelle frontend

La coherence visuelle n'est pas une note annexe: c'est un axe du chantier.

Reference principale:

- le chat Frida;
- sa topbar;
- ses boutons de navigation;
- son langage sobre, compact et deja reconnaissable.

Le dashboard doit rester coherent avec:

- `/log`;
- Memory Admin;
- Hermeneutic Admin;
- Identity;
- `/admin`;
- les boutons de navigation du chat.

Objectif:

- unite visuelle propre;
- pas de redesign sauvage;
- pas de rupture avec l'esthetique Frida;
- densite utile;
- boutons et navigation harmonises progressivement;
- composants partages lorsque cela reduit vraiment la divergence.

## 12. Lots recommandes

### Lot 1 - Contrat dashboard

Objectif: cadrer le contrat avant toute implementation.

Spec livree:

- `app/docs/states/specs/dashboard-long-term-observability-contract.md`

Cases:

- [x] Definir les faits par tour, les agregats, le vocabulaire francais et les modules observables.
- [x] Definir le content gate et la politique `Afficher le contenu complet`.
- [x] Definir les niveaux de lecture: cockpit, conversation, tour, inspection, contenu complet.
- [x] Definir les champs strictement content-free autorises par defaut.
- [x] Definir les champs interdits par defaut.
- [x] Documenter la difference entre logs compacts, agregats persistants et read-models humains.
- [x] Documenter que `/log` reste l'outil de debug technique.

Tests / preuves attendues:

- [x] Spec ou doc relue contre `log-module-contract.md`.
- [x] Matrice sources -> champs -> vues.
- [x] Preuve que chaque champ sensible est soit interdit par defaut, soit rattache au content gate.

Condition de cloture:

- [x] Aucun lot backend/frontend ne peut demarrer sans contrat de donnees, vocabulaire et content gate valides.

### Lot 2 - Faits persistants et agregats longue periode

Objectif: creer le socle analytique qui rend les fenetres 24 h / 7 j / 30 j / 90 jours fiables.

Implementation livree:

- facade: `app/observability/dashboard_analytics.py`;
- projection pure: `app/observability/dashboard_analytics_projection.py`;
- stockage / materialisation: `app/observability/dashboard_analytics_storage.py`;
- tables: `observability.dashboard_turn_facts`, `observability.dashboard_conversation_summaries`, `observability.dashboard_metric_buckets`, `observability.dashboard_materialization_status`;
- materialiseur: `materialize_dashboard_analytics_window()`;
- doctrine corrective: une petite fenetre met a jour les facts touches, puis regenere summaries/buckets depuis les facts persistants afin de ne pas fausser les agregats longs;
- pas de frontend, pas d'endpoint dashboard, pas de backfill massif automatique.

Cases:

- [x] Definir les facts par tour.
- [x] Definir les syntheses conversation.
- [x] Definir les buckets horaires / journaliers.
- [x] Definir la retention cible 90 jours.
- [x] Definir la granularite recente vs ancienne.
- [x] Definir le statut de materialisation: dernier event traite, retard, erreur, version de calcul.
- [x] Garder le lien vers les logs sources.
- [x] Ne pas stocker de contenu brut dans les agregats.

Tests / preuves attendues:

- [x] Tests de materialisation idempotente.
- [x] Tests de fenetre temporelle.
- [x] Tests de troncature / retard de materialisation.
- [x] Tests content-free stricts.

Condition de cloture:

- [x] Les courbes 30 / 90 jours ne dependent plus d'un `event_limit` court.

### Lot 3 - Architecture modulaire des modules observables

Objectif: eviter un dashboard fige autour du pipeline actuel.

Implementation livree:

- module de convention: `app/observability/dashboard_observable_modules.py`;
- facade publique via `app/observability/dashboard_analytics.py`;
- catalogue content-free: `build_dashboard_module_catalog()`;
- registre extensible: `observable_modules()` / `observable_module_keys()`;
- explication humaine des degradations: `explain_module_degradation()`;
- buckets Lot 2 branches sur le registre au lieu d'une liste hard-codee;
- reduction de metriques portee par les modules via `bucket_metrics_reducer` / `bucket_metrics_finalizer`, sans dispatch central par `module_key`;
- resume humain de tour porte par les modules via `turn_summary_renderer`, sans dispatch central par `module_key`;
- cause compacte de degradation portee par les modules via `turn_degradation_reason_resolver`, sans dispatch central par `module_key`;
- modules futurs `documents` et `images` declares dans le contrat, sans materialisation runtime.

Cases:

- [x] Definir une interface ou convention de module observable.
- [x] Couvrir pipeline, memory, identity, hermeneutic, providers, web et node_state.
- [x] Prevoir documents et images comme modules futurs.
- [x] Definir pour chaque module: metriques globales, resume conversation, resume tour, detail humain, etats, contenu complet optionnel, regles content-free, version.
- [x] Definir comment un module explique une degradation en francais.
- [x] Definir comment un module expose ses sources et limites.

Tests / preuves attendues:

- [x] Fixtures compactes multi-modules.
- [x] Tests d'ajout d'un module factice sans modifier toute la page.
- [x] Tests de libelles humains sans contenu brut.

Condition de cloture:

- [x] Ajouter demain un module documents ou images ne doit pas exiger de refaire l'architecture dashboard.

### Lot 4 - Endpoints dashboard

Objectif: exposer une API admin sobre et stable pour le futur frontend.

Implementation livree:

- read-model dedie: `app/observability/dashboard_read_model.py`;
- routes HTTP minces: `app/server.py`;
- source: tables analytiques persistantes `observability.dashboard_*`;
- catalogue modules expose dans l'overview via `build_dashboard_module_catalog()`;
- fenetres supportees: `24h`, `7d`, `30d`, `90d`, `today`, `yesterday`, `ts_from` / `ts_to`;
- couverture explicite de la fenetre demandee vs fenetre materialisee, avec statut non-ok si la fenetre longue n'est pas entierement couverte;
- pas d'endpoint contenu complet dans ce lot, car le content gate n'est pas encore implemente;
- pas de parsing `/log`, pas de dependance `event_limit=2000`.

Endpoints livres:

- `/api/admin/dashboard/overview`;
- `/api/admin/dashboard/conversations`;
- `/api/admin/dashboard/conversations/<conversation_id>/turns`;
- `/api/admin/dashboard/turns/<turn_id>/inspection`.

Cases:

- [x] Exposer l'overview fenetree.
- [x] Exposer la liste comparative des conversations.
- [x] Exposer les tours d'une conversation.
- [x] Exposer l'inspection traduite d'un tour.
- [x] Exposer les statuts de source: fenetre, retention, materialisation, truncation, version.
- [x] Refuser tout contenu brut hors endpoint explicitement gate.
- [x] Garder `app/server.py` en orchestration seulement.

Tests / preuves attendues:

- [x] Tests API des fenetres.
- [x] Tests schemas content-free.
- [x] Tests empty/degraded state.
- [x] Tests admin access existants non regresses.

Condition de cloture:

- [x] Le frontend peut construire le dashboard sans parser `/log` ni reimplementer les read-models dans le navigateur.

### Lot 5 - Squelette page dediee et coherence visuelle

Objectif: creer la surface dediee sans encore empiler les widgets.

Cases:

- [x] Creer `app/web/dashboard.html`.
- [x] Creer `app/web/dashboard/`.
- [x] Ajouter la route statique `/dashboard`.
- [x] Ajouter ou preparer la navigation depuis le chat et les surfaces admin.
- [x] Reprendre le chat comme reference visuelle principale.
- [x] Reprendre les boutons/navigation du chat comme modele.
- [x] Harmoniser progressivement les liens entre `/log`, Memory Admin, Hermeneutic Admin, Identity et dashboard.
- [x] Ne pas introduire un style visuel separe.

Tests / preuves attendues:

- [x] Checks HTML/JS.
- [x] Test frontend admin minimal.
- [x] Verification que la page charge sans contenu brut.
- [x] Verification responsive sobre si navigateur disponible.

Condition de cloture:

- [x] La page existe, se place naturellement dans Frida, et ne ressemble pas a un dashboard externe colle au produit.

### Lot 6 - Premier ecran

Objectif: rendre visible des l'ouverture le pouls global et les conversations.

Implementation livree:

- premier ecran branche sur `/api/admin/dashboard/overview` et `/api/admin/dashboard/conversations`;
- fenetres principales `24h`, `7d`, `30d` et options secondaires `today`, `yesterday`, `90d`, personnalisee;
- bandeau de couverture de materialisation base sur `source.coverage`;
- pouls global en libelles humains: tours reussis, reponses degradees, problemes rencontres, latences utiles, memoire utilisee, recherche web utile;
- table comparative des conversations avec titre / `display_label` ou date lisible, jamais identifiant opaque comme libelle principal;
- courbes temporelles compactes alimentees par `metric_buckets`: reponses a surveiller, memoire injectee, web utile, latence moyenne;
- latence de fenetre fiable: moyenne exacte `main_duration_ms_total / main_duration_ms_count` depuis les buckets providers, avec p95 seulement comme pic par bucket;
- barres compactes et counts tabulaires, sans courbe decorative ni parsing `/log`;
- pas de drill-down, pas de contenu complet, pas de reimplementation navigateur des read-models.

Cases:

- [x] Afficher les fenetres 24 h, 7 j, 30 j.
- [x] Ajouter les options aujourd'hui, hier, 90 jours et personnalisee.
- [x] Afficher le pouls global: tours reussis, reponses degradees, problemes, latences, memoire, web.
- [x] Afficher la table comparative des conversations.
- [x] Nommer les conversations par titre si disponible, sinon date / heure lisible.
- [x] Eviter les identifiants opaques comme libelle principal.
- [x] Ajouter seulement les courbes vraiment utiles.
- [x] Garder une alternative tabulaire pour les counts importants.

Tests / preuves attendues:

- [x] Tests empty state.
- [x] Tests degraded/materialisation late state.
- [x] Tests libelles humains.
- [x] Tests que les fenetres longues utilisent les agregats persistants.

Condition de cloture:

- [x] Un non-technicien peut comprendre en un ecran si Frida va bien et quelles conversations meritent attention.

### Lot 7 - Inspection traduite conversation / tour

Objectif: rendre exhaustive l'inspection sans imposer les payloads techniques.

Cases:

- [x] Ajouter drill-down conversation -> tour -> inspection.
- [x] Expliquer ce que chaque module a fait en francais clair.
- [x] Expliquer ce que le modele a recu sous forme traduite et content-free par defaut.
- [x] Expliquer ce qui a ete cherche, garde, injecte, persiste, degrade ou echoue.
- [x] Resumer les donnees massives sans dump, par exemple `25 embeddings demandes, 25 reussis`.
- [x] Afficher les causes probables par module avant de renvoyer vers `/log`.
- [x] Ajouter les liens de debug vers `/log`, Memory Admin, Hermeneutic Admin ou Identity quand utile.

Notes de correction avant cloture:

- les causes compactes sont traduites en francais dans la lecture principale; les reason codes non traduits restent reserves aux logs techniques;
- le lien `/log` hydrate `conversation_id` et `turn_id` depuis la query string;
- les compteurs embeddings du recit viennent des events `embedding` materialises dans le fact; si aucun compteur n'existe pour un tour, le recit l'indique explicitement.

Tests / preuves attendues:

- [x] Tests de recit de tour complet.
- [x] Tests tour degrade.
- [x] Tests module absent / not applicable.
- [x] Tests absence de contenu brut.

Condition de cloture:

- [x] L'operateur peut comprendre un tour sans lire une pluie de payloads techniques.

### Lot 8 - Acces volontaire au contenu complet

Objectif: rendre possible le contenu complet confirme par le produit, sans casser le content-free par defaut.

Cases:

- [x] Ajouter l'action explicite `Afficher le contenu complet`.
- [x] Ne jamais afficher le brut par defaut.
- [x] Ne pas precharger le contenu complet dans le DOM si ce n'est pas necessaire.
- [x] Ajouter une garde frontend claire.
- [x] Ajouter une garde backend claire.
- [x] Auditer l'action si possible.
- [x] Afficher une indication de sensibilite avant ouverture.
- [x] Separer contenu de conversation, prompt, identity, memory, web et autres sources.
- [x] Definir ce qui est reconstructible aujourd'hui et ce qui exige un stockage futur explicite.

Tests / preuves attendues:

- [x] Tests que le contenu complet est absent du payload par defaut.
- [x] Tests action volontaire.
- [x] Tests acces refuse / non disponible.
- [x] Tests audit compact sans contenu.

Condition de cloture:

- [x] Le contenu complet est accessible quand il est explicitement demande, mais ne peut pas apparaitre accidentellement dans la lecture cockpit.

### Lot 9 - Nettoyage progressif et harmonisation

Objectif: reduire les recouvrements devenus inutiles apres stabilisation du dashboard.

Cases:

- [x] Cartographier les recouvrements entre dashboard, `/log`, Memory Admin, Hermeneutic Admin et Identity.
- [x] Distinguer recouvrement transitoire utile et duplication confuse.
- [x] Deplacer les lectures devenues centrales vers le dashboard si cela clarifie le produit.
- [x] Garder `/log` comme debug technique.
- [x] Garder Memory Admin, Hermeneutic Admin et Identity comme surfaces domaine ou edition.
- [x] Harmoniser les boutons, la navigation, les titres et les etats empty/error.
- [x] Supprimer ou replier seulement ce qui est prouve redondant.

Decision Lot 9:

- duplication confuse corrigee: navigation admin desordonnee, absence de role explicite par surface, `/log` encore nomme comme cockpit operateur;
- recouvrement utile conserve: syntheses recentes de `/log`, inspections Memory/RAG, diagnostics hermeneutiques et edition Identity restent disponibles car ils portent des preuves domaine non remplacees par le dashboard;
- aucun bloc n'a ete supprime ou replie dans ce lot, car aucun retrait supplementaire n'etait prouve sans perte diagnostic.

Tests / preuves attendues:

- [x] Tests de navigation.
- [x] Tests non-regression des surfaces existantes.
- [x] Preuve que les suppressions/replis ne retirent pas de capacite diagnostic.

Condition de cloture:

- [x] L'observabilite est plus maitrisee qu'avant: moins de duplication confuse, recouvrements utiles assumes, surfaces domaine preservees.

## 13. Hors-scope global

- Pas de patch runtime dans le commit de creation de ce TODO.
- Pas de nouveau frontend dans le commit de creation.
- Pas de route dans le commit de creation.
- Pas de migration DB dans le commit de creation.
- Pas de backfill dans le commit de creation.
- Pas de rebuild Docker pour ce commit docs-only.
- Pas de suppression immediate de `/log`, Memory Admin, Hermeneutic Admin ou Identity.
- Pas de redesign graphique global.
- Pas de modification plateforme OVH.
- Pas de secrets ni contenu brut.
- Pas d'arbitrage final d'implementation sans relecture de l'etat courant au debut du lot concerne.

## 14. Condition de non-prolongation

Le chantier doit s'arreter ou etre recadre quand:

- le contrat dashboard est valide;
- les facts persistants et agregats couvrent les fenetres 24 h / 7 j / 30 j / 90 jours sans `event_limit` trompeur;
- la page dediee expose le pouls global et les conversations a egalite;
- l'inspection conversation / tour est traduite et content-free par defaut;
- l'action `Afficher le contenu complet` existe sous garde explicite;
- les modules observables sont extensibles a documents et images;
- `/log` reste le debug technique;
- les surfaces domaine restent utiles et les duplications confuses sont nettoyees progressivement.

Ne pas prolonger ce TODO pour:

- creer une plateforme BI generique;
- stocker l'historique sans limite;
- refondre toute l'UI Frida;
- changer la doctrine Memory, Identity ou Hermeneutic;
- modifier les providers ou prompts;
- absorber des chantiers documentaire / images qui doivent avoir leurs propres lots d'integration observable;
- contourner les garde-fous content-free.

## 15. Checks docs-only de creation

Pour le commit de creation de ce fichier:

```bash
git status --short
git diff --check
test -f app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "Lot 1" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "Afficher le contenu complet" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "90 jours" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "recouvrement transitoire" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "documents" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "images" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
grep -n "Condition de non-prolongation" app/docs/todo-todo/admin/dashboard-long-term-observability-todo.md
git diff --cached --check
```

Pas de rebuild runtime pour ce commit docs-only.
