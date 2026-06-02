# Frida Biblio refonte

Date: 2026-06-02
Statut: TODO active
Classement: `app/docs/todo-todo/product/`
Sources:

- `app/docs/states/audits/frida-biblio-stephanus-library-audit-2026-06-02.md`
- `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`

Portee: matrice d'action produit pour transformer Biblio en bibliotheque
reellement consultable. Ce document ne remplace pas le contrat agent ni la
roadmap agent. Il sert de plan d'execution transverse entre FridaDev et
Catalogue / DB / indexation.

## 1. Objectif produit final

Frida doit pouvoir utiliser la bibliotheque comme une vraie bibliotheque:

- lister tout le catalogue disponible tant que la taille reste raisonnable;
- ouvrir un document, un volume ou une edition sans le confondre avec une
  oeuvre interne;
- afficher une table des matieres reelle et exploitable;
- distinguer auteur, corpus, volume, oeuvre et edition;
- chercher un passage par theme, chaine exacte, locator simple ou intervalle
  canonique;
- naviguer avant, apres, autour, page par page ou sur une plage de pages quand
  l'outillage et les donnees le permettent;
- dire honnetement quand elle a un passage exact, un candidat plausible ou une
  approximation contextuelle;
- verifier la provenance du passage et privilegier le texte primaire avant le
  commentaire, la notice ou l'introduction.

## 2. Constats de depart

- [ ] Le systeme actuel n'est pas encore une vraie bibliotheque complete.
- [ ] Le front FridaDev et le front Catalogue / DB / indexation doivent etre
      traites separement, puis recales ensemble.
- [ ] Les smokes verts et les lanes injectees ne prouvent pas a eux seuls une
      capacite produit reelle.
- [ ] `catalog_search` est encore utilise comme bequille universelle alors qu'il
      ne prouve ni l'oeuvre, ni la source, ni l'exactitude du passage.
- [ ] Le parse metier reste tordu sur des formes du type `Theetete de Platon`
      et melange encore trop facilement oeuvre, auteur, corpus et document.
- [ ] Le systeme ne porte pas encore un objet natif d'intervalle canonique.
- [ ] La navigation sequentielle reelle manque encore cote contrat FridaDev.
- [ ] Des routes utiles existent deja cote Catalogue, mais ne sont pas encore
      integrees proprement dans le contrat Biblio FridaDev.
- [ ] Une partie des validations precedentes ont prouve des capacites
      partielles, pas une bibliotheque pleinement manipulable.

## 3. Matrice des capacites metier

| TODO | Capacite | Etat actuel | Front | Action a mener | Dependance | Validation produit reelle |
| --- | --- | --- | --- | --- | --- | --- |
| [ ] | Lister le catalogue | livre | FridaDev | Garder l'affichage complet jusqu'a 100 et rendre explicite la continuation au-dela | aucune | Frida n'annonce jamais une page comme totalite si le total depasse l'affichage |
| [ ] | Paginer le catalogue | partiel | FridaDev | Formaliser continuation, reprise et borne produit | etat multi-tour Biblio stable | `continue la liste` reprend proprement sans re-lister au hasard |
| [ ] | Ouvrir un ouvrage / volume / edition | partiel | mixte | Distinguer ouverture bibliographique, resume document et lecture documentaire | resolution oeuvre/document plus nette | Frida sait dire ce qu'elle a ouvert et a quel niveau |
| [ ] | Distinguer oeuvre / auteur / corpus / volume | partiel | FridaDev | Refaire la resolution metier, notamment sur `Theetete de Platon` | normalisation + resolveur metier | Les requetes mixtes ne tombent plus sur le mauvais niveau documentaire |
| [ ] | Afficher la table des matieres | livre | FridaDev | Garder la route legere et mieux l'integrer dans la logique produit | aucune | Une demande TOC reelle liste les chapitres sans faux resume |
| [ ] | Rechercher dans la table des matieres | absent | mixte | Definir si la recherche passe par chapters indexes, metadata ou outil dedie | contrat outil TOC + donnees Catalogue | Frida peut trouver une oeuvre interne via TOC sans detour fragile par paragraph search |
| [ ] | Chercher un passage par theme dans une oeuvre | partiel | mixte | Remplacer la logique `search -> premier contexte utile` par une selection bibliothecaire verifiable | meilleur ranking + source classes | Frida renvoie soit un passage plausible justifie, soit une ambiguite claire |
| [ ] | Chercher un passage par theme dans tout le corpus | partiel | mixte | Definir scope corpus, ranking, desambiguation et reprise | separation oeuvre/corpus + signals source | Frida dit dans quel corpus elle a cherche et pourquoi elle retient ou non un passage |
| [ ] | Chercher une chaine exacte | partiel | Catalogue/DB | Verifier et documenter les garanties exact-match et les limites d'index | index texte et surfaces d'appel | Frida distingue clairement exact-match, zero hit et hit contextuel |
| [ ] | Locator canonique simple | livre | mixte | Conserver `locate -> context` comme chemin exact borne | document_id + label simple resolus | Un locator simple donne une extraction ou une ambiguite honnete |
| [ ] | Intervalle canonique | absent | Catalogue/DB | Definir un objet natif ou un mapping stable debut/fin -> sequence documentaire | chantier indexation intervalle | Frida ne simule plus un range general avec une astuce locale |
| [ ] | Extraire ce qui precede un passage | partiel | FridaDev | La navigation page existe; la navigation exacte intra-page reste a definir | outil page borne + ancre de passage plus fine | `ce qui precede` ne depend plus d'une approximation libre |
| [ ] | Extraire ce qui suit un passage | partiel | FridaDev | La navigation page existe; la navigation exacte intra-page reste a definir | outil page borne + ancre de passage plus fine | `continue apres ce passage` donne une vraie continuation documentaire |
| [ ] | `autour de ce passage` | partiel | FridaDev | Clarifier la difference entre voisinage exact et simple contexte local | etat technique + primitive de voisinage | Frida sait dire si elle montre un vrai voisinage ou juste le contexte deja present |
| [ ] | `continue apres ce passage` | partiel | FridaDev | Brancher une navigation sequentielle sur etat ancre en gardant la verite page-vs-passage | etat multi-tour + outil page borne | La continuation ne re-search pas au hasard |
| [x] | `page suivante / page precedente` | livre | FridaDev | Route page legere integree dans le contrat FridaDev via `page_read` borne | `document_id` explicite + page ancree | Frida change reellement de page avec document_id explicite |
| [x] | `page 28 a page 32` | livre | FridaDev | Lecture de plage de pages bornee livree via `page_read` compose | `document_id` explicite + garde `<= 5` pages | Frida sait lire une plage de pages sans deriver vers export total |
| [ ] | `deux pages apres 147c` | absent | mixte | Relier locator canonique et navigation page | intervalle/positionnement stable | Frida peut calculer un deplacement documentaire reel |
| [ ] | `147c a 151d` | faux-semblant | mixte | Arreter de traiter une plage brute comme si elle etait deja localisable | objet intervalle canonique natif | Frida n'annonce pas un range general comme supporte avant preuve |
| [ ] | Verification de provenance | partiel | mixte | Porter un statut explicite source primaire/commentaire/notice et une verification de provenance | metadata/source classes + runtime | Frida peut dire si le passage vient bien de l'oeuvre demandee |
| [ ] | Priorite texte primaire > commentaire > notice > introduction | absent | mixte | Ajouter un signal bibliographique exploitable au ranking et a la selection | metadata/source classes | Un commentaire ne gagne plus silencieusement contre le texte primaire |
| [ ] | Navigation multi-tour | partiel | FridaDev | Stabiliser l'etat Biblio et la reprise d'action documentaire | conversation state + primitives nav | `continue`, `plus haut`, `dans ce livre` restent ancres et honnetes |
| [ ] | Distinguer passage exact / candidat plausible / approximation contextuelle | faux-semblant | FridaDev | Rendre ce statut visible dans la logique produit, pas seulement dans l'observabilite | reprise du contrat runtime | Frida ne sur-vend plus une approximation comme extraction exacte |

## 4. Front FridaDev

### A. Verite produit et contrat d'execution

- [ ] Requalifier explicitement dans le runtime et la doc ce qui est exact, ce
      qui est plausible et ce qui est seulement contextuel.
- [ ] Sortir `catalog_search` du role de bequille universelle.
- [ ] Garder `locate -> context` comme chemin exact pour les locators simples.
- [ ] Refuser explicitement les ranges canoniques generaux non supportes au lieu
      de laisser croire qu'ils le sont.

### B. Resolution metier

- [ ] Refaire la resolution metier `oeuvre / auteur / corpus / volume / edition`
      sans tout laisser a la recherche texte.
- [ ] Corriger les formes encore fragiles du type `Theetete de Platon`.
- [ ] Stabiliser la distinction `document ouvert` vs `oeuvre interne resolue`.
- [ ] Introduire un statut produit de provenance et de confiance bibliographique.

### C. Contrat d'outils FridaDev

- [ ] Integrer proprement les routes Catalogue utiles deja existantes quand elles
      sont compatibles avec le contrat GET-only.
- [x] Ajouter une primitive de navigation page bornee si elle est retenue.
- [ ] Ajouter une primitive documentaire de voisinage ou de lecture sequentielle
      si la page seule ne suffit pas.
- [ ] Garder interdites les routes `latest/*`, les exports massifs et toute
      lecture lourde implicite.

### D. Runtime bibliothecaire

- [ ] Ne plus laisser l'agent ou le deterministe presenter une approximation
      search/context comme une resolution canonique forte.
- [ ] Reprendre la logique de selection pour favoriser le texte primaire avant
      commentaire, notice ou introduction.
- [ ] Brancher les primitives de navigation reelles sur l'etat multi-tour.
- [ ] Garder l'observabilite content-free tout en rendant visible le niveau
      exact/plausible/approxime.

## 5. Front Catalogue / DB / indexation

### A. Representation bibliographique

- [ ] Verifier si la DB peut porter un signal exploitable primaire/commentaire
      sans heuristique fragile.
- [ ] Verifier si les chapitres/TOC peuvent servir a resoudre des oeuvres
      internes de facon plus forte.
- [ ] Definir, si necessaire, une representation plus nette des oeuvres internes
      dans les gros volumes.

### B. Intervalle canonique

- [ ] Definir si l'intervalle canonique devient un objet natif d'indexation.
- [ ] Si non, definir un mapping stable et borne debut/fin -> sequence
      paragraphes/pages.
- [ ] Documenter le contrat exact de cette capacite avant toute promesse
      produit.

### C. Navigation documentaire

- [ ] Verifier quelles routes page/paragraphes existent deja et sont vraiment
      assez legeres pour le produit.
- [ ] Definir si un outil `page_read` borne suffit ou si une primitive plus
      documentaire est necessaire.
- [ ] Eviter toute derive vers export integral ou lecture non bornee.

### D. Indexation et recherche

- [ ] Qualifier plus explicitement ce que `search` sait trouver: chaine exacte,
      occurrences thematiques, bruit, rang.
- [ ] Verifier si la TOC peut etre searchable de facon utile.
- [ ] Documenter les limites de l'index actuel pour eviter les faux verts.

## 6. Dependances et ordre reel des chantiers

### Ordre recommande

- [ ] Etape 1 - Refixer la verite produit et les statuts exact/plausible/approxime.
- [ ] Etape 2 - Refaire le contrat d'outils FridaDev autour de vraies primitives
      documentaires.
- [ ] Etape 3 - Corriger la resolution metier cote FridaDev.
- [ ] Etape 4 - Ouvrir le chantier Catalogue / DB / indexation pour ce qui ne
      peut pas etre resout proprement cote app.
- [ ] Etape 5 - Refaire les validations produit avec des cas de bibliotheque
      generiques et non plus des seuls smokes favorables.

### Dependances dures

- [ ] Pas de navigation sequentielle fiable sans primitive documentaire adaptee.
- [ ] Pas de support honnete des ranges canoniques generaux sans objet ou mapping
      d'intervalle.
- [ ] Pas de garantie texte primaire > commentaire sans signal bibliographique
      exploitable.
- [ ] Pas de vraie resolution oeuvre/corpus/volume sans sortir du reflexe
      `catalog_search` comme solution par defaut.

## 7. Criteres de sortie

- [ ] Frida ne presente plus un candidat de recherche comme un passage exact.
- [ ] Frida sait dire quand elle lit un document, une oeuvre interne, un
      commentaire ou une notice.
- [ ] Frida sait lister, ouvrir, afficher une TOC, chercher et naviguer sans
      s'appuyer sur des approximations silencieuses.
- [ ] Les ranges canoniques annonces comme supportes sont reellement supportes
      de facon generale, pas seulement sur quelques cas bornes.
- [ ] Les validations produit prouvent des cas generiques de bibliotheque et pas
      seulement des smokes verts locaux.
- [ ] La separation FridaDev / Catalogue / DB est documentee et les dettes
      restantes sont explicites.

## 8. Risques / illusions a eviter

- [ ] Confondre lane injectee et capacite produit reelle.
- [ ] Confondre `catalog_search` avec une resolution bibliothecaire forte.
- [ ] Confondre un locator simple qui marche avec un support general des ranges.
- [ ] Confondre une TOC disponible avec une vraie resolution des oeuvres internes.
- [ ] Confondre un contexte local avec une navigation documentaire.
- [ ] Confondre une preuve content-free propre avec une verite produit suffisante.
- [ ] Relancer des micro-correctifs locaux sans d'abord traiter les primitives
      manquantes.
- [ ] Laisser croire qu'une capacite est `livree` quand elle n'est que
      `partielle` ou `faux-semblant`.

## 9. Regle de pilotage

- [ ] Aucun lot ne peut se declarer `termine` sur un simple smoke vert si la
      capacite produit reste partielle.
- [ ] Toute correction FridaDev doit dire explicitement si elle ferme un probleme
      applicatif ou si elle revele un manque Catalogue / DB / indexation.
- [ ] Toute validation future doit nommer ce qui est exact, ce qui est plausible
      et ce qui reste non supporte.

## 10. Mise a jour Lot R1 - navigation documentaire reelle

Lot R1 livre le premier front documentaire utile cote FridaDev, sans patch
Catalogue ni DB:

- `CatalogueClient.page(document_id, page_no)` appelle seulement
  `GET /doc/{id}/page/{page_no}`;
- l'outil `page_read` est maintenant allowliste, GET-only, borne, avec
  `document_id` explicite obligatoire;
- le runtime dialogue Biblio execute reellement:
  - `page suivante / page precedente`;
  - `page 28 a page 32` avec garde `<= 5` pages;
  - `continue apres ce passage` quand une page ancree existe deja;
  - `autour de ce passage` via `passage_context` borne.

Limites maintenues:

- aucun `latest/page` ni `latest/context`;
- aucune navigation inventee depuis un titre explicite non resolu;
- aucune promesse d'intervalle canonique general;
- `deux pages apres 147c` reste absent tant que le lien locator -> page/offset
  n'est pas prouve comme primitive produit generale.
