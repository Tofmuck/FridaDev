# Frida - Reponses agentiques integrees

Date: 2026-06-06
Statut: TODO produit de cadrage, proposition docs-only
Classement: `app/docs/todo-todo/product/`

Sources:

- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/todo-done/product/frida-biblio-last-chance-archive-2026-06-06.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/response-arbiter-power-contract.md`

## Decision courte

Le chantier Biblio fonctionnel est ferme live: BIB-01 -> BIB-33 sont prouves
par artefacts JSONL content-free. Le prochain besoin produit n'est pas de
rouvrir Biblio, mais de cadrer comment une reponse d'agent specialise devient
une reponse assistant Frida normale.

Une reponse d'agent specialise visible doit entrer dans le dialogue, dans la
base conversationnelle, dans le contexte recent, dans Memory, dans les
embeddings et dans les resumes comme tout autre message assistant. Les metas
restent un complement observable, jamais un substitut au contenu
conversationnel.

Formule a graver:

> Le bibliothécaire ne raconte pas ses outils ; il restitue leur résultat dans le dialogue.

Invariant conversationnel a graver:

> Une réponse bibliothécaire visible est une réponse assistant Frida à part entière. Elle circule dans le contexte, la mémoire, les embeddings et les résumés comme tout autre message assistant.

Ce document ne lance aucun patch runtime. Il cadre un modele cible general pour
Biblio maintenant, Agenda plus tard, puis les autres agents specialises.

## Invariants non negociables

- Pas de patch runtime dans ce lot de cadrage.
- Pas de modification Biblio.
- Pas de modification Memory.
- Pas de modification DB.
- Pas de modification doc-pipeline ou plateforme.
- Pas de nouvelle route.
- Pas de decision produit cachee dans le code.
- Pas de suppression d'artefacts Biblio.
- Pas de reouverture de BIB-01 -> BIB-33.
- Pas de reponse d'agent hors conversation.
- Pas de canal parallele qui remplace le message assistant final.
- Pas de double reponse visible.
- Pas de jargon outil dans la surface visible normale.
- Pas de fuite de plomberie: ids techniques, reason codes, render modes,
  statuts machine, budgets, compteurs et noms d'outils restent en metas,
  observabilite et JSONL.
- Pas de reecriture d'extrait exact par LLM.
- Pas de faux exact: un snippet, un contexte local ou une recherche ne devient
  jamais un extrait exact.
- Pas de faux `primary_text`.
- Les metas ne remplacent jamais le contenu conversationnel.
- Le modele cible doit rester reutilisable pour Agenda et pour d'autres agents
  specialises, sans creer un cas special Biblio impossible a generaliser.

## Modele cible

### Verite metier / mecanique

La verite metier est produite ou verrouillee par l'agent specialise et les
garde-fous deterministes. Elle peut contenir:

- resultat structure;
- extrait exact mecanique;
- ancre;
- provenance;
- statut;
- limites;
- budget;
- final lock eventuel;
- metas d'observabilite content-free.

Pour Biblio:

- le bibliothecaire choisit les outils;
- le deterministe produit ou verrouille le resultat mecanique: extrait exact,
  ancre, provenance, statut et limites;
- le final lock protege ce qui est exact;
- les details techniques restent dans `message.meta`, l'observabilite et les
  JSONL.

Pour Agenda futur:

- l'agent agenda choisit les outils de calendrier autorises;
- le deterministe verifie horaires, conflits, fuseaux, droits, mutation
  autorisee ou lecture seule selon le contrat futur;
- la surface visible restitue le resultat utile sans raconter les appels
  internes.

### Restitution vernaculaire

La restitution vernaculaire transforme le resultat specialise en message
assistant Frida lisible:

- introduction naturelle;
- contexte bref;
- limite honnete;
- relance eventuelle;
- provenance utile quand elle aide l'utilisateur;
- aucun jargon outil;
- aucune plomberie technique;
- aucune reecriture des blocs exacts verrouilles.

Pour Biblio, la composition cible est:

1. phrase d'introduction naturelle;
2. provenance courte si utile;
3. bloc exact verrouille si un extrait mecanique est rendu;
4. limite ou continuation si le resultat est partiel;
5. relance naturelle si clarification ou suite utile.

### Transparence conversationnelle

Le message visible final doit etre un message assistant normal:

- persiste en base comme assistant;
- accessible dans le contexte recent;
- eligible Memory selon les regles existantes;
- indexable par embeddings si le pipeline le fait deja pour les messages
  assistant;
- resumable / compressible comme le reste du dialogue;
- reutilisable plus tard par Frida, notamment pour "reprends ce passage" ou
  "compare avec ce que tu as dit avant";
- accompagne de metas, mais non remplace par elles.

Le contenu conversationnel est la surface assistant. Les metas portent le
contrat technique, les preuves et les garde-fous.

## Questions ouvertes

- Qui parle dans la surface visible: Frida, le bibliothecaire, ou "Frida via le
  bibliothecaire"?
- Quel contexte minimal donner au mini-agent de restitution?
- Faut-il un mini-agent de restitution separe, ou le bibliothecaire doit-il
  produire directement l'introduction vernaculaire?
- Comment empecher toute reecriture des extraits exacts?
- Comment composer proprement introduction + bloc exact verrouille?
- Comment representer un bloc exact dans le prompt de restitution sans
  autoriser le modele a le modifier?
- Comment preserver les metas sans les afficher brutalement?
- Comment garantir que le message final entre dans toute la chaine
  conversationnelle: DB, contexte recent, Memory, embeddings, resume?
- Quels signaux prouvent qu'une reponse d'agent n'a pas ete stockee dans un
  canal parallele?
- Comment reutiliser le meme modele pour Agenda?
- Quels tests prouvent la persistance, Memory, embeddings, resume et contexte?
- Quels risques de rupture de voix Frida?
- Quels risques de double reponse ou de reponse parallele?
- Quelle limite poser si la restitution agentique rend Frida moins naturelle?

## Lots

### Lot 0 - Cadrage du contrat

- [ ] Relire les specs Biblio, chat, Memory et response arbiter pertinentes.
- [ ] Decrire le contrat general `agent_result -> assistant_message`.
- [ ] Stabiliser le vocabulaire: resultat mecanique, restitution vernaculaire,
  bloc verrouille, metas, message assistant normal.
- [ ] Decider si la voix visible est Frida seule, Frida via agent, ou agent
  specialise explicitement nomme.
- [ ] Definir les interdits: reecriture d'exact, canal parallele, double
  reponse, fuite de plomberie.
- [ ] Identifier les consequences attendues pour Biblio.
- [ ] Identifier les consequences attendues pour Agenda futur.
- [ ] Produire une note de decision ou promouvoir ce document en spec si le
  modele est valide humainement.

### Lot 1 - Preuve du chemin actuel

- [ ] Cartographier ou vont deja les reponses Biblio visibles.
- [ ] Verifier la persistence DB des messages assistant Biblio.
- [ ] Verifier l'entree dans le contexte recent.
- [ ] Verifier l'observation Memory actuelle.
- [ ] Verifier ce qui part ou ne part pas aux embeddings.
- [ ] Verifier ce qui part ou ne part pas au resume / compression.
- [ ] Identifier les metas Biblio deja conservees.
- [ ] Identifier les surfaces qui restent purement techniques.
- [ ] Produire un artefact content-free du chemin actuel.
- [ ] Ne modifier aucun runtime dans ce lot.

### Lot 2 - Design de composition

- [ ] Proposer le format interne `introduction_vernaculaire + result_lock`.
- [ ] Definir comment un extrait exact verrouille est transporte.
- [ ] Definir comment un segment partiel est annonce.
- [ ] Definir comment une clarification est formulee sans plomberie.
- [ ] Definir comment une erreur propre est formulee sans faux refus.
- [ ] Definir comment les metas restent consultables sans etre affichees.
- [ ] Definir les hooks de preuve content-free.
- [ ] Definir les tests unitaires minimaux.
- [ ] Definir les tests live minimaux.
- [ ] Obtenir validation humaine avant prototype.

### Lot 3 - Prototype Biblio minimal

- [ ] Choisir un seul flux Biblio pilote a faible risque.
- [ ] Prouver l'etat avant patch par vraie conversation Frida.
- [ ] Ajouter le plus petit mecanisme de composition si necessaire.
- [ ] Garantir que le LLM ne reecrit pas l'extrait exact.
- [ ] Garantir que la surface visible reste une reponse assistant normale.
- [ ] Conserver les metas Biblio existantes.
- [ ] Conserver final lock.
- [ ] Conserver Memory et contexte recent.
- [ ] Lancer tests Biblio/chat cibles.
- [ ] Produire JSONL live content-free.
- [ ] Ne pas generaliser avant preuve.

### Lot 4 - Preuve contexte / DB / Memory / embeddings / resume

- [ ] Creer une conversation live avec reponse Biblio agentique integree.
- [ ] Verifier message assistant sauvegarde.
- [ ] Verifier presence dans le contexte recent.
- [ ] Verifier Memory observee quand le pipeline le permet.
- [ ] Verifier embeddings ou documenter pourquoi le chemin ne les produit pas.
- [ ] Verifier resume / compression ou documenter pourquoi le chemin ne passe
  pas encore par ce cran.
- [ ] Verifier qu'une reprise ulterieure utilise le contenu conversationnel, pas
  seulement les metas.
- [ ] Verifier que les metas restent conservees.
- [ ] Verifier que le JSONL reste content-free.
- [ ] Documenter les limites restantes.

### Lot 5 - Generalisation agent specialise pour Agenda

- [ ] Identifier les resultats Agenda futurs analogues aux resultats Biblio.
- [ ] Distinguer verite metier Agenda et restitution vernaculaire.
- [ ] Definir les garde-fous specifiques Agenda: temps, fuseaux, conflits,
  permissions et mutations.
- [ ] Verifier que le contrat `agent_result -> assistant_message` reste valable.
- [ ] Identifier ce qui doit etre different entre Biblio et Agenda.
- [ ] Refuser toute generalisation qui force Agenda dans un moule Biblio.
- [ ] Produire une proposition Agenda docs-only.
- [ ] Obtenir validation humaine avant patch Agenda.

### Lot 6 - Validation live

- [ ] Rejouer un panel Biblio representatif.
- [ ] Couvrir extrait exact court.
- [ ] Couvrir extrait segmente ou continuation.
- [ ] Couvrir ambiguite / clarification.
- [ ] Couvrir erreur propre.
- [ ] Couvrir passage deja lu.
- [ ] Verifier vraie conversation Frida.
- [ ] Verifier agent specialise appele.
- [ ] Verifier message assistant sauvegarde.
- [ ] Verifier surface visible naturelle.
- [ ] Verifier aucun jargon outil.
- [ ] Verifier aucun faux exact.
- [ ] Verifier aucun extrait exact reecrit.
- [ ] Verifier metas conservees.
- [ ] Verifier Memory / contexte / resume selon le contrat du lot.
- [ ] Produire JSONL live content-free.
- [ ] Documenter les limites restantes.

### Lot X - Abandon / no-op

- [ ] Evaluer si le modele complique trop Frida.
- [ ] Evaluer si la voix Frida devient moins naturelle.
- [ ] Evaluer si le risque de double reponse est trop eleve.
- [ ] Evaluer si la separation metas / surface devient trop fragile.
- [ ] Si le risque depasse le benefice, arreter sans patch runtime.
- [ ] Documenter que le systeme actuel est conserve.
- [ ] Archiver cette TODO si elle ne pilote plus de travail actif.

## Criteres de validation

- La reponse visible est un message assistant Frida normal.
- Le resultat specialise n'apparait pas comme un canal parallele.
- Le message est sauvegarde en base.
- Le message entre dans le contexte recent.
- Le message est disponible pour Memory, embeddings et resume selon les
  contrats runtime existants.
- Les metas restent conservees.
- Les metas ne remplacent pas le contenu conversationnel.
- La surface visible ne raconte pas les outils.
- La surface visible ne fuit pas la plomberie.
- Les extraits exacts mecaniques ne sont jamais reecrits par LLM.
- Les limites et incertitudes restent honnetes.
- Le modele est reutilisable pour Agenda sans decision cachee.

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
- Faux exact: une introduction LLM peut reformuler un extrait qui devait rester
  verrouille.
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
