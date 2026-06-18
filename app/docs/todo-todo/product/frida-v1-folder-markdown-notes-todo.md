# Frida V1 - Notes Markdown par dossier - TODO

Statut: TODO detaillee, Lot 8 observabilite / smokes live Notes livre, Lot Z
non ouvert.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Sources de verite

- Socle dossiers Nextcloud V1 clos:
  `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- Documents V1 clos:
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- Archive Documents V1:
  `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
- Audit Lot 0 Notes V1:
  `app/docs/states/audits/frida-v1-folder-markdown-notes-lot0-audit-2026-06-18.md`
- Contrat Notes V1:
  `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- Preuve live Lot 3:
  `app/docs/states/baselines/notes-smokes/frida-v1-notes-lot3-create-live-20260618T095734Z.jsonl`
- Preuve live Lot 8:
  `app/docs/states/baselines/notes-smokes/frida-v1-notes-lot8-observability-smokes-20260618T125408Z.jsonl`
- Clarification de portee preuve Lot 8.1:
  `app/docs/states/baselines/notes-smokes/frida-v1-notes-lot8-1-proof-scope-20260618T131304Z.jsonl`

## Objectif produit

Permettre a Frida de creer, lister, retrouver, lire et completer des notes
Markdown rattachees a un dossier Frida, avec stockage Nextcloud sous:

```text
/Frida/<dossier>/Notes
```

Le dossier Frida visible dans l'UI reste le centre produit. Une note V1
appartient a un `workspace_folder`; elle n'est ni un document source, ni un
export, ni une image, ni une entree Biblio.

## Decisions produit deja prises

- Le chantier Notes vient apres la cloture du socle Nextcloud folders V1 et
  apres la cloture Documents V1.
- Une note Frida V1 appartient a un dossier Frida `workspace_folder`.
- Une note Markdown est stockee comme fichier `.md` sous
  `/Frida/<dossier>/Notes`.
- Seuls les dossiers Frida `linked` peuvent creer, modifier, retrouver, lire ou
  lister des notes dans Nextcloud.
- Les etats `local_only`, `sync_pending`, `sync_error`, `conflict` et `deleted`
  bloquent les ecritures Notes; les lectures/lists Nextcloud sont egalement
  refusees si l'etat ne permet pas une preuve saine.
- Le sous-dossier standard `Notes` doit exister et etre une collection WebDAV
  valide; un `PROPFIND 207` seul ne suffit pas.
- Les titres ou noms de notes peuvent etre visibles dans l'interface utilisateur
  et dans les reponses utilisateur quand cela aide le travail.
- Le corps Markdown est autorise dans la reponse utilisateur quand l'utilisateur
  demande explicitement de lire ou completer une note.
- Le corps Markdown, les noms sensibles, chemins DAV, URL DAV, XML, payload
  WebDAV, secrets, tokens, cookies et app-password sont interdits dans les logs,
  JSONL, dashboard, observabilite technique et preuves.
- Notes ne rouvre pas Documents, Exports, Images, Biblio, Agenda, Mail,
  Memory/RAG/Identity/Summary, TTS ou SMS.
- Notes n'utilise pas `/Frida/<dossier>/Documents`.
- Notes ne produit pas d'export Markdown/TXT/DOCX/PDF; les exports appartiennent
  au chantier Exports.
- Notes V1 n'est pas un editeur Markdown complet.
- Notes V1 a un modele local dedie Notes, strictement rattache a
  `workspace_folders.id`.
- La table applicative `workspace_folder_notes` est obligatoire pour Notes V1.
- Le modele local Notes n'est pas `workspace_files`; `workspace_files` reste le
  registre/read-model Documents V1.
- Le modele local Notes sert au read-model utilisateur, aux refs content-free,
  aux statuts, aux liens Nextcloud et a la resolution par titre/liste.
- Absence de modele local Notes dedie = no-go pour les lots runtime.
- Absence de table `workspace_folder_notes` = no-go Lot 2 et no-go runtime.
- Notes V1 ne stocke pas le corps Markdown en local.
- Le modele local Notes stocke uniquement metadonnees, statuts, refs
  content-free, titre utilisateur lorsque utile a l'UI, cible interne, ETag
  exact interne, hash/ref technique, timestamps et reason codes.
- Le corps Markdown est lu depuis Nextcloud a la demande, garde seulement en
  memoire pour le tour utile ou pour construire un append, puis non persiste
  localement.
- L'append V1 fait `GET` borne + ETag + construction en memoire + `PUT
  If-Match`.
- Un cache local du corps Markdown releve d'un chantier post-V1 separe.
- La recherche plein texte riche dans le corps Markdown n'est pas livree en V1.
  V1 couvre le titre connu, la liste du dossier et une resolution par
  metadonnees via le read-model local Notes dedie.
- Completer une note signifie append uniquement a la fin de la note existante.
  V1 ne fait ni insertion au milieu, ni reecriture globale, ni remplacement
  complet, ni append sans cible claire.
- Le format d'append V1 est un bloc Markdown ajoute apres un separateur
  `\n\n---\n\n`; il n'y a pas d'horodatage automatique.
- Si l'utilisateur demande une edition fine au milieu du texte, V1 refuse
  proprement ou propose de creer un nouvel ajout a la fin.
- Les modifications de note utilisent une garde de concurrence de type ETag /
  `If-Match` ou mecanisme equivalent avant ecriture; un conflit de version est
  un refus content-free.
- La lecture conversationnelle d'une note est explicite: une note lue ou
  completee ne part pas en Memory/RAG/Identity/Summary par confusion. Depuis
  Lot 7, `/api/chat` injecte une note dans le prompt du tour courant seulement
  si la requete porte explicitement `workspace_note_id` ou `workspace_note_ids`.
- La lecture est entiere ou refusee proprement; pas de troncature silencieuse
  vendue comme lecture complete.
- Limite V1 initiale pour lecture/preparation conversationnelle: 120_000
  caracteres Markdown maximum par note; au-dela, refus propre.
- Limite V1 initiale pour append entrant: 20_000 caracteres Markdown maximum;
  au-dela, refus propre.
- Ces limites sont gravees dans le contrat Lot 1 comme constantes V1.

## Questions produit ouvertes avant lots applicatifs

Aucune decision produit bloquante connue a ce stade.

Aucun lot applicatif Notes V1 ne doit demarrer si une nouvelle question produit
apparait. Dans ce cas, le lot s'arrete avant patch et ajoute explicitement la
reponse a cette section ou a la spec Notes V1.

Blocage technique attendu, non produit: si un lot runtime exige une migration DB
applicative, il doit s'arreter avant application et proposer un micro-lot avec
backup, rollback, tests et preuve content-free.

## Frontieres produit

### Notes vs Documents

- Documents V1 gere les documents sources et fichiers persistants sous
  `/Frida/<dossier>/Documents`.
- Notes V1 gere uniquement des fichiers Markdown notes sous
  `/Frida/<dossier>/Notes`.
- Une note peut citer un document dans une reponse utilisateur, mais ne devient
  pas un `workspace_file` Documents par commodite.

### Notes vs Exports

- Une note est un objet de travail vivant.
- Un export est un artefact produit par le chantier Exports sous
  `/Frida/<dossier>/Exports`.
- Notes V1 ne genere pas DOCX, PDF, TXT ou export final.

### Notes vs Images

- Notes V1 ne stocke pas d'images generees.
- Les references Markdown vers des images ne sont pas une livraison V1 tant
  qu'un contrat Images ne les cadre pas.

### Notes vs Biblio / Memory / RAG

- Notes V1 ne cree pas de Biblio parallele.
- La lecture d'une note dans une conversation ne nourrit pas Memory, RAG global,
  Identity ou Summary.

## Comportements cibles V1

### Creer une note

- L'utilisateur demande la creation dans le dossier Frida courant ou dans un
  dossier cible resolu sans ambiguite.
- Le dossier doit etre `linked` et le sous-dossier `Notes` doit etre une
  collection valide.
- Le titre utilisateur est normalise puis sanitise; la cible est
  `<titre_sanitise>.md`.
- Titre absent, vide ou ambigu: pas de creation silencieuse; clarification
  utilisateur ou refus propre.
- Collision locale ou Nextcloud: conflit explicite, pas d'ecrasement, pas de
  renommage automatique.
- Creation Nextcloud-first.
- Persistance du modele local Notes apres succes Nextcloud.
- Si Nextcloud reussit puis la persistance locale echoue, rollback strict de la
  note creee par ce flux uniquement; si rollback echoue, etat content-free
  explicite.

### Lister les notes

- Liste utilisateur par dossier Frida.
- Les titres/noms sont visibles cote utilisateur.
- Les notes supprimees/tombstonees sont exclues.
- Observabilite technique: compteurs, refs/hashes courts, statuts et reason
  codes seulement.
- Pas de corps Markdown dans les logs, preuves ou dashboard technique.

### Retrouver une note

- Resolution V1 par titre connu, par selection dans la liste du dossier ou par
  metadonnees/read-model local Notes.
- Pas de promesse de recherche plein texte riche dans le corps Markdown.
- Cible ambigue: refus propre ou demande de clarification, pas de choix
  automatique.

### Completer une note

- Completer signifie ajouter un bloc Markdown a la fin de la note.
- Le bloc append est ajoute apres le separateur Markdown `\n\n---\n\n`.
- Il n'y a pas d'insertion au milieu, pas de reecriture globale et pas de
  remplacement complet en V1.
- La note cible doit etre resolue clairement.
- La version distante doit etre verifiee avant ecriture avec ETag / `If-Match`
  ou mecanisme equivalent.
- Version obsolete, cible disparue ou cible non-collection: refus content-free.
- Edition fine au milieu du texte demandee par l'utilisateur: refus propre ou
  proposition d'un nouvel ajout a la fin.

### Lire / preparer une note pour conversation

- Lecture seulement sur demande explicite utilisateur.
- Contenu injectable au modele dans le tour utile si la taille est dans les
  limites V1.
- Limite initiale: 120_000 caracteres Markdown maximum par note lue/preparee.
- Trop volumineux: refus propre, pas de troncature silencieuse.
- Aucun contenu Markdown brut dans observabilite technique, JSONL, logs ou meta
  technique.

## Reason codes attendus

Catalogue initial stabilise par le contrat Lot 1, sans contenu utilisateur:

- `folder_note_folder_not_linked`
- `folder_note_notes_target_missing`
- `folder_note_notes_target_not_collection`
- `folder_note_notes_target_unavailable`
- `folder_note_name_invalid`
- `folder_note_name_conflict`
- `folder_note_create_ok`
- `folder_note_append_ok`
- `folder_note_read_ok`
- `folder_note_list_ok`
- `folder_note_lookup_ok`
- `folder_note_lookup_ambiguous`
- `folder_note_lookup_failed`
- `folder_note_not_found`
- `folder_note_too_large`
- `folder_note_version_conflict`
- `folder_note_local_persistence_failed`
- `folder_note_remote_compensation_ok`
- `folder_note_remote_compensation_failed`
- `folder_note_nextcloud_error_redacted`

## Lots

### Lot 0 - Audit existant

- [x] Relire les surfaces `workspace_folders`, Nextcloud folders, sous-dossiers
  standards, Documents V1, UI dossier et tests existants.
- [x] Identifier les briques reutilisables telles quelles: sanitisation,
  WebDAV borne, verification collection, rollback, observabilite content-free.
- [x] Identifier les briques a eviter pour Notes: `workspace_files` comme modele
  produit, OCR Documents, Biblio, Exports, Images.
- [x] Cartographier les routes existantes pouvant porter Notes sans route
  parallele inutile.
- [x] Produire un audit content-free sous `app/docs/states/audits/`.
- [x] Ne livrer aucun runtime.

### Lot 1 - Contrat produit Notes V1

- [x] Creer `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
  comme source-of-truth Notes V1 avant tout runtime.
- [x] Reporter dans la spec le modele produit Note, les surfaces utilisateur, les
  limites deja decidees, les reason codes, les invariants de securite et les
  criteres Lot Z.
- [x] Acter le modele local dedie Notes comme precondition runtime obligatoire,
  rattache a `workspace_folders.id` et distinct de `workspace_files`.
- [x] Acter que Notes V1 ne stocke pas le corps Markdown localement et que tout
  cache local de corps est post-V1.
- [x] Acter les limites initiales: 120_000 caracteres Markdown pour
  lecture/preparation, 20_000 caracteres Markdown pour append entrant.
- [x] Acter que la recherche plein texte riche est hors V1.
- [x] Acter que les titres peuvent etre user-facing mais redacted/hashes dans
  les preuves techniques.
- [x] Acter que completer une note = append fin uniquement avec separateur
  Markdown `\n\n---\n\n`, sans insertion ni reecriture globale.
- [x] Acter la garde ETag / `If-Match` pour toute modification.
- [x] Ne cocher aucun lot runtime.

### Lot 2 - Modele local / read-model Notes

- [x] Livrer le modele local dedie Notes, obligatoire avant tout runtime create,
  list, lookup, append ou read.
- [x] Creer la table applicative obligatoire `workspace_folder_notes`; le store
  Python Notes n'est que l'acces applicatif a cette table.
- [x] Le rattacher strictement a `workspace_folders.id`.
- [x] Garder `workspace_files` reserve a Documents V1; ne pas l'utiliser comme
  modele produit Notes.
- [x] Representer note, dossier, etat de synchronisation, ref content-free et
  version distante sans exposer titre sensible dans les surfaces techniques.
- [x] Porter le read-model utilisateur, les refs content-free, les statuts, les
  liens Nextcloud et la resolution par titre/liste.
- [x] Preparer les statuts et reason codes locaux qui bloquent les futures
  ecritures si le dossier n'est pas `linked` ou si la cible `Notes` est invalide.
- [x] Ajouter tests anti-fuite et tests de statuts.
- [x] Utiliser le pattern applicatif existant `ensure_schema(cur)` et produire
  un backup DB applicative avant application live de la migration.
  Backup OVH Lot 2:
  `/opt/platform/_codex_reports/frida-v1-notes-lot2-db-backup-20260618T093415Z.dump`.

### Lot 3 - Creation de note Markdown

- [x] Creer une note `.md` sous `/Frida/<dossier>/Notes/<titre_sanitise>.md`.
- [x] Utiliser une creation anti-ecrasement.
- [x] Refuser titre absent, invalide, ambigu ou collision de sanitisation.
- [x] Verifier reellement en WebDAV que `Notes` existe et est une collection
  valide par status-only avant creation.
- [x] Persister le modele local Notes dedie.
- [x] Rollback strict de la note creee si la persistance locale echoue apres
  succes Nextcloud.
- [x] Tester success, conflit, dossier non `linked`, cible `Notes` absente ou
  non-collection, rollback et absence de fuite.
- [x] Produire une preuve live synthetique content-free avec cleanup remote et
  cleanup local du read-model synthetique.

### Lot 4 - Liste des notes d'un dossier

- [x] Exposer une liste utilisateur utile pour le dossier Frida selectionne.
- [x] Afficher les titres/noms cote utilisateur.
- [x] Exclure les notes supprimees ou incoherentes.
- [x] Ne pas lister le contenu Markdown comme preuve technique.
- [x] Garder logs/JSONL/observabilite content-free.
- [x] Tester liste vide, notes liees, conflit/sync_error et anti-fuite.
- [x] Servir la liste depuis le read-model local Notes uniquement, sans WebDAV
  live et sans lecture du corps Markdown.
- [x] Fail-closed si la lecture du store Notes echoue: `folder_note_lookup_failed`
  et pas de fausse liste vide.

### Lot 5 - Retrouver une note

- [x] Retrouver par titre exact/sanitise ou selection explicite dans la liste.
- [x] Utiliser le read-model local Notes dedie.
- [x] Refuser cible absente ou ambigue.
- [x] Ne pas promettre de recherche plein texte riche.
- [x] Tester resolution, ambiguite, absence, dossier invalide et anti-fuite.
- [x] Ne pas lire le corps Markdown et ne pas contacter WebDAV/Nextcloud.
- [x] Distinguer note absente, cible ambigue et panne store fail-closed.

### Lot 6 - Completer une note existante

- [x] Ajouter du Markdown uniquement a la fin d'une note existante.
- [x] Utiliser le separateur Markdown V1 `\n\n---\n\n` avant le bloc ajoute.
- [x] Refuser l'insertion au milieu, la reecriture globale et le remplacement
  complet.
- [x] Exiger cible claire.
- [x] Utiliser ETag / `If-Match` ou garde equivalente.
- [x] Refuser conflit de version, cible disparue, cible non resolue ou cible non
  eligible.
- [x] Ne pas ecraser, ne pas renommer automatiquement, ne pas supprimer.
- [x] Tester append nominal, conflit de version, ambiguity, rollback/etat partiel
  si applicable et anti-fuite.
- [x] Tester explicitement le conflit ETag/version en fake/unit.
- [x] Ne pas persister le corps Markdown localement.
- [x] Tenter une compensation distante stricte si la persistance locale echoue
  apres PUT; sinon remonter un etat content-free, jamais un succes silencieux.
- [x] En cas de PUT reussi sans ETag post-ecriture, ne jamais retourner de
  succes, tenter une compensation prouvable par relecture bornee + `If-Match`,
  uniquement si le Markdown relu correspond au Markdown appendu attendu, et
  marquer le read-model local `sync_error` si la compensation est impossible.

### Lot 7 - Lecture / preparation conversationnelle de note

- [x] Lire une note seulement apres demande explicite utilisateur.
- [x] Injecter le corps Markdown uniquement dans le tour utile et seulement si la
  taille respecte les limites V1.
- [x] Appliquer la limite initiale de 120_000 caracteres Markdown maximum.
- [x] Appliquer le budget prompt Notes V1: une seule note injectee par tour,
  120_000 caracteres Markdown maximum au total, refus content-free
  `folder_note_turn_limit_exceeded` avant lecture distante pour les notes
  demandees hors limite.
- [x] Refuser proprement une note trop grande.
- [x] Ne pas alimenter Memory/RAG/Identity/Summary.
- [x] Ne pas logguer le corps Markdown brut.
- [x] Tester lecture entiere, refus taille, note absente, note conflictuelle et
  absence de fuite.
- [x] Servir la preparation par route namespaced
  `POST /api/workspace-folders/<folder_id>/notes/<note_id>/prepare`, sans route
  globale `/api/notes*`.
- [x] Brancher la preparation conversationnelle reelle dans `/api/chat` via
  `workspace_note_id` / `workspace_note_ids`, sans selection durable ni route
  globale.
- [x] Garder le corps Markdown uniquement dans `note_conversation` pour le tour
  courant ou dans la lane Notes du prompt du tour; projections techniques, logs
  et `note_nextcloud` restent content-free.
- [x] Signaler explicitement les notes demandees mais non injectees, sans
  troncature silencieuse ni coupure invisible au-dela de la limite.
- [ ] Dette hygiene: `workspace_folder_notes_prompt_lane.py` reste au-dessus de
  500 lignes apres ce micro-correctif; extraire une responsabilite claire avant
  tout elargissement de la lane Notes.

### Lot 8 - Observabilite / smokes live

- [x] Produire des events/read-model techniques content-free pour create, list,
  lookup, append, read et conflicts.
- [x] Produire un JSONL live content-free avec notes synthetiques uniquement.
- [x] Prouver creation, collision, list, lookup, append, read et cleanup
  synthetiques.
- [x] Prouver l'injection `/api/chat` via `workspace_note_id` dans la meme lane
  applicative que la route, avec provider fake et observabilite content-free.
- [x] Clarifier que la preuve runtime Lot 8 exprime un statut secret redacted et
  aucune valeur affichee; le champ historique `secret_available=false` ne doit
  pas etre lu comme preuve d'absence du secret runtime.
- [x] Clarifier que la preuve d'injection chat Lot 8 prouve la lane applicative
  `/api/chat` avec provider fake, pas une generation modele/provider live.
- [x] Tenter un smoke synthetique de conflit ETag/version si possible sans
  toucher de contenu utilisateur; sinon marquer le cas `not_applicable` /
  `covered_by_unit_tests`, jamais `met`. Lot 8 marque ce cas
  `not_applicable` / `covered_by_unit_tests`.
- [x] Scanner logs/preuves contre corps Markdown, noms sensibles, DAV/XML,
  payload WebDAV et secrets.
- [x] Ne toucher aucun contenu utilisateur reel.

### Lot Z - Cloture Notes V1

- [ ] Rejouer les smokes transverses Notes V1.
- [ ] Utiliser des champs non ambigus pour la preuve runtime, par exemple
  `secret_configured_status=redacted` et `secret_value_displayed=false`, jamais
  `secret_available=false`.
- [ ] Distinguer preuve de lane applicative `/api/chat` et preuve de generation
  modele live; ne presenter une generation provider live comme prouvee que si
  Lot Z l'execute explicitement.
- [ ] Inclure le conflit ETag/version dans Lot Z; si le live n'est pas possible
  proprement, documenter `not_applicable` / `covered_by_unit_tests` sans le
  vendre comme preuve live complete.
- [ ] Verifier que Notes ne livre pas Exports, Images, Documents, Biblio,
  Agenda, Mail ou Memory/RAG.
- [ ] Documenter les limites V1 restantes.
- [ ] Archiver cette TODO seulement si les criteres V1 sont prouves.

## Points faibles a surveiller

- Confusion Note vs Document source.
- Confusion Note vs Export.
- Creation dans `/Documents` ou un mauvais sous-dossier.
- Ecrasement d'une note existante.
- Append sans cible claire.
- Conflit concurrent / ETag ignore.
- Fuite du corps Markdown dans observabilite, logs, JSONL ou dashboard.
- Logs contenant titre sensible ou corps brut.
- Route parallele inutile contournant `workspace_folders`.
- Reutilisation dangereuse de `workspace_files` qui brouille Documents et Notes.
- Suppression implicite ou rangement silencieux de notes historiques.
- Promesse de recherche plein texte non livree.
- Mutation Nextcloud sans rollback/compensation.
- Choix produit cache dans un lot applicatif.

## Hors-scope V1

- Editeur Markdown complet.
- Collaboration multi-utilisateur ou temps reel.
- Recherche plein texte riche dans les corps Markdown.
- Exports DOCX/PDF/TXT.
- Documents sources.
- Images generees.
- Biblio / Catalogue.
- Agenda, Mail, TTS, SMS.
- Memory/RAG/Identity/Summary.
- Migration/copie de notes historiques sans lot dedie.
- Listing de contenu Nextcloud comme preuve technique.

## Preuves attendues

- Tests unitaires/fake pour chaque lot runtime.
- Tests serveur si une route existante est etendue.
- Tests frontend si l'UI expose liste, creation ou selection.
- Smokes live uniquement sur notes synthetiques.
- JSONL content-free sous `app/docs/states/baselines/`.
- Scans anti-fuite: aucun corps Markdown brut, nom sensible, chemin DAV, URL
  DAV, XML, payload WebDAV, secret, token, cookie ou app-password.

## Prochain pas

Ouvrir Lot Z - Cloture Notes V1. Ce lot devra rejouer/relire les preuves
transverses, documenter la limite ETag live `not_applicable` /
`covered_by_unit_tests`, verifier l'absence de fuite et ne pas rouvrir les
chantiers Documents, Exports, Images, Biblio, Agenda, Mail ou Memory/RAG.
