# Frida Biblio native / Frida Catalogue - TODO

Statut: actif
Date de creation: 2026-05-16
Classement: `app/docs/todo-todo/product/`
Audit-plan source: `app/docs/todo-todo/product/frida-biblio-native-catalogue-audit-plan.md`
Chantier compatible mais distinct archive: `app/docs/todo-done/product/active-conversation-documents-todo.md`
Spec fondatrice a creer: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Portee: consultation native, a la demande, d'une bibliotheque persistante via Frida Catalogue / doc-pipeline
Hors-scope du commit de creation: runtime, endpoint, frontend, migration, backfill, OCR, fusion avec documents actifs, AnythingLLM comme intermediaire principal, rebuild

## 1. Intention

Ce TODO ouvre le chantier produit Biblio native.

Le besoin est que Frida puisse consulter une bibliotheque persistante deja adossee a Frida Catalogue, identifier un document, resoudre un repere, extraire un passage borne, puis l'utiliser dans sa reponse.

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

## 4. Hors-scope du chantier

- fusion avec documents actifs;
- stockage des documents Catalogue dans l'etat actif serveur;
- transformation de la Biblio en document reinjecte a chaque tour;
- OCR;
- refonte doc-pipeline;
- migration ou backfill Catalogue;
- RAG documentaire opaque comme premiere promesse;
- AnythingLLM comme intermediaire principal;
- UI finale avant contrat;
- exposition brute de passages dans logs ou dashboard ordinaires.

## 5. Criteres de fermeture du chantier

Le chantier pourra etre clos seulement si:

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

La condition de non-prolongation est atteinte quand Frida sait consulter nativement Catalogue pour resoudre un document et un passage, injecter un extrait borne dans une lane dediee, et prouver l'operation sans melanger Biblio avec les documents actifs.

## 7. Lots

### Lot 1 - Spec fondatrice Biblio native

- [ ] Creer `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`.
- [ ] Stabiliser le vocabulaire: `library_document`, `catalogue_document`, `passage documentaire`, locator, resolution, ambiguite, confiance.
- [ ] Definir la frontiere avec `active_document`.
- [ ] Definir les sources de verite: Catalogue / doc-pipeline, pas AnythingLLM.
- [ ] Definir les limites initiales autour des milestones Stephanus.
- [ ] Definir la doctrine content-free.

### Lot 2 - Contrat d'outil / acces au Catalogue

- [ ] Choisir l'emplacement code FridaDev apres relecture du depot.
- [ ] Definir un client/service natif vers l'API Catalogue.
- [ ] Encapsuler `/catalog`, `/doc/...`, `/locate`, `/context`, `/search` et exports strictement utiles.
- [ ] Garantir que le chemin nominal ne depend pas d'AnythingLLM.
- [ ] Tester health, catalogue, document absent et erreur Catalogue.

### Lot 3 - Resolution documentaire et desambiguisation

- [ ] Resoudre un document par titre, corpus ou metadata disponible.
- [ ] Detecter les cas ambigus.
- [ ] Resoudre un locator simple.
- [ ] Traiter explicitement Stephanus et ses limites.
- [ ] Tester le cas `Platon` / `126b` / `126e` comme resolution ou ambiguite explicite.
- [ ] Ne jamais presenter une resolution incertaine comme certaine.

### Lot 4 - Extraction de passage borne

- [ ] Extraire un passage borne depuis les unites Catalogue disponibles.
- [ ] Definir longueur maximale et comportement si le passage est trop long.
- [ ] Retourner chars, hash court, locator resolu, document ref et statut.
- [ ] Tester passage trouve, absent, ambigu et trop long.
- [ ] Ne pas stocker le passage comme document actif.

### Lot 5 - Contrat prompt de lane `passage de bibliotheque consulte`

- [ ] Definir les balises ou l'encadrement stable.
- [ ] Enseigner au modele que la lane vient d'une bibliotheque persistante consultee a la demande.
- [ ] Expliquer que le passage consulte n'implique pas lecture de tout le document.
- [ ] Distinguer cette lane des documents actifs, Memory/RAG, summary, Identity, Web et Hermeneutic.
- [ ] Tester que l'instruction d'interpretation est presente dans le prompt final.

### Lot 6 - Observabilite / dashboard

- [ ] Ajouter events compacts de requete Biblio.
- [ ] Exposer document resolu, locator, passage extrait, statut, ambiguite, confiance, chars/hash sans contenu brut par defaut.
- [ ] Ajouter un module observable ou une projection compatible dashboard.
- [ ] Raconter dans l'inspection traduite: Biblio consultee, document resolu, passage extrait ou ambigu.
- [ ] Tester content-free strict.

### Lot 7 - UI Biblio eventuelle

- [ ] Auditer si une surface UI dediee est necessaire.
- [ ] Ne pas reutiliser un libelle generique `Documents` qui confondrait upload temporaire et Biblio.
- [ ] Definir navigation et libelles seulement apres validation du contrat.
- [ ] Garder cette UI hors du chemin critique si l'outil modele suffit au premier lot produit.

### Lot 8 - Tests / preuves

- [ ] Tester consultation Catalogue nominale.
- [ ] Tester document absent.
- [ ] Tester locator absent.
- [ ] Tester locator ambigu.
- [ ] Tester passage borne extrait.
- [ ] Tester exemple `126b -> 126e` avec statut fiable ou ambigu documente.
- [ ] Tester non-contamination `active_document`.
- [ ] Tester absence d'AnythingLLM dans le chemin nominal.

### Lot 9 - Documentation de cloture

- [ ] Mettre a jour les specs vivantes touchees.
- [ ] Documenter les limites restantes: OCR, editions, locators ambigus, UI future.
- [ ] Verifier que le TODO ne contient plus de case ouverte reelle.
- [ ] Archiver le TODO dans `app/docs/todo-done/product/` quand tous les lots sont fermes.

## 8. Tests attendus par le chantier

Les lots devront adapter les suites exactes au code courant, mais viser:

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

- Le bon emplacement code doit etre revalide avant patch.
- Les APIs Catalogue doivent etre consommees comme source persistante, pas copiees dans FridaDev.
- Les passages extraits ne doivent pas devenir des `active_document`.
- Les milestones Stephanus ne suffisent pas toujours a lever l'ambiguite.
- Les libelles UI doivent distinguer Biblio, documents actifs et Memory/RAG.
- Toute modification plateforme doc-pipeline reste hors scope FridaDev sauf demande explicite.
