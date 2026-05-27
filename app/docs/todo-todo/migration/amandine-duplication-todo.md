# Duplication Amandine depuis FridaDev sain

Statut: actif sur `migration`
Portee: plan operatoire de creation d'une instance Amandine separee
Precondition: freeze sante Frida valide GO le 2026-05-27
Source freeze: `app/docs/todo-done/migrations/frida-health-freeze-before-amandine-final-validation-2026-05-27.md`

## Principe

La duplication Amandine part du repository FridaDev sain, pas des donnees Frida.
Le code applicatif Amandine doit venir d'un checkout/clone Git propre d'un
commit ou d'une branche identifies. Il ne doit pas venir d'un `rsync`, d'une
copie manuelle ou d'une duplication opaque de la working copy live Frida.

La cible est une instance separee:

```text
repository FridaDev sain
+ stack applicative Amandine separee
+ DB Amandine neuve
+ state Amandine propre
+ runtime settings reseedes
+ identite active Amandine explicite
-> instance Amandine autonome
```

Ce plan ne cree pas Amandine. Il decrit les lots a executer ensuite avec GO explicite.

## Decision de base

- [ ] Strategie retenue: instance separee, pas multi-utilisateur dans la meme DB.
- [ ] Copier la structure applicative depuis le repository, pas les donnees Frida/Tof.
- [ ] Creer le code applicatif Amandine depuis un clone/checkout Git propre, avec commit ou branche source consignes.
- [ ] Interdire la copie de la working copy live comme source applicative Amandine.
- [ ] Garder les secrets hors Git et hors preuves.
- [ ] Utiliser un token OpenRouter Amandine separe du token Frida.
- [ ] Distinguer strictement actions applicatives Celebrimbor et actions plateforme Sauron.
- [ ] Ne pas commencer une action destructive sans backup et rollback documentes.
- [ ] Ne pas promettre de memoire durable sans mecanisme persistant reel.

## Hors-scope de cette TODO

- [ ] Ne pas creer Amandine dans ce lot docs-only.
- [ ] Ne pas purger, copier ou migrer la DB Frida.
- [ ] Ne pas copier `state/` Frida.
- [ ] Ne pas modifier Docker, Caddy, Authelia, reseaux, secrets ou hostnames depuis Celebrimbor.
- [ ] Ne pas modifier `.env`, runtime settings live, prompts runtime ou identites live.
- [ ] Ne pas rebuild, restart ou creer de conteneur.
- [ ] Ne pas afficher secret, `.env`, DSN complet, token, cookie, payload brut, conversation brute, prompt complet, identite brute ou document utilisateur.

## Donnees Frida a ne pas copier

Pour Amandine, ces familles doivent repartir vides ou etre reseedees explicitement:

| Famille | Decision Amandine |
| --- | --- |
| conversations / messages | ne pas copier; DB neuve vide |
| traces Memory/RAG | ne pas copier; repartir vide |
| summaries | ne pas copier; repartir vide |
| identity_mutables | ne pas copier Frida/Tof; vide ou seed minimal explicite |
| identity_mutable_audit | ne pas copier; repartir vide |
| identity_mutable_staging | ne pas copier; repartir vide |
| identities legacy / evidence / conflicts | ne pas copier; repartir vide |
| observability events / dashboard projections | ne pas copier; repartir vide |
| active documents / workspace files / selections | ne pas copier; repartir vide sauf seed produit explicite |
| runtime settings history | ne pas copier; reseed neuf et historique Amandine propre |
| `state/conv`, uploads, workspace files | ne pas copier; repertoire propre |
| `state/logs` | ne pas copier; logs Amandine neufs |
| backups manuels Frida | ne pas copier dans la stack Amandine |

## Frontiere Celebrimbor / Sauron

Celebrimbor documente, prepare et verifie le produit applicatif:

- structure repo et docs;
- migrations SQL applicatives;
- seeds non secrets;
- runtime settings attendus;
- identite Amandine initiale;
- tests applicatifs;
- smokes applicatifs content-free;
- surfaces admin/read-model/logs.

Sauron execute ou valide les actions plateforme:

- creation des sous-stacks sous `/opt/platform`;
- Docker Compose runtime hors repo applicatif;
- reseaux Docker;
- Caddy;
- Authelia;
- hostnames et certificats;
- secrets runtime;
- creation DB et volumes au niveau plateforme si hors scripts applicatifs;
- sauvegardes host-level.

Regle: si un lot exige Caddy, Authelia, Docker global, secrets ou hostnames, Celebrimbor produit la checklist et s'arrete; Sauron execute sous son propre protocole.

## Preuves content-free

Autorise dans les preuves:

- statuts;
- counts;
- noms de tables/sections;
- model ids;
- routes;
- timestamps;
- hash courts;
- longueurs;
- reason codes;
- exit codes.

Interdit dans les preuves:

- contenus de conversations;
- identites brutes;
- mutables reelles brutes;
- prompts complets;
- documents utilisateur;
- `.env`;
- DSN complet;
- tokens, cookies, secrets ou headers d'authentification.

## Lot 0 - Inventaire de depart et preconditions

Responsable: Celebrimbor

Objectif:

- [ ] Confirmer que le freeze Frida GO est la base de depart.
- [ ] Verifier branche, commit, worktree et docs source.
- [ ] Lister les decisions produit encore ouvertes avant creation Amandine.

Surfaces concernees:

- `app/docs/todo-done/migrations/frida-health-freeze-before-amandine-final-validation-2026-05-27.md`;
- `app/docs/todo-done/migrations/frida-health-freeze-before-amandine-todo.md`;
- `app/docs/states/specs/mutable-identity-judge-contract.md`;
- `app/docs/states/specs/admin-runtime-settings-schema.md`;
- `app/docs/states/specs/identity-read-model-contract.md`;
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`.

Actions autorisees:

- [ ] Lire les docs et produire un inventaire content-free.
- [ ] Verifier que la branche de travail est `migration`.
- [ ] Confirmer que la duplication n'a pas commence.

Actions interdites:

- [ ] Ne pas creer DB, state, stack, conteneur ou hostname.
- [ ] Ne pas modifier runtime settings.

Preuves attendues:

- [ ] `git status --short --branch`
- [ ] `git log --oneline -10`
- [ ] liste des decisions produit ouvertes: nom/persona assistant, hostnames, modeles, seeds identity.

Rollback:

- aucun rollback technique: docs-only.

Critere de sortie:

- [ ] Preconditions freeze GO relues.
- [ ] Decisions ouvertes listees avant Lot 1.
- [ ] Aucun effet runtime.

## Lot 1 - Topologie Amandine

Responsable: Celebrimbor pour le cadrage; Sauron pour validation/execution plateforme future.

Objectif:

- [ ] Decider les noms de stack, conteneurs, DB, volumes et hostnames Amandine.
- [ ] Decider le commit ou la branche Git source du clone/checkout Amandine.
- [ ] Eviter toute collision avec `platform-fridadev`.
- [ ] Formaliser les referers/titles OpenRouter attendus pour Amandine.

Surfaces concernees:

- conventions `/opt/platform`;
- futurs sous-dossiers applicatifs et DB;
- hostnames publics;
- sections runtime `main_model`, `identity_periodic_model`, `services`, `resources`, `database`.

Actions autorisees:

- [ ] Proposer noms et ports internes.
- [ ] Documenter la commande de clone/checkout attendue sans l'executer dans ce lot docs-only.
- [ ] Produire une matrice Frida actuelle -> Amandine cible.
- [ ] Identifier ce qui releve de Sauron.

Actions interdites:

- [ ] Ne pas modifier Docker Compose.
- [ ] Ne pas creer l'app Amandine par `rsync`, copie manuelle ou duplication de la working copy live.
- [ ] Ne pas creer hostname ni certificat.
- [ ] Ne pas changer Caddy/Authelia.

Preuves attendues:

- [ ] tableau de topologie cible;
- [ ] commit ou branche source du checkout Amandine consigne;
- [ ] liste des hostnames envisages;
- [ ] liste des decisions Sauron requises.

Rollback:

- revenir au plan precedent si la topologie est refusee; aucune action runtime avant validation.

Critere de sortie:

- [ ] Topologie cible approuvee.
- [ ] Source Git applicative Amandine approuvee et reproductible.
- [ ] Frontiere Celebrimbor/Sauron explicite.

## Lot 2 - Backup Frida prealable et rollback

Responsable: Sauron pour backups host/DB; Celebrimbor pour checklist applicative et preuves attendues.

Objectif:

- [ ] Sauvegarder Frida avant toute action de duplication.
- [ ] Definir un rollback verifiable avant DB/state Amandine.
- [ ] Ne jamais afficher les secrets ni dumps.

Surfaces concernees:

- DB Frida live;
- `state/conv`;
- `state/logs`;
- `state/data`;
- runtime settings chiffres;
- sous-stacks FridaDev.

Actions autorisees:

- [ ] Produire commandes de backup a faire par Sauron.
- [ ] Lister preuves content-free: tailles, checksums, `pg_restore --list`, counts.
- [ ] Definir emplacement backup hors Git.

Actions interdites:

- [ ] Ne pas lancer backup depuis cette TODO sans GO.
- [ ] Ne pas afficher dump SQL, `.env`, DSN ou secrets.

Preuves attendues:

- [ ] backup DB cree et liste;
- [ ] backup state cree;
- [ ] test de restauration minimal sur cible temporaire, si Sauron le valide.

Rollback:

- [ ] procedure documentee pour restaurer Frida a partir des backups, sans toucher Amandine.

Critere de sortie:

- [ ] Backup Frida existe et est verifie content-free.
- [ ] Rollback Frida documente avant creation Amandine.

## Lot 3 - DB Amandine neuve + extensions + migrations

Responsable: Sauron pour creation DB/role/secret; Celebrimbor pour migrations et checks applicatifs.

Objectif:

- [ ] Creer une DB Amandine vide.
- [ ] Installer les extensions attendues.
- [ ] Appliquer la structure/migrations, sans donnees Frida/Tof.

Surfaces concernees:

- Postgres Amandine;
- extensions `pgcrypto`, `vector`, `pg_trgm`, `plpgsql`;
- migrations SQL applicatives;
- tables `runtime_settings`, `conversations`, `identity_mutables`, `observability.*`, workspace/documents.

Actions autorisees:

- [ ] Creer schema/tables dans une DB neuve.
- [ ] Verifier counts initiaux.
- [ ] Appliquer seeds strictement necessaires non personnels.

Actions interdites:

- [ ] Ne pas restaurer un dump Frida.
- [ ] Ne pas copier conversations, logs, mutables, traces, summaries ou documents.
- [ ] Ne pas importer runtime settings history Frida.

Preuves attendues:

- [ ] liste tables/schemas;
- [ ] extensions presentes;
- [ ] counts initiaux vides ou seeds attendus;
- [ ] aucune table utilisateur peuplee par donnees Frida.

Rollback:

- [ ] supprimer/recreer uniquement la DB Amandine neuve si la migration structurelle echoue.
- [ ] ne jamais toucher la DB Frida pour rollback Amandine.

Critere de sortie:

- [ ] DB Amandine structurellement prete.
- [ ] Donnees Frida absentes.

## Lot 4 - `state/` Amandine propre

Responsable: Sauron pour volumes host; Celebrimbor pour classification applicative.

Objectif:

- [ ] Creer les repertoires `state/` Amandine propres.
- [ ] Partir avec uploads, logs, conversations et workspace vides.
- [ ] Ne conserver que les seeds explicitement non personnels.

Surfaces concernees:

- futur `state/conv`;
- futur `state/logs`;
- futur `state/data`;
- identity statics;
- prompts et assets depuis le repo.

Actions autorisees:

- [ ] Creer arborescence vide.
- [ ] Copier seulement fichiers applicatifs non personnels explicitement retenus.
- [ ] Documenter les fichiers seedes.

Actions interdites:

- [ ] Ne pas copier `state/conv` Frida.
- [ ] Ne pas copier `state/logs` Frida.
- [ ] Ne pas copier uploads, workspace files ou backups Frida.
- [ ] Ne pas copier identity Frida/Tof telle quelle.

Preuves attendues:

- [ ] `find` / counts par repertoire, sans noms sensibles si possible;
- [ ] tailles initiales;
- [ ] liste des fichiers seedes non secrets.

Rollback:

- [ ] supprimer le `state/` Amandine nouvellement cree et le recreer propre.

Critere de sortie:

- [ ] `state/` Amandine propre, sans donnees Frida.

## Lot 5 - Reseed runtime settings, secrets hors Git, modeles et referers

Responsable: Celebrimbor pour matrice de settings; Sauron pour injection de secrets et env.

Objectif:

- [ ] Reseeder les runtime settings Amandine.
- [ ] Adapter referers/titles/URLs a Amandine.
- [ ] Conserver les secrets hors Git.
- [ ] Injecter un token OpenRouter propre a Amandine, distinct du token Frida.
- [ ] Separer quotas, couts et logs provider Amandine de Frida.
- [ ] Garder `identity_periodic_model` comme slot compat du juge mutable v2.

Surfaces concernees:

- `runtime_settings`;
- `runtime_settings_history`;
- sections `main_model`, `identity_periodic_model`, `identity_extractor_model`, `memory_arbiter_model`, `summary_model`, `web_reformulation_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`, `identity_governance`.

Actions autorisees:

- [ ] Definir modele principal Amandine.
- [ ] Reseeder `identity_periodic_model.model` selon decision produit, probablement `openai/gpt-5.2` si le meme juge mutable est conserve.
- [ ] Adapter `referer_*`, `title_*`, `app_name` a Amandine.
- [ ] Creer ou fournir un token OpenRouter Amandine distinct via Sauron, sans copier la valeur Frida.
- [ ] Injecter secrets via mecanisme runtime chiffre ou env Sauron, jamais en Git.

Actions interdites:

- [ ] Ne pas copier `runtime_settings_history` Frida.
- [ ] Ne pas copier le token OpenRouter Frida.
- [ ] Ne pas afficher `api_key`, DSN, tokens ou secret embedding.
- [ ] Ne pas changer le contrat mutable v2 pour Amandine.

Preuves attendues:

- [ ] sections runtime presentes;
- [ ] secrets `is_set=true/false` sans valeurs;
- [ ] referers/titles Amandine visibles;
- [ ] token OpenRouter Amandine prouve seulement par `is_set=true`, jamais par sa valeur;
- [ ] quotas/couts/logs provider attribuables a Amandine sans melange avec Frida;
- [ ] modele juge mutable visible en admin;
- [ ] ancien benchmark Frida/Haiku non presente comme actif.

Rollback:

- [ ] reseed settings depuis matrice documentee;
- [ ] rotation possible du token OpenRouter Amandine sans toucher Frida;
- [ ] rotation secrets si une valeur a ete exposee par erreur.

Critere de sortie:

- [ ] Runtime settings Amandine coherents, secrets masques, referers propres.
- [ ] Aucun secret runtime Amandine ne depend du token OpenRouter Frida.

## Lot 6 - Seed identite Amandine

Responsable: Celebrimbor pour contenu applicatif; validation produit par l'operateur.

Objectif:

- [ ] Etablir l'identite active Amandine avant tout smoke mutable.
- [ ] Garantir que le nom principal user est detectable par le validateur mutable v2.
- [ ] Decider si l'assistant reste `Frida` ou change de nom/persona.

Surfaces concernees:

- static user identity;
- static llm identity;
- `identity_mutables`;
- `identity_mutable_staging`;
- `identity_mutable_audit`;
- read-model `/identity`;
- prompt augmente.

Actions autorisees:

- [ ] Creer `user.static` Amandine avec une premiere formulation principale claire, par exemple `Amandine est...` ou `Amandine tient...`.
- [ ] Eviter toute mention historique ou relationnelle de tiers avant la formulation principale.
- [ ] Seed `llm.static` selon decision produit: conserver Frida ou documenter le nouveau nom/persona.
- [ ] Laisser `identity_mutables` vides au depart, ou ajouter un seed minimal explicite seulement si decision produit.

Actions interdites:

- [ ] Ne pas copier static/mutable Frida/Tof.
- [ ] Ne pas utiliser `Utilisateur` comme sujet canonique mutable.
- [ ] Ne pas laisser `Tof` apparaitre comme nom principal user sur Amandine.
- [ ] Ne pas promettre une memoire durable sans mecanisme.

Preuves attendues:

- [ ] preuve content-free `active_user_names ['Amandine']`;
- [ ] `active_llm_names` conforme a la decision produit;
- [ ] mutables initiales vides ou seed explicite liste par count/hash court;
- [ ] `/identity` raconte static + mutable sans staging comme canon.

Rollback:

- [ ] remplacer les fichiers/seeds identity Amandine par la version precedente sauvegardee;
- [ ] vider mutables/staging/audit Amandine si le seed etait incorrect, uniquement sur DB Amandine neuve.

Critere de sortie:

- [ ] Amandine est le nom principal actif du sujet `user`.
- [ ] Le juge mutable v2 refuse les noms tiers si seulement mentionnes.

## Lot 7 - Configuration applicative et surfaces admin Amandine

Responsable: Celebrimbor

Objectif:

- [ ] Verifier que l'app Amandine expose une verite operateur coherente.
- [ ] Adapter labels produit si necessaire sans casser FridaDev.
- [ ] Verifier admin, identity, memory-admin, hermeneutic-admin, log et dashboard.

Surfaces concernees:

- `/admin`;
- `/identity`;
- `/memory-admin`;
- `/hermeneutic-admin`;
- `/log`;
- `/dashboard`;
- runtime settings read-only;
- docs operateur.

Actions autorisees:

- [ ] Ajouter docs/specs si une surface doit indiquer Amandine.
- [ ] Corriger uniquement les labels applicatifs qui tromperaient l'operateur.
- [ ] Verifier que le modele juge mutable et le prompt actif sont visibles.

Actions interdites:

- [ ] Ne pas renommer globalement Frida si la decision produit conserve Frida comme assistant.
- [ ] Ne pas refaire l'UI admin.
- [ ] Ne pas masquer les compatibilites necessaires comme `identity_periodic_model`.

Preuves attendues:

- [ ] `/admin` montre settings Amandine et secrets masques;
- [ ] `/identity` montre user Amandine et assistant choisi;
- [ ] `/log` ne montre pas prompt complet ni contenu brut;
- [ ] read-model indique `mutable_identity_judge_v2_add_only`.

Rollback:

- [ ] revert des labels/docs applicatifs trompeurs;
- [ ] reseed settings si la surface admin pointe vers Frida.

Critere de sortie:

- [ ] Surfaces admin racontent Amandine, pas Frida/Tof, sauf mention explicite d'origine repo/assistant.

## Lot 8 - Plateforme Sauron: Caddy, Authelia, Docker, reseaux, hostnames

Responsable: Sauron

Objectif:

- [ ] Creer la stack plateforme Amandine sans perturber Frida.
- [ ] Publier les hostnames Amandine avec Authelia.
- [ ] Connecter les reseaux et secrets attendus.

Surfaces concernees:

- `/opt/platform`;
- Docker Compose plateforme;
- Caddy;
- Authelia;
- reseaux Docker;
- secrets runtime;
- certificats / DNS.

Actions autorisees:

- [ ] Executer uniquement sous protocole Sauron.
- [ ] Sauvegarder les fichiers plateforme avant modification.
- [ ] Verifier config Docker/Caddy avant reload.

Actions interdites pour Celebrimbor:

- [ ] Ne pas modifier Caddy, Authelia, reseaux, secrets ou Compose plateforme.
- [ ] Ne pas redemarrer services plateforme.

Preuves attendues:

- [ ] containers Amandine up/healthy;
- [ ] hostnames Amandine proteges par Authelia;
- [ ] aucun port DB public;
- [ ] Frida toujours healthy.

Rollback:

- [ ] rollback Caddy/Authelia/Compose depuis backups Sauron;
- [ ] stop de la stack Amandine sans toucher Frida.

Critere de sortie:

- [ ] Plateforme Amandine accessible et isolee.

## Lot 9 - Smokes live Amandine

Responsable: Celebrimbor pour smokes applicatifs; Sauron si une preuve plateforme echoue.

Objectif:

- [ ] Prouver l'instance Amandine live sans polluer Frida.
- [ ] Verifier chat, admin, identity, memory/RAG, mutable v2, documents/web selon activation.
- [ ] Produire preuves content-free.

Surfaces concernees:

- routes publiques Amandine;
- conteneur app Amandine;
- DB Amandine;
- logs Amandine;
- admin/read-model.

Actions autorisees:

- [ ] Smoke chat synthetique non sensible.
- [ ] Smoke identity mutable avec 5 paires synthetiques et verification add/no_change.
- [ ] Smoke 6e paire -> buffer 1/5 si active.
- [ ] Smoke Memory/RAG avec fixture synthetique.
- [ ] Smoke documents/web seulement si modules actives pour Amandine.

Actions interdites:

- [ ] Ne pas utiliser conversations Frida.
- [ ] Ne pas afficher identite brute si elle contient contenu personnel.
- [ ] Ne pas appeler provider externe sans besoin explicite et preuve cout/raison.

Preuves attendues:

- [ ] app Amandine healthy;
- [ ] `/admin` 302 Authelia;
- [ ] tests unitaires cibles OK dans conteneur Amandine;
- [ ] `active_user_names ['Amandine']`;
- [ ] mutable judge v2 add-only OK;
- [ ] static write absent;
- [ ] Frida toujours healthy apres smokes.

Rollback:

- [ ] stop stack Amandine si smoke P0/P1;
- [ ] recreate DB/state Amandine depuis zero si seed initial pollue.

Critere de sortie:

- [ ] Amandine fonctionne comme instance separee, avec donnees propres et surfaces coherentes.

## Lot 10 - Note finale GO/NO-GO duplication

Responsable: Celebrimbor

Objectif:

- [ ] Produire la note finale de duplication Amandine.
- [ ] Decider GO/NO-GO d'ouverture produit.
- [ ] Archiver cette TODO si GO.

Surfaces concernees:

- `app/docs/todo-done/migrations/`;
- `app/docs/todo-todo/migration/README.md`;
- `app/docs/README.md`;
- preuves Sauron referencees sans secrets.

Actions autorisees:

- [ ] Rediger note finale avec commit, tests, smokes, DB/state, P0/P1/P2, P3.
- [ ] Mettre a jour les index docs.
- [ ] Lister actions non effectuees.

Actions interdites:

- [ ] Ne pas corriger en douce un P0/P1/P2 dans la note finale.
- [ ] Ne pas masquer les P3 acceptes.
- [ ] Ne pas commencer un chantier produit non approuve.

Preuves attendues:

- [ ] tests/smokes finaux;
- [ ] health Frida et Amandine;
- [ ] secrets masques;
- [ ] DB/state Amandine propres;
- [ ] aucune donnees Frida copiee.

Rollback:

- [ ] si NO-GO, laisser cette TODO active et ouvrir micro-lots correctifs;
- [ ] si GO, archiver la roadmap et garder la note finale comme source de verite.

Critere de sortie:

- [ ] Decision GO/NO-GO explicite.
- [ ] Aucun P0/P1/P2 ouvert si GO.
- [ ] Prochaine action produit claire.

## Conditions d'arret

Arreter et revenir a l'operateur si:

- un secret est expose ou risque de l'etre;
- l'app Amandine est proposee depuis une copie opaque de la working copy live au lieu d'un checkout/clone Git propre;
- une commande necessite une purge/copie DB non approuvee;
- une action plateforme est necessaire mais Sauron n'a pas donne GO;
- l'identite Amandine ne peut pas etre seedee sans ambiguite;
- le runtime settings reseed ne permet pas de masquer les secrets;
- les smokes revelent un P0/P1/P2;
- le plan derive vers une migration de donnees Frida au lieu d'une instance propre.

## Definition de fini

- [ ] Amandine dispose d'une stack separee.
- [ ] DB Amandine neuve et structuree, sans donnees Frida/Tof.
- [ ] `state/` Amandine propre.
- [ ] Runtime settings reseedes et secrets masques.
- [ ] Runtime Amandine isole des tokens, quotas, couts et logs provider Frida.
- [ ] Token OpenRouter Amandine distinct, injecte hors Git et prouve seulement par `is_set=true`.
- [ ] Code applicatif Amandine issu d'un checkout/clone Git propre d'un commit ou d'une branche identifies.
- [ ] Identite active Amandine etablie avant mention de tiers/historique.
- [ ] Surfaces admin racontent Amandine.
- [ ] Juge mutable v2 add-only fonctionne.
- [ ] Frida reste healthy.
- [ ] Note finale GO/NO-GO existe.
