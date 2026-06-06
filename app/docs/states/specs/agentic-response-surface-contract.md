# Agentic Response Surface Contract

Statut: spec vivante
Date: 2026-06-06
Classement: `app/docs/states/specs/`
Portee: contrat minimal de restitution visible pour les agents specialises,
avec Biblio comme premier chantier.

Sources:

- `app/docs/todo-todo/product/frida-agentic-response-surface.md`
- `app/docs/states/audits/frida-agentic-response-surface-lot0-audit-2026-06-06.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/response-arbiter-power-contract.md`

## 1. Decision

Une reponse agentique integree est un message assistant Frida normal, assemble
depuis un resultat agentique structure.

L'agent specialise peut fournir une enveloppe vernaculaire courte. Le runtime
assemble et protege, sans styliser.

Regle courte:

- Frida reste la seule voix visible.
- Le bibliothecaire travaille en interne.
- Le bibliothecaire sait quoi dire parce qu'il sait ce qu'il vient de faire.
- Le deterministe assemble, verrouille et prouve.
- Les metas prouvent en `message.meta`, observabilite et JSONL content-free.

Ce contrat n'ajoute aucun nouveau LLM, aucun nouveau locuteur visible et aucun
canal parallele.

## 2. Champs du contrat

Le resultat agentique structure porte les champs de surface suivants:

- `surface_intro`: `string`;
- `surface_outro`: `string`.

Regles:

- les champs font partie du contrat;
- une chaine vide est autorisee seulement si le statut ou le type de resultat le
  justifie;
- `null` est invalide;
- l'absence justifiee d'enveloppe se represente par une chaine vide;
- la raison de cette chaine vide reste en meta / observabilite content-free;
- ne pas introduire un troisieme etat ambigu entre champ absent, `null` et
  chaine vide;
- `surface_intro` et `surface_outro` restent courts;
- ils ne contiennent pas de jargon outil;
- ils ne promettent pas ce que le resultat ne tient pas;
- ils ne recopient pas et ne paraphrasent pas le contenu exact mecanique;
- ils ne remplacent jamais les blocs verrouilles, la provenance ou les metas.

## 3. Enveloppe vide

Le contrat definit des attentes, pas des templates par statut.

Regle simple:

- `ready`: intro attendue sauf si la surface assemblee est deja naturellement
  autoportante;
- `ambiguous`: intro attendue pour situer l'ambiguite;
- `not_found`: intro attendue pour dire l'echec proprement;
- `needs_clarification`: intro attendue pour formuler la clarification;
- `blocked` / `error`: intro sobre attendue, sauf si le renderer existant
  produit deja une surface suffisante.

Si l'enveloppe est vide, le runtime ne fabrique pas une voix locale
standardisee. Il garde un comportement sobre, conserve la preuve en meta /
observabilite, et ne casse pas la reponse.

## 4. Role du deterministe

Le deterministe peut verifier:

- presence des champs;
- type `string`;
- taille maximale large;
- coherence structurelle entre statut, type de resultat, limites et
  continuation;
- presence des exacts verrouilles quand le statut et le type de resultat
  l'exigent;
- copie verbatim des blocs exacts verrouilles;
- timestamp normal du message final.

Le deterministe ne peut pas:

- corriger le style;
- remplacer l'intro ou l'outro;
- appliquer une regex de vocabulaire;
- appliquer un filtre stylistique local;
- tronquer pour produire une phrase uniforme;
- reformuler;
- choisir une phrase locale;
- moraliser, paraphraser ou standardiser la voix.

La qualite vernaculaire de l'enveloppe releve du contrat de l'agent, pas d'un
validateur regex de surface.

## 5. Assemblage cible

Ordre cible du message visible:

1. `surface_intro` si non vide;
2. provenance lisible si disponible;
3. surface existante ou blocs verrouilles;
4. limites ou continuation;
5. `surface_outro` si non vide.

Les exacts verrouilles sont copies verbatim.

Pour `comparaison / reprise` de passages deja lus, le message final reste une
reponse conversationnelle LLM fondee sur les passages deja presents dans le fil.
Ce chemin peut porter la meta Biblio de surface, avec `surface_intro` /
`surface_outro` observes en content-free, sans creer de final lock exact: il ne
produit pas un nouvel extrait mecanique. L'absence de final lock exact est alors
explicite en meta et ne doit pas etre vendue comme un extrait verrouille.

Si le JSON agentique porte une enveloppe de surface valide mais que le plan
d'outils est rejete, cette enveloppe peut etre conservee pour ce chemin
conversationnel. Le plan reste rejete: aucun outil n'est execute a partir de lui,
aucun extrait n'est vendu comme exact et aucune phrase locale ne remplace la voix
agentique.

Le message final assemble devient `assistant_message.content`. Il passe par le
chemin assistant normal: DB, timestamp, fenetre de contexte, labels temporels /
Delta-T, Memory, embeddings et resume selon les contrats existants.

En streaming, une reponse qui porte une enveloppe `surface_intro` /
`surface_outro` peut etre bufferisee jusqu'au `final_text` terminal. Ce
comportement est acceptable quand il evite d'envoyer un corps provisoire puis de
le remplacer par une reponse recomposee. La garantie prioritaire reste: un seul
message assistant final, assemble dans l'ordre du contrat, sans double reponse
et sans canal parallele.

## 6. Couverture Biblio par familles

Le mecanisme couvre BIB-01 -> BIB-33 sans restitution speciale par numero BIB.

Les preuves futures peuvent etre organisees par familles:

- inventaire / metadonnees;
- resolution / ambiguite;
- structure / sections;
- recherche scoped;
- extraction exacte;
- extraction segmentee / continuation;
- provenance / navigation;
- comparaison / reprise;
- echec propre.

Ces familles doivent prouver qu'aucune capacite BIB fermee n'est exclue du
mecanisme general.

## 7. Preuves attendues pour Lot 2 et Lot 3

Les lots runtime futurs doivent prouver au minimum:

- tests unitaires cibles;
- vraie conversation Frida;
- JSONL content-free;
- message assistant sauvegarde;
- timestamp present;
- reprise dans contexte / payload avec Delta-T;
- metas conservees;
- final lock conserve quand le resultat produit un bloc mecanique verrouille;
- absence de final lock exact explicite quand le resultat est conversationnel,
  par exemple `comparaison / reprise`;
- exacts non reecrits;
- absence de double reponse;
- absence de canal parallele;
- absence de nouveau LLM;
- absence de validateur regex ou de filtre de style.

Un patch runtime de ce chantier exige toujours une preuve live, meme si la
surface visible semble inchangee.

## 8. Hors contrat

Ce contrat ne lance pas Agenda. Il impose seulement de ne pas enfermer Biblio
dans une solution impossible a reutiliser plus tard.

Ce contrat ne rouvre pas BIB-01 -> BIB-33 et ne modifie pas le produit Biblio
ferme live.
