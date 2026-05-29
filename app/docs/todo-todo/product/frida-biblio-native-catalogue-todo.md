# Frida Biblio native / Frida Catalogue - TODO

Statut: actif (Lots 0, 1, 2, 3, 4, 5, 6 et 7 livres, Lot 8 ouvert)
Date de creation: 2026-05-16
Classement: `app/docs/todo-todo/product/`
Audit-plan source: `app/docs/todo-todo/product/frida-biblio-native-catalogue-audit-plan.md`
Audit cible Lot 0: `app/docs/states/audits/frida-catalogue-human-metadata-editing-audit-2026-05-28.md`
Chantier compatible mais distinct archive: `app/docs/todo-done/product/active-conversation-documents-todo.md`
Spec fondatrice active: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Portee: Lot 0 prioritaire de correction humaine des metadonnees Catalogue, puis consultation native, a la demande, d'une bibliotheque persistante via Frida Catalogue / doc-pipeline
Hors-scope courant: runtime FridaDev, branchement LLM, endpoint FridaDev, migration DB dans ce depot, backfill, OCR, fusion avec documents actifs, AnythingLLM comme intermediaire principal, rebuild
Livraison Lot 0 plateforme: 2026-05-28, hors depot FridaDev, dans `/opt/platform/doc-pipeline` et `/opt/platform/doc-library`
Correctif UI Lot 0: 2026-05-28, protection du formulaire dirty contre l'auto-refresh Catalogue
Livraison Lot 1: 2026-05-28, spec native read-only creee dans `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Livraison Lot 2: 2026-05-28, client FridaDev Catalogue GET-only cree dans `app/biblio/catalogue_client.py`
Correctif Lot 2: 2026-05-28, validation bornee et strictement entiere des parametres numeriques publics avant reseau avec erreur `biblio_catalogue_invalid_parameter`
Livraison Lot 3: 2026-05-28, resolver documentaire cree dans `app/biblio/document_resolver.py`, sans extraction de passage ni branchement chat
Correctif Lot 3: 2026-05-28, observabilite resolver rendue content-free pour les locators demandes et resolus
Livraison Lot 4: 2026-05-28, extraction de passage bornee creee dans `app/biblio/passage_extractor.py`, sans branchement chat ni lane prompt
Correctif Lot 4: 2026-05-28, `document_id` rendu obligatoire dans le payload `/context` avant extraction
Livraison Lot 5: 2026-05-29, lane prompt Biblio creee dans `app/biblio/prompt_lane.py`, sans branchement chat, frontend, toggle, API, Catalogue, DB, Memory/RAG, Identity, Summary, Web ni OCR
Correctif post-audit Lot 5: 2026-05-29, hash observable durci et balises Biblio internes neutralisees dans le texte injecte
Livraison Lot 6: 2026-05-29, observabilite/admin Biblio content-free creee dans `app/biblio/observability.py` et `GET /api/admin/biblio/observability`, avec module dashboard `biblio`, sans branchement chat, frontend, toggle, Catalogue automatique ni DB Biblio
Correctif post-audit Lot 6: 2026-05-29, persistence dashboard `biblio_json` ajoutee a `observability.dashboard_turn_facts` et relue par le read-model admin
Livraison Lot 7: 2026-05-29, toggle frontend Biblio et branchement chat minimal livres via `app/web/chat_biblio_mode.js` et `app/biblio/chat_runtime.py`, avec detection conservatrice, lane prompt injectee seulement apres extraction et observabilite `stage=biblio` content-free

## 1. Intention

Ce TODO ouvre le chantier produit Biblio native.

Priorite produit du 2026-05-28: avant de brancher Frida sur Catalogue, rendre le Catalogue humainement editable pour corriger les metadonnees bibliographiques sales ou trop pauvres. Un ouvrage affiche comme `der` doit pouvoir etre corrige manuellement en titre bibliographique lisible, avec auteur, editeur, collection, annee, langue, type et notes operateur si necessaire.

Le besoin cible reste que Frida puisse consulter une bibliotheque persistante deja adossee a Frida Catalogue, identifier un document, resoudre un repere, extraire un passage borne, puis l'utiliser dans sa reponse. Mais ce branchement doit attendre une surface Catalogue fiable et corrigible.

Ce chantier est separe des documents actifs de conversation:

- `active_document`: fichier temporaire fourni par l'utilisateur, actif dans une conversation jusqu'au retrait manuel;
- `library_document` / `catalogue_document`: document persistant connu du Catalogue;
- `passage documentaire`: extrait borne issu d'un document de bibliotheque et consulte a la demande.

Pourquoi deux chantiers separes mais compatibles ?

- ils ne partagent pas la meme duree de vie;
- ils ne partagent pas le meme etat serveur;
- ils ne partagent pas le meme geste utilisateur;
- ils doivent en revanche partager une discipline de lanes prompt, d'observabilite content-free et de vocabulaire clair.

## 2. Doctrine produit

- Frida consulte la Biblio a la demande, elle ne garde pas tout le document comme contexte actif.
- Le passage extrait peut etre utilise dans la reponse du tour.
- Une fois repris dans la reponse, le passage devient matiere conversationnelle ordinaire.
- La Biblio n'est pas un upload temporaire.
- La Biblio n'est pas un `active_document`.
- La Biblio n'est pas un RAG opaque sans preuve de document / locator.
- La Biblio doit avoir son propre contrat prompt.
- La Biblio doit avoir sa propre observabilite.
- Les metadonnees bibliographiques corrigees par humain doivent etre distinguees du nom de fichier source et des metadonnees extraites automatiquement.
- Les corrections humaines doivent etre sauvegardees en SQL avec audit minimal.
- La suppression DB/fichiers doit demander une confirmation forte et rester distincte de l'edition de metadonnees.
- AnythingLLM et OpenWebUI peuvent etre relus comme precedents, mais ne sont pas le chemin principal cible.
- Les milestones Stephanus aident, mais ne suffisent pas toujours a garantir une resolution fiable.

## 3. Existant a respecter

La cartographie read-only a confirme:

- Frida Catalogue / doc-pipeline existent deja;
- la DB contient notamment `documents`, `pages`, `paragraphs`, `raw_units`, `milestones`, `document_chapters`;
- l'API expose deja des primitives de catalogue, document, localisation, contexte, recherche et exports;
- un corpus Platon existe;
- des milestones Stephanus existent;
- des reperes comme `126b` et `126e` existent;
- `126b -> 126e` est faisable en principe, mais pas fiable tel quel sans desambiguisation oeuvre / dialogue / passage;
- l'instance AnythingLLM courante n'est pas une vraie source active de bibliotheque;
- `frida_biblio.py` cote OpenWebUI est un precedent utile a relire, pas l'integration cible.
- la spec Lot 1 `app/docs/states/specs/frida-biblio-native-catalogue-contract.md` fixe maintenant le contrat FridaDev GET-only, les frontieres, le toggle futur, le resolver, l'extraction bornee, la lane prompt et l'observabilite content-free.
- le client Lot 2 `app/biblio/catalogue_client.py` implemente la lecture Catalogue GET-only sans branchement chat, prompt, frontend, DB, Memory/RAG, Identity, Summary ou OCR.

Audit cible Lot 0 du 2026-05-28:

- la page humaine visible est `FRIDA Bibliotheque`, servie hors FridaDev par `/opt/platform/doc-library/index.html` via Caddy `/bibliotheque*`;
- Homepage pointe `FRIDA Catalogue` vers `https://home.frida-system.fr/bibliotheque`;
- la fiche JSON et la liste appellent l'API doc-pipeline via `/doc-api`;
- l'API Catalogue est dans `/opt/platform/doc-pipeline/query_api.py`;
- la table metadata actuelle est surtout `documents`;
- les metadonnees SQL courantes sont des metadonnees d'ingestion/OCR: `title`, `source_filename`, hash, langue, compteurs, qualite JSON, type source et TOC;
- aucun champ auteur, traducteur, editeur, collection, annee, notes operateur, statut de validation ou titre original n'existe dans `documents`;
- aucune table audit/history/revision/metadata/edit n'a ete trouvee;
- aucune route `PATCH`/`PUT` de metadonnees documentaires n'a ete trouvee;
- deux routes de suppression existent deja: `DELETE /doc/{doc_id}` et `DELETE /doc/{doc_id}/with-files`;
- le front Catalogue actuel expose deja ces suppressions via deux boutons et `window.confirm`;
- le front Catalogue actuel n'est pas dans le depot FridaDev.

Livraison plateforme Lot 0 du 2026-05-28:

- `/opt/platform/doc-pipeline/db_store.py` ajoute les tables SQL separees `catalogue_human_metadata` et `catalogue_human_metadata_audit`;
- `/opt/platform/doc-pipeline/query_api.py` ajoute les routes non destructrices `GET /doc/{doc_id}/metadata` et `PUT /doc/{doc_id}/metadata`;
- `/opt/platform/doc-library/index.html` ajoute une fiche ouvrage lisible et un formulaire d'edition des metadonnees humaines;
- les suppressions existantes restent separees dans une zone dangereuse, avec confirmation par saisie de l'id document complet;
- l'edition metadata ne modifie pas les tables OCR, les pages, les paragraphs, les raw units, les milestones ni les fichiers sources;
- aucune route DELETE n'a ete appelee pendant la livraison;
- aucun OCR, branchement Frida/LLM, Memory/RAG, document actif ou workspace n'a ete ajoute;
- backup plateforme: `/opt/platform/backups/catalogue-human-metadata-20260528-155550`;
- preuve smoke content-free: une note operateur benigne a ete ecrite puis relue sur un document test reel, id court `dabfe4a7`, avec une ligne d'audit.

Correctif UI Catalogue du 2026-05-28:

- `/opt/platform/doc-library/index.html` protege le formulaire metadata avec un etat `formDirty`;
- l'auto-refresh periodique est suspendu pendant une edition non sauvegardee;
- le reload de fiche selectionnee ne remplace plus les valeurs du formulaire si la fiche est dirty;
- le changement volontaire de fiche demande confirmation avant perte des modifications;
- apres sauvegarde, la fiche peut etre rechargee proprement depuis l'API;
- backup plateforme: `/opt/platform/backups/catalogue-ui-refresh-fix-20260528-164209`;
- nettoyage realise: `/tmp/catalogue-human-metadata-work` supprime;
- aucun changement DB, API doc-pipeline, OCR, FridaDev runtime, Caddy, Authelia ou Homepage.

## 4. Hors-scope du chantier

- fusion avec documents actifs;
- stockage des documents Catalogue dans l'etat actif serveur;
- transformation de la Biblio en document reinjecte a chaque tour;
- re-OCR dans le Lot 0;
- branchement Frida/LLM dans le Lot 0;
- injection Memory/RAG dans le Lot 0;
- refonte doc-pipeline non bornee;
- migration ou backfill Catalogue hors lot explicite;
- RAG documentaire opaque comme premiere promesse;
- AnythingLLM comme intermediaire principal;
- UI finale FridaDev avant contrat;
- exposition brute de passages dans logs ou dashboard ordinaires.

## 5. Criteres de fermeture du chantier

Le chantier pourra etre clos seulement si:

Note 2026-05-28: les criteres Lot 0 ci-dessous sont remplis cote plateforme Catalogue, mais le chantier global reste actif tant que les lots FridaDev read-only et chat ne sont pas livres.

- le Lot 0 a rendu les metadonnees Catalogue corrigeables humainement ou a ete explicitement requalifie par decision produit;
- la liste Catalogue et la fiche ouvrage sont lisibles par un humain, pas seulement en JSON brut;
- le modele de metadonnees distingue fichier source, extraction automatique et correction humaine;
- l'edition metadata est sauvegardee en SQL avec audit minimal;
- la suppression DB/fichiers est protegee par confirmation forte;
- une spec fondatrice active existe;
- le vocabulaire `active_document` / `library_document` / `catalogue_document` / `passage documentaire` est stabilise;
- Frida peut consulter Catalogue via un contrat natif;
- un document peut etre identifie avec preuve compacte;
- un locator peut etre resolu ou marque ambigu/non resolu;
- un passage borne peut etre extrait;
- la lane prompt `passage de bibliotheque consulte` ou equivalent est definie;
- le modele recoit une instruction expliquant le statut du passage consulte;
- l'observabilite montre requete, document resolu, locator, passage extrait, ambiguite et confiance sans contenu brut par defaut;
- l'exemple type `126b -> 126e` est teste comme cas de resolution ou d'ambiguite explicite;
- AnythingLLM n'est pas requis dans le chemin nominal;
- les documents actifs restent separes et non contamines.

## 6. Condition de non-prolongation

Ne pas prolonger ce chantier vers une refonte complete de doc-pipeline, une bibliotheque UI definitive, un OCR generalise, un RAG documentaire opaque ou une ingestion longue duree non decidee.

Le Lot 0 s'arrete quand la correction humaine des metadonnees Catalogue est possible, auditee minimalement et protegee cote suppression, sans re-OCR ni branchement Frida/LLM.

La condition de non-prolongation globale est atteinte quand Frida sait consulter nativement Catalogue pour resoudre un document et un passage, injecter un extrait borne dans une lane dediee, et prouver l'operation sans melanger Biblio avec les documents actifs.

## 7. Lots

### Lot 0 - Catalogue humain editable / correction des metadonnees

Responsabilite probable: stack Catalogue / doc-pipeline sous discipline Sauron, pas runtime FridaDev, sauf decision explicite contraire.

- [x] Confirmer le repo/runtime proprietaire de la page `FRIDA Bibliotheque`, de l'API `/doc-api` et de la DB Catalogue avant tout patch.
- [x] Afficher une liste lisible des ouvrages OCRises avec titre humain, auteur si disponible, type, langue, statut metadata et fichier source.
- [x] Ajouter une fiche ouvrage lisible, pas seulement la fiche JSON brute.
- [x] Permettre l'edition manuelle des metadonnees bibliographiques.
- [x] Sauvegarder les corrections en SQL.
- [x] Distinguer explicitement:
  - nom de fichier source;
  - metadonnees extraites automatiquement;
  - metadonnees corrigees humainement.
- [x] Prevoir au minimum:
  - titre canonique;
  - titre original;
  - auteur(s);
  - traducteur(s) / editeur scientifique si pertinent;
  - editeur;
  - collection;
  - annee;
  - langue;
  - type: livre, article, recueil, oeuvres completes, etc.;
  - fichier source;
  - notes operateur;
  - statut implemente: `to_review`, `corrected`, `validated`.
- [x] Ajouter un audit minimal de modification metadata: date, champ, anciennes/nouvelles valeurs, acteur logique si disponible.
- [x] Remplacer les suppressions legeres par une confirmation forte pour DB seule et DB + fichiers.
- [x] Tester que l'edition metadata ne lance pas de re-OCR.
- [x] Tester que l'edition metadata ne branche pas Frida/LLM, Memory/RAG, documents actifs ou workspace.
- [x] Proteger le formulaire metadata contre l'auto-refresh destructeur pendant une edition dirty.

### Lot 1 - Spec FridaDev Biblio native read-only

- [x] Creer `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`.
- [x] Stabiliser le vocabulaire: `library_document`, `catalogue_document`, `passage documentaire`, locator, resolution, ambiguite, confiance.
- [x] Definir la frontiere avec `active_document`.
- [x] Definir les sources de verite: Catalogue / doc-pipeline, pas AnythingLLM.
- [x] Definir les limites initiales autour des milestones Stephanus.
- [x] Definir la doctrine content-free.
- [x] Definir que FridaDev consomme Catalogue en lecture seule au depart.

### Lot 2 - Client Catalogue GET-only

- [x] Choisir l'emplacement code FridaDev apres relecture du depot: `app/biblio/catalogue_client.py`.
- [x] Definir un client/service natif GET-only vers l'API Catalogue.
- [x] Encapsuler `/catalog`, `/doc/...`, `/metadata`, `/locate`, `/context` et `/search` strictement utiles au Lot 2.
- [x] Interdire au client FridaDev initial les routes DELETE, PUT metadata, settings et progress mutateurs.
- [x] Valider les parametres numeriques publics avant reseau avec erreurs Biblio content-free, sans troncature silencieuse.
- [x] Garantir que le chemin nominal ne depend pas d'AnythingLLM.
- [x] Tester health, catalogue, document absent et erreur Catalogue.

### Lot 3 - Resolver documentaire

- [x] Resoudre un document par id, titre, auteur ou metadata Catalogue disponible.
- [x] Detecter les cas ambigus.
- [x] Resoudre un locator simple sans extraction de passage.
- [x] Traiter explicitement Stephanus et ses limites: un locator sans document resolu est `invalid_request`, pas `resolved`.
- [x] Tester le cas `Platon` / `126b` / `126e` comme resolution ou ambiguite explicite.
- [x] Ne jamais presenter une resolution incertaine comme certaine.
- [x] Garantir que l'observabilite du resolver n'expose pas les locators bruts, titres, auteurs, payloads ou texte d'ouvrage.

### Lot 4 - Extraction passage bornee

- [x] Extraire un passage borne depuis les unites Catalogue disponibles via `context()` GET-only.
- [x] Definir longueur maximale et comportement si le passage est trop long: `too_long`, sans passage brut accepte.
- [x] Retourner chars, hash court, locator resolu, document ref et statut.
- [x] Tester passage trouve, absent, ambigu, vide, incoherent, indisponible et trop long.
- [x] Ne pas stocker le passage comme document actif.
- [x] Garantir que `to_observability()` n'expose pas passage brut, texte OCR, payload Catalogue, locator brut, titre, auteur ou requete utilisateur brute.
- [x] Refuser les ranges resolus dans ce lot avec `range_extraction_not_supported`, pour ne pas extraire silencieusement seulement le debut.

### Lot 5 - Lane prompt dediee

- [x] Definir les balises ou l'encadrement stable: `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`.
- [x] Creer `app/biblio/prompt_lane.py` comme formatter dedie de `BiblioPassageResult` deja extraits.
- [x] Injecter dans la lane seulement les resultats `status=extracted` avec passage present.
- [x] Enseigner au modele, dans le bloc produit, que la lane vient d'une bibliotheque persistante consultee a la demande.
- [x] Expliquer que le passage consulte n'implique pas lecture de tout le document.
- [x] Distinguer cette lane des documents actifs, Memory/RAG, summary, Identity, Web et Hermeneutic.
- [x] Definir les bornes locales: `DEFAULT_MAX_PASSAGES = 3` et `DEFAULT_MAX_TOTAL_CHARS = 8000`.
- [x] Tracer explicitement les skips content-free: statut non extrait, passage vide, limite nombre, limite taille.
- [x] Ajouter `BiblioPromptLane.to_observability()` content-free: compte passages, skips, chars, hashes courts, doc ids courts, positions non textuelles et decisions.
- [x] Corriger le hash observable pour ne jamais exposer un `passage_hash` arbitraire.
- [x] Neutraliser les balises Biblio presentes dans un passage avant injection dans la lane.
- [x] Tester que l'instruction d'interpretation est presente dans la lane produite.
- [x] Tester que la lane ne confond pas ses balises avec les documents actifs.

Note Lot 5: le prompt final du chat n'est pas modifie dans ce lot. `app/biblio/prompt_lane.py` fabrique seulement un message de lane disponible pour un lot futur; il n'appelle pas Catalogue et ne decide pas quoi extraire.

### Lot 6 - Observabilite/admin FridaDev

- [x] Ajouter events compacts de requete Biblio.
- [x] Exposer document resolu, locator, passage extrait, statut, ambiguite, confiance, chars/hash sans contenu brut par defaut.
- [x] Ajouter un module observable ou une projection compatible dashboard.
- [x] Raconter dans l'inspection traduite: Biblio consultee, document resolu, passage extrait ou ambigu.
- [x] Tester content-free strict.

Note Lot 6: `app/biblio/observability.py` construit une projection passive `stage=biblio` et une surface admin read-only. Le lot ne branche toujours pas le chat, ne lance pas de recherche Catalogue, ne cree pas de route metier Biblio, ne cree pas de toggle et ne serialise jamais `BiblioPromptLane.message`.

Correctif Lot 6: le dashboard materialise conserve maintenant `fact["biblio"]` dans `biblio_json` et le read-model admin le relit. La colonne est ajoutee par migration additive `ADD COLUMN IF NOT EXISTS`; elle ne contient que la projection compacte content-free.

### Lot 7 - Branchement chat minimal

- [x] Brancher le resolver et la lane dans un chemin chat minimal.
- [x] Garder le declenchement borne et explicite.
- [x] Tester consultation Catalogue nominale.
- [x] Tester document absent.
- [x] Tester locator absent.
- [x] Tester locator ambigu.
- [x] Tester passage borne extrait.
- [x] Tester exemple `126b -> 126e` avec statut fiable ou ambigu documente.
- [x] Tester non-contamination `active_document`.
- [x] Tester absence d'AnythingLLM dans le chemin nominal.
- [x] Mettre a jour les specs vivantes touchees.
- [x] Documenter les limites restantes: OCR, editions, locators ambigus, UI future.
- [ ] Verifier que le TODO ne contient plus de case ouverte reelle.
- [ ] Archiver le TODO dans `app/docs/todo-done/product/` quand tous les lots sont fermes.

Note Lot 7: le branchement est volontairement minimal. `app/biblio/chat_runtime.py` ne construit un client Catalogue que si le toggle `biblio_enabled` est actif et si le message contient un signal bibliographique conservateur. Les skips `toggle_disabled`, `no_bibliographic_signal` et `adobe_topic_ignored` sont explicites et content-free. La lane n'est injectee dans le prompt principal que si `build_biblio_prompt_lane()` produit un message a partir d'un passage extrait. Le frontend ajoute `btnBiblioMode` avec icone livre juste apres Adobe et transmet toujours `biblio_enabled`.

Limites restantes documentees apres Lot 7: ranges de locators toujours non extraits silencieusement, OCR et editions Catalogue hors FridaDev, detection bibliographique volontairement conservatrice, pas d'UI Catalogue dans FridaDev, pas de recherche semantique large ni de RAG documentaire.

## 8. Tests attendus par le chantier

Les lots devront adapter les suites exactes au code courant, mais viser:

- tests plateforme Lot 0 metadata: edition, persistance SQL, audit minimal, confirmation suppression, absence de re-OCR;
- tests unitaires client Catalogue;
- tests de resolution documentaire;
- tests Stephanus / locator;
- tests d'extraction borne;
- tests prompt lane Biblio;
- tests observabilite content-free;
- tests dashboard read-model;
- tests anti-confusion avec documents actifs;
- tests d'absence de dependance AnythingLLM.

## 9. Notes d'implementation a revalider a chaque lot

- Le bon emplacement code doit etre revalide avant patch; Lot 0 semble appartenir a la stack Catalogue `/opt/platform/doc-pipeline` / `/opt/platform/doc-library`, pas au runtime FridaDev.
- Le premier client FridaDev doit rester GET-only.
- Les APIs Catalogue doivent etre consommees comme source persistante, pas copiees dans FridaDev.
- Les passages extraits ne doivent pas devenir des `active_document`.
- Les milestones Stephanus ne suffisent pas toujours a lever l'ambiguite.
- Les libelles UI doivent distinguer Biblio, documents actifs et Memory/RAG.
- Toute modification plateforme doc-pipeline reste hors scope FridaDev sauf demande explicite.
