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

Decision de voix visible:

> Frida parle. Le bibliothécaire travaille. Le déterministe verrouille. Les metas prouvent.

La voix visible est Frida seule. Les agents specialises ne deviennent pas des
locuteurs visibles separes. Le bibliothecaire n'apparait pas comme personnage
dans le dialogue utilisateur: il est une capacite interne de Frida.

Formulation generale:

> Frida est l'unique voix visible. Les agents spécialisés travaillent en
> coulisses ; ils ne deviennent pas des locuteurs séparés.

Pour Biblio:

> Le bibliothécaire ne parle pas à côté de Frida : il fournit à Frida le
> résultat de bibliothèque que Frida restitue naturellement.

Decision technique de restitution:

> L'enveloppe vernaculaire est proposee par l'agent specialise dans son resultat
> structure, sous forme de champs bornes comme `surface_intro` et
> `surface_outro`. Elle n'est pas un message visible autonome. Le code applique
> seulement des garde-fous structurels minimaux, assemble les blocs exacts
> verrouilles verbatim, puis persiste le tout comme une reponse assistant Frida
> normale.

La decision produit est donc fixee: par defaut, le modele cible est le **modele B avec garde deterministe**. L'agent specialise qui a fait le travail produit
une enveloppe vernaculaire courte et bornee dans son JSON. Le code reste
responsable de l'assemblage final, des blocs exacts, des limites et des metas.

Ce n'est pas un nouveau locuteur, ce n'est pas "le bibliothecaire dit", ce n'est
pas un nouveau LLM, et ce n'est pas le LLM principal libre qui reprend tout le
contexte pour improviser. Le role produit est fixe; le schema exact, la
generation agentique, les garde-fous structurels minimaux et le comportement en
cas d'enveloppe absente pourront etre definis dans les lots de design.

Formules a graver:

> La qualité vernaculaire de l'enveloppe relève du contrat de l'agent, pas d'un validateur regex de surface.

> Le déterministe assemble et protège ; il ne stylise pas, ne paraphrase pas, ne moralise pas et ne remplace pas la voix.

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
- Pas de validateur regex de surface.
- Pas de filtre stylistique local.
- Pas de liste locale de vocabulaire interdit pour corriger la voix apres coup.
- Pas de remplacement automatique de `surface_intro` ou `surface_outro`.
- Pas de reformulation deterministe.
- Pas de sanitizer qui transforme le texte.
- Pas de normalisation stylistique.
- Pas de reecriture d'extrait exact par LLM.
- Pas de faux exact: un snippet, un contexte local ou une recherche ne devient
  jamais un extrait exact.
- Pas de faux `primary_text`.
- Frida ne refait pas le travail de bibliotheque.
- Frida ne choisit pas la verite documentaire.
- Frida ne reecrit pas les extraits exacts.
- Frida enonce le resultat dans le dialogue.
- Le bibliothecaire choisit et prepare le resultat.
- Le deterministe verrouille les extraits, ancres, limites et metas.
- Le deterministe assemble et protege; il ne stylise pas, ne paraphrase pas, ne
  moralise pas et ne remplace pas la voix.
- Les metas ne remplacent jamais le contenu conversationnel.
- Le message final est un message assistant normal.
- Aucun canal parallele bibliothecaire ne doit exister.
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

La restitution vernaculaire est une enveloppe courte proposee par l'agent
specialise dans son resultat structure. Elle transforme le resultat specialise
en message assistant Frida lisible, sans devenir un locuteur separe:

- introduction naturelle;
- contexte bref;
- limite honnete;
- relance eventuelle;
- provenance utile quand elle aide l'utilisateur;
- aucun jargon outil;
- aucune plomberie technique;
- aucune reecriture des blocs exacts verrouilles.

L'agent specialise peut proposer cette enveloppe parce qu'il a deja recu la
requete, le contexte utile et les resultats de ses outils. Mais il la propose
comme champ structure, pas comme parole visible autonome. La qualite
vernaculaire releve du contrat de l'agent, pas d'un validateur regex de surface
applique apres coup.

Le code ne corrige pas le style de cette enveloppe. Il ne la paraphrase pas, ne
la moralise pas, ne la standardise pas et ne la remplace pas par une voix locale.
Il peut seulement appliquer des garde-fous structurels minimaux: champ present
ou absent, type attendu `string`, taille raisonnable pour eviter un champ enorme,
et champ vide si l'agent ne propose rien.

Pour Biblio, la composition cible est:

1. `surface_intro` courte;
2. provenance courte si utile;
3. bloc exact verrouille si un extrait mecanique est rendu;
4. limite ou continuation si le resultat est partiel;
5. `surface_outro` courte si clarification ou suite utile.

Comparaison A / B:

- Modele A, phase de restitution Frida separee: voix Frida homogene, mais appel
  LLM supplementaire ou retour au LLM principal, donc cout plus eleve et risque
  de refaire le sens documentaire.
- Modele B, enveloppe produite par l'agent specialise: plus simple, moins cher,
  plus proche du contexte reel de recherche, sans nouveau locuteur si le champ
  reste structure et si le code assemble le message final.
- Decision: B est meilleur par defaut, a condition de borner le contrat
  agentique et de limiter le deterministe a des garde-fous structurels minimaux,
  sans validateur regex de surface, sans filtre stylistique et sans fallback
  uniforme qui ecrase la voix.

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

### Paquet de restitution structure

Frida sait quoi dire parce qu'elle ne recoit pas seulement un extrait brut. Elle
recoit un paquet de restitution structure qui dit ce qui est vrai, ce qui est
verrouille, ce qui peut etre formule et ce qui est interdit.

Ce paquet doit contenir au minimum:

- intention utilisateur;
- statut du resultat: `ready`, `ambiguous`, `not_found`,
  `needs_clarification`, `blocked`, `error`;
- type de resultat: `exact_excerpt`, `candidates`, `provenance`,
  `continuation`, `clarification` ou equivalent;
- `surface_intro` courte proposee par l'agent specialise;
- `surface_outro` courte si utile;
- provenance lisible;
- limites a mentionner;
- blocs exacts verrouilles;
- actions discursives autorisees;
- actions discursives interdites;
- metas techniques content-free.

Exemple indicatif, non contractuel pour le schema runtime:

```json
{
  "user_intent": "lire le debut de cette section",
  "result_status": "ready",
  "result_kind": "exact_excerpt",
  "surface_intro": "J'ai retrouve le debut de la section. Je te donne les premieres pages.",
  "surface_outro": "Je peux continuer si tu veux.",
  "provenance": {
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
    "claim section complete if partial"
  ],
  "technical_meta": {
    "content_free": true
  }
}
```

Les JSONL de preuve ne doivent jamais inclure le texte brut des blocs exacts:
ils portent hashes, tailles, statuts, ancres et reason codes content-free.

`surface_intro` et `surface_outro` sont des contenus conversationnels candidats:
ils peuvent etre visibles dans le message final, mais ils ne sont pas corriges
par un validateur de style. Les JSONL de preuve doivent les resumer par
presence, longueurs, hashes et reason codes, pas par texte brut si le lot exige
un artefact content-free strict.

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

Le plus sur:

- l'agent specialise propose `surface_intro` et `surface_outro` dans le paquet
  structure;
- le code verifie seulement les garde-fous structurels minimaux: presence ou
  absence, type `string`, taille raisonnable, champ vide accepte;
- si l'enveloppe est absente ou structurellement inutilisable, le comportement
  doit etre defini sobrement sans fabriquer une voix generique qui remplace
  tout;
- le code n'utilise ni regex de style, ni liste de vocabulaire interdit, ni
  remplacement automatique, ni reformulation deterministe;
- le code assemble deterministiquement les blocs exacts verrouilles;
- les blocs exacts sont copies verbatim;
- un hash ou un garde-fou verifie qu'ils n'ont pas ete modifies si necessaire;
- le message final assemble devient `assistant_message.content`;
- ce message est persiste comme message assistant normal;
- il entre dans le contexte recent, Memory, embeddings et resume comme
  n'importe quelle reponse assistant.

## Questions ouvertes

- Decision proposee: Frida parle. Reste a valider humainement que cette voix
  unique ne rend pas invisible une limite utile de l'agent specialise.
- Decision proposee: `surface_intro` / `surface_outro` sont produits par l'agent
  specialise dans son JSON, puis assembles par le code. Reste ouvert: schema
  exact, limites de taille, champs optionnels et comportement si l'enveloppe est
  absente ou structurellement inutilisable.
- Decision proposee: pas de validateur regex de surface, pas de filtre
  stylistique, pas de sanitizer et pas de remplacement automatique de la voix.
- Quel contexte minimal donner a l'agent specialise pour produire une enveloppe
  courte sans lui donner un pouvoir de locuteur autonome?
- Comment empecher toute reecriture des extraits exacts?
- Comment composer proprement introduction + bloc exact verrouille?
- Comment s'assurer que l'agent specialise ne paraphrase jamais un bloc exact
  dans `surface_intro` ou `surface_outro`?
- Comment preserver les metas sans les afficher brutalement?
- Comment garantir que le message final entre dans toute la chaine
  conversationnelle: DB, contexte recent, Memory, embeddings, resume?
- Quels signaux prouvent qu'une reponse d'agent n'a pas ete stockee dans un
  canal parallele?
- Comment reutiliser le meme modele pour Agenda?
- Quels tests prouvent la persistance, Memory, embeddings, resume et contexte?
- Quels risques de rupture de voix Frida?
- Quels risques de double reponse ou de reponse parallele?
- Comment generaliser a Agenda sans copier Biblio ni masquer les differences de
  temps, conflit et mutation?
- Quelle limite poser si la restitution agentique rend Frida moins naturelle?

## Lots

### Lot 0 - Cadrage du contrat

- [ ] Relire les specs Biblio, chat, Memory et response arbiter pertinentes.
- [ ] Decrire le contrat general `agent_result -> assistant_message`.
- [ ] Acter la decision de voix visible: Frida parle, les agents travaillent en
  coulisses.
- [ ] Acter la decision de restitution: enveloppe courte produite par l'agent
  specialise dans son JSON, puis validee et assemblee par le code.
- [ ] Acter l'interdit: pas de nouveau LLM, pas de LLM principal libre, pas de
  mini-agent visible, pas de bibliothecaire locuteur.
- [ ] Acter l'interdit: pas de validateur regex de surface, pas de filtre
  stylistique, pas de sanitizer, pas de remplacement automatique de la voix.
- [ ] Stabiliser le vocabulaire: resultat mecanique, restitution vernaculaire,
  bloc verrouille, metas, message assistant normal.
- [ ] Stabiliser le vocabulaire du paquet de restitution structure, notamment
  `surface_intro`, `surface_outro` et `locked_blocks`.
- [ ] Definir les interdits: reecriture d'exact, canal parallele, double
  reponse, fuite de plomberie.
- [ ] Definir le modele d'assemblage deterministe des blocs exacts.
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
- [ ] Proposer le format interne du paquet de restitution structure.
- [ ] Definir le contrat `surface_intro` / `surface_outro` produit par l'agent
  specialise.
- [ ] Definir les garde-fous structurels minimaux de cette enveloppe: presence,
  type `string`, taille raisonnable, champ vide accepte.
- [ ] Definir le comportement sans nouveau LLM si l'enveloppe est absente ou
  structurellement inutilisable, sans fallback uniforme qui ecrase la voix.
- [ ] Interdire explicitement regex de style, filtre stylistique, sanitizer,
  liste locale de vocabulaire interdit et reformulation deterministe.
- [ ] Definir comment un extrait exact verrouille est transporte.
- [ ] Definir comment le code assemble les blocs exacts verbatim.
- [ ] Definir comment verifier hash ou garde-fou de non-reecriture.
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
- [ ] Faire produire `surface_intro` / `surface_outro` par le bibliothecaire
  dans son resultat structure.
- [ ] Verifier seulement la structure minimale de cette enveloppe avant
  affichage.
- [ ] Prouver qu'aucun validateur regex de surface ne transforme l'enveloppe.
- [ ] Garantir que le LLM ne reecrit pas l'extrait exact.
- [ ] Garantir que le code copie les blocs exacts verbatim.
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
- La voix visible est Frida seule.
- L'agent specialise n'est pas un locuteur separe.
- Le resultat specialise n'apparait pas comme un canal parallele.
- Frida recoit un paquet de restitution structure.
- `surface_intro` et `surface_outro` sont produits par l'agent specialise comme
  champs du resultat structure, pas comme message visible autonome.
- La qualite vernaculaire de l'enveloppe releve du contrat de l'agent, pas d'un
  validateur regex de surface.
- Le deterministe assemble et protege; il ne stylise pas, ne paraphrase pas, ne
  moralise pas et ne remplace pas la voix.
- Les seuls garde-fous structurels autorises sur `surface_intro` /
  `surface_outro` sont: presence ou absence, type `string`, taille raisonnable,
  champ vide accepte.
- Aucun filtre stylistique, sanitizer, liste locale de vocabulaire interdit ou
  transformation deterministe de l'enveloppe n'est utilise.
- Aucun nouveau LLM n'est appele pour l'enveloppe vernaculaire.
- Le LLM principal libre ne reprend pas tout le contexte pour improviser
  l'enveloppe.
- L'agent specialise n'est ni un mini-agent visible ni un locuteur separe.
- Le message est sauvegarde en base.
- Le message entre dans le contexte recent.
- Le message est disponible pour Memory, embeddings et resume selon les
  contrats runtime existants.
- Les metas restent conservees.
- Les metas ne remplacent pas le contenu conversationnel.
- La surface visible ne raconte pas les outils.
- La surface visible ne fuit pas la plomberie.
- Le code assemble les blocs exacts verrouilles.
- Les extraits exacts mecaniques ne sont jamais reecrits par LLM.
- Les hashes ou garde-fous prouvent la non-modification si le lot runtime le
  requiert.
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
- preuve du paquet de restitution structure en content-free;
- preuve que `surface_intro` / `surface_outro` viennent du resultat structure et
  ne sont pas transformes par un validateur regex de surface;
- preuve que les garde-fous appliques a l'enveloppe sont seulement structurels;
- preuve qu'aucun nouvel appel LLM n'a produit l'enveloppe;
- preuve d'assemblage deterministe des blocs exacts;
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
- Faux exact: `surface_intro` ou `surface_outro` peuvent reformuler un extrait
  qui devait rester verrouille si le contrat agentique ne l'interdit pas.
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
