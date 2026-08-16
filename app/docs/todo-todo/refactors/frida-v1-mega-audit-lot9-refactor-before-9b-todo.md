# Frida V1 mega-audit - remise au vert avant Lot 9B TODO

Statut: actif, tests et documentation uniquement a la creation.

Roadmap parente:
`app/docs/todo-todo/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`

## Objet

Retablir une suite complete lisible avant tout refactor du Lot 9B. Le dernier
audit independant du 25 juillet 2026 a observe `2549` tests, `22` echecs et
`16` erreurs. Les memes `38` identifiants existaient au parent du correctif de
continuite Web: ils ne sont pas une regression de ce correctif, mais ils
masquent de futures regressions et interdisent une baseline defendable pour le
coeur du chat.

Ce chantier ne consiste pas a faire passer les tests par affaiblissement. Il
doit etablir, pour chaque cas rouge, si le comportement courant ou l'attente du
test est la source du desalignement, puis corriger uniquement la source
prouvee.

## Gate avant 9B

- Aucun sous-lot 9B.0-9B.6 ne commence avant la fermeture de cette TODO.
- Le correctif de continuite de provenance Web est techniquement valide et a
  ete valide en dialogue live par Tof le 14 aout 2026. Son P2 doit etre ferme
  dans la documentation vivante sans modifier le code.
- Le travail de remise au vert part d'une branche dediee creee depuis le HEAD
  applicatif effectivement deploye et audite.
- Une nouvelle panne produit decouverte pendant le triage arrete la famille
  concernee et ouvre un lot correctif separe. Elle n'est pas masquee dans un
  patch tests-only.

## Baseline obligatoire

Avant toute correction:

- [ ] Capturer branche, HEAD, parent, upstream et worktree propre.
- [ ] Verifier que checkout et code FridaDev execute correspondent.
- [ ] Executer la decouverte complete dans le runner hermetique autoritatif,
  sans reseau ni secret reel.
- [ ] Capturer le nombre de tests, echecs, erreurs, skips et expected failures.
- [ ] Conserver une liste content-free des identifiants `FAIL` et `ERROR`, avec
  une empreinte deterministe.
- [ ] Rejouer chaque cas rouge de facon ciblee avant de le classer.
- [ ] Ne pas imposer `2549 / 22 / 16` si le HEAD courant differe: toute
  variation doit etre expliquee par le code, les tests ou le runner reels.

## Registre de triage

Construire dans ce fichier, avant patch, une ligne par identifiant rouge:

| identifiant | famille | reproduction ciblee | contrat autoritatif | cause prouvee | action | preuve finale | statut |
| --- | --- | --- | --- | --- | --- | --- | --- |

Valeurs admises pour `cause prouvee`:

- `BUG_PRODUIT`;
- `TEST_OBSOLETE`;
- `RUNNER_OU_FIXTURE`;
- `CONTRAT_DOCUMENTAIRE_INCOHERENT`;
- `INCONNU`.

Aucune ligne `INCONNU` ne peut etre fermee ou retiree de la baseline.

## Familles historiques a revalider

Le classement ci-dessous est un point de depart issu de l'audit du 25 juillet,
pas une autorisation de corriger en bloc:

### F1 - Runner et environnement, 7 cas historiques

Hypotheses a revalider: secrets runtime absents, outil `rg` absent de l'image,
chemin `/app` fige alors que le runner monte `/workspace/app`, DB absente, mode
Identity different entre runner hermetique et runtime.

- [ ] Rendre les tests hermetiques avec fakes et valeurs synthetiques quand le
  contrat est unitaire.
- [ ] Rendre les chemins independants du point de montage.
- [ ] Ne jamais injecter un secret reel pour faire passer un test.
- [ ] Ne pas transformer silencieusement un test runtime en test unitaire.
- [ ] Ne pas ajouter de skip general pour cacher une dependance non preparee.

### F2 - Attentes Web anterieures a la capsule, 8 cas historiques

Hypothese a revalider: les tests prouvent encore l'absence d'auto-Web, mais
comparent le prompt complet sans accepter la capsule de continuite deja
contractuelle.

- [ ] Preserver les assertions qui prouvent qu'aucune recherche Web n'est
  lancee.
- [ ] Tester la presence et la position de la capsule sans snapshoter du
  contenu utilisateur brut.
- [ ] Ne pas retirer la capsule du runtime pour satisfaire une attente ancienne.
- [ ] Verifier les cas Web off, contexte vide, injection effective et legacy.

### F3 - Contrats d'observabilite, 12 cas historiques

Hypothese a revalider: les attentes exigent des champs supprimes, renommes ou
rediges par les contrats content-free et default-deny courants.

- [ ] Identifier pour chaque champ le sink et le schema vivant autoritatifs.
- [ ] Corriger le test si le champ est legitimement interdit ou renomme.
- [ ] Corriger le code seulement si le contrat vivant exige encore le champ.
- [ ] Ne reintroduire aucun contenu, prompt, query, URL, exception brute ou
  identifiant sensible dans une surface content-free.
- [ ] Conserver la politique distincte des logs serveur prives Identity/Memory.

### F4 - Validation minimale, 5 cas historiques

Hypotheses a revalider: attentes anciennes sur secret Agenda, referer de
reformulation Web, matrice de settings, marqueur UI et champ du modele
principal.

- [ ] Comparer chaque attente au schema runtime courant et au contrat vivant.
- [ ] Distinguer validation offline, image de test et configuration runtime.
- [ ] Ne pas retablir une compatibilite obsolete uniquement pour le test.
- [ ] Conserver une sortie content-free et des reason codes stables.

### F5 - Erreurs admin anciennes, 3 cas historiques

Hypothese a revalider: les tests attendent des messages detailles anterieurs
aux erreurs generiques content-free.

- [ ] Verifier statut HTTP, reason code et schema public courant.
- [ ] Ne pas reexposer de texte d'exception ou de detail prive.
- [ ] Mettre a jour les attentes seulement apres preuve du contrat actif.

### F6 - Contrats isoles, 3 cas historiques

Hypotheses a revalider: helper temporel retire, statut Identity requalifie et
marqueur frontend obsolete.

- [ ] Verifier qu'aucun appel runtime vivant ne depend du helper retire.
- [ ] Verifier le statut Identity contre le mode et les guards courants.
- [ ] Verifier le marqueur frontend contre le DOM et le contrat actifs.
- [ ] Ne pas recreer une API morte ou un texte UI obsolete pour satisfaire le
  test.

## Regles de correction

- Une famille a la fois, avec reproduction rouge ciblee puis preuve verte.
- Lire code, appelants, tests, contrat vivant et documentation avant le patch.
- Preferer une fixture partagee explicite a des valeurs copiees dans plusieurs
  tests.
- Ne jamais supprimer un test sans prouver que sa responsabilite est couverte
  ailleurs avec une sensibilite equivalente ou superieure.
- Interdiction de masquer une panne par `skip`, `expectedFailure`, `xfail`,
  broad `except`, timeout augmente, assertion retiree ou comparaison rendue
  triviale.
- Aucun acces Internet, provider reel, secret reel ou donnee operateur.
- Aucun changement produit, prompt, route, provider, DB, Caddy, Docker global,
  Memory, Identity, Agenda ou Biblio dans un correctif tests-only.
- Tout changement runtime necessaire revele un lot correctif distinct, borne et
  valide avant de reprendre cette TODO.
- Apres chaque famille: suites ciblees, suites voisines, decouverte complete,
  comparaison de la liste content-free et `git diff --check`.
- Un commit ne melange pas plusieurs causes sans lien.

## Auto-audit obligatoire par famille

- [ ] Le test echouait bien avant la correction.
- [ ] Le comportement attendu vient d'une source de verite courante.
- [ ] Le test corrige echouerait encore si le bug protege etait reintroduit.
- [ ] Aucun test voisin n'a ete affaibli, supprime ou ignore.
- [ ] Aucun nombre, chemin, ordre ou texte interne instable n'est fige sans
  raison contractuelle.
- [ ] Aucun contenu sensible n'entre dans fixture, snapshot, diff ou rapport.
- [ ] Le patch ne commence aucun refactor 9B.

## Condition de sortie

La TODO ne peut etre fermee que si:

- [ ] Le registre contient tous les identifiants de la baseline et aucun
  `INCONNU`.
- [ ] Chaque ancienne panne est reproduite, expliquee et corrigee a sa source.
- [ ] La decouverte complete termine avec `0` echec et `0` erreur.
- [ ] Le nombre de skips et expected failures n'augmente pas.
- [ ] Le nombre total de tests et toute variation sont expliques.
- [ ] Les suites critiques chat, Web, observabilite, admin, validation minimale,
  Identity et frontend sont vertes separement.
- [ ] La route map et les golden tests du Lot 9 restent verts.
- [ ] Le P2 de continuite Web est documente ferme par audit technique et
  validation live utilisateur.
- [ ] La roadmap Lot 9 pointe vers la preuve finale et degele explicitement
  9B.0.
- [ ] Le worktree final est propre et la branche est alignee avec son upstream
  apres livraison autorisee.

Statut de sortie attendu:

`SUITE COMPLETE VERTE - PREREQUIS AVANT 9B FERME`
