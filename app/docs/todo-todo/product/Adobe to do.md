# Adobe Photoshop / Illustrator - TODO

Classement: `app/docs/todo-todo/product/`
Statut: actif, non lance runtime.
Date d'ouverture: 2026-05-23.
Besoin produit: rendre Frida utile pour Amandine sur Photoshop et Illustrator via une lecture officielle Adobe a la demande, sans index durable Adobe et sans casser la recherche web generale.

## Decisions deja prises

- [ ] Garder ce chantier separe de `job-divers-todo.md`; `job-divers-todo.md` reste actif pour les petits jobs produit/hiver.
- [ ] Ne pas creer de mode `auto`: Amandine choisit explicitement Photoshop ou Illustrator.
- [ ] Ne pas vendre ce chantier comme une base de connaissance Adobe persistante.
- [ ] Ne pas demander a Amandine de documenter chaque geste ou effet pendant son travail.
- [ ] Construire une specialisation par protocole de lecture sourcee: doc Adobe officielle + cas concret utilisateur.
- [ ] Utiliser HelpX officiel en lecture a la demande pour le MVP.
- [ ] Ne pas indexer durablement HelpX, Learn, Community ou PDF Adobe.
- [ ] Ne pas utiliser OpenRouter/Exa comme discovery nominale du MVP Adobe.
- [ ] Ne pas faire reposer le MVP sur SearXNG: le diagnostic local n'a pas trouve HelpX de facon fiable.
- [ ] Demarrer depuis un registre tres court d'URLs officielles connues.
- [ ] Suivre seulement des liens internes HelpX officiels, bornes et filtrables.
- [ ] Lire large avec Crawl4AI `raw`, puis reduire en passages courts.
- [ ] Jeter le texte Adobe lu a la demande apres le tour.
- [ ] Ne jamais envoyer les passages Adobe vers Memory, Identity, Summary, Biblio, Active Documents ou historique persistant.
- [ ] Repondre en francais, avec prudence si la source est anglaise ou si le libelle UI localise n'est pas confirme.

## Diagnostic technique du 2026-05-23

Constats content-free, sans stockage de contenu Adobe:

- [x] Crawl4AI est disponible depuis `fridadev` via `crawl4ai:11235`.
- [x] Le budget courant d'injection URL explicite est `25 000` caracteres.
- [x] Photoshop HelpX hub lu en `raw`: environ `183k` caracteres et plus de `1200` liens Markdown.
- [x] Photoshop release notes lues en `raw`: environ `193k` caracteres.
- [x] Illustrator HelpX hub lu en `raw`: environ `183k` caracteres.
- [x] Illustrator release notes lues en `raw`: environ `213k` caracteres.
- [x] Les hubs officiels exposent beaucoup de liens internes HelpX suivables.
- [x] Une sonde `root -> page enfant` fonctionne pour Photoshop et Illustrator.
- [x] Le mode generique `fit` est trop variable pour etre la seule preuve de lecture complete.
- [x] Les pages Adobe sont trop grosses pour etre injectees telles quelles.
- [x] Une sonde large de crawl frais recursif a ete trop lente: le pipeline doit etre strictement borne.
- [x] SearXNG local ne remonte pas HelpX sur les requetes `site:helpx.adobe.com/...` testees.

Conclusion diagnostic:

- [x] Le chantier est techniquement possible.
- [x] Le chemin simple n'est pas un moteur web general, mais un mini-pipeline Adobe specialise.
- [x] Le pipeline doit lire avec Crawl4AI `raw`, extraire, filtrer, selectionner puis injecter peu.

## Cible produit

Frida doit pouvoir aider Amandine sur une question Photoshop ou Illustrator en combinant:

- [ ] le cas particulier de l'utilisateur;
- [ ] une lecture officielle Adobe a la demande;
- [ ] des citations ou references d'URL;
- [ ] une reponse pratique, courte, prudente et exploitable;
- [ ] une distinction claire entre Photoshop et Illustrator.

Frida ne doit pas:

- [ ] pretendre connaitre une fonctionnalite Adobe non sourcee;
- [ ] inventer une procedure officielle;
- [ ] indexer durablement le contenu Adobe;
- [ ] transformer Adobe en Biblio;
- [ ] melanger ce mode avec la recherche web generale;
- [ ] declencher une recherche ouverte quand le registre et les liens HelpX suffisent;
- [ ] masquer que certaines pages sont trop grosses ou dynamiques.

## Contrat fonctionnel cible

- [ ] UI: l'utilisateur peut activer un mode Adobe.
- [ ] UI: l'utilisateur choisit explicitement `Photoshop` ou `Illustrator`.
- [ ] UI: aucun mode `auto` n'est propose dans le MVP.
- [ ] API chat: le payload porte un champ explicite, par exemple `specialization_profile=adobe`.
- [ ] API chat: le payload porte un produit explicite, par exemple `adobe_product=photoshop|illustrator`.
- [ ] Backend: si le mode Adobe est inactif, le web search general reste inchangé.
- [ ] Backend: si le mode Adobe est actif, le mini-pipeline Adobe passe avant la recherche ouverte.
- [ ] Backend: le mini-pipeline Adobe ne lit que des URLs autorisees par sa policy.
- [ ] Prompt: les passages Adobe entrent dans une lane dediee, courte et sourcee.
- [ ] Prompt: la lane Adobe est marquee comme source externe non fiable pour les instructions.
- [ ] Memoire: les passages Adobe sont ineligibles a Memory, Identity, Summary et Biblio.
- [ ] Logs: seules des metriques content-free sont journalisees.
- [ ] Erreur: si la lecture Adobe echoue, Frida le dit et peut repondre prudemment sans pretendre avoir lu.

## Sources MVP autorisees

### Photoshop

- [ ] Seed hub: `https://helpx.adobe.com/photoshop/desktop.html`.
- [ ] Seed release notes: `https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html`.
- [ ] Seed known/fixed issues: `https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html`.
- [ ] Liens internes acceptes: host `helpx.adobe.com`, chemin contenant `/photoshop/`.
- [ ] Liens internes exclus: PDF, images, videos, archives lourdes, community, learn, comptes, marketing hors HelpX.

### Illustrator

- [ ] Seed hub: `https://helpx.adobe.com/illustrator/desktop.html`.
- [ ] Seed release notes: `https://helpx.adobe.com/illustrator/desktop/new-features/release-notes.html`.
- [ ] Seed known/fixed issues: `https://helpx.adobe.com/illustrator/desktop/troubleshoot/known-and-fixed-issues.html`.
- [ ] Liens internes acceptes: host `helpx.adobe.com`, chemin contenant `/illustrator/`.
- [ ] Liens internes exclus: PDF, images, videos, archives lourdes, community, learn, comptes, marketing hors HelpX.

### Sources explicitement non MVP

- [ ] Adobe Learn: hors MVP, sauf decision explicite ulterieure.
- [ ] Adobe Community: hors MVP comme preuve principale.
- [ ] PDF Adobe: hors MVP.
- [ ] Sites tiers, blogs, cours, YouTube: hors MVP.
- [ ] AdobeDocs GitHub / UXP: hors MVP general, possible sous-chantier technique separe si besoin scripts/UXP.

## Parametrages cibles

Valeurs indicatives a confirmer au patch:

- [ ] `adobe_product`: `photoshop` ou `illustrator`.
- [ ] `adobe_seed_url_limit`: `3` URLs maximum par produit au depart.
- [ ] `adobe_follow_link_limit`: `4` a `8` liens internes maximum par tour.
- [ ] `adobe_crawl_page_limit`: `3` a `5` pages Crawl4AI maximum par tour.
- [ ] `adobe_crawl_filter`: `raw` en lecture primaire.
- [ ] `adobe_fit_allowed`: seulement comme optimisation ou fallback, pas comme preuve unique.
- [ ] `adobe_max_raw_chars_per_page`: borne defensive a definir apres mesure.
- [ ] `adobe_passage_chars`: environ `800` a `1500` caracteres par passage.
- [ ] `adobe_passage_count`: `3` a `8` passages injectes maximum.
- [ ] `adobe_prompt_budget_chars`: borne dediee, inferieure au brut Adobe.
- [ ] `adobe_timeout_s`: borne courte par page et borne globale par tour.
- [ ] `adobe_cache_policy`: cache technique Crawl4AI autorise, mais pas stockage applicatif du texte Adobe.
- [ ] `adobe_language_preference`: FR si disponible, EN sinon avec caveat.
- [ ] `adobe_min_evidence_threshold`: seuil minimal avant reponse affirmative sourcee.

## Observabilite privacy-safe

A journaliser:

- [ ] mode Adobe actif/inactif;
- [ ] produit choisi;
- [ ] nombre d'URLs seed candidates;
- [ ] nombre de liens internes extraits;
- [ ] nombre de pages crawlees;
- [ ] host;
- [ ] hash court URL;
- [ ] type de source: hub, release_notes, known_issues, help_page;
- [ ] filtre Crawl4AI utilise: `raw`, `fit`, fallback;
- [ ] statut crawl;
- [ ] caracteres markdown bruts;
- [ ] nombre de headings;
- [ ] nombre de liens;
- [ ] nombre de passages candidats;
- [ ] nombre de passages injectes;
- [ ] chars injectes;
- [ ] latence par page;
- [ ] latence totale;
- [ ] decision evidence: suffisante, partielle, insuffisante;
- [ ] code d'erreur si echec.

A ne jamais journaliser:

- [ ] texte Adobe extrait;
- [ ] passage Adobe complet;
- [ ] transcription ou contenu utilisateur sensible;
- [ ] prompt final complet si passages Adobe inclus;
- [ ] cookies, tokens, `.env`, DSN, secrets;
- [ ] fichiers temporaires de pages;
- [ ] screenshots;
- [ ] OCR/PDF brut.

## Architecture cible

Le mini-pipeline Adobe est une capacite a cote du web search general.

- [ ] Ne pas remplacer `tools/web_search.py`.
- [ ] Ne pas transformer la recherche web generale en pipeline Adobe.
- [ ] Ajouter un module dedie, par exemple `app/tools/adobe_docs.py` ou `app/core/adobe_docs_*`, selon les frontieres existantes.
- [ ] Garder `app/server.py` comme entree HTTP/orchestration seulement.
- [ ] Garder la selection des sources Adobe dans un registre lisible.
- [ ] Garder l'extraction et le filtrage dans le module Adobe, pas dans le prompt.
- [ ] Injecter une lane dediee via le contexte de chat existant.
- [ ] Ajouter un garde-fou anti-contamination dans le flux Memory/Summary si necessaire.
- [ ] Ne pas creer de dependance AnythingLLM.
- [ ] Ne pas creer de Biblio Adobe persistante.

## Lot 0 - Cadrage final avant patch runtime

### PLAN

- [ ] Relire ce TODO.
- [ ] Relire `AGENTS.md`.
- [ ] Relire le pipeline web existant: `app/tools/web_search.py`, policies et tests.
- [ ] Verifier les surfaces UI de boutons/modes chat.
- [ ] Verifier les surfaces payload `/api/chat`.
- [ ] Verifier les garde-fous Memory/Identity/Summary.
- [ ] Confirmer que `job-divers-todo.md` reste actif et non archive.

### PATCH

- [ ] Aucun patch runtime dans ce lot.
- [ ] Si une spec vivante est necessaire, creer une spec courte avant code.
- [ ] Sinon, utiliser ce TODO comme contrat initial.

### TEST

- [ ] `git status --short --branch`.
- [ ] `rg "web_search|explicit_url|Crawl4AI|Memory|Summary|Identity" app`.
- [ ] Relire les tests web existants avant design.

### RISQUES

- [ ] Risque de melanger Adobe avec le web search general.
- [ ] Risque de rouvrir Biblio/native Catalogue par accident.
- [ ] Risque de creer un mode `auto` malgre la decision utilisateur.

### REDUCTION DES RISQUES

- [ ] Nommer clairement le module Adobe.
- [ ] Garder le mode produit explicite.
- [ ] Refuser tout stockage durable Adobe au MVP.

## Lot 1 - Registre de sources Adobe

### PLAN

- [ ] Definir une structure de source Adobe content-free.
- [ ] Declarer les seeds Photoshop.
- [ ] Declarer les seeds Illustrator.
- [ ] Declarer les types de source: hub, release_notes, known_issues, help_page.
- [ ] Declarer les hosts et chemins autorises.
- [ ] Declarer les extensions et chemins exclus.
- [ ] Declarer une politique FR/EN.

### PATCH

- [ ] Ajouter le registre source dans un module dedie.
- [ ] Ajouter une fonction `sources_for_product(product)`.
- [ ] Ajouter une fonction de validation URL: host, produit, extension, scheme, fragment.
- [ ] Ajouter une canonicalisation URL sans fragment.
- [ ] Ajouter des reason codes d'exclusion.

### TEST

- [ ] Test: `photoshop` retourne les trois seeds Photoshop.
- [ ] Test: `illustrator` retourne les trois seeds Illustrator.
- [ ] Test: une URL Photoshop est refusee en mode Illustrator.
- [ ] Test: une URL Illustrator est refusee en mode Photoshop.
- [ ] Test: `community.adobe.com` est refuse.
- [ ] Test: `www.adobe.com/learn` est refuse.
- [ ] Test: `.pdf`, image, video sont refuses.
- [ ] Test: canonicalisation retire le fragment.

### RISQUES

- [ ] Sur-autorisation de domaines Adobe.
- [ ] Confusion entre HelpX, Learn et Community.
- [ ] Liens region/langue dupliques.

### REDUCTION DES RISQUES

- [ ] Allowlist stricte `helpx.adobe.com`.
- [ ] Chemin produit obligatoire.
- [ ] Tests d'exclusion explicites.
- [ ] Pas de wildcard large `*.adobe.com`.

## Lot 2 - Client Crawl4AI Adobe `raw`

### PLAN

- [ ] Reutiliser la configuration Crawl4AI existante.
- [ ] Appeler `/md` avec filtre `raw` comme lecture primaire Adobe.
- [ ] Ne pas envoyer le texte brut dans les logs.
- [ ] Definir timeout par page.
- [ ] Definir borne globale par tour.
- [ ] Prevoir un fallback `fit` seulement si utile pour pages courtes, sans remplacer `raw` comme preuve.

### PATCH

- [ ] Ajouter une fonction `read_adobe_url(url, product, source_type)`.
- [ ] Retourner metadonnees + markdown en memoire seulement.
- [ ] Retourner statut `success`, `empty`, `error`, `timeout`.
- [ ] Retourner chars, headings, link_count, elapsed_ms.
- [ ] Retourner reason codes content-free.
- [ ] Ne pas persister le markdown.

### TEST

- [ ] Test unitaire avec faux client Crawl4AI: succes `raw`.
- [ ] Test unitaire: timeout propre.
- [ ] Test unitaire: empty propre.
- [ ] Test unitaire: erreur HTTP propre.
- [ ] Test unitaire: aucun log ne contient le markdown.
- [ ] Preuve runtime manuelle bornee sur une URL HelpX si environnement disponible.

### RISQUES

- [ ] Latence excessive sur pages Adobe.
- [ ] Extraction `raw` bruitee par navigation.
- [ ] Page tres grosse depassant le budget memoire ou prompt.

### REDUCTION DES RISQUES

- [ ] Limite de pages par tour.
- [ ] Limite de chars retenus apres extraction.
- [ ] Timeout par page.
- [ ] Selection de passages avant injection.

## Lot 3 - Extraction de liens internes HelpX

### PLAN

- [ ] Extraire les liens depuis Markdown Crawl4AI.
- [ ] Canonicaliser chaque URL.
- [ ] Filtrer par produit explicite.
- [ ] Dedupliquer.
- [ ] Classer les liens par type probable: release, known issue, help page, troubleshooting, feature.
- [ ] Prioriser selon la question utilisateur.

### PATCH

- [ ] Ajouter `extract_adobe_links(markdown, base_url, product)`.
- [ ] Ajouter `rank_adobe_links(question, links, product)`.
- [ ] Ajouter borne `follow_link_limit`.
- [ ] Ajouter reason codes de filtrage.

### TEST

- [ ] Test: liens relatifs resolus.
- [ ] Test: fragments supprimes.
- [ ] Test: doublons dedupes.
- [ ] Test: liens autre produit refuses.
- [ ] Test: liens non HelpX refuses.
- [ ] Test: liens PDF/media refuses.
- [ ] Test: ranking favorise release notes pour question version.
- [ ] Test: ranking favorise troubleshooting pour question bug/erreur.

### RISQUES

- [ ] Trop de liens candidats.
- [ ] Liens marketing ou navigation en tete.
- [ ] Liens utiles caches loin dans la page.

### REDUCTION DES RISQUES

- [ ] Borne stricte.
- [ ] Scoring simple et explicable.
- [ ] Seeds release/known issues toujours disponibles.
- [ ] Fallback: si liens insuffisants, rester sur les seeds.

## Lot 4 - Selection de passages

### PLAN

- [ ] Segmenter les pages Adobe en sections/passages.
- [ ] Retirer navigation/footer quand identifiable.
- [ ] Scorer les passages contre la question utilisateur.
- [ ] Garder peu de passages.
- [ ] Conserver URL, titre/section si disponible, source type et produit.
- [ ] Ne pas stocker les passages apres le tour.

### PATCH

- [ ] Ajouter un splitter Markdown borne.
- [ ] Ajouter un score lexical simple ou BM25 local si deja disponible.
- [ ] Ajouter un seuil minimal.
- [ ] Ajouter une limite de passages injectes.
- [ ] Ajouter une limite de chars par passage.
- [ ] Ajouter metadonnees de citation.

### TEST

- [ ] Test: une page longue produit plusieurs passages bornes.
- [ ] Test: les passages ne depassent pas `adobe_passage_chars`.
- [ ] Test: le total injecte ne depasse pas `adobe_prompt_budget_chars`.
- [ ] Test: ranking retrouve un passage contenant les termes de la question.
- [ ] Test: absence de passage pertinent donne evidence insuffisante.
- [ ] Test: les passages ne sont pas persistes.

### RISQUES

- [ ] Passage trop court donc inutilisable.
- [ ] Passage trop long donc bruit/prompt cher.
- [ ] Navigation retenue comme preuve.
- [ ] Mauvaise section citee.

### REDUCTION DES RISQUES

- [ ] Garder section/titre quand possible.
- [ ] Exclure patterns de navigation repetitifs.
- [ ] Exiger score minimal.
- [ ] Afficher une limite de confiance si preuve faible.

## Lot 5 - Integration chat backend

### PLAN

- [ ] Ajouter le champ mode Adobe au contrat payload.
- [ ] Ajouter le produit explicite au contrat payload.
- [ ] Brancher le mini-pipeline avant l'assemblage prompt.
- [ ] Garantir que le web search general reste inchangé hors mode Adobe.
- [ ] Ajouter une lane prompt dediee.
- [ ] Ajouter hard guard contre prompt injection web.

### PATCH

- [ ] Etendre le parsing `/api/chat` sans casser les clients existants.
- [ ] Ajouter `adobe_context_payload` ou equivalent.
- [ ] Injecter les passages dans le contexte chat avec metadonnees.
- [ ] Marquer la lane comme source externe non instructionnelle.
- [ ] Ajouter etats: not_requested, success, partial, insufficient, error.
- [ ] Ajouter observabilite content-free.

### TEST

- [ ] Test: mode absent ne change pas le payload existant.
- [ ] Test: mode Photoshop appelle le pipeline Photoshop.
- [ ] Test: mode Illustrator appelle le pipeline Illustrator.
- [ ] Test: produit manquant refuse ou ignore proprement selon contrat.
- [ ] Test: evidence insuffisante ajoute caveat.
- [ ] Test: erreur Crawl4AI n'ecrase pas la reponse utilisateur.
- [ ] Test: lane Adobe ne part pas en Memory/Identity/Summary.

### RISQUES

- [ ] Regression du chat normal.
- [ ] Contamination de la memoire.
- [ ] Prompt trop gros.
- [ ] Confusion entre web search et Adobe docs.

### REDUCTION DES RISQUES

- [ ] Tests de non-regression web off/web search normal.
- [ ] Budget prompt dedie.
- [ ] Garde-fous de non-contamination.
- [ ] Feature flag ou champ explicite uniquement.

## Lot 6 - UI bouton Adobe

### PLAN

- [ ] Ajouter un controle visible mais sobre dans l'UI chat.
- [ ] Proposer deux choix explicites: Photoshop, Illustrator.
- [ ] Ne pas proposer `Auto`.
- [ ] Afficher clairement le mode actif.
- [ ] Permettre desactivation simple.
- [ ] Ne pas transformer cela en landing page ou refonte UI.

### PATCH

- [ ] Ajouter l'etat frontend `adobeModeEnabled`.
- [ ] Ajouter l'etat frontend `adobeProduct`.
- [ ] Ajouter boutons/chips Photoshop et Illustrator.
- [ ] Ajouter le payload vers `/api/chat`.
- [ ] Ajouter indication de sources Adobe consultees si le backend les expose content-free.
- [ ] Garder les conversations normales inchangees.

### TEST

- [ ] Test frontend: mode inactif par defaut.
- [ ] Test frontend: activation Photoshop.
- [ ] Test frontend: activation Illustrator.
- [ ] Test frontend: pas de mode Auto.
- [ ] Test frontend: payload contient le produit explicite.
- [ ] Test frontend: desactivation retire le mode.
- [ ] Test navigateur si surface existante.

### RISQUES

- [ ] L'utilisateur croit que le bouton garantit une expertise absolue.
- [ ] Le controle surcharge l'UI.
- [ ] Le mode reste actif par accident.

### REDUCTION DES RISQUES

- [ ] Badge clair du mode actif.
- [ ] Desactivation accessible.
- [ ] Reponses avec sources/caveats, pas promesse absolue.

## Lot 7 - Observabilite et privacy

### PLAN

- [ ] Definir un evenement content-free pour chaque tour Adobe.
- [ ] Definir une synthese par source consultee sans texte.
- [ ] Definir des codes d'echec lisibles.
- [ ] Verifier que les logs existants ne capturent pas les passages.

### PATCH

- [ ] Ajouter logs content-free du pipeline Adobe.
- [ ] Ajouter compteurs sources/passages/latences.
- [ ] Ajouter hashes courts d'URLs si utile.
- [ ] Ajouter signal evidence.
- [ ] Ajouter tests anti-fuite.

### TEST

- [ ] Test logs: pas de texte Adobe.
- [ ] Test logs: pas de contenu utilisateur sensible.
- [ ] Test logs: pas de prompt avec passages.
- [ ] Test logs: metriques presentes.
- [ ] Test erreur: code d'echec present.

### RISQUES

- [ ] Fuite de contenu Adobe dans les logs.
- [ ] Fuite de contenu utilisateur.
- [ ] Logs inutilisables car trop pauvres.

### REDUCTION DES RISQUES

- [ ] Tests explicitement negatifs.
- [ ] Champs content-free seulement.
- [ ] Hash URL court au lieu de contenu.
- [ ] Pas de markdown en log.

## Lot 8 - Evaluation metier Amandine

### PLAN

- [ ] Construire un petit jeu de questions Photoshop.
- [ ] Construire un petit jeu de questions Illustrator.
- [ ] Inclure questions version/bug/release notes.
- [ ] Inclure questions ambiguës a traiter sans Auto: l'utilisateur doit choisir le produit.
- [ ] Inclure cas ou Frida doit dire que la preuve est insuffisante.

### PATCH

- [ ] Ajouter fixtures/evals si le framework existant le justifie.
- [ ] Sinon documenter un protocole manuel de validation.
- [ ] Ajouter snapshots content-free de preuves.

### TEST

- [ ] Photoshop: detourage/masque, calques, remove tool, disque de travail, export.
- [ ] Illustrator: plume, tracés, logo vectoriel, import PSD, PDF print.
- [ ] Version: release notes lues pour questions recentes.
- [ ] Bugs: known/fixed issues lues avant affirmation.
- [ ] Refus: fonctionnalite inventee non confirmee.
- [ ] Non-regression: chat normal sans Adobe.

### RISQUES

- [ ] Eval trop facile.
- [ ] Le modele repond par connaissance generale sans utiliser les sources.
- [ ] Sources Adobe lues mais mal exploitees.

### REDUCTION DES RISQUES

- [ ] Exiger citations/metadonnees de source.
- [ ] Comparer mode Adobe actif vs inactif sur quelques cas.
- [ ] Inclure questions pieges.
- [ ] Valider avec Amandine sur cas reels.

## Lot 9 - Rebuild, validation live et cloture provisoire

### PLAN

- [ ] Rebuild seulement si runtime frontend/backend touche.
- [ ] Preparer un smoke test live sans secrets.
- [ ] Preparer rollback simple.
- [ ] Definir criteres de cloture provisoire.

### PATCH

- [ ] Aucun patch supplementaire dans ce lot sauf correction de bug trouvee.
- [ ] Mettre a jour ce TODO avec preuves finales.
- [ ] Archiver uniquement quand le mode est livre et stabilise.

### TEST

- [ ] `git status --short --branch`.
- [ ] `git diff --check`.
- [ ] `git diff --cached --check`.
- [ ] Tests unitaires modules Adobe.
- [ ] Tests frontend si UI touchee.
- [ ] Tests backend `/api/chat` si payload touche.
- [ ] Rebuild app si runtime touche.
- [ ] `docker ps --filter name=platform-fridadev --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"`.
- [ ] `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'`.
- [ ] Test live Photoshop court.
- [ ] Test live Illustrator court.

### RISQUES

- [ ] Une correction tardive elargit le chantier.
- [ ] Live OK sur une question mais fragile sur pages longues.
- [ ] Latence trop haute pour l'usage reel.

### REDUCTION DES RISQUES

- [ ] Garder le MVP petit.
- [ ] Fermer provisoirement sous surveillance.
- [ ] Journaliser latence et evidence.
- [ ] Ajouter une decision explicite avant tout Learn/Community/PDF/index durable.

## Criteres de fermeture provisoire

- [ ] Le mode Adobe n'a pas de choix Auto.
- [ ] Photoshop et Illustrator sont selectionnables explicitement.
- [ ] Le chat normal sans Adobe est inchangé.
- [ ] Le web search general est inchangé.
- [ ] Crawl4AI `raw` lit les pages HelpX cibles.
- [ ] Les liens internes HelpX sont suivis seulement dans le produit choisi.
- [ ] Le nombre de pages lues par tour est borne.
- [ ] Les passages injectes sont courts et sources.
- [ ] Les grosses pages ne sont jamais injectees brutes.
- [ ] La reponse cite les sources ou signale l'insuffisance de preuve.
- [ ] Aucun contenu Adobe n'est stocke durablement.
- [ ] Aucun contenu Adobe n'entre en Memory/Identity/Summary/Biblio/Active Documents.
- [ ] Les logs restent content-free.
- [ ] Les tests couvrent non-regression chat/web normal.
- [ ] Amandine valide au moins un cas Photoshop reel et un cas Illustrator reel.

## Questions a trancher avant implementation

- [ ] Nom exact du bouton UI: `Adobe`, `Docs Adobe`, `Photoshop / Illustrator`, autre.
- [ ] Emplacement UI du controle.
- [ ] Produit actif persistant par conversation ou reset a chaque nouvelle conversation.
- [ ] Budget prompt Adobe cible.
- [ ] Nombre maximal de pages par tour.
- [ ] Strategy FR/EN: preferer FR quand disponible ou rester sur pages EN plus fraiches.
- [ ] Affichage utilisateur des sources consultees: URL visibles, titres, ou badge minimal.
- [ ] Niveau de citation attendu dans les reponses.
- [ ] Faut-il une spec vivante dediee avant runtime ou ce TODO suffit-il pour MVP.

## Hors-scope strict MVP

- [ ] Pas de mode Auto.
- [ ] Pas d'index durable Adobe.
- [ ] Pas de Biblio Adobe.
- [ ] Pas d'AnythingLLM.
- [ ] Pas de fine-tuning.
- [ ] Pas d'ingestion PDF.
- [ ] Pas d'Adobe Learn sans decision explicite.
- [ ] Pas d'Adobe Community comme source principale.
- [ ] Pas de recherche web ouverte nominale.
- [ ] Pas de modification plateforme/Docker hors rebuild applicatif si runtime touche.
- [ ] Pas de changement Memory/Identity/Summary hors garde-fou strictement necessaire.
