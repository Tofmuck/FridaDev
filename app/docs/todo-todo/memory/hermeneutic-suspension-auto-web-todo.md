# Hermeneutic Suspension / Auto-Web TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Origine: diagnostic code+traces revalide le `2026-04-06`

## Objectif

Resserrer un chantier generique de routage hermeneutique/runtime a partir d'un diagnostic prouve:
- certains tours conceptuels, interpretatifs ou atemporels peuvent etre sur-classes en `verification_externe_requise`;
- le web reste aujourd'hui pilote par un booleen d'entree de session, donc une vraie verification externe ne peut pas se declencher seule;
- la suspension peut alors arriver trop tot, avant une reponse prudente normale ou avant une marche intermediaire mieux calibree.

Ce TODO ne presuppose pas la solution. Il fige d'abord ce qui est confirme, ce qui reste hypothese, et ce qui doit etre prouve avant implementation.

## Cas diagnostique de reference

Cas observe comme preuve, sans en faire une regle speciale:
- `conversation_id = a2bebfd3-96d3-4088-b622-6495461f534a`
- `turn_id = turn-6a02836c-b2e8-4813-88ce-05915d590a59`
- `timestamp_utc = 2026-04-06T15:49:01+00:00`

Tours voisins compares:
- `turn-f2afb9fe-5a78-417d-a334-ca0c97a1467f` avant le tour suspendu
- `turn-be44aaf8-43ab-451f-acab-0fa086911544` juste apres le tour suspendu
- `turn-2310a2fd-35ee-45e6-b52c-acf7be191e1c` plus loin dans la meme sequence

## Diagnostic confirme sur le cas observe

- [x] Le web n'a pas ete tente sur le tour critique:
  - `web_search.status = skipped`
  - `web_search.reason_code = feature_disabled`
  - `web_search.enabled = false`
- [x] Le web desactive n'explique pas a lui seul la suspension:
  - les tours voisins non suspendus ont eux aussi `web_search.reason_code = feature_disabled`
  - le differentiel se situe donc dans la qualification du tour, pas dans le seul booleen web
- [x] Le `user_turn_input` reconstruit depuis le texte exact du tour critique est coherent avec les champs traces:
  - `geste_dialogique_dominant = positionnement`
  - `qualification_temporelle.portee_temporelle = atemporale`
  - `regime_probatoire.types_de_preuve_attendus = ["factuelle"]`
  - `regime_probatoire.provenances = ["web"]`
  - `regime_probatoire.regime_de_vigilance = renforce`
- [x] Les deux marqueurs qui font basculer le tour critique sont aujourd'hui des faux positifs lexicaux plausibles:
  - `preuve` est detecte dans l'expression ordinaire `faire preuve de ...`
  - `lien` est detecte dans l'expression ordinaire `lien a l'autre`
- [x] Le passage a `verification_externe_requise` vient du code doctrinal reel:
  - `_needs_external_verification(...)` retourne `True` si `"web" in required_provenances and not web_evidence_available`
  - sur ce tour, `required_provenances = {"web"}` et `web_evidence_available = false`
  - la branche temporelle `factuelle + actuelle/immediate/prospective` n'est pas la cause ici, car le tour est `atemporale`
- [x] Le passage a `suspend` vient ensuite mecaniquement de `build_judgment_posture(...)`:
  - `proof_regime = verification_externe_requise`
  - `epistemic_regime = a_verifier`
  - l'un ou l'autre suffit a produire `judgment_posture = suspend`
- [x] Le `validation_agent` ne cree pas la suspension sur ce cas:
  - `decision_source = primary`
  - `validation_decision = confirm`
  - `primary_judgment_posture = suspend`
  - `final_judgment_posture = suspend`
  - le role observe est donc de conserver la posture amont, pas de la produire
- [x] Les tours voisins montrent un contraste net:
  - avant: `types_de_preuve_attendus = []`, `regime_de_vigilance = standard`, `judgment_posture = answer`
  - apres: `types_de_preuve_attendus = []`, `regime_de_vigilance = standard`, `judgment_posture = answer`
  - plus loin: `types_de_preuve_attendus = ["argumentative"]`, `regime_de_vigilance = standard`, `judgment_posture = answer`

## Contradiction apparente: verdict

Verdict provisoirement retenu:
- il n'y a pas de contradiction entre la logique reelle du code et le runtime reconstruit du tour critique;
- il y a en revanche un probleme de classification/routage confirme;
- et un probleme d'observabilite secondaire qui peut donner une impression de contradiction.

Ce qui est confirme:
- le code suspend de facon coherente avec les entrees qu'il croit voir;
- le tour critique est sur-route vers `verification_externe_requise` a cause de marqueurs lexicaux trop larges;
- la vraie cause immediate est la provenance `web`, pas le simple fait que le tour soit conceptuel ou atemporel.

Ce qui manque aujourd'hui dans l'observabilite resumee:
- la carte `hermeneutic_node_insertion.inputs.user_turn.regime_probatoire` expose `types_de_preuve_attendus` et `regime_de_vigilance`;
- mais elle n'expose pas `provenances`;
- l'operateur voit donc `renforce` et `["factuelle"]` sans voir explicitement le `["web"]` qui declenche `_needs_external_verification(...)`.

## Ancrages code reellement impliques

- `app/core/chat_session_flow.py`
  - `web_search_on` reste un booleen de session lu en entree.
- `app/core/chat_service.py`
  - `_resolve_web_runtime_payload(...)` force `feature_disabled` si `web_search_on` est faux.
  - `_run_hermeneutic_node_insertion_point(...)` transmet ensuite `user_turn_input`, `web_input`, `primary_payload` puis `validated_result`.
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
  - `_resolve_regime_probatoire(...)`
  - `_web_markers(...)`
  - les marqueurs `preuve` et `lien` sont aujourd'hui suffisants sur le cas observe
- `app/core/hermeneutic_node/doctrine/epistemic_regime.py`
  - `_needs_external_verification(...)`
  - `build_epistemic_regime(...)`
- `app/core/hermeneutic_node/doctrine/judgment_posture.py`
  - `build_judgment_posture(...)`
- `app/core/hermeneutic_node/validation/validation_agent.py`
  - le mapping final conserve ici une posture `suspend` deja produite en amont
- `app/observability/hermeneutic_node_logger.py`
  - `_summarize_user_turn(...)` masque aujourd'hui `provenances` dans le resume observable

## Probleme a traiter

- le pipeline peut sur-classer certains tours conceptuels, interpretatifs ou atemporels comme dependants d'une verification externe;
- ces faux positifs ne viennent pas necessairement de mots explicitement "web", mais aussi d'usages ordinaires de marqueurs trop larges;
- le web manuel en entree de session coupe alors toute verification externe potentielle;
- la suspension devient la premiere issue pratique alors que, sur le cas observe, le routage lui-meme semble deja discutable.

## Ce qui reste hypothese a ce stade

- [ ] La meilleure correction est-elle surtout amont, dans `_resolve_regime_probatoire(...)`, plutot qu'aval ?
- [ ] Faut-il revoir seulement la notion de provenance `web`, ou aussi la notion de `factuelle` pour les tours conceptuels longs ?
- [ ] Un auto-web backend borne est-il vraiment necessaire pour ce chantier, ou seulement pour les cas qui restent legitimement `verification_externe_requise` apres nettoyage des faux positifs ?
- [ ] La combinaison `verification_externe_requise -> suspend` est-elle trop dure en general, ou seulement problematique quand l'etiquetage amont est faux ?
- [ ] Faut-il traiter le manque d'observabilite (`provenances` non exposees) dans le meme cycle que la correction doctrinale, ou en pas separe ?

## Pistes de travail a comparer, sans solution deja figee

- [ ] Reduire les faux positifs qui classent certains tours conceptuels / interpretatifs / atemporels en `verification_externe_requise`
- [ ] Distinguer plus proprement les tours hermeneutiques / interpretatifs / conceptuels / atemporels des tours reellement factuels / sources / citationnels / dependants du web
- [ ] Evaluer si l'auto-web backend doit n'intervenir qu'apres assainissement des faux positifs, et non comme rustine primaire
- [ ] Garder la suspension comme filet final, pas comme premiere reponse par defaut
- [ ] Rendre la cause de bascule observable de facon plus explicite si le chantier est ensuite implemente
- [ ] Documenter la doctrine retenue dans les specs vivantes si le chantier est ensuite implemente

## Preuves attendues avant implementation

- [ ] Reproduction testee du cas critique avec un texte conceptuel atemporel contenant des usages ordinaires de marqueurs actuellement trop larges
- [ ] Preuve qu'un tour conceptuel / interpretatif / atemporel ne tombe plus a tort en `verification_externe_requise`
- [ ] Preuve qu'un tour reellement factuel / source / citationnel reste bien classable comme necessitant une verification externe
- [ ] Si l'auto-web est retenu: preuve qu'il ne se declenche pas sur les faux positifs nettoyes, mais seulement sur des cas reellement dependants du web
- [ ] Si la suspension reste necessaire: preuve qu'elle n'arrive plus avant les marches intermediaires retenues
- [ ] Preuve d'observabilite: les traces exposent suffisamment la cause de bascule (`provenances`, raison de verification externe, ou equivalent stable)
- [ ] Non-regression: pas d'exceptions codees par contenu ou par mots-cles metier

## Cadre doctrinal du chantier

Ce TODO ne dit pas:
- qu'il faut desactiver la suspension;
- qu'il faut allumer le web partout;
- qu'il faut hardcoder des exceptions par mots-cles ou par contenu;
- qu'il faut traiter differemment tel auteur, tel mythe ou tel champ lexical.

Ce TODO dit:
- qu'il faut mieux router certains tours;
- qu'il faut mieux distinguer les vrais besoins de verification externe des faux positifs lexicaux;
- qu'il faut mieux ordonner reponse prudente, verification externe et suspension finale.

## Risques a garder en vue

- corriger un symptome lexical local sans clarifier la doctrine generale;
- ouvrir le web trop large au lieu de le declencher de facon ciblee et explicable;
- affaiblir la suspension au lieu de la reserver aux cas vraiment bloquants;
- deplacer le probleme d'une etape doctrinale a une autre sans exposer la vraie cause observable.

## Hors scope

- implementer le correctif dans ce document;
- modifier maintenant les seuils, heuristiques, prompts ou regles de posture;
- coder des exceptions par contenu;
- rouvrir le chantier identity deja ferme.
