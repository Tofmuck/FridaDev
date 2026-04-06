# Hermeneutic Suspension / Auto-Web TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Origine: symptome runtime revalide le `2026-04-06`

## Objectif

Ouvrir un chantier generique pour traiter un probleme de routage hermeneutique/runtime:
- certains tours conceptuels, interpretatifs ou atemporels peuvent etre sur-classes en `verification_externe_requise`;
- le web reste aujourd'hui pilote trop rigidement par un booleen d'entree de session;
- la suspension peut alors arriver trop tot, avant d'avoir epuise des issues plus proportionnees.

Ce TODO ne presuppose pas la solution. Il cadre le probleme, ses points d'ancrage dans le code, les hypotheses a tester et les preuves attendues.

## Symptome observe a revalider

Cas observe comme preuve, sans en faire une regle speciale:
- `conversation_id = a2bebfd3-96d3-4088-b622-6495461f534a`
- `turn_id = turn-6a02836c-b2e8-4813-88ce-05915d590a59`
- `timestamp_utc = 2026-04-06T15:49:01+00:00`

Faits traces:
- `web_search.status = skipped`
- `web_search.reason_code = feature_disabled`
- `user_turn.regime_probatoire.principe = maximal_possible`
- `user_turn.regime_probatoire.regime_de_vigilance = renforce`
- `user_turn.regime_probatoire.types_de_preuve_attendus = ["factuelle"]`
- `qualification_temporelle.portee_temporelle = atemporale`
- `primary_node.proof_regime = verification_externe_requise`
- `primary_node.epistemic_regime = a_verifier`
- `primary_node.judgment_posture = suspend`
- `validation_agent.final_judgment_posture = suspend`
- `validation_agent.pipeline_directives_final = ["posture_suspend"]`

Ce cas sert de symptome reel:
- il ne doit pas conduire a coder des exceptions par contenu;
- il doit aider a cadrer un probleme plus general de mauvais routage, de web manuel trop rigide et de suspension trop precoce.

## Ancrages code a inspecter

- `app/core/chat_session_flow.py`
  - `web_search_on` reste un booleen de session lu en entree.
- `app/core/chat_service.py`
  - `_resolve_web_runtime_payload(...)` force `feature_disabled` si `web_search_on` est faux.
  - le pipeline construit ensuite `web_input` puis alimente le noeud hermeneutique avec cet etat.
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
  - `_resolve_regime_probatoire(...)` peut faire remonter des attentes de preuve ou de provenance web.
- `app/core/hermeneutic_node/doctrine/epistemic_regime.py`
  - `_needs_external_verification(...)`
  - `build_epistemic_regime(...)`
- `app/core/hermeneutic_node/doctrine/judgment_posture.py`
  - `build_judgment_posture(...)`
  - `proof_regime = verification_externe_requise` pousse aujourd'hui vers `suspend`.

## Probleme a traiter

- le pipeline peut sur-classer certains tours conceptuels, interpretatifs ou atemporels comme dependants d'une verification externe;
- le web manuel en entree de session peut couper trop tot une verification pourtant utile;
- la suspension devient alors une premiere issue pratique, la ou il faudrait parfois:
  - tenir une reponse prudente normale;
  - declencher une verification web backend ciblee;
  - ou ne suspendre qu'en dernier ressort si aucune lecture responsable ne reste tenable.

## Cadre doctrinal du chantier

Ce TODO ne dit pas:
- qu'il faut desactiver la suspension;
- qu'il faut allumer le web partout;
- qu'il faut hardcoder des exceptions par mots-cles ou par contenu;
- qu'il faut traiter differemment tel auteur, tel mythe ou tel champ lexical.

Ce TODO dit:
- qu'il faut mieux router certains tours;
- qu'il faut mieux distinguer ce qui releve vraiment du web;
- qu'il faut mieux ordonner reponse prudente, auto-web cible et suspension finale.

## Pistes de travail a cadrer

- [ ] Reduire les faux positifs qui classent certains tours conceptuels / interpretatifs / atemporels en `verification_externe_requise`
- [ ] Distinguer plus proprement les tours hermeneutiques / interpretatifs / conceptuels / atemporels des tours reellement factuels / sources / citationnels / dependants du web
- [ ] Etudier un declenchement web backend automatique et cible quand une vraie verification externe est necessaire
- [ ] Garder la suspension comme filet final, pas comme premiere reponse par defaut
- [ ] Definir les tests de non-regression associes avant toute implementation
- [ ] Documenter la doctrine retenue dans les specs vivantes si le chantier est ensuite implemente

## Hypotheses a comparer, sans decision deja figee

- [ ] Revoir seulement la classification amont du `regime_probatoire` si le probleme vient surtout de faux positifs precoces
- [ ] Revoir seulement `_needs_external_verification(...)` si le probleme vient surtout de la bascule probatoire
- [ ] Introduire un auto-web backend borne si la vraie lacune est l'absence d'une marche intermediaire entre "pas de web" et "suspend"
- [ ] Revoir la combinaison `proof_regime -> judgment_posture` si la suspension est aujourd'hui trop immediate une fois `a_verifier` pose
- [ ] Conserver explicitement la possibilite qu'aucune de ces hypotheses ne suffise seule et qu'une solution mixte soit necessaire

## Tests et preuves attendus si ce chantier est implemente

- [ ] Cas conceptuel / interpretatif / atemporel qui ne tombe plus a tort en `verification_externe_requise`
- [ ] Cas reellement factuel / source / citationnel ou le web auto-cible, s'il est retenu, se declenche de facon explicable
- [ ] Cas ou la suspension reste bien possible en dernier ressort si aucune assise responsable n'existe
- [ ] Non-regression: pas d'exceptions codees par contenu ou par mots-cles
- [ ] Non-regression: le booleen utilisateur ne devient pas une pseudo-source de verite cachant un auto-web implicite non documente
- [ ] Non-regression: les traces runtime restent lisibles sur `web_search`, `proof_regime`, `epistemic_regime`, `judgment_posture` et `pipeline_directives_final`

## Risques a garder en vue

- ouvrir le web trop large au lieu de le declencher de facon ciblee et explicable;
- affaiblir la suspension au lieu de la reserver aux cas vraiment bloquants;
- corriger un cas symptomatique au lieu du mecanisme general;
- deplacer le probleme d'une etape doctrinale a une autre sans clarifier la regle retenue.

## Hors scope

- implementer le correctif dans ce document;
- modifier maintenant les seuils, heuristiques, prompts ou regles de posture;
- coder des exceptions par contenu;
- rouvrir le chantier identity deja ferme.
