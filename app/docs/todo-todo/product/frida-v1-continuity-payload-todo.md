# Frida V1 - Continuity Payload TODO

Statut: TODO actif
Date: 2026-06-22
Classement: `app/docs/todo-todo/product/`
Branche de travail initiale: `FridaV1-Continuity-Payload-Audit`

## Objet du chantier

Frida V1 a deja des briques fortes: identity stable et mutable, memoire,
resumes, lanes Documents/Notes/Biblio/Agenda/Web, runtime settings et
observabilite content-free.

Le probleme produit restant est plus precis: la continuite de ton, methode,
relation et presence entre conversations reste emergente. Une conversation
longue reconstruit beaucoup par son dialogue recent; une nouvelle conversation
recupere surtout le prompt statique, l'identite, et de la memoire si le
retrieval tombe juste.

Le but de ce chantier est de rendre cette continuite:

- specifiable, sans la confondre avec identity, memory ou summary;
- prouvable, sans capturer de prompt brut ni de payload provider;
- eventuellement injectable, mais seulement apres preuve content-free du
  payload final.

Regle dure: aucun runtime de capsule de continuite ne doit partir avant
livraison et test de `main_payload_manifest_v1`.

## Sources de verite

- Audit principal:
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-audit-2026-06-22.md`
- Contre-audit:
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`
- Contrat source-of-truth Continuity Payload:
  `app/docs/states/specs/frida-v1-continuity-payload-contract.md`
- Doctrine voix, identite et reprise apres ecart:
  `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Contrat source-of-truth mutable judge:
  `app/docs/states/specs/mutable-identity-judge-contract.md`
- Plan doctrinal `static` / `mutable`:
  `app/docs/states/policies/identity-new-contract-plan.md`
- Archive operatoire identity:
  `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Contrat observabilite agentique:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`
- Roadmap finale produit:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Findings vivants

Chaque finding demarre ouvert. Il ne peut pas etre considere clos sans preuve
content-free relue, testee ou explicitement reportee post-V1.

| Statut | Finding | Lot cible | Critere de cloture court |
| --- | --- | --- | --- |
| - [ ] | P1-CONT-01 | Lot 6 puis Lot 7 | Capsule distincte d'identity/memory/summary specifiee, tests artificiels passes, injection runtime seulement apres lots 1-6. |
| - [ ] | P1-PAYLOAD-01 | Lot 1 puis Lot 2 | `main_payload_manifest_v1` livre et teste sur le payload final apres injections tardives, sans contenu brut. |
| - [ ] | P2-SUMMARY-01 | Lot 4 | Resume qualifie: ce qu'il garde/perd pour la voix, avec test ou preuve content-free de non-aplatissement minimal. |
| - [ ] | P2-LANES-01 | Lot 5 | Biblio/Agenda/renderers couverts par la doctrine de voix ou explicitement bornes. |
| - [ ] | P2-MEMORY-01 | Lot 4 | Difference arbiter observe vs memoire reellement injectee prouvee dans le manifeste ou les traces. |
| - [ ] | P2-WINDOWS-01 | Lot 4 | Fenetres memory, hermeneutic node, Biblio, Agenda et prompt final cartographiees par tailles/empreintes. |
| - [ ] | P2-IDENTITY-STAGING-01 | Lot 4 | Staging mutable conversation-scoped documente comme non disponible en nouvelle conversation avant canonisation. |
| - [ ] | P2-LANE-PROVENANCE-01 | Lot 2 | Role provider et role logique distingues pour chaque bloc/lane dans le manifeste. |
| - [ ] | P2-FINAL-LOCK-POLICY-01 | Lot 5 | Politique de priorite Agenda/Biblio final-lock documentee et testee. |
| - [ ] | P2-NOTES-UI-01 | Lot 5 | Statut Notes UI tranche: hors chemin chat courant documente, ou branchement explicite teste. |
| - [ ] | P2-OBS-WRITER-01 | Lot 3 | Guard writer-side livre contre cles/payloads dangereux, avec sentinelles anti-fuite. |
| - [ ] | P3-SOFT-LIMIT-01 | Lot 4 | Soft limit explique ou durci: depassement visible et politique de troncation/exclusion testee ou reportee. |
| - [ ] | P3-NOOP-LANES-01 | Lot 5 | Non-selection Documents/Notes observable ou absence justifiee sans confusion avec lane non instrumentee. |
| - [ ] | P3-DOC-01 | Lot 1 puis Lot Z | Docs historiques requalifiees ou indexees avec statuts actifs/archive/stale. |
| - [ ] | P3-TEST-01 | Lot 6 | Tests nouvelle conversation vs longue conversation sur fixtures artificielles, sans contenu utilisateur reel. |
| - [ ] | P3-OBS-01 | Lot 6 | Preuve qualitative content-free definie: presence jugee par fixtures artificielles et signaux bornes. |
| - [ ] | P3-OFFLINE-PAYLOAD-EXPORT-01 | Lot 2 | Export local existant verifie comme borne/non-runtime, ou remplace par manifeste final content-free. |

## Lots

### Lot 0 - Cadrage TODO actif

- [x] Creer cette TODO active produit, rattachee aux audits et sans patch runtime.

Criteres de cloture Lot 0:

- fichier cree dans `app/docs/todo-todo/product/`;
- tous les findings consolides sont presents;
- chaque finding a un lot cible;
- le gate `main_payload_manifest_v1` avant capsule runtime est explicite;
- index/roadmap mis a jour quand ils servent de portes d'entree actives;
- aucun code runtime, test executable, provider live, DB, migration ou reset.

### Lot 1 - Spec source-of-truth Continuity Payload

Docs-only.

- [x] Specifier `main_payload_manifest_v1`: structure, champs autorises,
  champs interdits, roles provider, roles logiques, origine des lanes,
  injections tardives, final locks, budgets, exclusions, hashes courts et
  compteurs.
- [x] Specifier la Continuity Capsule ou nom equivalent: objet, taille,
  version, non-souverainete, contestabilite, rollback et non-objectifs.
- [x] Distinguer strictement capsule, identity stable, identity mutable,
  memoire, resume, observabilite et lanes documentaires.
- [x] Reprendre la doctrine de non-souverainete: la capsule guide la presence,
  elle ne remplace ni le tour courant ni les preuves visibles.
- [x] Graver le no-go runtime: la capsule peut etre specifiee, mais pas
  injectee tant que `main_payload_manifest_v1` n'est pas livre et teste.
- [x] Requalifier les docs historiques utiles sans rouvrir les archives
  identitaires ou observabilite.

Statut 2026-06-22: Lot 1 livre par
`app/docs/states/specs/frida-v1-continuity-payload-contract.md`. Aucun finding
n'est clos par ce lot docs-only; Lot 2+ et Lot Z restent non coches.

### Lot 2 - Manifest payload content-free runtime/fake

Objectif: implementer et tester `main_payload_manifest_v1`, sans contenu brut.

- [ ] Prouver l'ordre final du payload apres toutes les injections tardives.
- [ ] Exposer la sequence des roles provider et des roles logiques.
- [ ] Exposer l'origine des lanes: human user, system context, memory,
  summary, document, note, biblio, agenda, web, adobe ou autre origine
  allowlistee.
- [ ] Exposer final locks et assistant override sans recopier la reponse.
- [ ] Exposer budgets, exclusions, tailles, compteurs et empreintes seulement
  selon la politique de hachage du contrat: pas de hash stable naif sur contenu
  textuel sensible.
- [ ] Poser des flags explicites: `raw_prompt_included=false`,
  `raw_message_included=false`, `raw_lane_content_included=false`,
  `raw_provider_payload_included=false`.
- [ ] Verifier `app/scripts/export_main_prompt_payload.py`: reutilisable,
  borne comme outil offline, ou remplace par un chemin plus fiable.
- [ ] Couvrir au minimum nouvelle conversation, conversation longue, resume,
  lanes activees/desactivees et final response lock.

Findings principalement traites: `P1-PAYLOAD-01`,
`P2-LANE-PROVENANCE-01`, `P3-OFFLINE-PAYLOAD-EXPORT-01`.

### Lot 3 - Garde writer-side observability

Objectif: eviter qu'une future instrumentation payload introduise du contenu
brut dans l'observabilite.

- [ ] Durcir `chat_turn_logger` ou l'equivalent writer-side par schema,
  allowlist ou rejet explicite des cles dangereuses.
- [ ] Couvrir les cles de risque: messages, prompt, content, payload,
  provider payload, raw, base64/data URL et secrets.
- [ ] Ajouter des sentinelles anti-fuite sur les chemins writer et projections
  admin pertinentes.
- [ ] Preserver les vraies pannes visibles: un rejet de payload dangereux ne
  doit pas devenir un faux succes.

Finding traite: `P2-OBS-WRITER-01`.

### Lot 4 - Fenetres, summary, memory, staging

Objectif: cadrer et prouver ce que chaque sous-systeme voit.

- [ ] Cartographier les fenetres recent dialogue du prompt principal, memory,
  hermeneutic node, Biblio et Agenda.
- [ ] Prouver dans le manifeste ou l'observabilite les tailles, periodes,
  roles et empreintes content-free de ces fenetres.
- [ ] Documenter le mode memory `shadow`: decisions arbiter observees vs
  contenu effectivement injecte.
- [ ] Qualifier l'effet du summary sur la continuite de voix et les rituels
  de travail.
- [ ] Documenter la mutable identity staging comme conversation-scoped avant
  canonisation.
- [ ] Traiter le soft token limit: politique assumee, preuve de signal, ou
  durcissement borne.

Findings traites: `P2-SUMMARY-01`, `P2-MEMORY-01`, `P2-WINDOWS-01`,
`P2-IDENTITY-STAGING-01`, `P3-SOFT-LIMIT-01`.

### Lot 5 - Lanes et conflits

Objectif: rendre les lanes compatibles avec la continuite de voix.

- [ ] Declarer la politique de conflit Agenda/Biblio final-lock.
- [ ] Tester la priorite ou l'arbitrage final-lock retenu.
- [ ] Couvrir les renderers/agents de lane dans la doctrine de voix visible.
- [ ] Trancher le statut Notes UI: non branche chat courant documente ou
  branchement explicite.
- [ ] Ajouter ou justifier les no-op Documents/Notes quand rien n'est
  selectionne.
- [ ] Verifier que les lanes ne masquent pas l'origine logique du contexte.

Findings traites: `P2-LANES-01`, `P2-FINAL-LOCK-POLICY-01`,
`P2-NOTES-UI-01`, `P3-NOOP-LANES-01`.

### Lot 6 - Spec/tests de Continuity Capsule

Avant runtime reel, prouver la continuite sur donnees artificielles.

- [ ] Ecrire des fixtures sans contenu utilisateur reel.
- [ ] Tester nouvelle conversation vs conversation longue.
- [ ] Tester une conversation apres resume.
- [ ] Tester une conversation sans memoire ou avec lanes non selectionnees.
- [ ] Prouver que la capsule reste distincte d'identity, memory et summary.
- [ ] Prouver que la presence qualitative peut etre jugee sans provider live
  obligatoire.
- [ ] Prouver que les logs et artefacts restent content-free.

Findings traites: `P1-CONT-01`, `P3-TEST-01`, `P3-OBS-01`.

### Lot 7 - Runtime capsule borne

Seulement si Lots 1-6 OK.

- [ ] Injecter eventuellement une capsule courte, versionnee et bornee.
- [ ] Rendre l'injection desactivable par flag ou settings clairement
  rollbackables.
- [ ] Observer la capsule content-free: version, presence, longueur, hash
  court, provenance, raw flags a false.
- [ ] Garder la capsule non souveraine: le tour courant, les preuves injectees
  et les guards produit priment.
- [ ] Ne jamais melanger capsule et identity mutable sans decision doctrinale
  explicite.
- [ ] Tester rollback simple et absence de fuite.

### Lot Z - Cloture

- [ ] Relire audits, spec, TODO, code et tests.
- [ ] Verifier que tous les findings sont clos ou explicitement reportes
  post-V1 avec raison.
- [ ] Verifier qu'aucune case ouverte ne reste dans l'archive finale.
- [ ] Rejouer scans anti-fuite sur docs, artefacts, diff et logs bornes.
- [ ] Verifier que les preuves content-free existent et sont retrouvables.
- [ ] Verifier que les tests structuraux et qualitatifs artificiels passent.
- [ ] Mettre a jour docs/spec/index avant archivage.
- [ ] Archiver cette TODO seulement quand tout est clos ou reporte
  explicitement.

## No-go globaux

- Pas de capsule runtime avant `main_payload_manifest_v1`.
- Pas de prompt brut.
- Pas de dialogue brut.
- Pas de document, note, passage Biblio, export, image, bytes, base64 ou data
  URL brut.
- Pas de secret, token, cookie, valeur d'en-tete d'autorisation, mot de passe
  applicatif ou URL DAV sensible.
- Pas de provider live pour "voir" le payload.
- Pas de capture ou commit de payload provider.
- Pas de backfill historique implicite.
- Pas de reset, purge, migration ou modification DB dans ce chantier sans lot
  separe et GO explicite.
- Pas de melange identity mutable / continuity capsule sans decision
  doctrinale.
- Pas de test qualitatif fonde sur contenu utilisateur reel.
- Pas de correction opportuniste de Biblio, Agenda, Notes ou Web hors lot
  dedie.

## Critères de clôture Lot Z

Lot Z ne peut cloturer que si:

- tous les findings ont un statut clos ou explicitement reporte post-V1;
- aucune case ouverte ne reste dans l'archive finale;
- les preuves content-free du payload final existent;
- les tests structuraux et qualitatifs artificiels passent;
- les docs, specs, index et roadmap sont coherents;
- le no-go capsule avant manifeste a ete respecte pendant tout le chantier;
- aucune fuite de contenu brut ou secret n'a ete introduite;
- les limites restantes sont ecrites en francais simple et visibles depuis les
  index actifs.

## Traçabilité Lot 0

Patch Lot 0 attendu:

- creation de ce fichier;
- mise a jour des index actifs si necessaire;
- aucune modification runtime;
- aucun test executable lourd;
- aucun provider live;
- aucune capture de payload brut.

Apres ce patch, les lots suivants doivent repartir de cette TODO et ne pas
rouvrir directement les audits comme checklist de travail.

Patch Lot 1 livre:

- contrat source-of-truth cree dans
  `app/docs/states/specs/frida-v1-continuity-payload-contract.md`;
- `main_payload_manifest_v1` defini avant Continuity Capsule;
- no-go runtime capsule avant manifeste livre et teste grave;
- aucun finding marque clos;
- aucune modification runtime.
