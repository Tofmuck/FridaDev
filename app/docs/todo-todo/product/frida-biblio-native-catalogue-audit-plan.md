# Frida Biblio native / Frida Catalogue - audit-plan

Statut: actif
Date: 2026-05-16
Classement: `app/docs/todo-todo/product/`
TODO derive: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Chantier compatible mais distinct: `app/docs/todo-todo/product/active-conversation-documents-todo.md`
Portee: consultation native, a la demande, d'une bibliotheque documentaire persistante deja adossee a Frida Catalogue / doc-pipeline
Hors-scope: runtime dans ce commit, endpoint FridaDev, frontend, migration, backfill, OCR, fusion avec documents actifs, AnythingLLM comme intermediaire principal

## 1. Question initiale et verdict

Existe-t-il un meilleur plan ?

Non pour ce cycle docs-only. Le meilleur plan est de creer un chantier Biblio separe maintenant, pendant que la cartographie est fraiche, sans lancer d'implementation runtime.

Verdict produit:

- documents actifs de conversation = fichiers temporaires fournis par l'utilisateur, actifs dans une conversation, reinjectes jusqu'au retrait manuel;
- Biblio native = bibliotheque persistante consultable a la demande, capable de resoudre un document et un passage, puis d'injecter l'extrait utile dans le tour;
- les deux capacites doivent partager une discipline de lanes, de vocabulaire et d'observabilite, mais pas le meme etat serveur.

## 2. Question produit

Le besoin cible n'est pas de poser tout un livre comme document actif du chat.

Exemple produit:

```text
Va dans les oeuvres completes de Platon, prends le passage du Theetete 126b a 126e, et sors-moi ce passage.
```

Le flux attendu est:

1. Frida comprend qu'elle doit consulter une bibliotheque persistante.
2. Frida identifie le document ou corpus cible.
3. Frida resout le repere documentaire demande.
4. Frida extrait un passage borne.
5. Frida utilise ce passage dans sa reponse.
6. Une fois repris dans la reponse, le passage devient matiere conversationnelle ordinaire.

Ce n'est ni un upload temporaire, ni un `active_document`, ni un bloc reinjecte a chaque tour jusqu'au retrait manuel.

## 3. Cartographie existante reprise de l'audit read-only

### Stack documentaire OVH

La stack OVH contient deja une base documentaire reelle autour de Frida Catalogue / doc-pipeline.

Zones observees en lecture seule:

- `doc-pipeline`;
- `doc-library`;
- `ocr-web`;
- stockage OCR dedie;
- instance AnythingLLM existante, relue seulement comme precedent.

Conteneurs observes:

- service pipeline documentaire;
- API pipeline documentaire;
- DB pipeline documentaire;
- UI bibliotheque;
- service info pipeline;
- AnythingLLM.

### DB Catalogue

Tables principales observees:

- `documents`;
- `pages`;
- `paragraphs`;
- `raw_units`;
- `milestones`;
- `document_chapters`;
- `schema_migrations`.

Comptes compacts observes pendant l'audit:

- documents: 10;
- types sources: PDF et EPUB;
- pages / sections: 4 837;
- paragraphes: 101 421;
- raw_units: 378 034;
- milestones: 26 492, avec repere `Stephanus`;
- chapters: 973.

Aucun contenu documentaire brut n'a ete repris dans ce plan.

### API existante

L'API Catalogue expose deja des primitives utiles, notamment:

- `/health`;
- `/catalog`;
- `/doc/...`;
- acces pages / paragraphes;
- `/locate`;
- `/context`;
- `/search`;
- exports document / chapitre / chunks selon les chemins existants.

Ces routes prouvent une base consultable, mais elles ne constituent pas encore une integration native FridaDev.

### Corpus Platon et Stephanus

La cartographie a confirme:

- un corpus Platon existe dans Catalogue;
- des milestones `Stephanus` existent;
- des reperes comme `126b`, `126c`, `126d`, `126e` existent.

Limite majeure:

- `126b -> 126e` est faisable en principe, mais pas fiable tel quel sans desambiguisation oeuvre / dialogue / passage;
- les milestones seuls ne prouvent pas toujours que le bon dialogue, la bonne edition ou le bon segment ont ete resolus;
- une couche native devra expliciter document cible, locator, ambiguite et confiance.

### AnythingLLM / OpenWebUI

L'instance AnythingLLM courante ne doit pas etre traitee comme source principale de bibliotheque:

- elle n'etait pas peuplee comme bibliotheque active exploitable pour ce besoin;
- elle sert surtout de precedent faible sur la notion de workspace / vecteurs;
- elle ne change pas la recommandation d'une integration native Frida.

Le fichier `frida_biblio.py` cote OpenWebUI est en revanche un precedent utile a relire pour:

- catalogue;
- recherche;
- localisation Stephanus;
- contexte;
- exports.

Il reste un precedent d'interface, pas le chemin cible.

## 4. Qualification produit

Biblio native est un chantier separe des documents actifs.

| Capacite | Documents actifs de conversation | Biblio native / Frida Catalogue |
| --- | --- | --- |
| Origine | Fichier fourni par l'utilisateur | Bibliotheque persistante deja connue |
| Duree | Temporaire, conversation-scoped | Durable, hors conversation |
| Activation | Drag-and-drop / retrait manuel | Demande utilisateur ou outil modele |
| Injection | Document entier ou absent par tour | Passage borne extrait a la demande |
| Repetition | Reinjecte tant qu'actif | Non reinjecte par defaut a chaque tour |
| Etat serveur | Etat actif temporaire | Catalogue persistant separe |
| Observabilite | actif, injecte, retire, trop gros | requete, document resolu, locator, passage extrait, ambiguite, confiance |
| Prompt | Lane `documents actifs` | Lane future `passage de bibliotheque consulte` |

Ils sont compatibles parce qu'ils peuvent partager une discipline de lanes et d'observabilite content-free. Ils ne sont pas la meme capacite.

## 5. Architecture cible recommandee

### 5.1 Principe

Construire une integration native Frida, au-dessus de Frida Catalogue / doc-pipeline, sans passer par AnythingLLM comme intermediaire principal.

Le futur module Biblio doit:

- exposer un contrat d'outil ou de service interne;
- interroger Catalogue;
- resoudre document + locator;
- extraire un passage borne;
- restituer une preuve content-free de ce qui a ete consulte;
- injecter le passage dans une lane prompt dediee;
- garder le passage lui-meme hors des logs ordinaires.

### 5.2 Lane prompt

La future lane doit etre distincte de:

- `documents actifs`;
- Memory/RAG;
- summary;
- Identity;
- Web;
- Hermeneutic.

Nom conceptuel:

- `passage de bibliotheque consulte`;
- ou equivalent a fixer dans la spec fondatrice.

Le modele doit comprendre que:

- le passage vient d'une bibliotheque persistante;
- il a ete extrait en reponse a une requete documentaire;
- il peut servir a repondre a la demande courante;
- il ne prouve pas que tout le document ou tout le corpus a ete lu;
- les ambiguites ou limites de resolution doivent etre respectees.

### 5.3 Observabilite

Par defaut, rendre visible:

- requete Biblio;
- document resolu;
- document_id / hash court / titre content-free si applicable;
- locator demande;
- locator resolu;
- passage extrait oui/non;
- longueur / chars / hash court;
- ambiguite;
- confiance ou statut de resolution;
- erreurs compactes.

Ne pas afficher par defaut:

- texte complet du passage;
- document complet;
- contenu brut de la requete si elle contient du texte sensible;
- secret, DSN, token ou credential.

### 5.4 Relation avec la reponse

Quand Frida cite ou reprend le passage dans sa reponse, ce texte entre naturellement dans la conversation ordinaire. Cela ne transforme pas la bibliotheque en document actif, et ne rend pas le document persistant actif dans les tours suivants.

## 6. Alternatives considerees

### Fusion avec documents actifs

Rejetee. Un document actif est temporaire et fourni par l'utilisateur. Un document de bibliotheque est persistant et consulte a la demande. Les fusionner rendrait confus le retrait manuel, la reinjection multi-tour et l'observabilite.

### AnythingLLM comme intermediaire principal

Rejete comme chemin cible. L'instance courante ne porte pas la bibliotheque active et l'architecture produit veut une integration native Frida. AnythingLLM peut rester une source de comparaison, pas une dependance centrale.

### RAG opaque sur tout Catalogue

Rejete comme premiere promesse. Le besoin produit inclut des demandes par repere fin, comme `126b -> 126e`. Il faut savoir expliquer quel document, quel locator et quel passage ont ete resolus, pas seulement retourner un chunk vectoriel opaque.

### Supposer que Stephanus suffit

Rejete. Les milestones Stephanus sont un atout, mais la resolution fine exige une couche de desambiguisation oeuvre / dialogue / passage / edition et une preuve de confiance.

## 7. Risques

- Ambiguite documentaire: plusieurs occurrences du meme locator peuvent exister.
- Illusion de precision: `126b -> 126e` peut sembler resolu alors que le dialogue cible ne l'est pas.
- RAG opaque: il peut masquer les erreurs de document ou de repere.
- Fuite de contenu: les passages peuvent etre sensibles ou longs; logs ordinaires content-free obligatoires.
- Confusion UI: un bouton generique `Documents` melangerait upload temporaire et Biblio.
- Dependances plateforme: FridaDev ne doit pas modifier la stack doc-pipeline dans un lot applicatif sans decision explicite.
- AnythingLLM: utile comme precedent, dangereux comme detour si traite comme cible.

## 8. Preuves attendues quand le code commencera

Les futurs lots devront prouver:

- consultation Catalogue sans event_limit ni scraping UI;
- resolution d'un document par titre / corpus;
- resolution explicite d'un locator;
- extraction borne d'un passage;
- cas ambigu avec statut non definitif;
- cas absent / non resolu;
- lane prompt distincte de `active_document`;
- observabilite content-free;
- absence de contenu brut dans dashboard ordinaire;
- non-dependance a AnythingLLM comme chemin principal.
