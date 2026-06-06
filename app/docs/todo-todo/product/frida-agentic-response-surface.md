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
par artefacts JSONL content-free. Cette TODO ne rouvre pas Biblio. Elle cadre un
mecanisme simple de restitution agentique visible.

Le bibliothecaire fait son travail. Il produit son resultat structure habituel.
Il ajoute eventuellement `surface_intro` et `surface_outro`. Le runtime assemble:

1. intro;
2. provenance lisible;
3. blocs verrouilles;
4. limites ou relance.

Le tout devient un message assistant Frida normal.

Formules a garder:

> Frida parle. Le bibliothécaire travaille. Le déterministe verrouille. Les metas prouvent.

> Le bibliothécaire sait quoi dire parce qu'il sait ce qu'il vient de faire. La restitution visible est donc produite depuis son résultat structuré, puis assemblée comme message assistant Frida normal.

## Decisions actees

- Frida est l'unique voix visible.
- Le bibliothecaire est interne et ne devient pas un personnage visible.
- Aucun nouveau LLM n'ecrit l'enveloppe.
- Aucun nouveau locuteur visible n'est cree.
- Le resultat agentique Biblio peut porter `surface_intro` et `surface_outro`.
- `surface_intro` et `surface_outro` sont optionnels.
- Le runtime assemble, conserve et verrouille.
- Les exacts verrouilles sont copies verbatim.
- Les metas restent en observabilite et dans `message.meta`, pas en surface
  brute.
- Le message final est une reponse assistant normale: DB, contexte recent,
  Memory, embeddings et resume suivent les contrats existants.
- La couverture Biblio reste generique par familles de resultats.
- Ne pas concevoir une solution Biblio impossible a reutiliser plus tard pour
  Agenda.

## Interdits

- Pas de patch runtime dans ce lot documentaire.
- Pas de modification Biblio.
- Pas de modification Memory.
- Pas de modification DB.
- Pas de modification doc-pipeline ou plateforme.
- Pas de reouverture de BIB-01 -> BIB-33.
- Pas de restitution speciale par BIB.
- Pas de branche locale du type `if BIB-17 then phrase speciale`.
- Pas de validateur regex de surface.
- Pas de filtre stylistique local.
- Pas de liste locale de vocabulaire interdit.
- Pas de sanitizer qui transforme la voix.
- Pas de reformulation deterministe.
- Pas de remplacement automatique de `surface_intro` ou `surface_outro`.
- Pas de reecriture d'extrait exact par LLM.
- Pas de faux exact.
- Pas de faux `primary_text`.
- Pas de jargon outil dans la surface visible normale.
- Pas de fuite de plomberie visible: ids techniques, reason codes, render modes,
  statuts machine, budgets, compteurs et noms d'outils restent en metas,
  observabilite et JSONL.

## Mecanisme cible

Le paquet Biblio existant reste la source du resultat documentaire. Le changement
vise seulement la surface visible:

- l'agent Biblio recoit la demande utilisateur et le contexte utile;
- il choisit ses outils et produit son resultat structure;
- il ajoute, si utile, une intro et une relance courtes;
- le deterministe garde les exacts, ancres, limites, final lock et metas;
- le runtime assemble le message visible;
- le message assemble est sauve comme assistant Frida normal.

Garde-fous structurels autorises:

- champ present ou absent;
- type `string` pour `surface_intro` et `surface_outro`;
- taille raisonnable;
- champ vide accepte;
- coherence entre statut, exact verrouille, limites et continuation.

Le code ne corrige pas le style. Il ne standardise pas la voix. Il ne fabrique
pas une phrase locale pour remplacer l'enveloppe.

## Couverture BIB par familles

BIB-01 -> BIB-33 doivent rester couverts par ce meme mecanisme general. Les
preuves peuvent etre organisees par familles, sans refaire trente-trois chemins
locaux.

Familles a couvrir:

- inventaire / metadonnees;
- resolution / ambiguite;
- structure / sections;
- recherche scoped;
- extraction exacte;
- extraction segmentee / continuation;
- provenance / navigation;
- comparaison / reprise;
- echec propre.

Critere: ces familles prouvent que BIB-01 -> BIB-33 restent couverts sans
traitement BIB par BIB.

## Lots

### Lot 0 - Audit du chemin actuel

Objectif: comprendre ou se fabrique aujourd'hui la reponse Biblio visible.

- [ ] Localiser l'assemblage de la reponse visible.
- [ ] Localiser les metas Biblio.
- [ ] Verifier le message assistant en DB.
- [ ] Verifier le contexte recent.
- [ ] Verifier Memory si le chemin est deja branche.
- [ ] Verifier embeddings si le chemin est deja branche.
- [ ] Verifier resume si le chemin est deja branche.
- [ ] Produire un diagnostic content-free.
- [ ] Ne modifier aucun runtime.

### Lot 1 - Contrat court

Objectif: fixer le contrat generique.

- [ ] Definir `surface_intro` optionnel.
- [ ] Definir `surface_outro` optionnel.
- [ ] Definir le comportement si l'enveloppe est absente.
- [ ] Confirmer que les exacts verrouilles ne sont pas reecrits.
- [ ] Confirmer l'absence de nouveau LLM.
- [ ] Confirmer l'absence de validateur regex ou de filtre de style.
- [ ] Confirmer l'absence de branche par BIB.
- [ ] Confirmer les familles Biblio couvertes.

### Lot 2 - Implementation generique Biblio

Objectif: brancher le mecanisme simple.

- [ ] Faire porter `surface_intro` et `surface_outro` par le resultat agentique
  Biblio.
- [ ] Assembler intro, surface existante, limites et relance.
- [ ] Conserver final lock.
- [ ] Conserver metas, provenance et observabilite.
- [ ] Conserver le message assistant normal.
- [ ] Ajouter ou ajuster les tests unitaires cibles.
- [ ] Produire une preuve live si la surface visible change.

### Lot 3 - Preuve live par familles

Objectif: verifier la couverture sans refaire trente-trois micro-tests.

- [ ] Couvrir inventaire / metadonnees.
- [ ] Couvrir resolution / ambiguite.
- [ ] Couvrir structure / sections.
- [ ] Couvrir recherche scoped.
- [ ] Couvrir extraction exacte.
- [ ] Couvrir extraction segmentee / continuation.
- [ ] Couvrir provenance / navigation.
- [ ] Couvrir comparaison / reprise.
- [ ] Couvrir echec propre.
- [ ] Prouver que les familles couvrent BIB-01 -> BIB-33.
- [ ] Produire un JSONL live content-free.

### Lot X - Arret no-op

- [ ] Evaluer si le mecanisme ajoute trop de complexite.
- [ ] Arreter sans patch runtime si le risque depasse le benefice.
- [ ] Conserver le systeme actuel.
- [ ] Archiver cette TODO avec decision explicite.

## Validation attendue

- Une seule voix visible: Frida.
- Aucun nouveau LLM.
- Aucun nouveau locuteur visible.
- Aucun validateur regex de surface.
- Aucune restitution speciale par BIB.
- Exacts verrouilles copies verbatim.
- Metas conservees hors surface brute.
- Message final assistant normal.
- BIB-01 -> BIB-33 couverts par familles.
- JSONL live content-free pour tout changement visible.

## Point d'arret

Si ce mecanisme alourdit Frida, fragilise les exacts, cree une double reponse ou
demande trop de plomberie pour peu de benefice, on s'arrete. Le systeme actuel
reste acceptable.
