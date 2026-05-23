# Adobe Photoshop / Illustrator - TODO

Classement: `app/docs/todo-todo/product/`
Statut: actif, Lots 1-7 livres progressivement; pas d'index Adobe durable.
Date d'ouverture: 2026-05-23.
Spec normative: `app/docs/states/specs/fridadev-adobe-docs-mode-contract.md`
Besoin produit: rendre Frida utile pour Amandine sur Photoshop et Illustrator via une lecture officielle Adobe a la demande, sans index durable Adobe et sans casser la recherche web generale.

## Invariants deja actes

- Garder ce chantier separe de `job-divers-todo.md`; `job-divers-todo.md` reste actif pour les petits jobs produit/hiver.
- Ne pas creer de mode `auto`: Amandine choisit explicitement Photoshop ou Illustrator.
- Ne pas vendre ce chantier comme une base de connaissance Adobe persistante.
- Ne pas demander a Amandine de documenter chaque geste ou effet pendant son travail.
- Construire une specialisation par protocole de lecture sourcee: doc Adobe officielle + cas concret utilisateur.
- Utiliser HelpX officiel en lecture a la demande pour le MVP.
- Ne pas indexer durablement HelpX, Learn, Community ou PDF Adobe.
- Ne pas utiliser OpenRouter/Exa comme discovery nominale du MVP Adobe.
- Ne pas faire reposer le MVP sur SearXNG: le diagnostic local n'a pas trouve HelpX de facon fiable.
- Demarrer depuis un registre tres court d'URLs officielles connues.
- Suivre seulement des liens internes HelpX officiels, bornes et filtrables.
- Lire large avec Crawl4AI `raw`, puis reduire en passages courts.
- Jeter le texte Adobe lu a la demande apres le tour.
- Ne jamais envoyer les passages Adobe vers Memory, Identity, Summary, Biblio, Active Documents ou historique persistant.
- Repondre en francais, avec prudence si la source est anglaise ou si le libelle UI localise n'est pas confirme.

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
- [ ] `adobe_cache_policy`: cache applicatif interdit; cache Crawl4AI desactive ou explicitement borne/ephemere, sauf preuve technique documentee qu'il ne conserve pas le contenu brut.
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

Statut: clos le 2026-05-23 par creation de la spec normative `app/docs/states/specs/fridadev-adobe-docs-mode-contract.md`.

### PLAN

- [x] Relire ce TODO.
- [x] Relire `AGENTS.md`.
- [x] Relire le pipeline web existant: `app/tools/web_search.py`, policies et tests.
- [x] Verifier les surfaces UI de boutons/modes chat.
- [x] Verifier les surfaces payload `/api/chat`.
- [x] Verifier les garde-fous Memory/Identity/Summary.
- [x] Confirmer que `job-divers-todo.md` reste actif et non archive.

### PATCH

- [x] Aucun patch runtime dans ce lot.
- [x] Si une spec vivante est necessaire, creer une spec courte avant code.
- [x] Conserver ce TODO comme feuille de route actionnable, adossee a la spec normative.

### TEST

- [x] `git status --short --branch`.
- [x] `rg "web_search|explicit_url|Crawl4AI|Memory|Summary|Identity" app`.
- [x] Relire les tests web existants avant design.

### RISQUES

- [x] Risque de melanger Adobe avec le web search general.
- [x] Risque de rouvrir Biblio/native Catalogue par accident.
- [x] Risque de creer un mode `auto` malgre la decision utilisateur.

### REDUCTION DES RISQUES

- [x] Nommer clairement le module Adobe.
- [x] Garder le mode produit explicite.
- [x] Refuser tout stockage durable Adobe au MVP.

## Lot 1 - Registre de sources Adobe

### PLAN

- [x] Definir une structure de source Adobe content-free.
- [x] Declarer les seeds Photoshop.
- [x] Declarer les seeds Illustrator.
- [x] Declarer les types de source: hub, release_notes, known_issues, help_page.
- [x] Declarer les hosts et chemins autorises.
- [x] Declarer les extensions et chemins exclus.
- [x] Declarer une politique FR/EN.

### PATCH

- [x] Ajouter le registre source dans un module dedie.
- [x] Ajouter une fonction `sources_for_product(product)`.
- [x] Ajouter une fonction de validation URL: host, produit, extension, scheme, fragment.
- [x] Ajouter une canonicalisation URL sans fragment.
- [x] Ajouter des reason codes d'exclusion.

### TEST

- [x] Test: `photoshop` retourne les trois seeds Photoshop.
- [x] Test: `illustrator` retourne les trois seeds Illustrator.
- [x] Test: un produit inconnu est refuse.
- [x] Test: une URL Photoshop est refusee en mode Illustrator.
- [x] Test: une URL Illustrator est refusee en mode Photoshop.
- [x] Test: `community.adobe.com` est refuse.
- [x] Test: `www.adobe.com/learn` est refuse.
- [x] Test: `.pdf`, image, video sont refuses.
- [x] Test: scheme non-https refuse.
- [x] Test: canonicalisation retire le fragment.
- [x] Test: query string supprimee avec reason code.
- [x] Test: deduplication stable.

### RISQUES

- [x] Sur-autorisation de domaines Adobe.
- [x] Confusion entre HelpX, Learn et Community.
- [ ] Liens region/langue dupliques.

### REDUCTION DES RISQUES

- [x] Allowlist stricte `helpx.adobe.com`.
- [x] Chemin produit obligatoire.
- [x] Tests d'exclusion explicites.
- [x] Pas de wildcard large `*.adobe.com`.

## Lot 2 - Client Crawl4AI Adobe `raw`

### PLAN

- [x] Reutiliser la configuration Crawl4AI existante.
- [x] Appeler `/md` avec filtre `raw` comme lecture primaire Adobe.
- [x] Ne pas envoyer le texte brut dans les logs.
- [x] Definir timeout par page.
- [ ] Definir borne globale par tour.
- [x] Prevoir un fallback `fit` seulement si utile pour pages courtes, sans remplacer `raw` comme preuve.

### PATCH

- [x] Ajouter une fonction `read_adobe_url(url, product, source_type)`.
- [x] Retourner metadonnees + markdown en memoire seulement.
- [x] Retourner statut `success`, `empty`, `error`, `timeout`.
- [x] Retourner statut `invalid_url`.
- [x] Retourner chars, headings, link_count, elapsed_ms.
- [x] Retourner reason codes content-free.
- [x] Ne pas persister le markdown.

### TEST

- [x] Test unitaire avec faux client Crawl4AI: succes `raw`.
- [x] Test unitaire: URL invalide refusee avant appel Crawl4AI.
- [x] Test unitaire: mauvais produit refuse avant appel Crawl4AI.
- [x] Test unitaire: timeout propre.
- [x] Test unitaire: empty propre.
- [x] Test unitaire: erreur HTTP propre.
- [x] Test unitaire: aucun log ne contient le markdown.
- [x] Test unitaire: pas de fichier temporaire.
- [ ] Preuve runtime manuelle bornee sur une URL HelpX si environnement disponible.

### RISQUES

- [x] Latence excessive sur pages Adobe.
- [ ] Extraction `raw` bruitee par navigation.
- [x] Page tres grosse depassant le budget memoire ou prompt.

### REDUCTION DES RISQUES

- [ ] Limite de pages par tour.
- [x] Limite de chars retenus apres extraction.
- [x] Timeout par page.
- [ ] Selection de passages avant injection.

## Lot 3 - Extraction de liens internes HelpX

### PLAN

- [x] Extraire les liens depuis Markdown Crawl4AI.
- [x] Canonicaliser chaque URL.
- [x] Filtrer par produit explicite.
- [x] Dedupliquer.
- [x] Classer les liens par type probable: release_notes, known_issues, help_page, hub.
- [x] Prioriser selon la question utilisateur.

### PATCH

- [x] Ajouter `extract_adobe_links(markdown, base_url, product)`.
- [x] Ajouter `rank_adobe_links(question, links, product)`.
- [x] Ajouter borne `follow_link_limit`.
- [x] Ajouter reason codes de filtrage.

### TEST

- [x] Test: liens relatifs resolus.
- [x] Test: fragments supprimes.
- [x] Test: query string supprimee avec reason code.
- [x] Test: doublons dedupes.
- [x] Test: liens autre produit refuses.
- [x] Test: liens non HelpX refuses.
- [x] Test: liens PDF/media refuses.
- [x] Test: Community/Learn refuses.
- [x] Test: classification release notes, known issues et help page.
- [x] Test: ranking favorise release notes pour question version.
- [x] Test: ranking favorise troubleshooting pour question bug/erreur.
- [x] Test: ranking favorise help page pour question d'usage.
- [x] Test: limite `follow_link_limit` respectee.
- [x] Test: aucun Markdown complet ni texte d'ancre dans `repr` / export content-free.

### RISQUES

- [x] Trop de liens candidats.
- [x] Liens marketing ou navigation en tete.
- [ ] Liens utiles caches loin dans la page.

### REDUCTION DES RISQUES

- [x] Borne stricte.
- [x] Scoring simple et explicable.
- [x] Seeds release/known issues toujours disponibles.
- [x] Fallback: si liens insuffisants, rester sur les seeds.

## Lot 4 - Selection de passages

### PLAN

- [x] Segmenter les pages Adobe en sections/passages.
- [x] Retirer navigation/footer quand identifiable.
- [x] Scorer les passages contre la question utilisateur.
- [x] Garder peu de passages.
- [x] Conserver URL, titre/section si disponible, source type et produit.
- [x] Ne pas stocker les passages apres le tour.

### PATCH

- [x] Ajouter un splitter Markdown borne.
- [x] Ajouter un score lexical simple ou BM25 local si deja disponible.
- [x] Ajouter un seuil minimal.
- [x] Ajouter une limite de passages injectes.
- [x] Ajouter une limite de chars par passage.
- [x] Ajouter metadonnees de citation.
- [x] Ajouter alias metier FR/EN bornes pour le scoring uniquement.
- [x] Supprimer le signal decoratif `_PROCEDURE_TERMS` non utilise.

### TEST

- [x] Test: une page longue produit plusieurs passages bornes.
- [x] Test: les passages ne depassent pas `adobe_passage_chars`.
- [x] Test: le total injecte ne depasse pas `adobe_prompt_budget_chars`.
- [x] Test: ranking retrouve un passage contenant les termes de la question.
- [x] Test: question FR `masques de calque` retrouve `Layer masks`.
- [x] Test: question FR `calques` retrouve `Layers`.
- [x] Test: question Illustrator `outil plume` retrouve `Pen tool`.
- [x] Test: alias generique `outil` seul ne promeut pas une section arbitraire.
- [x] Test: question version favorise release notes.
- [x] Test: question bug favorise known/fixed issues.
- [x] Test: navigation/footer est exclu ou declasse.
- [x] Test: absence de passage pertinent donne evidence insuffisante.
- [x] Test: les passages ne sont pas persistes.
- [x] Test: `repr` / export content-free ne contiennent pas le texte Adobe complet.
- [x] Test: metadonnees de citation conservees.

### RISQUES

- [x] Passage trop court donc inutilisable.
- [x] Passage trop long donc bruit/prompt cher.
- [x] Navigation retenue comme preuve.
- [x] Mauvaise section citee.

### REDUCTION DES RISQUES

- [x] Garder section/titre quand possible.
- [x] Exclure patterns de navigation repetitifs.
- [x] Exiger score minimal.
- [x] Afficher une limite de confiance si preuve faible.

## Lot 5 - Integration chat backend

### PLAN

- [x] Ajouter le champ mode Adobe au contrat payload.
- [x] Ajouter le produit explicite au contrat payload.
- [x] Brancher le mini-pipeline avant l'assemblage prompt.
- [x] Garantir que le web search general reste inchange hors mode Adobe.
- [x] Ajouter une lane prompt dediee.
- [x] Ajouter hard guard contre prompt injection web.

### PATCH

- [x] Etendre le parsing `/api/chat` sans casser les clients existants.
- [x] Ajouter `adobe_context_payload` ou equivalent.
- [x] Injecter les passages dans le contexte chat avec metadonnees.
- [x] Marquer la lane comme source externe non instructionnelle.
- [x] Ajouter etats: not_requested, success, partial, insufficient, error.
- [x] Ajouter observabilite content-free.

### TEST

- [x] Test: mode absent ne change pas le payload existant.
- [x] Test: mode Photoshop appelle le pipeline Photoshop.
- [x] Test: mode Illustrator appelle le pipeline Illustrator.
- [x] Test: produit manquant refuse selon contrat.
- [x] Test: produit invalide refuse selon contrat.
- [x] Test: `specialization_profile=adobe` + `web_search=true` ne lance pas le web search general.
- [x] Test: evidence insuffisante ajoute caveat.
- [x] Test: erreur Crawl4AI n'ecrase pas la reponse utilisateur.
- [x] Test: lane Adobe ne part pas en Memory/Identity/Summary.
- [x] Test: observabilite Adobe reste content-free.

### RISQUES

- [x] Regression du chat normal.
- [x] Contamination de la memoire.
- [x] Prompt trop gros.
- [x] Confusion entre web search et Adobe docs.

### REDUCTION DES RISQUES

- [x] Tests de non-regression web off/web search normal.
- [x] Budget prompt dedie.
- [x] Garde-fous de non-contamination.
- [x] Feature flag ou champ explicite uniquement.

## Lot 6 - UI bouton Adobe

### PLAN

- [x] Ajouter un controle visible mais sobre dans l'UI chat.
- [x] Proposer deux choix explicites: Photoshop, Illustrator.
- [x] Ne pas proposer `Auto`.
- [x] Afficher clairement le mode actif.
- [x] Permettre desactivation simple.
- [x] Ne pas transformer cela en landing page ou refonte UI.

### PATCH

- [x] Ajouter l'etat frontend derive du produit Adobe actif.
- [x] Ajouter l'etat frontend `adobeProduct`.
- [x] Ajouter boutons/chips Photoshop et Illustrator.
- [x] Ajouter le payload vers `/api/chat`.
- [ ] Ajouter indication de sources Adobe consultees si le backend les expose content-free.
- [x] Garder les conversations normales inchangees.
- [x] Desactiver le bouton web search pendant le mode Adobe actif.
- [x] Reorganiser les petits boutons du composer sur une ligne d'actions sous la zone de saisie.

### TEST

- [x] Test frontend: mode inactif par defaut.
- [x] Test frontend: activation Photoshop.
- [x] Test frontend: activation Illustrator.
- [x] Test frontend: pas de mode Auto.
- [x] Test frontend: payload contient le produit explicite.
- [x] Test frontend: desactivation retire le mode.
- [x] Test frontend: web button + Adobe ne creent pas de double activation confuse.
- [x] Test navigateur si surface existante.
- [x] Test responsive desktop/mobile sans chevauchement.

### RISQUES

- [x] L'utilisateur croit que le bouton garantit une expertise absolue.
- [x] Le controle surcharge l'UI.
- [x] Le mode reste actif par accident.

### REDUCTION DES RISQUES

- [x] Badge clair du mode actif.
- [x] Desactivation accessible.
- [x] Reponses avec sources/caveats, pas promesse absolue.

## Lot 7 - Observabilite et privacy

Statut: clos le 2026-05-23 par validation live bornee. Note: `app/docs/states/audits/fridadev-adobe-docs-mode-live-validation-2026-05-23.md`.

### PLAN

- [x] Definir un evenement content-free pour chaque tour Adobe.
- [x] Definir une synthese par source consultee sans texte.
- [x] Definir des codes d'echec lisibles.
- [x] Verifier que les logs existants ne capturent pas les passages.

### PATCH

- [x] Ajouter logs content-free du pipeline Adobe.
- [x] Ajouter compteurs sources/passages/latences.
- [x] Ajouter hashes courts d'URLs si utile.
- [x] Ajouter signal evidence.
- [x] Ajouter tests anti-fuite.

### TEST

- [x] Test logs: pas de texte Adobe.
- [x] Test logs: pas de contenu utilisateur sensible.
- [x] Test logs: pas de prompt avec passages.
- [x] Test logs: metriques presentes.
- [x] Test erreur: code d'echec present.
- [x] Test live UI: mode inactif sans champs Adobe.
- [x] Test live UI: Photoshop envoie `specialization_profile=adobe`, `adobe_product=photoshop`, `web_search=false`.
- [x] Test live UI: Illustrator envoie `specialization_profile=adobe`, `adobe_product=illustrator`, `web_search=false`.
- [x] Test live Crawl4AI: HelpX lu en `raw` avec pages bornees.
- [x] Test live web + Adobe: reason code `adobe_profile_owns_retrieval`.

### RISQUES

- [x] Fuite de contenu Adobe dans les logs.
- [x] Fuite de contenu utilisateur.
- [x] Logs inutilisables car trop pauvres.

### REDUCTION DES RISQUES

- [x] Tests explicitement negatifs.
- [x] Champs content-free seulement.
- [x] Hash URL court au lieu de contenu.
- [x] Pas de markdown en log.

## Lot 8 - Evaluation metier Amandine

### PLAN

- [x] Construire un petit jeu de questions Photoshop.
- [x] Construire un petit jeu de questions Illustrator.
- [x] Inclure questions version/bug/release notes.
- [x] Inclure questions ambiguës a traiter sans Auto: l'utilisateur doit choisir le produit.
- [x] Inclure cas ou Frida doit dire que la preuve est insuffisante.

### PATCH

- [x] Ajouter fixtures/evals si le framework existant le justifie.
- [x] Documenter le protocole manuel restant pour validation Amandine.
- [x] Ajouter snapshots content-free de preuves.
- [x] Renforcer les alias metier FR/EN bornes exposes par l'evaluation: detourage, disque, vectoriel, impression, import/export, suppression.

### TEST

- [x] Photoshop: detourage/masque, calques, remove tool, disque de travail, export.
- [x] Illustrator: plume, tracés, logo vectoriel, import PSD, PDF print.
- [x] Version: release notes lues pour questions recentes.
- [x] Bugs: known/fixed issues lues avant affirmation.
- [x] Refus: fonctionnalite inventee non confirmee.
- [x] Non-regression: chat normal sans Adobe.

### RISQUES

- [x] Eval trop facile.
- [x] Le modele repond par connaissance generale sans utiliser les sources.
- [x] Sources Adobe lues mais mal exploitees.

### REDUCTION DES RISQUES

- [x] Exiger citations/metadonnees de source.
- [x] Comparer mode Adobe actif vs inactif sur quelques cas.
- [x] Inclure questions pieges.
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
- [x] Test live Photoshop court.
- [x] Test live Illustrator court.

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
- [x] Le chat normal sans Adobe est inchangé.
- [x] Le web search general est inchangé sur le chemin UI streaming.
- [x] Crawl4AI `raw` lit les pages HelpX cibles.
- [x] Les liens internes HelpX sont suivis seulement dans le produit choisi.
- [x] Le nombre de pages lues par tour est borne.
- [x] Les passages injectes sont courts et sources.
- [x] Les grosses pages ne sont jamais injectees brutes.
- [ ] La reponse cite les sources ou signale l'insuffisance de preuve.
- [ ] Aucun contenu Adobe n'est stocke durablement.
- [ ] Aucun contenu Adobe n'entre en Memory/Identity/Summary/Biblio/Active Documents.
- [x] Les logs restent content-free.
- [x] Les tests couvrent non-regression chat/web normal.
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
