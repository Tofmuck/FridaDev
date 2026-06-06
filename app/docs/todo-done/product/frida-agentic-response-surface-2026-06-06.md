# Frida - Reponses agentiques integrees

Date: 2026-06-06
Statut: ARCHIVE - chantier clos; Lots 0-3 livres, prouves et documentes
Classement: `app/docs/todo-done/product/`

## Archive

Cette roadmap ne pilote plus le travail actif. Elle est archivee parce que le
mecanisme de restitution agentique Biblio est livre, verifie et corrige apres
les derniers findings Lot 3.

Source de verite runtime encore vivante:

- `app/docs/states/specs/agentic-response-surface-contract.md`

Ne pas rouvrir cette roadmap sans decision explicite. Les cases restantes non
cochees, notamment le Lot X no-op, sont historiques et non applicables apres la
fermeture effective des Lots 0-3.

Commits principaux:

- `e1423ea` - implementation de l'enveloppe agentique Biblio.
- `b24fed4` - durcissement du contrat parseur `surface_intro` /
  `surface_outro`.
- `48ae9ff` - fermeture de la preuve `comparaison / reprise`.
- `8158209` - correction de la reinjection meta read-passages dans le dialogue
  Biblio recent et documentation streaming bufferise.

Etat final:

- Frida reste l'unique voix visible.
- Le bibliothecaire reste interne.
- Le runtime assemble les enveloppes et surfaces verrouillees sans styliser.
- Les metas Biblio restent exploitables en content-free.
- Les artefacts JSONL Lot 2 / Lot 3 sont conserves ci-dessous.
- La spec contractuelle reste vivante; cette archive conserve l'execution.

Sources:

- `app/docs/states/specs/agentic-response-surface-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/todo-done/product/frida-biblio-last-chance-archive-2026-06-06.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/response-arbiter-power-contract.md`

## Decision courte

Le chantier Biblio fonctionnel est ferme live: BIB-01 -> BIB-33 sont prouves
par artefacts JSONL content-free. Cette TODO ne rouvre pas Biblio. Elle cadre un
mecanisme simple de restitution agentique visible.

Le bibliothecaire fait son travail. Il produit son resultat structure habituel.
Il renseigne le contrat `surface_intro` / `surface_outro`; leur contenu peut
rester vide seulement si le statut ou le type de resultat le justifie. Le
runtime assemble:

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
- `surface_intro` et `surface_outro` font partie du contrat de restitution
  agentique.
- Leur contenu peut etre vide seulement si le type de resultat ou le statut le
  justifie.
- La chaine vide ne doit pas redevenir la norme silencieuse.
- Le runtime assemble, conserve et verrouille.
- Les exacts verrouilles sont copies verbatim.
- Les metas restent en observabilite et dans `message.meta`, pas en surface
  brute.
- Le message final est une reponse assistant normale: DB, contexte recent,
  Memory, embeddings et resume suivent les contrats existants.
- Le message final agentique est timestampé comme toute reponse assistant Frida
  normale et passe par le meme chemin temporel: sauvegarde conversationnelle,
  fenetre de contexte, labels temporels / Delta-T, Memory, embeddings et resume
  selon les contrats existants.
- La couverture Biblio reste generique par familles de resultats.
- Ne pas concevoir une solution Biblio impossible a reutiliser plus tard pour
  Agenda.

## Interdits

- Pas de patch runtime hors lot explicitement runtime et preuve live.
- Pas de modification Biblio.
- Pas de modification Memory.
- Pas de modification DB.
- Pas de modification doc-pipeline ou plateforme.
- Pas de reouverture de BIB-01 -> BIB-33.
- Pas de restitution speciale par BIB.
- Pas de branche locale specialisee par numero BIB.
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
- il renseigne l'intro et la relance, ou justifie leur chaine vide dans les
  metas;
- le deterministe garde les exacts, ancres, limites, final lock et metas;
- le runtime assemble le message visible;
- le message assemble est sauve comme assistant Frida normal;
- aucune reponse agentique visible ne doit exister hors de ce chemin timestampé.

Garde-fous structurels autorises:

- champ present;
- type `string` pour `surface_intro` et `surface_outro`;
- `null` invalide;
- taille raisonnable;
- chaine vide acceptee seulement si le statut ou le type de resultat le
  justifie, avec raison conservee en meta / observabilite content-free;
- coherence entre statut, exact verrouille, limites et continuation.

Le code ne corrige pas le style. Il ne standardise pas la voix. Il ne fabrique
pas une phrase locale pour remplacer l'enveloppe.

Si l'enveloppe est vide, le comportement reste sobre, explicite cote
meta/observabilite, et ne doit pas casser la reponse.

En streaming, une reponse avec enveloppe peut etre bufferisee jusqu'au
`final_text` terminal afin de ne pas envoyer un corps provisoire puis une version
recomposee avec intro/outro. Ce choix reste compatible avec le contrat si le
message final sauvegarde est unique, timestampé, repris dans le contexte normal,
et qu'il n'existe ni double reponse ni canal parallele.

Tout patch runtime de ce chantier exige une preuve live en vraie conversation
Frida, meme si la surface semble inchangee. La raison est simple: ce chantier
touche le chemin assistant normal, le contexte, Memory, les metas ou
l'assemblage de reponse. L'artefact JSONL reste content-free.

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

- Audit produit: `app/docs/states/audits/frida-agentic-response-surface-lot0-audit-2026-06-06.md`.

- [x] Localiser l'assemblage de la reponse visible.
- [x] Localiser les metas Biblio.
- [x] Verifier le message assistant en DB.
- [x] Verifier le contexte recent.
- [x] Verifier que le message assistant timestampé entre dans le contexte
  envoye au LLM avec le traitement temporel normal.
- [x] Verifier Memory si le chemin est deja branche.
- [x] Verifier embeddings si le chemin est deja branche.
- [x] Verifier resume si le chemin est deja branche.
- [x] Produire un diagnostic content-free.
- [x] Ne modifier aucun runtime.

### Lot 1 - Contrat court

Objectif: fixer le contrat generique.

- Spec normative: `app/docs/states/specs/agentic-response-surface-contract.md`.

- [x] Definir `surface_intro` comme champ du contrat, vide seulement si le
  statut ou le type de resultat le justifie.
- [x] Definir `surface_outro` comme champ du contrat, vide seulement si le
  statut ou le type de resultat le justifie.
- [x] Definir le comportement si l'enveloppe est vide.
- [x] Confirmer que les exacts verrouilles ne sont pas reecrits.
- [x] Confirmer l'absence de nouveau LLM.
- [x] Confirmer l'absence de validateur regex ou de filtre de style.
- [x] Confirmer l'absence de branche par BIB.
- [x] Confirmer les familles Biblio couvertes.

### Lot 2 - Implementation generique Biblio

Objectif: brancher le mecanisme simple.

- Preuve live:
  `app/docs/states/baselines/biblio-smokes/agentic-response-surface-lot2-real-conversation-20260606T165059Z.jsonl`.

- [x] Faire porter `surface_intro` et `surface_outro` par le resultat agentique
  Biblio.
- [x] Assembler intro, surface existante, limites et relance.
- [x] Conserver final lock.
- [x] Conserver metas, provenance et observabilite.
- [x] Conserver le message assistant normal.
- [x] Conserver le timestamp et le chemin temporel normal: DB, contexte,
  labels temporels / Delta-T, Memory, embeddings et resume selon contrats.
- [x] Ajouter ou ajuster les tests unitaires cibles.
- [x] Produire une preuve live en vraie conversation Frida pour tout patch
  runtime de ce chantier.

### Lot 3 - Preuve live par familles

Objectif: verifier la couverture sans refaire trente-trois micro-tests.

- Statut: ferme live. Les neuf familles sont prouvees par artefacts
  JSONL content-free, y compris `comparaison / reprise` via le chemin
  conversationnel `read_passages` avec meta Biblio, `surface_intro` /
  `surface_outro`, timestamp, Delta-T et absence de final lock exact abusif.
- Preuve live principale:
  `app/docs/states/baselines/biblio-smokes/agentic-response-surface-lot3-family-live-20260606T191014Z.jsonl`.
- Correction / diagnostic:
  `app/docs/states/baselines/biblio-smokes/agentic-response-surface-lot3-correction-20260606T191907Z.jsonl`.
- Preuve live de fermeture `comparaison / reprise`:
  `app/docs/states/baselines/biblio-smokes/agentic-response-surface-lot3-comparison-reprise-live-20260606T195023Z.jsonl`.

- [x] Couvrir inventaire / metadonnees.
- [x] Couvrir resolution / ambiguite.
- [x] Couvrir structure / sections.
- [x] Couvrir recherche scoped.
- [x] Couvrir extraction exacte.
- [x] Couvrir extraction segmentee / continuation.
- [x] Couvrir provenance / navigation.
- [x] Couvrir comparaison / reprise.
- [x] Couvrir echec propre.
- [x] Prouver que les familles couvrent BIB-01 -> BIB-33.
- [x] Verifier que la reponse agentique finale possede un timestamp.
- [x] Verifier que cette reponse est reprise ensuite dans le contexte envoye au
  LLM avec le traitement temporel normal.
- [x] Verifier que le timestamp n'est pas seulement une meta ou une ligne DB
  isolee.
- [x] Produire un JSONL live content-free.

### Lot X - Arret no-op historique

Statut: non applique. Le mecanisme a ete livre et prouve par les Lots 0-3; ce
point d'arret reste une trace de gouvernance, pas une action ouverte.

- Evaluer si le mecanisme ajoute trop de complexite.
- Arreter sans patch runtime si le risque depasse le benefice.
- Conserver le systeme actuel.
- Archiver cette TODO avec decision explicite.

## Validation attendue

- Une seule voix visible: Frida.
- Aucun nouveau LLM.
- Aucun nouveau locuteur visible.
- Aucun validateur regex de surface.
- Aucune restitution speciale par BIB.
- Exacts verrouilles copies verbatim.
- Metas conservees hors surface brute.
- Message final assistant normal.
- Timestamp, contexte / payload, labels temporels / Delta-T, Memory, embeddings
  et resume suivent le chemin conversationnel normal.
- BIB-01 -> BIB-33 couverts par familles.
- Preuve live en vraie conversation Frida pour tout patch runtime de ce
  chantier.
- JSONL live content-free.

## Point d'arret

Si ce mecanisme alourdit Frida, fragilise les exacts, cree une double reponse ou
demande trop de plomberie pour peu de benefice, on s'arrete. Le systeme actuel
reste acceptable.
