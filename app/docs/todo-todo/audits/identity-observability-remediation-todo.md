# Identity observability remediation - TODO

Statut: clos, pret a archiver
Source: audit Identity du 2026-05-13
Classement: `app/docs/todo-todo/audits/`
Portee: observabilite et preuves operateur du module Identity
Hors-scope: modification de la doctrine Identity, changement du seuil de 15 paires, creation forcee d'une mutable LLM, redesign des surfaces admin, refactor general du module Identity

Note de cloture: les cinq lots de remediation sont livres, testes et couverts par preuves. Ce fichier reste temporairement dans `todo-todo/audits/` pour cette cloture documentaire et peut etre deplace vers `app/docs/todo-done/audits/` par un patch d'archivage separe.

## 1. Intention

Ce TODO transforme l'audit Identity du 2026-05-13 en feuille de route de remediation bornee.

L'audit n'a pas etabli de cassure critique du modele Identity. Le runtime courant reste globalement coherent avec le contrat `static + mutable narrative`: `static` et `mutable` canoniques sont les seules couches injectees, le staging reste hors injection active, et le legacy `identities` / `identity_evidence` / `identity_conflicts` reste diagnostique.

Le probleme a corriger n'est donc pas: "Frida doit absolument avoir une mutable LLM maintenant".

Le probleme est: quand Frida n'a pas de mutable LLM, l'operateur doit pouvoir comprendre pourquoi avec des preuves compactes, non sensibles et relisibles tour par tour.

Ce chantier vise uniquement:
- a mieux prouver ce qui est injecte dans le prompt principal;
- a clarifier l'etat du staging courant par rapport au dernier run periodique termine;
- a conserver les `reason_code` utiles du regime periodique;
- a auditer durablement les ecritures et effacements de mutables;
- a prouver par test qu'une mutable `llm` acceptee arrive bien jusqu'a `identity_input` et au prompt final.

## 2. Source de verite

- [x] Traiter ce fichier comme la source de travail active des cinq remediations issues de l'audit Identity du 2026-05-13.
- [x] Garder `app/docs/states/policies/identity-new-contract-plan.md` comme source doctrinale: `mutable` reste de l'identite forte, pas une preference, un confort local ou une consigne de reponse.
- [x] Garder `app/docs/todo-done/refactors/identity-new-contract-todo.md` comme archive operatoire: le regime actif est deja `static + mutable narrative`, avec staging de 15 paires, agent periodique, scoring deterministe, promotion et suspension.
- [x] Garder `app/docs/states/specs/identity-read-model-contract.md` et `app/docs/states/specs/identity-surface-contract.md` comme contrats de lecture operateur tant qu'ils ne sont pas explicitement mis a jour.
- [x] Relire l'etat courant du code avant chaque lot, notamment les fichiers listes dans la section du lot, pour eviter de corriger un finding deja devenu stale.
- [x] Ne jamais utiliser un contenu brut identitaire, un buffer brut, un prompt utilisateur ou une conversation comme preuve documentaire: utiliser longueurs, presence, statuts, timestamps, `updated_by`, `update_reason`, reason codes et hash courts.

## 3. Principes de cloture

- [x] Chaque lot doit etre ferme par un patch petit, reversible et teste.
- [x] Chaque preuve runtime doit rester compacte et sans contenu sensible.
- [x] Une absence de mutable LLM est un etat admissible si les preuves montrent `no_change`, seuil non atteint, rejet deterministe ou absence de signal durable.
- [x] Aucun lot ne doit modifier le seuil de 15 paires, la doctrine d'admission du `mutable`, ni le statut non injecte du staging.
- [x] Aucun lot ne doit reactiver le legacy `identities` comme source d'injection active.
- [x] Les specs vivantes ne sont modifiees que si le patch runtime change un contrat operateur, un champ expose ou une preuve attendue.
- [x] Chaque lot doit ajouter ou mettre a jour au moins un test qui aurait echoue avec le finding initial.

## 4. Ordre de correction recommande

1. Lot 1: ajouter l'empreinte compacte de l'identite injectee tour par tour.
2. Lot 2: clarifier le staging courant par rapport au dernier run termine.
3. Lot 3: conserver le `reason_code` utile du dernier agent periodique.
4. Lot 4: introduire un audit durable des ecritures et effacements de mutables.
5. Lot 5: ajouter un test d'integration prouvant la chaine complete d'une mutable LLM acceptee.

Cet ordre commence par ce qui aide le plus l'operateur a comprendre le prompt final, puis corrige les ambiguites de lecture staging, puis ferme l'audit historique et les trous de test.

## Lot 1 - Empreinte compacte de l'identite injectee

Objectif: enregistrer, pour chaque tour chat, une preuve compacte de l'identite effectivement compilee dans le prompt principal, sans exposer le contenu des identites.

Fichiers probablement touches:
- `app/server.py`
- `app/core/chat_llm_flow.py`
- `app/core/llm_client.py`
- `app/identity/identity.py`
- `app/identity/active_identity_projection.py`
- `app/observability/identity_observability.py`
- tests de logs, prompt et chat turn logger
- specs de logs ou Identity si un champ public operateur change

Hors-scope:
- [x] Ne pas logger les textes `static` ou `mutable` bruts.
- [x] Ne pas changer la composition du prompt principal.
- [x] Ne pas injecter le staging dans le prompt.
- [x] Ne pas creer de mutable LLM pour faire passer la preuve.

Cases de correction:
- [x] Definir une empreinte compacte de `identity_block`: presence, longueur totale, hash court, `used_identity_ids_count`, `staging_included=false`.
- [x] Ajouter une empreinte par sujet et couche: `llm.static`, `llm.mutable`, `user.static`, `user.mutable`, avec `present`, `chars`, hash court et metadonnees non sensibles quand disponibles.
- [x] Brancher cette empreinte dans `prompt_prepared` ou dans un event adjacent du meme tour, afin que la preuve soit reliee au payload final du LLM principal.
- [x] Garantir que l'empreinte est calculee depuis la meme base runtime que `build_identity_block()` / `build_identity_input()`.
- [x] Verifier que l'event ne contient aucun champ `content`, `prompt`, `messages`, `history` ou texte identitaire brut.

Tests attendus:
- test unitaire de construction de l'empreinte avec `llm.mutable` absente et `user.mutable` presente;
- test `chat_turn_logger` ou serveur prouvant que `prompt_prepared` contient l'empreinte compacte;
- test de redaction prouvant l'absence de contenu brut dans l'event;
- test de regression sur `staging_included=false`.

Preuves runtime attendues:
- commande in-container lisant le dernier `prompt_prepared` et affichant seulement les champs compacts;
- preuve qu'un tour avec `llm.mutable` absente montre `llm.mutable.present=false` sans erreur;
- preuve que le hash/longueur changent quand la source identitaire change dans un test isole, sans dump de contenu.

Condition de cloture:
- [x] Pour un tour chat donne, l'operateur peut dire quelles couches Identity ont ete injectees, lesquelles etaient absentes, et quelle empreinte compacte correspond au bloc final.

## Lot 2 - Clarifier staging courant vs dernier run termine

Objectif: eviter qu'un buffer en cours affiche une raison ancienne comme si elle decrivait encore l'etat courant.

Fichiers probablement touches:
- `app/memory/memory_identity_staging.py`
- `app/memory/memory_identity_periodic_agent.py`
- `app/admin/admin_identity_read_model_service.py`
- `app/web/hermeneutic_admin/render_identity_read_model.js`
- `app/web/identity/render_identity_runtime_representations.js`
- tests staging, read-model et surfaces admin

Hors-scope:
- [x] Ne pas modifier le seuil `BUFFER_TARGET_PAIRS = 15`.
- [x] Ne pas changer la politique de purge du buffer apres application reussie.
- [x] Ne pas afficher les paires du buffer.
- [x] Ne pas transformer le staging en canon injecte.

Cases de correction:
- [x] Decider entre deux formes: vider `last_agent_reason` quand un nouveau buffer demarre, ou introduire des champs separes `current_buffer_*` et `last_completed_agent_*`.
- [x] Faire en sorte que `buffering` ne soit plus accompagne d'une raison terminale ambigue comme `completed_no_change`.
- [x] Garder lisible le dernier run termine avec son timestamp quand cette information reste utile a l'operateur.
- [x] Adapter le read-model pour exposer la distinction sans casser le contrat `identity_staging` existant plus que necessaire.
- [x] Adapter l'UI si un libelle actuel risque de melanger "buffer courant" et "dernier run".

Tests attendus:
- test `append_identity_staging_pair()` apres clear d'un run `completed_no_change`;
- test read-model avec buffer courant sous seuil et dernier run termine;
- test frontend/source ou browser si le libelle UI change;
- test de non-regression: les statuts `running`, `contract_invalid`, `auto_canonization_suspended` restent lisibles.

Preuves runtime attendues:
- commande in-container sur `get_latest_identity_staging_state()` montrant un buffer courant sans raison terminale trompeuse;
- lecture `/api/admin/identity/read-model` via loopback ou service montrant les champs separes ou nettoyes;
- absence de contenu brut du buffer dans les preuves.

Condition de cloture:
- [x] L'operateur peut distinguer sans interpretation manuelle l'etat du buffer courant et le dernier run periodique termine.

## Lot 3 - Conserver le reason_code du dernier agent periodique

Objectif: faire remonter le `reason_code` utile du run `identity_periodic_agent`, y compris quand le statut top-level est `ok`.

Fichiers probablement touches:
- `app/memory/memory_identity_periodic_agent.py`
- `app/observability/chat_turn_logger.py`
- `app/admin/admin_identity_read_model_service.py`
- tests logs, periodic agent et read-model
- specs de logs/read-model si le champ expose change

Hors-scope:
- [x] Ne pas modifier le scoring deterministe.
- [x] Ne pas modifier les decisions de l'agent periodique.
- [x] Ne pas ajouter de texte de proposition brute aux logs.
- [x] Ne pas fusionner `identity_periodic_agent` et `identity_periodic_agent_apply` sans decision separee.

Cases de correction:
- [x] Garantir que le `reason_code` terminal (`completed_no_change`, `applied`, `completed_with_open_tension`, etc.) est conserve dans le payload compact de `identity_periodic_agent`.
- [x] Verifier si le champ top-level `reason_code` du logger doit aussi etre conserve pour les statuts `ok`, ou si le read-model doit lire le payload.
- [x] Adapter `latest_agent_activity.reason_code` pour ne plus retourner `None` quand un run `ok` a une raison terminale connue.
- [x] Preserver les champs existants: `writes_applied`, `promotion_count`, `outcomes`, `rejection_reasons`, `auto_canonization_suspended`.

Tests attendus:
- test periodic agent avec run `ok/completed_no_change`;
- test periodic agent avec write applique;
- test read-model `latest_agent_activity.reason_code`;
- test de redaction des outcomes: scores et reason codes oui, propositions brutes non.

Preuves runtime attendues:
- lecture compacte des derniers events `identity_periodic_agent`;
- read-model montrant un `latest_agent_activity.reason_code` non nul apres run termine;
- verification qu'aucun contenu identitaire brut n'est ajoute.

Condition de cloture:
- [x] Le dernier run periodique utile expose un `reason_code` exploitable dans les logs et le read-model, meme quand le status est `ok`.

## Lot 4 - Audit durable des ecritures/effacements de mutables

Objectif: permettre de distinguer une mutable absente parce qu'elle n'a jamais existe, parce qu'elle a ete effacee, ou parce qu'aucune operation recente n'a ete admise, sans dependre uniquement des logs retenus.

Fichiers probablement touches:
- `app/memory/memory_identity_mutables.py`
- `app/memory/memory_store.py`
- migration ou bootstrap DB runtime
- `app/admin/admin_identity_mutable_edit_service.py`
- `app/admin/admin_identity_mutable_edit_audit.py`
- `app/memory/memory_identity_periodic_apply.py`
- `app/admin/admin_identity_read_model_service.py`
- tests DB, admin mutable edit, periodic apply et read-model

Hors-scope:
- [x] Ne pas stocker de contenu mutable brut supplementaire dans l'audit.
- [x] Ne pas exposer de secret, DSN ou prompt.
- [x] Ne pas changer la table canonique `identity_mutables` au-dela du strict necessaire.
- [x] Ne pas empecher `clear` d'effacer effectivement la mutable canonique.

Cases de correction:
- [x] Definir un stockage durable compact des mutations de mutable: subject, action, actor/update source, reason_code, old/new chars, hash courts, timestamps, source_trace_id si non sensible.
- [x] Couvrir les chemins admin `set` et `clear`.
- [x] Couvrir les chemins periodiques `add`, `tighten`, `merge`, promotion ou no-write significatif si utile.
- [x] Exposer dans le read-model un resume compact de la derniere mutation mutable par sujet, sans contenu brut.
- [x] Conserver une semantique claire entre "absence courante" et "historique de mutation".

Tests attendus:
- test `set` admin cree une entree d'audit sans contenu brut;
- test `clear` admin cree une tombstone exploitable;
- test periodic apply accepted cree une trace compacte;
- test read-model pour `llm.mutable` absente avec dernier audit `clear` ou aucun audit;
- test de redaction des hash/longueurs.

Preuves runtime attendues:
- commande DB/API affichant le dernier audit mutable par sujet avec longueurs/hash courts;
- preuve qu'une absence `llm.mutable` peut etre qualifiee sans ouvrir les conversations;
- verification que les logs admin restent compatibles.

Condition de cloture:
- [x] L'absence d'une mutable canonique peut etre expliquee par une trace durable ou par l'absence explicite de trace connue, sans consulter de contenu brut.

## Lot 5 - Test d'integration chaine mutable LLM

Objectif: prouver que si une operation `llm` admissible est acceptee, elle va bien jusqu'au stockage canonique, a `identity_input.frida.mutable` et au bloc injecte dans le prompt principal.

Fichiers probablement touches:
- `app/tests/unit/memory/test_identity_periodic_apply_phase2.py`
- `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`
- `app/tests/test_identity_phase4.py`
- tests serveur/chat ou nouveau test d'integration cible
- `app/identity/identity.py`
- `app/identity/active_identity_projection.py`
- `app/core/chat_prompt_context.py`
- `app/core/llm_client.py` seulement si le test inspecte le payload final

Hors-scope:
- [x] Ne pas rendre le test dependant d'un vrai appel OpenRouter.
- [x] Ne pas exiger que la production cree une mutable LLM.
- [x] Ne pas relacher les gardes d'admission pour fabriquer une acceptation.
- [x] Ne pas utiliser de texte identitaire personnel ou long comme fixture.

Cases de correction:
- [x] Construire une fixture courte et explicitement identitaire pour `subject="llm"` qui passe les gardes existantes.
- [x] Faire passer l'operation par l'applicateur deterministe ou par un store DB de test realiste.
- [x] Verifier que `identity_mutables.llm` est ecrit avec `updated_by=identity_periodic_agent` ou la source attendue du chemin teste.
- [x] Verifier que `build_identity_input()` expose cette mutable dans `frida.mutable.content`.
- [x] Verifier que `build_identity_block()` ajoute une section `[MUTABLE]` sous la section modele.
- [x] Si possible, verifier que `build_augmented_system()` puis `llm.build_payload()` conservent cette section dans les messages envoyes au modele principal.

Tests attendus:
- test integration sans reseau couvrant `llm add accepted -> identity_mutables -> identity_input -> identity_block`;
- test prompt principal sans appel provider;
- test negatif: `llm.mutable` absente reste un etat valide et n'ajoute pas de section `[MUTABLE]` sous le modele;
- test prouvant que le staging n'est pas injecte.

Preuves runtime attendues:
- execution ciblee des tests Identity dans le conteneur ou dans l'environnement Python disponible;
- si `pytest` n'est pas disponible sur OVH, consigner explicitement l'indisponibilite et fournir les preuves statiques/commandes alternatives prevues par `AGENTS.md`;
- aucune modification de donnees production pour fabriquer la preuve.

Condition de cloture:
- [x] Les tests prouvent qu'une mutable LLM acceptee atteint le prompt final, et qu'une absence de mutable LLM reste lisible comme etat normal quand aucune proposition durable n'a ete acceptee.

## Condition de non-prolongation

Ce chantier se ferme lorsque les cinq findings de l'audit Identity du 2026-05-13 sont couverts par preuves:

- [x] empreinte compacte de l'identite injectee tour par tour;
- [x] staging courant non confondu avec dernier run termine;
- [x] `reason_code` du dernier agent periodique conserve et relisible;
- [x] audit durable des `set` / `clear` / writes de mutables;
- [x] test d'integration prouvant `llm add accepted -> DB -> identity_input -> prompt`.

Ne pas ajouter de sixieme lot pour:
- refactoriser tout Identity;
- modifier la doctrine `static` / `mutable`;
- changer la taille du buffer;
- forcer la creation d'une mutable LLM;
- remplacer les surfaces admin;
- reouvrir le legacy `identity_mutable_rewriter`.

Si un futur audit decouvre un probleme distinct, creer un nouveau TODO cible au lieu d'etendre celui-ci.

## Matrice findings -> lots

| Finding audit 2026-05-13 | Severite | Lot de remediation | Preuve de cloture attendue |
| --- | --- | --- | --- |
| Observabilite insuffisante du contenu identitaire reellement injecte tour par tour | P1 | Lot 1 | Event compact par tour avec presence/longueurs/hash courts des couches injectees |
| Staging `buffering` melange avec ancienne raison `completed_no_change` | P2 | Lot 2 | Read-model et staging distinguent buffer courant et dernier run termine |
| Read-model perd le `reason_code` utile du dernier agent periodique | P2 | Lot 3 | `latest_agent_activity.reason_code` relisible pour les runs `ok` |
| Absence historique de mutable LLM pas totalement auditable | P2 | Lot 4 | Audit durable/tombstone compact des mutations de `identity_mutables` |
| Tests protegent les contrats mais pas la chaine runtime complete LLM mutable | P2 | Lot 5 | Test sans reseau prouvant `llm add accepted -> DB -> identity_input -> prompt` |

## Notes de prudence

- [x] Une mutable LLM absente n'est pas un bug par defaut.
- [x] `no_change` est une decision valide quand le signal durable est faible, ambigu ou deja couvert par le statique.
- [x] Les preuves doivent montrer pourquoi une mutable n'est pas ecrite, pas contourner le regime d'admission pour produire une mutable artificielle.
- [x] Les futures corrections doivent rester redacted-by-design: pas de dump de prompts, conversations, buffers ou contenus identitaires longs.
