# FridaDev - reconstruction locale de la recherche web - TODO A-Z

Statut: actif, non lance runtime.

Ce document devient la source-of-truth operatoire pour reconstruire la recherche web locale FridaDev de A a Z, apres le durcissement V0 SearXNG + Crawl4AI et le benchmark Lot 8 du 2026-05-22.

References a relire avant toute phase:

- Audit stack locale web: `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`
- Benchmark final Lot 8: `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`
- TODO hardening V0 terminee: `app/docs/todo-todo/product/fridadev-local-web-search-hardening-todo.md`
- Benchmark web: `benchmark/web-search/README.md`

## Doctrine produit

- FridaDev web runtime reste local uniquement.
- Pas d'hybride runtime.
- Pas de fallback OpenRouter / Exa / Parallel dans FridaDev.
- SearXNG sert a decouvrir des URLs.
- Crawl4AI sert a lire et crawler les URLs.
- OpenRouter / Exa / Parallel peuvent rester des temoins externes de benchmark, jamais une strategie produit runtime.
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
- [ ] Phase 4 — Reconfig SearXNG gouvernee
- [ ] Phase 5 — Parametres FridaDev par profil
- [ ] Phase 6 — Reranking explicable
- [ ] Phase 7 — Comportement d'echec
- [ ] Phase 8 — Benchmark final
- [ ] Phase 9 — Deploiement

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

- [ ] Choisir par profil entre recherche ouverte assistee et source-first stricte.
- [x] Valider les moteurs SearXNG acceptes politiquement et techniquement, au moins partiellement apres Phase 1.
- [x] Valider les sources legitimes pour l'actualite.
- [x] Valider les sources legitimes pour l'administratif francais.
- [x] Valider les sources legitimes pour l'academique.
- [x] Valider les sources legitimes pour la documentation officielle.
- [ ] Accepter ou refuser des listes de domaines par profil.
- [ ] Fixer une latence maximale cible pour un tour web manuel.
- [ ] Fixer le comportement d'echec: demander une URL, elargir la recherche, ou dire non prouve.

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

Frida ne doit pas transformer un ranking opaque en verite. La contestabilite doit rester possible: sources visibles, raisons lisibles, echec dicible, aucun fallback externe automatique.

## Phase 0 — Etat des lieux reel

Proprietaire: Sauron + Celebrimbor.

Objectif: figer l'etat actuel avant toute nouvelle reconstruction, pour ne pas corriger une image fantasmee de la stack. La Phase 0 doit produire un diagnostic suffisant pour agir, pas une cartographie exhaustive du web.

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
- Activer OpenRouter / Exa / Parallel.
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

## Phase 4 — Reconfig SearXNG gouvernee

Proprietaire: Sauron.

Objectif: sortir d'un heritage SearXNG incontrole si l'etat des lieux prouve qu'il penalise la recherche locale.

Gate obligatoire: cette phase ne peut pas etre lancee sans GO utilisateur explicite.

Livrables:

- [ ] Audit de `use_default_settings: true`.
- [ ] Proposition `remove` / `keep_only` selon la documentation officielle SearXNG.
- [ ] Proposition Sauron avant modification: config actuelle, config cible, diff attendu, risques, rollback et fenetre de restart.
- [ ] Backup obligatoire avant toute modification.
- [ ] Plan de rollback documente.
- [ ] Validation `docker compose config --quiet` quand applicable.
- [ ] Restart SearXNG uniquement apres decision utilisateur explicite.
- [ ] Rapport de comparaison avant/apres.

Fichiers ou zones concernes:

- `/opt/platform/searxng/settings.yml`
- `/opt/platform/searxng/limiter.toml`
- `/opt/platform/docker-compose.yml`
- Documentation operatoire versionnee cote FridaDev si les attentes produit changent.

Decisions utilisateur requises avant patch:

- [ ] Decider si cette phase est lancee.
- [ ] Valider la liste de moteurs a conserver, retirer ou garder en observation.
- [ ] Valider la fenetre de restart.

Hors-scope:

- Lancer cette phase automatiquement depuis ce TODO.
- Embarquer un changement de configuration plateforme dans un lot applicatif Celebrimbor.
- Afficher des secrets.
- Changer Caddy, Authelia ou les reseaux sans demande explicite.
- Remplacer SearXNG.

Tests/preuves attendus:

- [ ] Backup reference sans contenu secret expose.
- [ ] `docker compose config --quiet` si Compose est touche.
- [ ] Requetes de smoke SearXNG apres restart.
- [ ] Baseline courte avant/apres.

Criteres de fin:

- [ ] La configuration effective est gouvernee et rollbackable.
- [ ] Les changements sont documentes.
- [ ] Sauron confirme la sante plateforme.

Risques/effets de bord:

- Casser la disponibilite SearXNG.
- Reduire trop fortement la diversite de sources.
- Confondre reconfiguration technique et doctrine documentaire.

## Phase 5 — Parametres FridaDev par profil

Proprietaire: Celebrimbor.

Objectif: ne plus envoyer tous les profils dans un comportement equivalent a `categories=general`, et aligner les parametres applicatifs sur les regimes de recherche.

Profils a couvrir:

- [ ] `explicit_url`
- [ ] `documentation_officielle`
- [ ] `administratif_francais`
- [ ] `academique`
- [ ] `actualite`
- [ ] `general_divers`

Pour chaque profil, preciser:

- [ ] `categories`
- [ ] `engines`
- [ ] `language`
- [ ] `time_range`
- [ ] domaines attendus
- [ ] domaines a declasser
- [ ] budget crawl
- [ ] observabilite

Livrables:

- [ ] Politique applicative par profil.
- [ ] Tests des parametres effectifs.
- [ ] Observabilite content-free des parametres envoyes.
- [ ] Preuve que `explicit_url` ne passe pas par les parametres de recherche ouverte.
- [ ] Preuve que `general_divers` reste sobre et pluraliste.

Fichiers ou zones concernes:

- `app/tools/web_search_searxng_params.py`
- `app/tools/web_search_query_plan.py`
- `app/tools/web_search.py`
- Tests web search.
- Benchmark local.

Decisions utilisateur requises avant patch:

- [ ] Valider les couples profil -> categories.
- [ ] Valider les moteurs autorises par profil si Sauron les a qualifies.
- [ ] Valider les budgets crawl et latence cible.

Hors-scope:

- Modifier SearXNG global.
- Ajouter BM25 ou cache policy.
- Activer OpenRouter / Exa / Parallel.
- Faire du reranking fort sans Phase 6.

Tests/preuves attendus:

- [ ] `documentation_officielle` cible docs/source primaire sans vendor fixture.
- [ ] `administratif_francais` garde langue francaise et sources institutionnelles probables.
- [ ] `academique` ne se limite pas a la philosophie.
- [ ] `actualite` garde fraicheur sans exclure les sources officielles.
- [ ] `general_divers` conserve un comportement historique ou quasi historique.
- [ ] Observabilite sans requete brute, prompt brut, secret ou contenu crawle.

Criteres de fin:

- [ ] Les profils ont des parametres lisibles et reversibles.
- [ ] Les parametres durs sont justifies.
- [ ] Les signaux souples sont distingues.

Risques/effets de bord:

- Enfermer un profil dans un moteur ou domaine unique.
- Degrader les cas ambigus.
- Durcir une preference documentaire sans decision humaine.

## Phase 6 — Reranking explicable

Proprietaire: Celebrimbor.

Objectif: ordonner un bon panier de resultats, pas sauver un mauvais panier ni censurer silencieusement le web.

Regles a couvrir:

- [ ] Source officielle devant SEO quand l'autorite est alignee avec la demande.
- [ ] Source primaire devant resume.
- [ ] Institution devant forum quand le profil le demande.
- [ ] Academique devant dictionnaire quand le profil est academique.
- [ ] Dictionnaire possible comme appoint definitionnel, pas autorite finale.
- [ ] Reason codes lisibles.
- [ ] Aucun bannissement invisible.
- [ ] Diversite minimale de domaines.

Livrables:

- [ ] Reranking explicable par profil.
- [ ] Reason codes content-free.
- [ ] Tests positifs par profil.
- [ ] Tests negatifs anti-overfit.
- [ ] Tests de preservation de la diversite.
- [ ] Observabilite avant/apres rerank.

Fichiers ou zones concernes:

- `app/tools/web_search_rerank.py`
- `app/tools/web_search_confidence.py`
- `app/tools/web_search.py`
- Tests web search.
- Benchmark local.

Decisions utilisateur requises avant patch:

- [ ] Valider les domaines a declasser par profil.
- [ ] Valider les sources qui peuvent rester comme appoint.
- [ ] Valider les reason codes exposables.

Hors-scope:

- Supprimer brutalement tous les resultats hors profil.
- Faire du score de confiance un declencheur.
- Appeler OpenRouter / Exa / Parallel.
- Corriger par reranking un panier SearXNG manifestement mauvais sans le dire.

Tests/preuves attendus:

- [ ] Documentation officielle alignee promue devant tutoriel SEO.
- [ ] CNI/CAF institutionnel promu devant conjugueur/dictionnaire hors sujet.
- [ ] Source academique alignee promue devant dictionnaire generaliste.
- [ ] Dictionnaire conserve quand la demande est definitionnelle.
- [ ] Aucun domaine unique impose.
- [ ] Reason codes sans contenu brut.

Criteres de fin:

- [ ] Le reranking explique le mouvement des sources.
- [ ] Les sources declassees restent inspectables.
- [ ] Le comportement ne depend pas de fixtures cachees.

Risques/effets de bord:

- Fabriquer une police invisible des sources legitimes.
- Rendre invisible une source contestataire mais pertinente.
- Surponderer le label officiel au lieu de l'alignement avec la requete.

## Phase 7 — Comportement d'echec

Proprietaire: Celebrimbor.

Objectif: quand Frida ne trouve pas de source solide, elle doit le dire clairement au lieu de combler l'incertitude.

Comportement attendu:

> Je n'ai pas trouve de source suffisamment fiable avec le profil demande. Tu peux me donner une URL, ou je peux elargir la recherche.

Livrables:

- [ ] Contrat de formulation d'echec.
- [ ] Signal de confiance visible, non souverain, non actionnable automatiquement.
- [ ] Distinction entre aucun resultat, resultats non lus, crawl pauvre, sources peu fiables et conflit de sources.
- [ ] Tests de non-fallback externe.
- [ ] Observabilite content-free de l'echec.

Fichiers ou zones concernes:

- `app/tools/web_search_confidence.py`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/core/web_read_state.py`
- Observabilite web.
- Tests serveur/chat web.

Decisions utilisateur requises avant patch:

- [ ] Choisir le comportement prioritaire: demander URL, elargir, ou dire non prouve.
- [ ] Valider le ton de la phrase d'echec.
- [ ] Valider si l'elargissement demande confirmation utilisateur.

Hors-scope:

- Fallback OpenRouter / Exa / Parallel.
- Auto-web lexical.
- Changement de prompts generaux sans necessite contractuelle.
- Score de confiance souverain.

Tests/preuves attendus:

- [ ] Echec web visible sans hallucination de source.
- [ ] URL explicite echouee conserve son `read_state`.
- [ ] Aucun appel externe n'est declenche.
- [ ] La phrase d'echec n'injecte pas de contenu brut.
- [ ] Logs sans requete brute si le contrat l'interdit.

Criteres de fin:

- [ ] Frida sait dire qu'elle n'a pas prouve.
- [ ] L'utilisateur voit les options suivantes.
- [ ] La confiance ne gouverne pas automatiquement le systeme.

Risques/effets de bord:

- Rendre Frida trop timide sur des resultats suffisants.
- Rendre l'echec trop verbeux.
- Glisser vers un fallback externe sous couvert d'assistance.

## Phase 8 — Benchmark final

Proprietaire: Sauron + Celebrimbor.

Objectif: comparer l'ancien local et le nouveau local pour decider si la reconstruction locale a vraiment ameliore la recherche.

Cas obligatoires:

- [ ] Documentation officielle Adobe Photoshop.
- [ ] Documentation officielle Adobe Illustrator.
- [ ] Renouvellement CNI.
- [ ] Actualite IA Europe.
- [ ] OpenRouter docs.
- [ ] Derrida / trace.
- [ ] Bourdieu / sociologie.
- [ ] Sciences exactes.
- [ ] Documentation technique.
- [ ] Divers volontairement ambigu.

Livrables:

- [ ] Rapport ancien local vs nouveau local.
- [ ] Analyse par cas: qualite sources, autorite, bruit, crawl, extraits, latence.
- [ ] Analyse des echecs restants.
- [ ] Comparaison facultative avec OpenRouter / Exa / Parallel comme temoins externes seulement.
- [ ] Decision produit explicite: continuer local, ajuster SearXNG, ajuster FridaDev, ou demander une nouvelle decision humaine.

Fichiers ou zones concernes:

- `benchmark/web-search/`
- `benchmark/suites/web_search/`
- `app/docs/states/audits/`
- `app/docs/todo-todo/product/`

Decisions utilisateur requises avant patch:

- [ ] Valider si les temoins externes OpenRouter / Exa / Parallel sont relances.
- [ ] Valider le budget cout/latence pour le benchmark.
- [ ] Valider le seuil qualitatif de passage.

Hors-scope:

- Activer OpenRouter / Exa / Parallel dans le runtime.
- Modifier la recherche pendant la mesure.
- Transformer un temoin externe en option produit.

Tests/preuves attendus:

- [ ] Dry-run benchmark.
- [ ] Run live local borne.
- [ ] Grep securite sur artefacts.
- [ ] Rapport versionne ou artefacts `/tmp` references explicitement.
- [ ] `git diff --check` si documentation versionnee.

Criteres de fin:

- [ ] Le nouveau local est compare a l'ancien local.
- [ ] Les gains et pertes sont nommes.
- [ ] Les limites restantes ne sont pas deguisees en succes.

Risques/effets de bord:

- Lire le benchmark comme concours de score au lieu de diagnostic.
- Confondre qualite d'index externe et doctrine produit.
- Masquer la dependance opaque des temoins externes.

## Phase 9 — Deploiement

Proprietaire: Sauron + Celebrimbor.

Objectif: deployer proprement les modifications decidees, avec rollback connu et preuves live.

Livrables:

- [ ] Backup config SearXNG si la plateforme change.
- [ ] Patch plateforme Sauron si decide.
- [ ] Patch FridaDev Celebrimbor si runtime applicatif modifie.
- [ ] Tests unitaires et integration adaptes.
- [ ] Rebuild app si runtime FridaDev modifie.
- [ ] Restart SearXNG seulement si configuration plateforme modifiee.
- [ ] Verifications live.
- [ ] Rapport final.
- [ ] Rollback connu.

Fichiers ou zones concernes:

- `/opt/platform/searxng/`
- `/opt/platform/fridadev/`
- `/opt/platform/fridadev-app/`
- Documentation de suivi dans `app/docs/states/` ou `app/docs/todo-done/` selon cloture.

Decisions utilisateur requises avant patch:

- [ ] Valider fenetre de deploiement.
- [ ] Valider rollback.
- [ ] Valider si le chantier actif peut etre archive apres preuves.

Hors-scope:

- Redemarrer Caddy, Authelia, Homepage ou DB sans necessite explicite.
- Afficher secrets, `.env`, tokens, DSN complets ou cookies.
- Lancer un nouveau chantier produit dans le meme commit.

Tests/preuves attendus:

- [ ] `git status --short --branch`
- [ ] `git diff --check`
- [ ] Tests applicatifs pertinents.
- [ ] `docker compose up -d --build fridadev` seulement si runtime modifie.
- [ ] `docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
- [ ] `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'`
- [ ] Smoke web local si recherche runtime modifiee.

Criteres de fin:

- [ ] Les changements sont deployes ou explicitement non deployes.
- [ ] Les preuves live sont lisibles.
- [ ] Le rollback est documente.
- [ ] Le TODO est archive ou laisse ouvert avec prochain lot explicite.

Risques/effets de bord:

- Melanger patch applicatif et patch plateforme sans coordination.
- Oublier le restart SearXNG apres une config plateforme.
- Rebuild inutile sur docs-only.
- Perdre la frontiere entre diagnostic benchmark et strategie produit.
