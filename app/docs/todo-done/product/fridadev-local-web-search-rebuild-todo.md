# FridaDev - reconstruction web discovery local-first + Exa - TODO A-Z

Statut: clos le 2026-05-22, reconstruction applicative web discovery local-first + Exa livree sans modification plateforme globale. Decision produit du 2026-05-22: la decouverte web ouverte bascule vers OpenRouter/Exa quand configure, tout en gardant Crawl4AI, evidence, confiance, source-first, reranking et observabilite sous controle FridaDev.

Ce document est l'archive source-of-truth operatoire du chantier web discovery local-first + Exa. Il conserve l'histoire du diagnostic local/SearXNG, mais la doctrine active n'est plus une reconstruction locale pure: SearXNG ne suffit pas seul a la recherche ouverte, et OpenRouter/Exa est devenu le provider de decouverte URL configure.

## Lecture de l'archive

Ce document est une archive de chantier, pas une TODO active.

Certaines sections historiques conservent des cases `[ ]` issues du plan initial. Elles ne signifient pas que le chantier est encore ouvert. Le statut de cloture est donne par:

- les blocs `Phase X - livraison/consolidation`;
- la section `Avancement global`;
- la validation finale Phase 9;
- la note `app/docs/states/audits/fridadev-web-search-phase-9-final-validation-2026-05-22.md`.

Les cases restees ouvertes relevent de trois categories:

- options explicitement non lancees, comme la reconfiguration globale SearXNG (categorie: option future);
- decisions futures hors cloture, comme rendre une source map editable;
- traces du plan initial superseded par les blocs de consolidation/livraison.

References a relire avant toute phase:

- Audit stack locale web: `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`
- Benchmark final Lot 8: `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`
- TODO hardening V0 terminee et archivee: `app/docs/todo-done/product/fridadev-local-web-search-hardening-todo.md`
- Decision produit active OpenRouter/Exa discovery: `app/docs/states/policies/fridadev-web-search-openrouter-exa-decision-2026-05-22.md`
- Benchmark web: `benchmark/web-search/README.md`

## Doctrine produit

- FridaDev reste local-first pour lire, crawler, qualifier, contextualiser et auditer.
- Recherche ouverte: OpenRouter/Exa devient le moteur prioritaire de decouverte URL; le defaut applicatif est `WEB_SEARCH_DISCOVERY_PROVIDER=openrouter_exa`.
- URL explicite: lecture directe locale inchangee, sans passage par Exa.
- Pas de fallback automatique OpenRouter / Exa / Parallel: Exa est un provider de decouverte configure, pas une soupape appelee par la confiance.
- SearXNG reste disponible comme provider `local`, baseline historique, fallback operateur explicite ou objet d'audit plateforme.
- Crawl4AI sert a lire et crawler les URLs.
- Parallel reste benchmark externe seulement.
- La recherche doit devenir source-first, gouvernee, explicable et contestable.
- La confiance reste visible, non souveraine et non actionnable automatiquement.

## Avancement global

- [x] Phase 0 — Etat des lieux reel
  - [x] Consolidation des preuves existantes
  - [x] Complement local-only des cas manquants
  - [x] Validation utilisateur du corpus borne
  - [x] Passage Phase 1 Sauron
- [x] Phase 1 — Inventaire des moteurs SearXNG
- [x] Phase 2 — Definir les regimes de recherche
- [x] Phase 3 — Source-first
- [x] Phase 4 — Paniers moteurs SearXNG gouvernes
  - [x] Paniers applicatifs par regime, sans modification plateforme.
  - [ ] Reconfig globale SearXNG optionnelle, seulement avec GO utilisateur Sauron.
- [x] Phase 5 — Parametres FridaDev par profil
- [x] Phase 6 — Reranking explicable
- [x] Phase 7 — Comportement d'echec
- [x] Phase 8 — Benchmark final
- [x] Phase 9 — Validation et deploiement Exa discovery
  - [x] Premier branchement provider de decouverte `local|openrouter_exa`.
  - [x] Validation live bornee du provider `openrouter_exa`.
  - [x] Validation finale du corpus borne, calibration confiance/evidence, rollback documente.
  - [x] Decision operateur sur variable runtime OVH: defaut applicatif `openrouter_exa`; rollback explicite vers `local`.

## Regles de pilotage

- Chaque phase doit etre livree par un patch minimal, ferme, testable et reversible.
- Une phase plateforme Sauron ne doit pas etre declenchee par Celebrimbor sans decision utilisateur explicite.
- Une phase runtime Celebrimbor ne doit pas modifier la plateforme OVH, SearXNG global, Docker ou les secrets.
- Les parametres durs doivent etre separes des signaux souples.
- Aucune liste de domaines ne doit devenir une police invisible des sources legitimes.
- Une source hors profil peut etre declassee, mais pas effacee sans raison explicite.
- Le chemin `explicit_url` reste prioritaire: lecture directe Crawl4AI, puis fallback raw seulement selon le contrat existant.
- L'auto-web lexical reste ferme.
- Memory, Identity, Summary, Biblio/RAG et documents actifs restent hors contamination.

## Decisions utilisateur requises avant runtime

- [x] Choisir par profil entre recherche ouverte assistee et source-first stricte.
- [x] Valider les moteurs SearXNG acceptes politiquement et techniquement, au moins partiellement apres Phase 1.
- [x] Valider les sources legitimes pour l'actualite.
- [x] Valider les sources legitimes pour l'administratif francais.
- [x] Valider les sources legitimes pour l'academique.
- [x] Valider les sources legitimes pour la documentation officielle.
- [x] Accepter ou refuser des listes de domaines par profil.
- [x] Fixer une latence maximale cible pour un tour web manuel.
- [x] Fixer le comportement d'echec: dire les preuves insuffisantes ou fragiles, proposer une reformulation si pertinent, demander une URL seulement si cela a du sens.

## Decisions actees apres Phase 1 Sauron

- Documentation officielle: Microsoft Learn est valide comme candidat fort; les docs officielles restent source-first par autorite cible; les Q&A techniques ne sont pas autorite documentaire premiere.
- Actualite: Bing News peut etre etudie ou active comme candidat borne; Reuters est accepte comme source fiable surtout internationale, sans devenir source unique; les sources institutionnelles restent prioritaires pour l'actualite institutionnelle.
- Administratif francais: sources validees `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, domaines `.gouv.fr`, `education.gouv.fr`, `eduscol.education.fr`, `enseignementsup-recherche.gouv.fr`, `onisep.fr` et sites academiques officiels `ac-*.fr` avec prudence.
- Academique: profil large valide, couvrant philosophie, SHS, droit, sciences exactes, medecine et informatique; sous-signaux oui, sous-profils prematurement non.
- Q&A techniques: StackOverflow, GitHub issues, AskUbuntu et SuperUser restent visibles mais declasses hors demande explicite.
- Moteurs externes tokenises: non, sauf DuckDuckGo officiel complet; pas de SERP API tierce qui scrape DuckDuckGo, pas de Brave Search API, pas de Google API, pas de Bing API.

## Angle critique et politique

La recherche n'est pas neutre. Choisir des moteurs, sources, domaines, categories, langues et signaux de ranking produit une certaine realite documentaire. Ce chantier doit donc rendre visibles:

- ce qui est un parametre dur;
- ce qui est un signal souple;
- ce qui vient de SearXNG;
- ce qui vient de Crawl4AI;
- ce qui vient du code applicatif FridaDev;
- ce qui releve d'une decision humaine explicite.

Frida ne doit pas transformer un ranking opaque en verite. La contestabilite doit rester possible: sources visibles, raisons lisibles, echec dicible, aucun fallback externe automatique. Quand Exa est utilise, il decouvre des URLs; FridaDev lit, qualifie et signale les limites.

## Lecture historique du chantier

- Phases 0 a 8: diagnostic et reconstruction locale/SearXNG, utiles pour comprendre ce qui a ete livre et pourquoi SearXNG seul reste fragile.
- Decision post-Phase 8: OpenRouter/Exa devient provider de decouverte URL pour la recherche ouverte quand configure.
- Phase 9: validation et deploiement de cette decision livres; le chantier est archive avec rollback connu.
- L'ancien TODO hardening V0 est archive comme preuve technique; il ne porte plus la doctrine active.

## Phase 0 — Etat des lieux reel

Proprietaire: Sauron + Celebrimbor.

Objectif: figer l'etat actuel avant toute nouvelle reconstruction, pour ne pas corriger une image fantasmee de la stack. La Phase 0 doit produire un diagnostic suffisant pour agir, pas une cartographie exhaustive du web.

Note d'archive: les cases ouvertes de cette section appartiennent au plan Phase 0 initial. Elles sont superseded par le bloc `Phase 0 - consolidation 2026-05-22`, la note `app/docs/states/audits/fridadev-local-web-search-phase-0-baseline-2026-05-22.md` et l'avancement global coche.

Livrables:

- [ ] Inventaire de la configuration SearXNG effective sur OVH.
- [ ] Liste des categories SearXNG disponibles et testees.
- [ ] Liste des moteurs actifs, des moteurs reellement utilisables, des moteurs instables et des moteurs a eviter.
- [ ] Inventaire des parametres FridaDev actuels par profil web.
- [ ] Baseline ancienne locale sur 10 a 15 requetes maximum.
- [ ] Baseline locale profilee actuelle sur les memes requetes.
- [ ] Rapport court distinguant probleme de requete, probleme de moteur, probleme de ranking, probleme de crawl et probleme d'injection.
- [ ] Regle de non-prolongation: ne pas enrichir indefiniment le corpus avant de passer aux phases suivantes; tout ajout au-dela de 15 requetes exige une decision explicite.

Fichiers ou zones concernes:

- Plateforme OVH SearXNG: `/opt/platform/searxng/settings.yml`, `/opt/platform/searxng/limiter.toml`
- Plateforme OVH Crawl4AI: `/opt/platform/crawl4ai/`
- Code FridaDev web: `app/tools/web_search*.py`
- Benchmark: `benchmark/web-search/`, `benchmark/suites/web_search/`
- Documentation: `app/docs/states/audits/`, `app/docs/todo-todo/product/`

Cas baseline obligatoires:

- [ ] Documentation officielle Adobe Photoshop.
- [ ] Documentation officielle Adobe Illustrator.
- [ ] Renouvellement CNI / administratif francais.
- [ ] Actualite IA Europe.
- [ ] Documentation OpenRouter web search.
- [ ] Derrida / trace.
- [ ] Bourdieu / sociologie.
- [ ] Sciences exactes.
- [ ] Documentation technique.
- [ ] Cas volontairement ambigu.

Decisions utilisateur requises avant patch:

- [ ] Valider le corpus exact des 10 a 15 requetes baseline.
- [ ] Valider si la baseline doit inclure des temoins externes OpenRouter / Exa / Parallel comme comparaison non runtime.

Hors-scope:

- Modifier SearXNG.
- Modifier Crawl4AI.
- Modifier le runtime FridaDev.
- Reconfigurer Docker.
- Activer un fallback externe.

Tests/preuves attendus:

- [ ] Commandes Sauron de lecture config expurgees de tout secret.
- [ ] Rapport de resultats baseline versionne ou artefacts `/tmp` references.
- [ ] Grep securite sur les artefacts.
- [ ] `git diff --check` pour toute documentation versionnee.

Criteres de fin:

- [ ] L'etat reel est documente.
- [ ] Les limites observees sont reliees a des causes probables.
- [ ] Les phases suivantes peuvent partir d'un diagnostic partage.
- [ ] Le diagnostic est suffisant pour prioriser la suite sans devenir un audit general du web.

Risques/effets de bord:

- Confondre moteur present et moteur utilisable.
- Tirer une conclusion a partir d'une seule requete.
- Masquer un probleme SearXNG sous un patch applicatif.

### Phase 0 - consolidation 2026-05-22

Statut: consolidation Celebrimbor livree, Phase 0 globale cochee.

- [x] Note consolidee creee: `app/docs/states/audits/fridadev-local-web-search-phase-0-baseline-2026-05-22.md`.
- [x] Artefacts Lot 8 reutilises: `/tmp/fridadev-web-search-lot8-live/local.md` et `/tmp/fridadev-web-search-lot8-live/local-profiled.md`.
- [x] Diagnostic same-query reutilise: `/tmp/fridadev-web-search-same-query-diagnostic/comparison.md` et `/tmp/fridadev-web-search-same-query-diagnostic/searxng.md`.
- [x] Complement local-only lance pour Adobe Photoshop, Adobe Illustrator, Bourdieu / sociologie, sciences exactes, Microsoft Graph et Jaguar ambigu: `/tmp/fridadev-web-search-phase0-missing-local/phase0-missing-local.md`.
- [x] Hypothese confirmee: actualite IA Europe, OpenRouter docs, Derrida / trace, CNI, URL explicite, local vs local_profiled, same-query et audit stack sont deja largement couverts.
- [x] Validation utilisateur du corpus borne.
- [x] Passage Phase 1: Sauron a qualifie les moteurs SearXNG pertinents par profil, sans transformer Phase 0 en audit interminable.

Decision utilisateur: le corpus Phase 0 est valide comme baseline bornee; tout ajout ulterieur exigera une decision explicite.

Critere de passage vers Phase 1: le corpus baseline reste borne, la note consolidee sert de diagnostic unique, et les manques restants sont traites comme inventaire moteur SearXNG plutot que comme nouveau benchmark general.

## Phase 1 — Inventaire des moteurs SearXNG

Proprietaire: Sauron.

Objectif: savoir quels moteurs SearXNG sont reellement utilisables depuis l'instance OVH, pas seulement declares dans la configuration. L'inventaire reste borne aux moteurs pertinents pour les profils decides: `documentation_officielle`, `administratif_francais`, `academique`, `actualite` et `general_divers`.

Livrables:

- [x] Tableau `moteur -> utilisable / instable / a eviter / profil pertinent`.
- [x] Signalement des moteurs qui CAPTCHA.
- [x] Signalement des moteurs qui 429.
- [x] Signalement des moteurs qui repondent mais produisent du bruit dominant.
- [x] Signalement des moteurs utiles mais lents.
- [x] Recommandation de configuration gouvernee: conserver, limiter, declasser ou tester plus tard.
- [x] Justification explicite si un moteur hors profils cibles doit etre audite.

Fichiers ou zones concernes:

- `/opt/platform/searxng/settings.yml`
- `/opt/platform/searxng/limiter.toml`
- Logs conteneur SearXNG, expurges.
- Documentation SearXNG officielle pour categories, engines, `use_default_settings`, `remove` et `keep_only`.

Decisions utilisateur requises avant patch:

- [ ] Accepter ou refuser certains moteurs pour raisons politiques, juridiques ou qualite.
- [ ] Valider si certains moteurs commerciaux peuvent servir uniquement comme temoins, jamais comme dependance centrale.

Hors-scope:

- Modifier la configuration SearXNG sans decision explicite.
- Auditer les 200+ moteurs SearXNG un par un sauf necessite justifiee.
- Remplacer SearXNG.
- Ajouter OpenRouter comme compensation runtime.

Tests/preuves attendus:

- [x] Tests de requetes representatifs par moteur.
- [x] Distinction entre panne temporaire et moteur structurellement impropre.
- [x] Preuve que les erreurs, CAPTCHA et 429 ne contiennent aucun secret.

Criteres de fin:

- [x] Chaque moteur pertinent a un statut.
- [x] Chaque profil cible a au moins un panier moteur plausible ou un manque explicite.
- [x] Les moteurs problematiques sont documentes avant toute reconfiguration.

### Phase 1 - inventaire Sauron 2026-05-22

Statut: livre et archive.

- [x] Note audit creee: `app/docs/states/audits/fridadev-searxng-engine-inventory-phase-1-2026-05-22.md`.
- [x] Artefacts Sauron lus: `/tmp/fridadev-searxng-engine-inventory-phase1-20260522/bang-probes.tsv`, `engine-only-probes.tsv`, `engine-probes.tsv`.
- [x] Nuance actee: les sondes `engine-probes` peuvent agreger plus large que le moteur seul; Phase 4 doit privilegier `bang-probes` et `engine-only-probes`.
- [x] Phase 1 suffisante pour passer a Phase 2/3 cote Celebrimbor et preparer une Phase 4 Sauron separee, avec GO utilisateur explicite.

Risques/effets de bord:

- Exclure trop vite un moteur utile.
- Garder un moteur bruyant seulement parce qu'il repond.
- Confondre preference ideologique, qualite documentaire et disponibilite technique.

## Phase 2 — Definir les regimes de recherche

Proprietaire: Celebrimbor, avec decisions utilisateur.

Objectif: remplacer les profils trop generiques par des regimes de recherche explicites, petits et pilotables.

Profils initiaux:

- [x] `explicit_url`
- [x] `documentation_officielle`
- [x] `administratif_francais`
- [x] `academique`
- [x] `actualite`
- [x] `general_divers`

Livrables:

- [x] Contrat de classification deterministe.
- [x] Tests de classification par profil.
- [x] Documentation des limites de chaque profil.
- [x] Matrice profil -> intention -> sources probables -> erreurs typiques.
- [x] Regle claire: le profil ne declenche jamais le web seul.

Fichiers ou zones concernes:

- `app/tools/web_search_profile.py`
- `app/tools/web_search_query_plan.py`
- `app/tools/web_search.py`
- `app/tools/web_search_source_first.py`
- `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md`
- Tests unitaires web search.
- Documentation active de ce TODO.

Decisions utilisateur requises avant patch:

- [x] Valider que `academique` reste large: philosophie, SHS, droit, sciences exactes, medecine, informatique, etc.
- [x] Valider que les sous-profils academiques ne sont pas crees trop tot.
- [x] Valider les termes utilisateur qui doivent orienter vers `documentation_officielle` plutot que `general_divers`.

Hors-scope:

- Ajouter des sous-profils fins prematurement.
- Modifier SearXNG global.
- Activer un fallback OpenRouter / Exa / Parallel dans cette phase.
- Relancer l'auto-web lexical.

Tests/preuves attendus:

- [x] URL explicite classee `explicit_url`.
- [x] Adobe/Microsoft/Stripe/OpenRouter docs classes `documentation_officielle`.
- [x] CNI/CAF/droit administratif classes `administratif_francais`.
- [x] Derrida/Bourdieu/sciences exactes/classes universitaires classes `academique`.
- [x] Nouvelles recentes/aujourd'hui/2026 classes `actualite`.
- [x] Ambigu et quotidien classes `general_divers`.

Criteres de fin:

- [x] Les profils sont stables, lisibles et testes.
- [x] Aucun profil ne declenche une recherche sans demande web existante.
- [x] `explicit_url` reste prioritaire.

### Phase 2 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/docs, sans modification plateforme.

- [x] Profils canoniques ajoutes dans `app/tools/web_search_profile.py`.
- [x] Anciens symboles Lot 2-7 conserves comme alias applicatifs pour eviter une casse diffuse, mais les valeurs observees sont les regimes Phase 2.
- [x] Tests ajoutes/actualises pour URL explicite, documentation officielle, administratif francais, academique large, actualite, general ambigu et Q&A technique.
- [x] Spec creee: `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md`.

Risques/effets de bord:

- Sur-decouper avant d'avoir assez de preuves.
- Creer des profils qui se chevauchent sans arbitrage.
- Transformer une classification sobre en prompt cache.

## Phase 3 — Source-first

Proprietaire: Celebrimbor.

Objectif: extraire l'autorite cible et orienter la recherche vers les lieux probables d'autorite avant de faire confiance au ranking general.

Exemples obligatoires:

- [x] `documentation officielle Adobe Photoshop` -> autorite `Adobe`, produit `Photoshop`, domaines probables `helpx.adobe.com`, `developer.adobe.com`, `adobe.com`.
- [x] `documentation officielle Adobe Illustrator` -> autorite `Adobe`, produit `Illustrator`, domaines probables `helpx.adobe.com`, `developer.adobe.com`, `adobe.com`.
- [x] `documentation officielle Microsoft Graph API` -> autorite `Microsoft`, produit `Graph API`, domaine probable `learn.microsoft.com`.
- [x] `documentation officielle Stripe Checkout` -> autorite `Stripe`, produit `Checkout`, domaine probable `docs.stripe.com`.
- [x] `documentation officielle OpenRouter web search` -> autorite `OpenRouter`, produit `web search`, domaine probable `openrouter.ai/docs`.

Livrables:

- [x] Extracteur deterministe d'autorite/produit pour `documentation_officielle`.
- [x] Source map souple et testable, limitee aux cas valides; elle sert d'appoint, pas de verite.
- [x] Regle generique obligatoire: extraire l'autorite cible depuis la requete, distinguer les termes generiques (`documentation`, `officiel`, `api`, `guide`) des termes d'autorite (`Adobe`, `Microsoft`, `Stripe`, etc.), et appliquer une promotion forte seulement si domaine et autorite cible sont alignes.
- [x] Tests negatifs montrant qu'OpenRouter, Adobe ou Stripe ne sont pas promus seulement parce que le mot `documentation` est present.
- [x] Observabilite content-free des autorites detectees, hashee ou enumeree sans prompt brut si necessaire.

Fichiers ou zones concernes:

- `app/tools/web_search_profile.py`
- `app/tools/web_search_query_plan.py`
- `app/tools/web_search_rerank.py`
- `app/tools/web_search_source_first.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/observability/turn_pipeline_read_model.py`
- `app/observability/turn_observability_checklist.py`
- Tests web search.

Decisions utilisateur requises avant patch:

- [x] Valider si une source map explicite par fournisseur est acceptable.
- [ ] Valider si la source map doit etre editable par configuration future ou rester codee en V1.

Hors-scope:

- Connecteur Adobe dedie.
- API Adobe.
- Fallback externe.
- Liste vendor interminable.
- Bannissement global des tutoriels tiers.

Tests/preuves attendus:

- [x] Adobe Photoshop oriente Adobe, pas OpenRouter.
- [x] Adobe Illustrator oriente Adobe, pas OpenRouter.
- [x] Microsoft Graph oriente Microsoft Learn.
- [x] Stripe Checkout oriente Stripe docs.
- [x] OpenRouter web search oriente OpenRouter docs.
- [x] Requete documentation generique ne promeut aucun vendor fixture.
- [x] Les cas Adobe/Microsoft/Stripe/OpenRouter restent des tests de garde-fou contre l'overfit, pas des normes cachees.

Criteres de fin:

- [x] Le bonus fort depend de l'autorite nommee dans la requete.
- [x] Les termes generiques de documentation ne suffisent jamais a promouvoir fortement un domaine.
- [x] Les sources probables restent des signaux souples.
- [x] Les sources non officielles restent visibles si elles sont pertinentes.

### Phase 3 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/docs, sans modification plateforme.

- [x] Module dedie cree: `app/tools/web_search_source_first.py`.
- [x] Source-first branche dans le plan de requetes bornees et le reranking souple.
- [x] Observabilite ajoutee: `source_first_policy_kind`, `source_first_active`, `source_first_authority`, `source_first_product`, `source_first_probable_domains`, `source_first_reason_codes`.
- [x] Tests negatifs anti-overfit ajoutes pour demandes generiques `documentation officielle` / `API documentation`.
- [x] Correctif P2: l'extraction d'autorite inconnue ignore les verbes/formules de demande (`trouve`, `peux-tu`, `cherche`, `official docs for`) et reste inactive si la cible est trop floue.

Risques/effets de bord:

- Reintroduire un overfit de fixtures.
- Faire d'une source officielle une verite absolue.
- Rater les produits dont l'autorite est implicite ou ambigue.

## Phase 4 — Paniers moteurs SearXNG gouvernes

Proprietaire: Celebrimbor pour le panier applicatif; Sauron uniquement pour une reconfiguration plateforme future.

Objectif: gouverner les moteurs demandes a SearXNG par regime depuis FridaDev, sans modifier la configuration globale SearXNG. La reconfiguration plateforme `use_default_settings` / `remove` / `keep_only` reste un lot Sauron optionnel, non lance ici.

Gate obligatoire: aucune modification plateforme ne peut etre lancee sans GO utilisateur explicite.

Note d'archive: les cases ouvertes liees a `use_default_settings`, backup, `docker compose config --quiet`, restart SearXNG et rollback plateforme relevent d'une option future hors cloture. La Phase 4 livree ici est strictement applicative; elle n'a pas modifie SearXNG global.

Livrables:

- [x] Paniers applicatifs par regime: `documentation_officielle`, `administratif_francais`, `academique`, `actualite`, `general_divers`, `explicit_url`.
- [x] Distinction parametres durs (`engines`, `categories`, `language`, `time_range`, `safesearch`) / signaux souples (source-first, reranking, downrank).
- [x] Observabilite content-free: `searxng_profile_params_kind`, `searxng_profile_params_policy`, `searxng_categories`, `searxng_engines`, `searxng_time_range`, `searxng_language`, `searxng_safesearch`, `searxng_params_reason_codes`, `searxng_hard_parameters`, `searxng_soft_signal_policy`.
- [x] Sondage Mojeek en lecture seule.
- [x] Spec Phase 4 creee: `app/docs/states/specs/fridadev-web-search-searxng-engine-baskets-contract.md`.
- [ ] Audit plateforme de `use_default_settings: true` si l'utilisateur demande explicitement une reconfiguration globale.
- [ ] Proposition Sauron avant toute modification plateforme: config actuelle, config cible, diff attendu, risques, rollback et fenetre de restart.
- [ ] Backup obligatoire avant toute modification plateforme.
- [ ] Validation `docker compose config --quiet` uniquement si Compose est touche.
- [ ] Restart SearXNG uniquement apres decision utilisateur explicite.

Fichiers ou zones concernes:

- `app/tools/web_search_searxng_params.py`
- `app/tools/web_search.py`
- Tests web search.
- `app/docs/states/specs/fridadev-web-search-searxng-engine-baskets-contract.md`
- Plateforme SearXNG seulement en lecture/sonde sous discipline Sauron.
- `/opt/platform/searxng/settings.yml`, `/opt/platform/searxng/limiter.toml`, `/opt/platform/docker-compose.yml` restent hors patch sans GO utilisateur.
- Documentation operatoire versionnee cote FridaDev si les attentes produit changent.

Decisions utilisateur requises avant patch:

- [x] Valider une Phase 4 applicative avant reconfiguration plateforme.
- [ ] Decider si une reconfiguration globale SearXNG doit etre lancee plus tard.
- [ ] Valider la fenetre de restart si et seulement si Sauron modifie la plateforme.

Hors-scope:

- Modifier la configuration globale SearXNG.
- Embarquer un changement de configuration plateforme dans un lot applicatif Celebrimbor.
- Afficher des secrets.
- Changer Caddy, Authelia ou les reseaux sans demande explicite.
- Remplacer SearXNG.
- Activer un fallback OpenRouter / Exa / Parallel dans cette phase.

Tests/preuves attendus:

- [x] `/config` SearXNG lu en lecture seule pour confirmer Mojeek.
- [x] Sondes Mojeek bornees via `engines=mojeek` et `!mjk`, sans secret: `/tmp/fridadev-mojeek-probe-phase4/mojeek-probe.md`.
- [x] Tests unitaires des paniers applicatifs.
- [x] Preuve que `explicit_url` garde le comportement historique.
- [ ] Backup plateforme, `docker compose config --quiet`, smoke SearXNG apres restart: uniquement si une Phase 4 plateforme future est decidee.

Criteres de fin:

- [x] Les paniers moteurs par regime sont explicites, testes et observables.
- [x] Les changements applicatifs sont documentes.
- [x] `local` benchmark peut garder la baseline historique via flags; `local_profiled` porte les paniers gouvernes.
- [ ] Une configuration SearXNG globale gouvernee et rollbackable reste optionnelle, sous Sauron.

Risques/effets de bord:

- Casser la disponibilite SearXNG.
- Reduire trop fortement la diversite de sources.
- Confondre reconfiguration technique et doctrine documentaire.
- Surestimer un moteur desactive globalement mais appelable explicitement.

### Phase 4 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/runtime, sans modification plateforme.

Paniers retenus:

- `explicit_url`: historique; pas de recherche ouverte sur lecture directe.
- `documentation_officielle`: `categories=general,it`, `engines=microsoft learn,mdn,docker hub,bing,brave,mojeek`, `language=all`.
- `administratif_francais`: `categories=general`, `engines=bing,brave`, `language=fr-FR`.
- `academique`: `categories=general,science`, `engines=arxiv,openairepublications,pubmed,bing,brave`, `language=all`.
- `actualite`: `categories=general,news`, `engines=bing news,reuters,bing,duckduckgo news`, `language=fr-FR`, `time_range=year`.
- `general_divers`: `categories=general`, `engines=bing,brave,mojeek`, `language=fr-FR`.

Mojeek:

- [x] Expose par `/config` sous les noms `mojeek`, `mojeek images`, `mojeek news`, mais desactive globalement.
- [x] `engines=mojeek` repond sur sondes bornees general/documentation.
- [x] `!mjk` est instable: une sonde a retourne `acces refuse`.
- [x] Retenu comme candidat secondaire `documentation_officielle` et `general_divers`.
- [x] Non retenu pour `actualite`, `administratif_francais` ou `academique` en V1.

## Phase 5 — Parametres FridaDev par profil

Proprietaire: Celebrimbor.

Objectif: ne plus envoyer tous les profils dans un comportement equivalent a `categories=general`, et aligner les parametres applicatifs sur les regimes de recherche.

Note 2026-05-22: la Phase 4 applicative a deja livre les paniers `categories` / `engines` / `language` / `time_range` par regime. La Phase 5 reste ouverte pour les ajustements fins: domaines attendus/declasses, budgets crawl, latence cible, observabilite supplementaire et arbitrages utilisateur qui ne doivent pas etre melanges au patch moteur Phase 4.

Profils a couvrir:

- [x] `explicit_url`
- [x] `documentation_officielle`
- [x] `administratif_francais`
- [x] `academique`
- [x] `actualite`
- [x] `general_divers`

Pour chaque profil, preciser:

- [x] `categories`
- [x] `engines`
- [x] `language`
- [x] `time_range`
- [x] domaines attendus
- [x] domaines secondaires
- [x] domaines a declasser
- [x] budget crawl
- [x] latence cible
- [x] observabilite

Livrables:

- [x] Politique applicative par profil.
- [x] Tests des parametres effectifs.
- [x] Observabilite content-free des parametres envoyes.
- [x] Preuve que `explicit_url` ne passe pas par les parametres de recherche ouverte.
- [x] Preuve que `general_divers` reste sobre et pluraliste.

Fichiers ou zones concernes:

- `app/tools/web_search_searxng_params.py`
- `app/tools/web_search_query_plan.py`
- `app/tools/web_search.py`
- Tests web search.
- Benchmark local.

Decisions utilisateur requises avant patch:

- [x] Valider les couples profil -> categories.
- [x] Valider les moteurs autorises par profil si Sauron les a qualifies.
- [x] Valider les budgets crawl et latence cible.
- [x] Acter que SUD/CGT/Solidaires sont des sources situees secondaires, jamais autorite administrative souveraine.
- [x] Acter que l'insuffisance de preuve est un signal applicatif, pas une reponse scriptee ni un fallback externe.

Hors-scope:

- Modifier SearXNG global.
- Ajouter BM25 ou cache policy.
- Activer un fallback OpenRouter / Exa / Parallel dans cette phase.
- Faire du reranking fort sans Phase 6.

Tests/preuves attendus:

- [x] `documentation_officielle` cible docs/source primaire sans vendor fixture.
- [x] `administratif_francais` garde langue francaise et sources institutionnelles probables.
- [x] `academique` ne se limite pas a la philosophie.
- [x] `actualite` garde fraicheur sans exclure les sources officielles.
- [x] `general_divers` conserve un comportement historique ou quasi historique.
- [x] Observabilite sans requete brute, prompt brut, secret ou contenu crawle.

Criteres de fin:

- [x] Les profils ont des parametres lisibles et reversibles.
- [x] Les parametres durs sont justifies.
- [x] Les signaux souples sont distingues.

### Phase 5 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/runtime, sans modification plateforme.

- [x] Module dedie cree: `app/tools/web_search_profile_policy.py`.
- [x] Spec creee: `app/docs/states/specs/fridadev-web-search-profile-policy-contract.md`.
- [x] Documentation officielle: source-first strict quand une autorite nommee expose des domaines probables; ouverte assistee sans domaine invente quand l'autorite est inconnue ou floue.
- [x] Administratif francais: sources officielles et Education nationale attendues; SUD, CGT et Solidaires visibles comme contrepoints situes secondaires, jamais preuve administrative souveraine.
- [x] Academique: profil large confirme pour SHS, philosophie, droit, sciences exactes, medical/sciences du vivant et informatique.
- [x] Budgets web manuel appliques: `actualite` et `general_divers` capes a 2 resultats crawles; profils specialises capes a 3; chars par profil capes entre 4500 et 8000 selon le regime.
- [x] Cible latence normale actee: 20 a 25 secondes; une recherche plus longue devra devenir un mode explicite futur.
- [x] Signal de preuve insuffisante ajoute: `profile_insufficient_evidence`, reason codes, presence de source attendue, presence de source situee, compteurs domaines.
- [x] La confiance locale peut refleter ce signal, mais ne declenche aucun fallback OpenRouter / Exa / Parallel.
- [x] Observabilite propagee dans le payload web, le noeud hermeneutique, le read model pipeline et la checklist.

Risques/effets de bord:

- Enfermer un profil dans un moteur ou domaine unique.
- Degrader les cas ambigus.
- Durcir une preference documentaire sans decision humaine.

## Phase 6 — Reranking explicable

Proprietaire: Celebrimbor.

Objectif: ordonner un bon panier de resultats, pas sauver un mauvais panier ni censurer silencieusement le web.

Regles a couvrir:

- [x] Source officielle devant SEO quand l'autorite est alignee avec la demande.
- [x] Source primaire devant resume.
- [x] Institution devant forum quand le profil le demande.
- [x] Academique devant dictionnaire quand le profil est academique.
- [x] Dictionnaire possible comme appoint definitionnel, pas autorite finale.
- [x] Reason codes lisibles.
- [x] Aucun bannissement invisible.
- [x] Diversite minimale de domaines.

Livrables:

- [x] Reranking explicable par profil.
- [x] Reason codes content-free.
- [x] Tests positifs par profil.
- [x] Tests negatifs anti-overfit.
- [x] Tests de preservation de la diversite.
- [x] Observabilite avant/apres rerank.

Fichiers ou zones concernes:

- `app/tools/web_search_rerank.py`
- `app/tools/web_search_confidence.py`
- `app/tools/web_search.py`
- Tests web search.
- Benchmark local.

Decisions utilisateur requises avant patch:

- [x] Valider les domaines a declasser par profil.
- [x] Valider les sources qui peuvent rester comme appoint.
- [x] Valider les reason codes exposables.

Hors-scope:

- Supprimer brutalement tous les resultats hors profil.
- Faire du score de confiance un declencheur.
- Appeler OpenRouter / Exa / Parallel comme fallback ou decision de reranking.
- Corriger par reranking un panier SearXNG manifestement mauvais sans le dire.

Tests/preuves attendus:

- [x] Documentation officielle alignee promue devant tutoriel SEO.
- [x] CNI/CAF institutionnel promu devant conjugueur/dictionnaire hors sujet.
- [x] Source academique alignee promue devant dictionnaire generaliste.
- [x] Dictionnaire conserve comme appoint inspectable, pas autorite finale.
- [x] Aucun domaine unique impose.
- [x] Reason codes sans contenu brut.

Criteres de fin:

- [x] Le reranking explique le mouvement des sources.
- [x] Les sources declassees restent inspectables.
- [x] Le comportement ne depend pas de fixtures cachees.

### Phase 6 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/runtime, sans modification plateforme.

- [x] Spec creee: `app/docs/states/specs/fridadev-web-search-reranking-contract.md`.
- [x] Le reranker utilise la politique Phase 5: domaines attendus, secondaires, situes et declasses.
- [x] Documentation officielle: source-first et domaines attendus ne promeuvent que l'autorite nommee; OpenRouter ne bat pas Adobe/Microsoft/Stripe hors alignement.
- [x] Administratif francais: sources officielles et Education nationale sont promues quand alignees; SUD/CGT/Solidaires restent visibles comme sources situees, pas autorite administrative.
- [x] Academique: profil large confirme; PubMed/arXiv/OpenAIRE/HAL/OpenEdition/Cairn/Persee/DOI peuvent etre promus selon sujet.
- [x] Actualite: fraicheur et source institutionnelle alignee peuvent passer devant une news generique; Reuters reste utile mais non souverain.
- [x] `general_divers`: downrank leger des conjugueurs/dictionnaires accidentels et preservation de diversite, sans source imposee.
- [x] Reason codes ajoutes ou stabilises: `profile_expected_domain_soft_bonus`, `profile_secondary_domain_soft_bonus`, `profile_situated_secondary_visible_not_authority`, `profile_downrank_domain_soft_penalty`, `source_first_expected_domain_soft_bonus`, `official_source_soft_bonus`, `academic_source_soft_bonus`, `freshness_soft_bonus`, `qa_soft_downrank`, `domain_diversity_soft_adjustment`.
- [x] Le reranking reste sans suppression dure, sans fallback externe et sans score de confiance actionnable.

Risques/effets de bord:

- Fabriquer une police invisible des sources legitimes.
- Rendre invisible une source contestataire mais pertinente.
- Surponderer le label officiel au lieu de l'alignement avec la requete.

## Phase 7 — Comportement d'echec

Proprietaire: Celebrimbor.

Objectif: quand Frida ne trouve pas de source solide, elle doit le dire clairement au lieu de combler l'incertitude.

Comportement attendu:

- Frida doit pouvoir repondre meme si la recherche est fragile, mais en disant clairement que les preuves sont insuffisantes, partielles ou non concluantes.
- La formulation finale reste naturelle et produite par le LLM; pas de phrase d'echec figee ni generique.
- Frida peut proposer de reformuler ou relancer la recherche si cela aide.
- Frida peut demander une URL seulement quand cela a vraiment du sens, sans en faire le reflexe par defaut.

Livrables:

- [x] Contrat de formulation d'echec.
- [x] Signal de confiance visible, non souverain, non actionnable automatiquement.
- [x] Distinction entre aucun resultat, resultats non lus, crawl pauvre, sources peu fiables et conflit de sources.
- [x] Tests de non-fallback externe.
- [x] Observabilite content-free de l'echec.

Fichiers ou zones concernes:

- `app/tools/web_search_evidence.py`
- `app/tools/web_search_confidence.py`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/core/web_read_state.py`
- Observabilite web.
- Tests serveur/chat web.

Decisions utilisateur requises avant patch:

- [x] Choisir le comportement prioritaire: repondre avec prudence quand c'est possible, dire les preuves insuffisantes ou fragiles, proposer une reformulation si pertinent.
- [x] Valider que la formulation reste naturelle et produite par le LLM, sans phrase d'echec figee ni generique.
- [x] Valider que la demande d'URL reste seulement contextuelle et non reflexe par defaut.

Hors-scope:

- Fallback OpenRouter / Exa / Parallel.
- Auto-web lexical.
- Changement de prompts generaux sans necessite contractuelle.
- Score de confiance souverain.

Tests/preuves attendus:

- [x] Echec web visible sans hallucination de source.
- [x] URL explicite echouee conserve son `read_state`.
- [x] Aucun appel externe n'est declenche.
- [x] La formulation d'echec n'est pas hardcodee dans le runtime.
- [x] Logs sans requete brute si le contrat l'interdit.

Criteres de fin:

- [x] Frida sait dire qu'elle n'a pas prouve.
- [x] L'utilisateur peut recevoir une proposition de reformulation ou relance quand utile.
- [x] La confiance ne gouverne pas automatiquement le systeme.

### Phase 7 - livraison Celebrimbor 2026-05-22

Statut: livre applicatif/runtime, sans modification plateforme.

- [x] Module dedie cree: `app/tools/web_search_evidence.py`.
- [x] Spec creee: `app/docs/states/specs/fridadev-web-search-evidence-failure-contract.md`.
- [x] Le signal distingue `no_results`, `results_found_but_not_read`, `snippet_only_material`, `crawl_poor_or_absent`, `expected_source_material_missing`, `situated_secondary_without_official_material`, `mixed_source_signals_visible` et les `read_state` explicites non lus.
- [x] Le prompt recoit `[GARDE DE PREUVE WEB]` seulement quand le statut est `partial` ou `insufficient`; ce bloc donne des consignes, pas une phrase finale scriptée.
- [x] `web_evidence_external_fallback_used` reste toujours `false`; la confiance ne declenche aucun fallback OpenRouter / Exa / Parallel. Depuis la decision produit du 2026-05-22, Exa peut etre provider de decouverte configure, expose via `web_discovery_*`.
- [x] Observabilite propagee dans le payload web, l'input canonique, le noeud hermeneutique, le read model pipeline et la checklist.
- [x] Correctif P2: les hard guards web respectent `web_evidence_can_answer`; ils peuvent exiger `caveat_required` sans interdire `answer`, tout en conservant `answer_forbidden` quand le contrat de preuve ne permet pas de repondre.

Risques/effets de bord:

- Rendre Frida trop timide sur des resultats suffisants.
- Rendre l'echec trop verbeux.
- Glisser vers un fallback externe sous couvert d'assistance.

## Phase 8 — Benchmark final

Proprietaire: Sauron + Celebrimbor.

Objectif: comparer l'ancien local et le nouveau local pour decider si la reconstruction locale a vraiment ameliore la recherche.

Cas obligatoires:

- [x] Documentation officielle Adobe Photoshop.
- [x] Documentation officielle Adobe Illustrator.
- [x] Renouvellement CNI.
- [x] Education nationale / obligation administrative.
- [x] Actualite IA Europe.
- [x] OpenRouter docs.
- [x] Derrida / trace.
- [x] Bourdieu / sociologie.
- [x] Sciences exactes / medical: CRISPR / PubMed.
- [x] Documentation technique: Microsoft Graph API.
- [x] Divers volontairement ambigu: Jaguar.
- [x] URL explicite / lecture directe.

Livrables:

- [x] Rapport ancien local vs nouveau local.
- [x] Analyse par cas: qualite sources, autorite, bruit, crawl, extraits, latence.
- [x] Analyse des echecs restants.
- [x] Comparaison facultative avec OpenRouter / Exa / Parallel comme temoins externes pendant la mesure Phase 8 locale; les artefacts Lot 8/same-query restent les preuves externes.
- [x] Decision produit initiale Phase 8: continuer en runtime exclusivement local et corriger qualite/confiance avant cloture Phase 9.
- [x] Decision produit remplacee le 2026-05-22: basculer la decouverte ouverte vers OpenRouter/Exa quand configure, sans fallback automatique et sans changer la lecture Crawl4AI locale.

Fichiers ou zones concernes:

- `benchmark/web-search/`
- `benchmark/suites/web_search/`
- `app/docs/states/audits/`
- `app/docs/todo-todo/product/`

Decisions utilisateur requises avant patch:

- [x] Valider si les temoins externes OpenRouter / Exa / Parallel sont relances: non pour cette Phase 8 locale, afin de mesurer l'ancien local vs le nouveau local sans cout externe.
- [x] Valider le budget cout/latence pour le benchmark Phase 8 initial: local-only, latence observee sous la cible 20-25 secondes.
- [x] Valider le seuil qualitatif de passage: non atteint pour cloture Phase 9 directe.

Hors-scope historique de la mesure Phase 8:

- Activer OpenRouter / Exa / Parallel dans le runtime pendant la mesure.
- Modifier la recherche pendant la mesure.
- Transformer un temoin externe en option produit.

Tests/preuves attendus:

- [x] Dry-run benchmark.
- [x] Run live local borne.
- [x] Grep securite sur artefacts.
- [x] Rapport versionne ou artefacts `/tmp` references explicitement.
- [x] `git diff --check` si documentation versionnee.

Criteres de fin:

- [x] Le nouveau local est compare a l'ancien local.
- [x] Les gains et pertes sont nommes.
- [x] Les limites restantes ne sont pas deguisees en succes.
- [x] Le nouveau local n'est pas declare pret: Phase 9 reste ouverte avec correctifs qualite/confiance requis.

### Phase 8 - livraison Celebrimbor 2026-05-22

Statut: benchmark final livre, sans modification runtime ni plateforme; cloture Phase 9 non autorisee en l'etat.

- [x] Artefacts crees:
  - `/tmp/fridadev-web-search-phase8-final/local.md`
  - `/tmp/fridadev-web-search-phase8-final/local-profiled.md`
  - `/tmp/fridadev-web-search-phase8-final/comparison.md`
  - `/tmp/fridadev-web-search-phase8-final/phase8-final.json`
- [x] Note versionnee: `app/docs/states/audits/fridadev-web-search-phase-8-final-benchmark-2026-05-22.md`.
- [x] Gains observes: URL explicite stable, CNI mieux ordonne, Microsoft Graph atteint `learn.microsoft.com`, OpenRouter docs stable.
- [x] Echecs bloquants: Adobe Illustrator, actualite IA Europe, Bourdieu / sociologie, CRISPR / PubMed, Derrida / trace.
- [x] Finding qualite: certains paniers/requetes `local_profiled` produisent du bruit hors sujet.
- [x] Finding confiance: `web_confidence_level=high` reste possible sur des paniers manifestement mauvais.
- [x] Decision initiale, desormais remplacee: garder un runtime exclusivement local, ne pas activer OpenRouter / Exa / Parallel, ouvrir un correctif local avant cloture Phase 9.
- [x] Decision remplacee: OpenRouter/Exa devient provider de decouverte ouverte; Parallel reste hors runtime; SearXNG reste provider local/baseline/fallback operateur.

Risques/effets de bord:

- Lire le benchmark comme concours de score au lieu de diagnostic.
- Confondre qualite d'index externe et doctrine produit.
- Masquer la dependance opaque des temoins externes.

## Phase 9 — Validation et deploiement Exa discovery

Proprietaire: Sauron + Celebrimbor.

Objectif: valider puis deployer proprement la decision produit active: web manuel seulement, URL explicite locale directe, recherche ouverte via OpenRouter/Exa discovery quand configure, lecture Crawl4AI locale et signaux FridaDev inchanges.

Note d'archive: cette phase est close par la validation finale ci-dessous. Les limites connues restent documentees, mais ne sont pas des cases actives de ce chantier.

Livrables:

- [x] Validation: web desactive = aucun appel web.
- [x] Validation: URL explicite = lecture locale directe, Exa non appele.
- [x] Validation: recherche ouverte = Exa discovery puis Crawl4AI local.
- [x] Mesure: nombre d'appels Exa par tour via `query_count`, `secondary_query_count` et `provider_caller=web_discovery`.
- [x] Mesure: latence et cout sur corpus borne.
- [x] Verification corpus: Adobe Photoshop / Illustrator, CNI, actualite institutionnelle Europe, OpenRouter docs, cas academique SHS et sciences.
- [x] Documentation des limites restantes: cout Exa, latence proche du plafond, Crawl4AI parfois faible sur PDF ou pages institutionnelles.
- [x] Decision operateur sur la variable runtime OVH: defaut applicatif `openrouter_exa`, rollback explicite vers `local`.
- [x] Rapport final de validation Phase 9.
- [x] Rollback connu: revenir a `WEB_SEARCH_DISCOVERY_PROVIDER=local`.

### Phase 9 - validation live bornee 2026-05-22

Statut historique au moment du premier smoke: preuve live minimale livree, Phase 9 globale encore ouverte avant la validation finale ci-dessous.

- [x] Note versionnee: `app/docs/states/audits/fridadev-web-search-phase-9-live-validation-2026-05-22.md`.
- [x] Artefacts temporaires: `/tmp/fridadev-web-search-phase9-live-validation/phase9-live.json` et `/tmp/fridadev-web-search-phase9-live-validation/phase9-live.md`.
- [x] Web desactive: `status=skipped`, `query_count=0`, aucun appel `web_discovery`.
- [x] URL explicite OpenRouter docs: `collection_path=explicit_url_direct`, `read_state=page_read`, provider effectif `local`, Exa non appele.
- [x] Recherche ouverte Adobe Photoshop: provider effectif `openrouter_exa`, 3 appels `provider_caller=web_discovery`, domaines Adobe attendus en tete.
- [x] Recherche ouverte CNI: provider effectif `openrouter_exa`, 3 appels `provider_caller=web_discovery`, Service Public et ANTS en tete.
- [x] Recherche ouverte actualite institutionnelle IA Europe: provider effectif `openrouter_exa`, 3 appels `provider_caller=web_discovery`, domaines institutionnels europeens en tete.
- [x] Cout observe sur les appels discovery quand renvoye par OpenRouter: environ `0.0323275` USD pour Adobe Photoshop, `0.030591` USD pour CNI, `0.04451625` USD pour actualite IA Europe.
- [x] Latence observee: environ 1,6 s pour URL explicite, 16,4 a 21,9 s pour recherches ouvertes du smoke.
- [x] Grep securite des artefacts `/tmp` vide pour cles, tokens, headers sensibles, fichier environnement, data URL et base64.

Limites identifiees par le premier smoke:

- [x] Adobe Illustrator et cas academiques etaient absents du premier micro-smoke; ils sont couverts par la validation finale.
- [x] Limites Crawl4AI PDF/pages institutionnelles documentees: une page ou PDF peut rester non lu, ce qui exige caveat si son snippet est injecte.
- [x] Calibration confiance corrigee: `crawl_failed_prompt_material_used` force evidence `partial` et confiance au plus `medium`; une erreur non utilisee reste observable sans punition aveugle.

### Phase 9 - validation finale 2026-05-22

Statut: corpus final borne valide, rollback documente, Phase 9 cloturee.

- [x] Commit code de calibration: `Calibrate web confidence for partial crawl failures`.
- [x] Note versionnee: `app/docs/states/audits/fridadev-web-search-phase-9-final-validation-2026-05-22.md`.
- [x] Artefacts temporaires: `/tmp/fridadev-web-search-phase9-final-validation/phase9-final.json` et `/tmp/fridadev-web-search-phase9-final-validation/phase9-final.md`.
- [x] Web desactive: aucun appel provider.
- [x] URL explicite OpenRouter docs: provider effectif `local`, aucun appel `web_discovery`, `read_state=page_read`.
- [x] Adobe Photoshop docs: provider `openrouter_exa`, 3 appels `web_discovery`, domaines Adobe attendus, evidence `partial`, confiance `medium`.
- [x] Adobe Illustrator docs: provider `openrouter_exa`, 3 appels `web_discovery`, domaines Adobe attendus, evidence `partial`, confiance `medium`.
- [x] Renouvellement CNI: provider `openrouter_exa`, 3 appels `web_discovery`, Service Public / ANTS, evidence `partial`, confiance `medium`.
- [x] Actualite institutionnelle IA Europe: provider `openrouter_exa`, 3 appels `web_discovery`, sources institutionnelles europeennes lues, evidence `sufficient`, confiance `high`.
- [x] OpenRouter docs: provider `openrouter_exa`, 3 appels `web_discovery`, domaine `openrouter.ai`, evidence `partial`, confiance `medium`.
- [x] Bourdieu / sociologie: provider `openrouter_exa`, 3 appels `web_discovery`, sources SHS, evidence `partial`, confiance `medium`.
- [x] CRISPR / PubMed: provider `openrouter_exa`, 3 appels `web_discovery`, sources scientifiques, evidence `partial`, confiance `medium`.
- [x] Couts observes: environ `0.264846` USD pour 21 appels `web_discovery` sur le corpus final.
- [x] Latences observees: environ 1,7 s pour URL explicite; 19,1 a 32,2 s pour recherches ouvertes du corpus final.
- [x] Grep securite des artefacts `/tmp` et notes Phase 9 vide pour cles, tokens, cookies, headers sensibles, fichiers environnement, data URL et base64.
- [x] Rollback operateur documente: revenir a `WEB_SEARCH_DISCOVERY_PROVIDER=local`, puis redeployer uniquement l'app si l'environnement change.

Fichiers ou zones concernes:

- `/opt/platform/fridadev/`
- `/opt/platform/fridadev-app/`
- settings/runtime applicatifs lies a `WEB_SEARCH_DISCOVERY_PROVIDER`
- Documentation de suivi dans `app/docs/states/` ou `app/docs/todo-done/` selon cloture.

Decisions utilisateur requises avant patch:

- [x] Valider la decision produit: OpenRouter/Exa comme provider de decouverte URL configure pour la recherche ouverte.
- [x] Valider fenetre de deploiement applicatif: rebuild `fridadev` uniquement apres patch runtime.
- [x] Valider rollback operateur vers `local`.
- [x] Valider si le chantier actif peut etre archive apres preuves.

Hors-scope:

- Redemarrer Caddy, Authelia, Homepage ou DB sans necessite explicite.
- Afficher secrets, fichiers environnement, tokens, DSN complets ou temoins de session.
- Lancer un nouveau chantier produit dans le meme commit.
- Modifier SearXNG global ou Crawl4AI global.
- Activer Parallel dans le runtime.
- Transformer Exa en fallback declenche par la confiance.

Tests/preuves attendus:

- [x] `git status --short --branch`
- [x] `git diff --check`
- [x] Tests applicatifs pertinents.
- [x] `docker compose up -d --build fridadev` apres patch runtime.
- [x] `docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
- [x] `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | grep -vi "set-cookie" | sed -n '1,12p'`
- [x] Smoke web manuel borne apres calibration confiance/evidence.
- [x] Grep securite sur artefacts de validation: pas de cle, token, temoin de session, fichier environnement, header d'autorisation ou dump de contenu.

Criteres de fin:

- [x] Le provider de decouverte effectif est lisible.
- [x] Les validations web desactive / URL explicite / recherche ouverte sont lisibles.
- [x] Les couts et latences Exa sont mesures sur corpus borne.
- [x] Les preuves live sont lisibles.
- [x] Le rollback est documente.
- [x] Le TODO est archive comme chantier produit clos.

Risques/effets de bord:

- Confondre provider configure et fallback automatique.
- Masquer le cout Exa sous l'observabilite locale.
- Melanger patch applicatif et patch plateforme sans coordination.
- Rebuild inutile sur docs-only.
- Perdre la frontiere entre diagnostic benchmark et strategie produit.
