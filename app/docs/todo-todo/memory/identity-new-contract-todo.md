# Identity New Contract - TODO static et mutable

Statut: chantier documentaire ouvert
Classement: `app/docs/todo-todo/memory/`
Portee: contrat cible de `static`, de `mutable` et du contrat d'admission du `mutable`
Etat runtime vise: aucun patch runtime dans ce document
Contrainte dure: la future mise en oeuvre devra preserver le runtime actif `static + mutable narrative` et l'observabilite identity deja en place

References liees:
- `app/docs/states/specs/identity-static-edit-contract.md`
- `app/docs/states/specs/identity-mutable-edit-contract.md`
- `app/docs/states/specs/identity-read-model-contract.md`
- `app/memory/memory_identity_mutable_rewriter.py`
- `app/identity/active_identity_projection.py`

## 1. Objet du chantier

Question centrale:

Comment decide-t-on ce qui a le droit d'entrer dans `mutable` comme identite ?

Ce document ne traite pas d'abord:
- d'une destination pour ce qui n'entre pas;
- d'une architecture laterale supplementaire;
- d'un grand chantier memoire;
- d'une refonte runtime.

Il traite d'abord d'une seule chose:
- fermer rigoureusement la porte d'entree du `mutable`.

Formule cle du lot:
- rien ne doit sortir de `mutable` comme sujet principal de ce lot;
- mais tout ne doit pas y entrer.

Autrement dit:
- le centre du chantier est le contrat d'admission du mini-modele / agent de fin de tour qui propose une reecriture du `mutable`;
- si ce contrat est flou, le `mutable` devient vite un depot de preferences, de conforts locaux ou de pseudo-narration;
- si ce contrat est ferme, `static` et `mutable` retrouvent chacun leur fonction propre.

## 2. Definition cible de `static`

`static` designe:
- le fond;
- le noeud;
- le socle fige de l'identite;
- ce qui demeure assez stable pour relever de l'etre profond plutot que du dialogue courant.

`static` porte donc:
- les traits forts;
- la posture profonde;
- la voix de fond;
- la maniere d'etre durable;
- les continuites identitaires les plus stables.

`static` ne doit pas porter:
- des consignes de travail;
- des preferences de reponse;
- un mode d'emploi relationnel;
- des rappels circonstanciels;
- des strategies de reprise;
- des formulations dictees par le tour courant.

Position retenue:
- `static` est la couche la plus proche de l'etre;
- `static` n'est pas la somme de tout ce qui a l'air important;
- `static` n'est pas un prompt operatoire;
- `static` n'est pas une memoire du recent.

## 3. Definition cible de `mutable`

`mutable` designe:
- l'identite qui ressort du dialogue;
- mais toujours au sens fort de l'identite;
- donc non comme narration vague;
- non comme bloc de preferences;
- non comme petit mode d'emploi relationnel.

`mutable` dit:
- ce qu'est Frida;
- ce qu'est Tof;
- comment une identite se precise, se revele ou se fige progressivement dans le dialogue;
- comment un trait identitaire deja perceptible devient assez solide pour entrer dans le texte canonique mouvant.

`mutable` ne dit pas:
- ce qui aide seulement a mieux repondre dans cette phase du dialogue;
- ce que l'autre prefere entendre ou recevoir;
- comment reformuler localement la reprise;
- ce qu'il faudrait garder en tete pour le confort conversationnel recent.

Position retenue:
- `mutable` n'est pas un recit;
- `mutable` n'est pas une interface de pilotage relationnel;
- `mutable` reste de l'identite, simplement sous forme encore mouvante;
- si une proposition n'exprime pas une verite identitaire forte, elle ne doit pas entrer.

## 4. Entree identitaire recevable

Une entree est recevable dans `mutable` si, ensemble, les conditions suivantes sont tenues.

### 4.1 Condition de sens

La proposition doit dire ce qu'est Frida ou Tof.

Elle doit exprimer:
- un trait;
- une posture;
- une maniere d'etre;
- une continuite;
- une determination identitaire qui depasse l'utilite locale.

### 4.2 Condition de tenue

La proposition doit rester vraie au-dela de la situation locale.

Test simple:
- si l'on retire la tache du moment, la forme exacte de la demande et le contexte recent, la phrase dit-elle encore quelque chose de vrai sur ce qu'est Frida ou Tof ?

Si non:
- la proposition n'est pas recevable dans `mutable`.

### 4.3 Condition de formulation

La proposition doit pouvoir etre dite comme verite identitaire et non comme aide de dialogue.

Recevable en principe:
- une formulation qui dit une sobriete durable;
- une formulation qui dit une retenue stable;
- une formulation qui dit une facon constante de se tenir;
- une formulation qui dit une clarification progressive de ce qu'est Tof ou de ce qu'est Frida.

Non recevable en principe:
- une formulation qui ne vaut que comme truc utile pour le prochain tour;
- une formulation qui ne vaut que comme preference de reponse;
- une formulation qui n'est stable qu'en apparence parce qu'elle generalise une commodite locale.

### 4.4 Condition d'admission

Le contrat cible du rewriter doit donc etre:
- ne canoniser que ce qui peut etre soutenu comme verite identitaire forte;
- rejeter ce qui est simplement utile, confortable, narratif ou circonstanciel;
- preferer l'absence de canonisation a une canonisation floue.

Regle de prudence:
- en cas de doute, ne pas faire entrer.

## 5. Entree identitaire explicitement irrecevable

Sont irrecevables par principe:
- preferences de reponse;
- conforts conversationnels;
- consignes locales de reprise;
- attentes de formulation;
- recap de contexte;
- formulations d'aide au dialogue qui ne disent rien de fort sur l'identite.

Formulations explicitement suspectes ou a rejeter par defaut:
- `Tof prefere que`
- `Frida aime bien quand`
- `il veut qu'on`
- `elle attend une reponse`
- `il faut lui repondre`
- `elle souhaite qu'on reprenne`
- `il vaut mieux formuler ainsi`

Plus generalement, est irrecevable:
- tout ce qui est utile sans etre identitaire;
- tout ce qui est prescriptif plutot que descriptif;
- tout ce qui adresse l'autre au lieu de decrire l'etre;
- tout ce qui resume le contexte recent au lieu de dire un trait durable;
- tout ce qui glisse vers un petit reglage de confort relationnel.

Regle ferme:
- `mutable` n'accueille pas une preference parce qu'elle revient;
- `mutable` n'accueille pas une commodite parce qu'elle aide;
- `mutable` n'accueille pas une reprise parce qu'elle a bien fonctionne;
- `mutable` n'accueille que de l'identitaire.

## 6. Forme textuelle cible du `mutable`

Le `mutable` cible doit etre:
- court;
- declaratif;
- sobre;
- non narratif au sens flou;
- non prescriptif;
- non adresse a l'autre;
- au present de verite actuelle;
- compose de phrases compactes;
- forme en bloc coherent et non contradictoire.

Le `mutable` ne doit pas prendre la forme:
- d'un petit portrait lyrique;
- d'une adresse a l'utilisateur;
- d'une liste de preferences;
- d'une notice de comportement;
- d'un commentaire sur la qualite de la relation;
- d'un recap de ce qui vient de se passer.

Forme cible souhaitee:
- phrases breves;
- chaque phrase portant une determination identitaire nette;
- peu de phrases;
- pas de digression;
- pas de justification integree dans le texte canonique.

Exigence de style:
- decrire;
- ne pas recommander;
- ne pas instruire;
- ne pas raconter plus que necessaire;
- ne pas psychologiser gratuitement.

Taille cible de travail a ce stade:
- viser 3000 caracteres par `mutable` (`llm` et `user`);
- comprendre cette hausse comme la consequence du nouveau regime de travail, et non comme un simple elargissement du systeme actuel;
- ne pas l'interpreter comme une permission de stocker davantage de bruit, de preferences ou de pseudo-contextes;
- l'assumer seulement si le writer devient plus costaud, plus selectif et moins frequent.

## 7. Gestion des contradictions dans le `mutable`

Le `mutable` final ne doit pas contenir de contradiction explicite.

Contrat cible:
- si une nouvelle proposition complete sans contredire, on integre;
- si elle contredit reellement, on tente une formulation plus haute qui absorbe la tension;
- si cette synthese est impossible, on ne canonise pas encore la proposition dans `mutable`.

Donc:
- la contradiction ne doit pas etre recopiee telle quelle dans le texte canonique;
- le texte final doit rester coherent comme texte identitaire unique;
- une tension non resolue reste un sujet d'arbitrage, d'evidence ou de validation ulterieure;
- elle ne devient pas une phrase canonique tant que la forme haute n'est pas trouvee.

Regle de prudence:
- mieux vaut laisser une proposition hors `mutable` que casser la coherence interne du texte canonique.

## 8. Contraintes de mise en oeuvre futures

Ce document n'ouvre pas encore l'implementation, mais il fixe les contraintes minimales de la future mise en oeuvre.

### 8.1 Contrat de l'agent d'identite pour `mutable`

Le rewriter actuel doit cesser d'etre pense comme un rewriter global du texte entier a chaque passage.

Le futur writer de `mutable`, pense ici comme un agent d'identite, devra:
- intervenir sur une fenetre elargie plutot que sur les 2 derniers tours;
- lire `llm.static` et `user.static` courants;
- lire `llm.mutable` et `user.mutable` courants;
- lire la fenetre temporaire de tours accumules avant passage;
- lire les evidences identitaires recentes retenues comme durables;
- lire les tensions ou contradictions deja ouvertes autour du canon identitaire.

Son travail cible:
- extraire de cette matiere des candidats identitaires recevables;
- comparer semantiquement chaque candidat au `static` et au `mutable` existants;
- comparer aussi les candidats entre eux avant toute ecriture;
- refuser toute canonisation en cas de doute, de contradiction non resolue, de doublon, de reformulation faible ou de derive vers l'utile non identitaire.

Le point cle n'est plus seulement:
- `rewrite` ou `no_change`.

Le point cle devient:
- selon quel contrat d'admission une proposition est jugee;
- et selon quelle operation locale le `mutable` est modifie sans etre integralement reecrit.

Sorties cibles a ce stade:
- `no_change`
- `add`
- `tighten`
- `merge`
- `raise_conflict`

Regle directrice:
- l'agent ne doit pas reecrire tout le `mutable` a chaque intervention;
- il doit d'abord voir si quelque chose s'ajoute, se resserre, se fusionne ou doit rester en conflit ouvert;
- une reecriture globale du bloc entier ne peut etre pensee, plus tard, que comme une operation rare de compaction distincte.

Controle semantique minimal avant toute operation:
- pas de doublon semantique avec `static`;
- pas de doublon semantique avec le `mutable` existant;
- pas de contradiction semantique avec `static`;
- pas de contradiction semantique avec le `mutable` existant;
- pas de contradiction semantique entre plusieurs candidats que l'agent s'appreterait a ajouter.

### 8.2 Cadence, buffer temporaire et contexte de travail

L'agent d'identite pour `mutable` ne doit pas travailler a chaque fin de tour.

Cadence cible retenue a ce stade:
- cadence fixe;
- pas de declenchement `trigger-based`;
- seuil simple: `N = 15` tours.

Premier regime cible:
- a chaque tour, on ne reecrit plus le `mutable`;
- on accumule a la place une fenetre temporaire de tours dans un espace distinct du `mutable` canonique;
- quand cette fenetre atteint 15 tours, on appelle l'agent d'identite;
- l'agent travaille alors sur cette fenetre elargie au lieu de travailler sur 2 tours seulement.

Le probleme actuel est double:
- il travaille trop souvent;
- il voit trop peu de matiere.

Contexte cible a fournir a l'agent lors de son passage:
- `llm.static` et `user.static` courants;
- `llm.mutable` et `user.mutable` courants;
- la fenetre temporaire de 15 tours;
- les evidences identitaires recentes pertinentes deja retenues comme durables;
- les tensions ou contradictions deja ouvertes autour du `mutable`.

Regles de conception:
- un agent qui ne voit que 2 tours recents ne peut pas juger correctement une inflexion identitaire durable;
- la consolidation du `mutable` doit travailler sur une fenetre plus large que la simple derniere alternance user/assistant;
- le stockage temporaire de cette fenetre doit rester distinct du `mutable` canonique;
- la modalite exacte de consommation de la fenetre (reset complet, glissement, autre) reste a fixer plus tard;
- parce qu'il n'intervient plus a chaque tour, cet agent peut devenir plus couteux et plus rigoureux;
- il peut etre pense, plus tard, comme une tache asynchrone ou un module separe, afin de ne pas peser sur la latence de la reponse courante.

### 8.3 Garde-fou metier entre `static` et `mutable`

La future mise en oeuvre ne devra pas seulement juger ce qui entre dans `mutable`.

Elle devra aussi verifier explicitement la frontiere avec `static`.

Contrat cible:
- ne pas recopier dans `mutable` un trait deja porte clairement par `static`;
- ne pas reformuler faiblement dans `mutable` ce qui est deja fixe dans `static`;
- ne pas laisser `mutable` contredire silencieusement `static`;
- ne laisser entrer dans `mutable` qu'un trait qui ajoute, precise ou densifie l'identite sans dupliquer ni annuler le socle fige.

Regle de decision:
- si une proposition candidate est deja couverte par `static`, elle ne doit pas etre canonisee dans `mutable`;
- si elle affine `static` sans le redire, elle peut etre integree;
- si elle entre en contradiction avec `static`, elle ne doit pas etre appliquee comme simple rewrite du `mutable`;
- une tension `static` / `mutable` doit rester visible comme sujet d'arbitrage ou de validation, pas comme contradiction silencieuse dans le canon actif.

### 8.4 Forme runtime

La mise en oeuvre future devra rester compatible avec l'etat reel courant:
- `static` reste file-backed;
- `mutable` reste stocke dans `identity_mutables`;
- l'injection runtime reste `static + mutable narrative`;
- le read-model continue de montrer `static` et `mutable` comme couches canoniques actives.

Evolution cible deja retenue dans ce brouillon:
- la capacite cible du `mutable` doit etre portee a 3000 caracteres pour `llm` comme pour `user`;
- ce changement doit etre implemente avec le nouveau regime de writer periodique et plus agentique, pas sur la base du mecanisme actuel de reecriture a chaque tour;
- le plafond dur exact devra etre recale en coherence avec cette nouvelle cible.
- un espace de staging temporaire doit etre introduit pour accumuler la fenetre de 15 tours sans la confondre avec le `mutable` canonique;
- si l'agent devient asynchrone, son etat d'execution doit rester lisible sans brouiller la lecture des couches identitaires actives.

### 8.5 Observabilite

L'observabilite n'est pas le centre de ce TODO, mais elle reste une contrainte dure:
- ne pas casser `identities_read`;
- ne pas casser `identity_write`;
- faire evoluer `identity_mutable_rewrite` et `identity_mutable_rewrite_apply` pour qu'ils decrivent le nouveau regime reel plutot qu'une reecriture globale par tour;
- ne pas casser les lectures `/api/admin/identity/read-model` et `/api/admin/identity/runtime-representations`.

Si le contrat change plus tard:
- traiter ce changement comme sujet de compatibilite et, si besoin, de versionnement explicite.

Implications minimales pour logs et surfaces admin:
- la page `/identity` doit pouvoir montrer, a terme, non seulement le canon actif, mais aussi l'etat du buffer temporaire et le dernier passage de l'agent d'identite;
- `/api/admin/identity/read-model` et `/api/admin/identity/runtime-representations` devront rester coherents avec cette separation entre canon actif et staging temporaire;
- les logs identity doivent rester compacts, sans dump de contenu brut, mais rendre visibles au minimum:
  - le nombre de tours actuellement bufferises;
  - le seuil configure (`15`);
  - le statut du dernier passage de l'agent;
  - le nombre de tours consideres;
  - le nombre de candidats traites;
  - les operations retenues par sujet (`no_change`, `add`, `tighten`, `merge`, `raise_conflict`);
  - la presence d'un conflit ouvert;
  - le mode d'execution si l'agent devient asynchrone.

## 9. Hors-scope de ce lot

Ce lot ne traite pas:
- `context_hints`;
- une `voie contextuelle` hors canon;
- les `moments contextuels`;
- `Frida from herself`;
- une destination laterale pour ce qui n'entre pas;
- une migration du contenu identitaire existant;
- un patch runtime;
- une modification de `/identity` ou de `/hermeneutic-admin`;
- une refonte des surfaces admin;
- une reouverture du legacy comme source active.

Ces sujets peuvent revenir plus tard.

Ils ne doivent pas piloter la premiere decision, qui est plus simple:
- qu'est-ce qui entre dans `mutable` ?

## 10. Plan de travail suivant

Ordre de travail recommande:

1. figer ce contrat doctrinal `static` / `mutable`;
2. remplacer le schema binaire `rewrite/no_change` par un contrat d'operations locales: `no_change`, `add`, `tighten`, `merge`, `raise_conflict`;
3. remplacer le declenchement a chaque tour par un buffer temporaire de 15 tours distinct du `mutable` canonique;
4. faire travailler l'agent d'identite sur cette fenetre de 15 tours, avec `static`, `mutable`, evidences durables et tensions ouvertes;
5. formaliser le controle semantique complet avant ajout: non-doublon et non-contradiction avec `static`, avec le `mutable` existant et entre nouveaux candidats;
6. acter la cible de 3000 caracteres par `mutable` dans le cadre de ce nouveau regime;
7. formaliser le garde-fou metier entre `static` et `mutable`, avec non-doublon et non-contradiction silencieuse;
8. relire le contenu actuel de `llm.mutable` et `user.mutable` a l'aune de ce contrat;
9. identifier ce qui releve de l'identitaire recevable et ce qui releve d'un bruit utile mais irrecevable;
10. realigner les logs identity, `/identity`, `/api/admin/identity/read-model` et `/api/admin/identity/runtime-representations` sur ce nouveau regime;
11. seulement ensuite traiter la forme finale cible du texte `mutable`, une eventuelle compaction rare du bloc, et le statut asynchrone de l'agent;
12. seulement ensuite ouvrir, si necessaire, les questions laterales laissees hors-scope ici.

Definition of done doctrinale pour ce lot:
- `static` est defini comme fond et noeud identitaire;
- `mutable` est defini comme identite issue du dialogue, mais au sens fort;
- les entrees recevables et irrecevables sont clairement tranchees;
- la forme textuelle cible du `mutable` est claire;
- la gestion des contradictions est fixee;
- le writer de `mutable` n'est plus pense comme une reecriture globale a chaque tour;
- le contrat d'operations locales (`no_change`, `add`, `tighten`, `merge`, `raise_conflict`) est pose;
- le regime `buffer temporaire de 15 tours -> appel de l'agent d'identite` est pose;
- le besoin d'un contexte elargi, distinct du simple dernier tour, est pose;
- le controle semantique explicite avant ajout au `mutable` est pose;
- la cible de 3000 caracteres par `mutable` est posee comme consequence du nouveau regime de writer;
- un garde-fou metier explicite interdit duplication et contradiction silencieuse entre `static` et `mutable`;
- l'observabilite et les surfaces admin identity sont explicitement a realigner sur ce nouveau regime;
- les couches laterales ne brouillent plus le centre du document.
