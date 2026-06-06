# Frida - Reponses agentiques integrees

Date: 2026-06-06
Statut: TODO produit decidee, docs-only pour le present lot
Classement: `app/docs/todo-todo/product/`

Sources:

- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/todo-done/product/frida-biblio-last-chance-archive-2026-06-06.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/response-arbiter-power-contract.md`

## Decision courte

Le chantier Biblio fonctionnel est ferme live: BIB-01 -> BIB-33 sont prouves
par artefacts JSONL content-free. Le prochain chantier produit n'est pas de
rouvrir Biblio, ni d'ajouter une regle locale par capacite, mais de cadrer un
systeme generique de restitution agentique integree.

Formule source:

> Frida parle. Le bibliothécaire travaille. Le déterministe verrouille. Les metas prouvent.

La voix visible est Frida seule. Les agents specialises travaillent en coulisses
et ne deviennent jamais des locuteurs visibles separes. Le bibliothecaire est
une capacite interne de Frida: il recoit la demande, le contexte utile, choisit
sa methode, execute ou pilote les outils, puis produit un resultat structure.

Formule a graver:

> Le bibliothécaire sait quoi dire parce qu'il sait ce qu'il vient de faire. La restitution visible est donc produite depuis son résultat structuré, puis assemblée comme message assistant Frida normal.

Decision technique:

- Par defaut, l'agent specialise propose `surface_intro` et `surface_outro` dans
  son resultat structure.
- Le runtime assemble le message assistant final avec les blocs verrouilles.
- Frida reste l'unique voix visible.
- Le message final est persiste comme `assistant_message.content` normal.
- Le message final circule dans le contexte recent, Memory, les embeddings et
  les resumes comme tout autre message assistant.
- Les metas restent en complement observable, jamais en remplacement du contenu
  conversationnel.

Le systeme de restitution doit etre generique pour Biblio. Il doit couvrir
BIB-01 -> BIB-33 avec le meme mecanisme general. Les tests peuvent etre groupes
par familles de resultats, mais aucune capacite BIB fermee ne doit etre exclue.

## Decisions actees

- Frida est l'unique voix visible.
- L'agent specialise ne parle pas a cote de Frida.
- L'agent specialise produit une enveloppe vernaculaire courte dans son resultat
  structure.
- Le code assemble la surface finale.
- Le deterministe assemble et protege; il ne stylise pas, ne paraphrase pas, ne
  moralise pas et ne remplace pas la voix.
- La qualite vernaculaire de l'enveloppe releve du contrat de l'agent, pas d'un
  validateur regex de surface.
- Le code ne cree pas une restitution speciale par BIB.
- Le contrat agentique doit permettre a l'agent de produire l'enveloppe en
  fonction de la demande utilisateur, du contexte recu, du travail realise, du
  statut du resultat, du type de resultat et des limites eventuelles.
- Les blocs exacts verrouilles sont copies verbatim.
- Les limites, incertitudes et continuations sont portees par le paquet de
  restitution et restituees honnetement.
- Le modele doit rester reusable pour Agenda et les autres agents specialises.

## Interdits

- Pas de patch runtime dans ce lot documentaire.
- Pas de modification Biblio.
- Pas de modification Memory.
- Pas de modification DB.
- Pas de modification doc-pipeline ou plateforme.
- Pas de nouvelle route.
- Pas de reouverture de BIB-01 -> BIB-33.
- Pas de nouveau LLM pour ecrire l'enveloppe.
- Pas de LLM principal libre qui reprend tout le contexte pour improviser.
- Pas de nouveau locuteur visible.
- Pas de canal parallele qui remplace le message assistant final.
- Pas de double reponse visible.
- Pas de branche locale du type `if BIB-17 then phrase speciale`.
- Pas de restitution speciale par BIB.
- Pas de regex utilisateur.
- Pas de validateur regex de surface.
- Pas de filtre stylistique local.
- Pas de liste locale de vocabulaire interdit pour corriger la voix.
- Pas de remplacement automatique de `surface_intro` ou `surface_outro`.
- Pas de reformulation deterministe.
- Pas de sanitizer qui transforme le texte.
- Pas de normalisation stylistique.
- Pas de reecriture d'extrait exact par LLM.
- Pas de faux exact: un snippet, un contexte local ou une recherche ne devient
  jamais un extrait exact.
- Pas de faux `primary_text`.
- Pas de jargon outil dans la surface visible normale.
- Pas de fuite de plomberie: ids techniques, reason codes, render modes,
  statuts machine, budgets, compteurs et noms d'outils restent en metas,
  observabilite et JSONL.

## Contrat cible

### Chaine de responsabilite

1. L'utilisateur parle a Frida.
2. Frida route vers un agent specialise quand le besoin produit le justifie.
3. L'agent specialise recoit la demande et le contexte conversationnel utile.
4. L'agent specialise choisit une methode et des outils autorises.
5. L'agent specialise produit un resultat structure.
6. Le deterministe verrouille ce qui doit l'etre: exact, ancres, provenance,
   limites, statuts et metas.
7. Le runtime assemble `surface_intro`, provenance lisible, blocs verrouilles,
   limites et `surface_outro`.
8. Le message assemble devient une reponse assistant Frida normale.
9. Le message entre dans la DB, le contexte recent, Memory, les embeddings et
   les resumes selon les contrats existants.

### Paquet de restitution generique

Le paquet de restitution doit etre valable pour toutes les familles Biblio et
preparer la reutilisation Agenda. Il porte au moins:

- `agent_kind`: agent specialise source, par exemple `biblio` ou `agenda`;
- `user_intent`: intention utilisateur resumee;
- `result_status`: `ready`, `ambiguous`, `not_found`, `needs_clarification`,
  `blocked` ou `error`;
- `result_kind`: `inventory`, `metadata`, `candidates`, `structure`,
  `scoped_search`, `exact_excerpt`, `segmented_excerpt`, `canonical_range`,
  `navigation`, `provenance`, `comparison_context`, `resume_previous`,
  `clean_failure` ou famille equivalente;
- `surface_intro`: enveloppe courte produite par l'agent specialise;
- `surface_outro`: relance ou limite courte produite par l'agent specialise;
- `human_context`: resume humain court du resultat;
- `readable_provenance`: provenance lisible et non technique;
- `limits`: limites utiles, partialite, continuation, budget, ambiguite;
- `locked_blocks`: blocs exacts verrouilles a copier verbatim;
- `allowed_moves`: actions discursives autorisees;
- `forbidden_moves`: actions interdites;
- `technical_meta`: metas content-free pour observabilite et JSONL.

Exemple indicatif:

```json
{
  "agent_kind": "biblio",
  "user_intent": "lire le debut d'une section resolue",
  "result_status": "ready",
  "result_kind": "exact_excerpt",
  "surface_intro": "J'ai retrouve le debut de la section. Je te le donne ici.",
  "surface_outro": "Je peux continuer la lecture si tu veux.",
  "human_context": "section resolue, lecture partielle disponible",
  "readable_provenance": {
    "work": "ouvrage resolu",
    "section": "section resolue",
    "page_range": "pages 12-13"
  },
  "limits": {
    "partial": true,
    "continuation_available": true
  },
  "locked_blocks": [
    {
      "type": "exact_excerpt",
      "text": "...",
      "hash": "..."
    }
  ],
  "allowed_moves": [
    "introduce",
    "mention provenance briefly",
    "mention partiality",
    "offer continuation"
  ],
  "forbidden_moves": [
    "rewrite exact excerpt",
    "invent missing provenance",
    "mention internal tools",
    "claim complete if partial"
  ],
  "technical_meta": {
    "content_free": true
  }
}
```

Les JSONL de preuve ne doivent jamais inclure le texte brut des blocs exacts:
ils portent hashes, tailles, statuts, ancres et reason codes content-free.

### Garde-fous structurels autorises

Le code peut seulement verifier:

- champ present ou absent;
- type attendu, notamment `string` pour `surface_intro` et `surface_outro`;
- taille raisonnable pour eviter un champ enorme;
- champ vide si l'agent ne propose pas d'enveloppe;
- presence des blocs verrouilles quand le statut annonce un exact;
- coherence structurelle entre statut, type de resultat, limites et blocs.

Le code ne corrige pas le style, ne remplace pas la voix et ne fabrique pas une
formulation uniforme. Si l'enveloppe est absente ou structurellement inutilisable,
le comportement futur doit rester sobre, documente et sans nouveau LLM.

### Assemblage cible

Le flow cible n'est pas:

```text
assistant_message = rendered_biblio_answer
```

Il est:

```text
assistant_message = compose_frida_answer(
  user_message,
  recent_dialogue,
  restitution_packet,
  locked_exact_blocks,
  provenance,
  limits
)
```

Le runtime:

- prend le paquet de restitution;
- verifie les garde-fous structurels autorises;
- assemble `surface_intro`, provenance lisible, blocs verrouilles, limites et
  `surface_outro`;
- copie les blocs exacts verbatim;
- verifie la non-modification des blocs si le lot runtime l'exige;
- persiste le contenu final comme message assistant normal;
- conserve les metas techniques dans `message.meta` et l'observabilite.

## Couverture BIB-01 -> BIB-33

BIB-01 -> BIB-33 doivent passer par le meme mecanisme general de restitution.
Les tests peuvent etre organises par familles produit, mais la couverture doit
prouver qu'aucune capacite BIB fermee n'est exclue.

Familles de resultats a couvrir:

- inventaire et compteur;
- metadonnees connues ou inconnues;
- resolution documentaire;
- ambiguite documentaire;
- oeuvre interne;
- role documentaire;
- structure, table des matieres, chapitres et sections;
- recherche scoped;
- extraction exacte courte;
- section complete ou segmentee;
- plage canonique courte;
- plage canonique longue segmentee;
- provenance et ancre courante;
- navigation lecteur, dont chapitre suivant;
- comparaison de passages deja lus;
- reprise d'un extrait lu plus tot;
- echec propre: introuvable, ambigu, structure manquante, extraction bloquee,
  role non prouve.

Regles de couverture:

- aucune famille ne doit introduire une phrase codee par numero BIB;
- les familles peuvent utiliser les methodes produit existantes;
- les tests doivent prouver que les capacites fermees restent atteignables;
- les preuves live doivent rester content-free;
- la checklist BIB archivee reste fermee, sans reouverture dans cette TODO.

## Lots d'execution

### Lot 0 - Contrat generique decide

- [ ] Relire les specs chat, Biblio, Memory et response arbiter pertinentes.
- [ ] Confirmer que cette TODO ne rouvre pas Biblio Last Chance.
- [ ] Promouvoir les decisions de ce document en contrat de travail actif.
- [ ] Stabiliser le vocabulaire: agent specialise, paquet de restitution,
  enveloppe vernaculaire, bloc verrouille, metas, message assistant normal.
- [ ] Stabiliser le schema cible du paquet de restitution.
- [ ] Stabiliser les garde-fous structurels autorises.
- [ ] Stabiliser les interdits de surface et de style.
- [ ] Relier le contrat aux familles BIB-01 -> BIB-33.
- [ ] Definir les conditions de no-op si le risque depasse le benefice.

### Lot 1 - Audit du chemin actuel

- [ ] Cartographier ou vont deja les reponses Biblio visibles.
- [ ] Cartographier les metas Biblio conservees.
- [ ] Verifier la persistence DB des messages assistant Biblio.
- [ ] Verifier l'entree dans le contexte recent.
- [ ] Verifier l'observation Memory actuelle.
- [ ] Verifier le chemin embeddings quand il existe.
- [ ] Verifier le chemin resume / compression quand il existe.
- [ ] Identifier les surfaces encore trop techniques.
- [ ] Identifier les points ou le contenu agentique reste en canal parallele.
- [ ] Produire un artefact content-free du chemin actuel.
- [ ] Ne modifier aucun runtime dans ce lot.

### Lot 2 - Design du paquet et de l'assemblage

- [ ] Definir le schema interne du paquet de restitution.
- [ ] Definir les champs `surface_intro` et `surface_outro`.
- [ ] Definir comment l'agent specialise produit l'enveloppe depuis son travail.
- [ ] Definir les familles de `result_kind`.
- [ ] Definir les statuts `result_status`.
- [ ] Definir le transport des blocs verrouilles.
- [ ] Definir l'assemblage deterministe.
- [ ] Definir la preservation des metas sans affichage brutal.
- [ ] Definir le comportement sobre si l'enveloppe est absente.
- [ ] Definir les preuves content-free.
- [ ] Definir les tests unitaires cibles.
- [ ] Definir les preuves live attendues.
- [ ] Valider que le design ne cree aucune branche par numero BIB.

### Lot 3 - Implementation generique Biblio

- [ ] Ajouter le paquet de restitution generique au chemin Biblio si necessaire.
- [ ] Faire produire `surface_intro` et `surface_outro` par le bibliothecaire
  dans son resultat structure.
- [ ] Assembler le message final comme reponse assistant Frida normale.
- [ ] Copier les blocs exacts verbatim.
- [ ] Conserver final lock.
- [ ] Conserver metas, provenance et observabilite.
- [ ] Conserver contexte recent et Memory.
- [ ] Garantir absence de nouveau LLM.
- [ ] Garantir absence de locuteur visible separe.
- [ ] Garantir absence de validateur regex de surface.
- [ ] Garantir absence de restitution speciale par BIB.
- [ ] Lancer les tests Biblio/chat cibles.
- [ ] Produire une preuve live content-free si la surface utilisateur change.

### Lot 4 - Couverture BIB par familles produit

- [ ] Couvrir inventaire et metadonnees.
- [ ] Couvrir resolution et ambiguite documentaire.
- [ ] Couvrir oeuvre interne et role documentaire.
- [ ] Couvrir structure, chapitres et sections.
- [ ] Couvrir recherche scoped.
- [ ] Couvrir extraction exacte.
- [ ] Couvrir section complete ou segmentee.
- [ ] Couvrir plage canonique courte.
- [ ] Couvrir plage canonique longue segmentee.
- [ ] Couvrir provenance et ancre courante.
- [ ] Couvrir navigation lecteur.
- [ ] Couvrir chapitre suivant.
- [ ] Couvrir comparaison de passages deja lus.
- [ ] Couvrir reprise d'un extrait lu plus tot.
- [ ] Couvrir echecs propres.
- [ ] Prouver que BIB-01 -> BIB-33 restent couverts par familles.
- [ ] Documenter tout cran non applicable avec reason code content-free.

### Lot 5 - Transparence conversationnelle

- [ ] Verifier que le message final est persiste en DB.
- [ ] Verifier que le message final entre dans le contexte recent.
- [ ] Verifier Memory quand le pipeline le permet.
- [ ] Verifier embeddings quand le pipeline le permet.
- [ ] Verifier resume / compression quand le pipeline le permet.
- [ ] Verifier qu'une reprise ulterieure utilise le contenu conversationnel.
- [ ] Verifier que les metas restent disponibles.
- [ ] Verifier que les metas ne remplacent pas le contenu visible.
- [ ] Verifier absence de canal parallele.
- [ ] Verifier absence de double reponse.

### Lot 6 - Generalisation Agenda et autres agents

- [ ] Identifier les resultats Agenda analogues aux resultats Biblio.
- [ ] Distinguer verite metier Agenda et restitution vernaculaire.
- [ ] Definir les garde-fous Agenda: temps, fuseaux, conflits, permissions,
  mutations et lecture seule.
- [ ] Verifier que `agent_result -> assistant_message` reste valable.
- [ ] Identifier ce qui doit differer entre Biblio et Agenda.
- [ ] Refuser toute generalisation qui force Agenda dans un moule Biblio.
- [ ] Produire une proposition Agenda docs-only.
- [ ] Obtenir validation humaine avant patch Agenda.

### Lot 7 - Validation live finale

- [ ] Rejouer un panel Biblio representatif couvrant BIB-01 -> BIB-33 par
  familles.
- [ ] Verifier vraie conversation Frida.
- [ ] Verifier agent specialise appele.
- [ ] Verifier message assistant sauvegarde.
- [ ] Verifier surface visible naturelle.
- [ ] Verifier aucun jargon outil.
- [ ] Verifier aucun faux exact.
- [ ] Verifier aucun extrait exact reecrit.
- [ ] Verifier aucun faux `primary_text`.
- [ ] Verifier metas conservees.
- [ ] Verifier contexte recent.
- [ ] Verifier Memory / embeddings / resume selon contrat.
- [ ] Produire JSONL live content-free.
- [ ] Documenter les limites restantes.

### Lot X - Arret no-op

- [ ] Evaluer si le modele complique trop Frida.
- [ ] Evaluer si la voix Frida devient moins naturelle.
- [ ] Evaluer si le risque de double reponse est trop eleve.
- [ ] Evaluer si la separation metas / surface devient trop fragile.
- [ ] Arreter sans patch runtime si le risque depasse le benefice.
- [ ] Documenter que le systeme actuel est conserve.
- [ ] Archiver cette TODO si elle ne pilote plus de travail actif.

## Criteres de validation

- La reponse visible est un message assistant Frida normal.
- La voix visible est Frida seule.
- L'agent specialise n'est pas un locuteur separe.
- Le resultat specialise n'apparait pas comme un canal parallele.
- Le paquet de restitution est generique pour Biblio.
- BIB-01 -> BIB-33 restent couverts par familles produit.
- Aucune phrase locale n'est codee par numero BIB.
- `surface_intro` et `surface_outro` viennent du resultat structure de l'agent.
- La qualite vernaculaire releve du contrat agentique.
- Le deterministe assemble et protege sans styliser.
- Aucun validateur regex de surface n'est utilise.
- Aucun filtre de vocabulaire local n'est utilise.
- Aucun sanitizer ne transforme la voix.
- Aucun nouveau LLM n'ecrit l'enveloppe.
- Les blocs exacts verrouilles sont copies verbatim.
- Les limites et incertitudes restent honnetes.
- Les metas restent conservees.
- Les metas ne remplacent pas le contenu conversationnel.
- Le message est sauvegarde en base.
- Le message entre dans le contexte recent.
- Le message reste disponible pour Memory, embeddings et resume selon les
  contrats existants.
- Le modele reste reusable pour Agenda.

## Tests et preuves attendus

Pour les lots docs-only:

- `git status --short --branch`;
- `git diff --check`;
- coherence des references documentaires;
- aucune modification runtime.

Pour tout lot runtime futur:

- tests unitaires Biblio/chat cibles;
- tests Memory si le chemin conversationnel est touche;
- preuve DB/message assistant;
- preuve contexte recent;
- preuve Memory / embeddings / resume ou reason code indiquant le cran non
  applicable;
- preuve du paquet de restitution structure en content-free;
- preuve que `surface_intro` et `surface_outro` viennent du resultat structure;
- preuve que les garde-fous appliques a l'enveloppe sont seulement structurels;
- preuve qu'aucun nouvel appel LLM n'a produit l'enveloppe;
- preuve d'assemblage deterministe des blocs exacts;
- preuve de couverture BIB-01 -> BIB-33 par familles produit;
- vraie conversation Frida;
- artefact JSONL content-free;
- verification surface visible propre;
- verification final lock si exact rendu;
- verification absence de double reponse.

## Risques

- Rupture de voix: Frida peut sembler deleguer au lieu de parler.
- Double reponse: une sortie agent et une sortie Frida peuvent coexister.
- Canal parallele: le resultat agentique peut rester en meta sans devenir
  contenu conversationnel.
- Faux exact: l'enveloppe peut reformuler un extrait qui devait rester
  verrouille si le contrat agentique ne l'interdit pas.
- Police de style locale: un validateur regex, un filtre stylistique ou un
  sanitizer peut standardiser la voix, aplatir les reponses et remplacer peu a
  peu le contrat agentique par une police deterministe.
- Jargon outil: le message peut redevenir un rapport de pipeline.
- Perte de metas: rendre la surface naturelle peut faire disparaitre les
  signaux necessaires a l'observabilite.
- Sur-generalisation: Agenda peut heriter d'un modele Biblio trop specifique.
- Complexite excessive: le modele peut alourdir Frida plus qu'il ne l'aide.

## Point d'arret

Si le modele de reponse agentique integree complique trop Frida, degrade sa voix,
fragilise les extraits exacts ou cree un canal parallele difficile a verifier,
on garde le systeme actuel. Un no-op explicite vaut mieux qu'un raffinement qui
rend Frida moins claire.
