# Frida V1 - Exports / creation documentaire - TODO

Statut: TODO Lot 3 livre, generation Markdown/TXT fake-local ouverte pour les
lots runtime suivants.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Sources de verite

- Roadmap finale Frida 1.0:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- Contrat source-of-truth Exports V1:
  `app/docs/states/specs/frida-v1-exports-contract.md`
- Socle dossiers Nextcloud V1 clos:
  `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- Archive socle dossiers Nextcloud V1:
  `app/docs/todo-done/product/frida-v1-nextcloud-folders-todo.md`
- Documents V1 clos:
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- Archive Documents V1:
  `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
- Notes Markdown V1 closes:
  `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- Archive Notes Markdown V1:
  `app/docs/todo-done/product/frida-v1-folder-markdown-notes-todo.md`
- Spec du bouton actuel de copie/export Markdown navigateur:
  `app/docs/states/specs/chat-copy-export-contract.md`

## Surfaces existantes a auditer sans les confondre avec Exports V1

- Export Markdown conversationnel navigateur:
  - spec `app/docs/states/specs/chat-copy-export-contract.md`;
  - `app/web/chat_copy_export.js`;
  - `app/web/app.js`, bouton `btnExportConversation`;
  - tests `app/tests/unit/frontend_chat/test_chat_copy_export_module.js` et
    `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`.
- Export Markdown technique de logs admin:
  - route `GET /api/admin/logs/chat/export.md` dans `app/server.py`;
  - `app/observability/log_markdown_export.py`;
  - UI `app/web/log.html` / `app/web/log/log.js`;
  - tests `app/tests/unit/logs/test_log_markdown_export_phase6.py` et
    `app/tests/integration/frontend_admin/test_frontend_logs_phase5.py`.

Ces surfaces sont utiles pour l'audit Lot 0 et pour reutiliser des patterns de
format Markdown ou de telechargement. Elles ne livrent pas Exports V1: elles ne
rattachent pas un export a un `workspace_folder`, ne stockent pas sous
`/Frida/<dossier>/Exports`, ne persistent pas un read-model export et ne
produisent pas DOCX/PDF.

Le bouton navigateur actuel reste une capacite locale et humaine: il relit la
conversation, produit un Markdown lisible, exclut les metadonnees techniques et
declenche un telechargement navigateur. Il ne cree ni export durable, ni lien
Nextcloud, ni observabilite produit. Exports V1 ne doit pas le remplacer ou le
detourner sans decision explicite ulterieure.

L'export Markdown admin des logs est une surface technique d'operateur. Il peut
inspirer uniquement des patterns tres limites, par exemple reponse HTTP,
attachement Markdown ou structure de test. Exports V1 utilisateur ne doit pas
reutiliser son contenu, son read-model, ses IDs, ses payloads compactes, son
scope conversation/turn technique ou son format de logs comme base produit.

## Objectif produit Exports V1

Permettre a Frida de produire, ranger, retrouver et reutiliser des exports
documentaires rattaches a un dossier Frida.

Formats V1 cibles:

- Markdown `.md`;
- texte brut `.txt`;
- DOCX `.docx`;
- PDF `.pdf`.

Cible normative:

```text
/Frida/<dossier>/Exports
```

Capacites V1 visees:

- produire un export Markdown;
- produire un export TXT;
- produire un export DOCX;
- produire un export PDF;
- ranger automatiquement l'export cree sous le sous-dossier standard `Exports`;
- lier l'export au `workspace_folder` source;
- lister/retrouver un export deja produit;
- reutiliser un export existant par action utilisateur explicite:
  retrouver/lister, telecharger/ouvrir, ou utiliser comme source d'un nouvel
  export, sans le confondre avec Documents ou Notes.

## Frontieres produit

### Exports vs Documents

- Documents V1 gere les documents sources et fichiers persistants sous
  `/Frida/<dossier>/Documents`.
- Un export est un artefact produit par Frida a partir d'une source choisie.
- Un export range dans `Exports` ne devient pas automatiquement un document
  source Documents V1.
- Exports V1 ne doit pas rouvrir l'ingestion, la lecture ou le fallback PDF des
  documents sources.

### Exports vs Notes

- Notes V1 gere les notes Markdown vivantes sous `/Frida/<dossier>/Notes`.
- Un export Markdown n'est pas une note vivante et ne doit pas etre modifie par
  les routes Notes.
- Exports V1 ne doit pas utiliser `workspace_folder_notes` comme read-model.

### Exports vs Images

- Images V1 gerera les images generees sous `/Frida/<dossier>/Images`.
- Exports V1 ne stocke pas d'image generee comme objet produit.
- Un PDF exporte peut contenir une mise en page ou des images, mais cela ne
  livre pas le chantier Images.

### Exports vs Biblio / Agenda / Mail / Memory

Exports V1 ne livre pas:

- Biblio ou Catalogue;
- Agenda;
- Mail;
- Memory/RAG global;
- Identity;
- Summary;
- TTS/SMS.

Un export produit peut etre mentionne ou reutilise sur demande explicite, mais
il ne nourrit pas Memory/RAG/Identity/Summary par confusion.

### Exports vs exports admin/logs

L'export Markdown des logs admin est une surface technique d'operateur. Elle
reste separee d'Exports V1. Exports V1 est une capacite produit rattachee a un
dossier Frida et rangee sous `Exports`.

### Exports vs simple telechargement navigateur

Le bouton actuel "Exporter la conversation en Markdown" genere un fichier local
dans le navigateur. Exports V1 doit produire un artefact durable rattache au
dossier Frida et range dans Nextcloud. Un telechargement navigateur sans
stockage Nextcloud ne suffit pas a livrer Exports V1.

## Decisions produit deja prises

- Exports V1 vient apres la cloture du socle Nextcloud folders V1, Documents V1
  et Notes Markdown V1.
- Un export V1 appartient a un `workspace_folder`.
- Le dossier Frida visible dans l'UI reste le centre produit.
- Seuls les dossiers Frida `linked` sont eligibles pour creer, ranger,
  retrouver ou reutiliser un export dans Nextcloud.
- Les etats `local_only`, `sync_pending`, `sync_error`, `conflict` et `deleted`
  bloquent les ecritures Exports.
- La cible normative est `/Frida/<dossier>/Exports`.
- Le sous-dossier standard `Exports` doit exister et etre une collection WebDAV
  valide; un `PROPFIND 207` seul ne suffit pas.
- FridaDev ne doit jamais acceder directement a la DB Nextcloud.
- Pas d'overwrite silencieux.
- Pas de suppression automatique d'exports existants.
- Les titres/noms d'exports peuvent etre visibles cote utilisateur quand c'est
  necessaire au travail.
- Les noms sensibles, le contenu exporte, les chemins DAV, URL DAV, XML,
  payload WebDAV, secrets, tokens, cookies et app-password sont interdits dans
  logs, JSONL, dashboard, observabilite technique et preuves.
- Les preuves techniques doivent utiliser compteurs, refs content-free, hashes
  courts, statuts et reason codes.
- Le chantier Exports ne rouvre pas Documents, Notes, Images, Biblio, Agenda,
  Mail ou Memory/RAG/Identity/Summary.

## Decisions produit fermees par Lot 1

Les decisions produit bloquantes sont gravees dans
`app/docs/states/specs/frida-v1-exports-contract.md`.

Decisions fermees:

- Sources exportables V1:
  - conversation complete explicitement demandee;
  - selection explicite de messages;
  - reponse de Frida explicitement choisie;
  - note Markdown existante Notes V1;
  - document prepare ou lu par Documents V1, seulement si la lecture Documents
    V1 est deja disponible proprement.
- Acquisition des sources:
  - conversation complete depuis le store conversationnel deja utilise par le
    chat/export navigateur, sur action explicite, sans messages
    systeme/outils/techniques;
  - selection de messages limitee aux messages explicitement selectionnes, en
    ordre stable;
  - reponse Frida uniquement si elle est explicitement designee;
  - note Markdown via les capacites Notes V1 explicites, entiere ou refus, sans
    stockage local durable du corps par Exports et sans append/modification;
  - document uniquement si Documents V1 fournit une lecture/preparation
    complete, sans relance ingestion, OCR ou fallback visuel par Exports;
  - export existant comme source seulement par action explicite, lecture bornee
    complete ou refus, sans injection chat automatique.
- Sources refusees V1:
  - Biblio/Catalogue;
  - Agenda;
  - Mail;
  - images generees comme objet produit;
  - Memory/RAG/Identity/Summary;
  - source ambigue ou implicite;
  - export admin logs.
- Formats V1:
  - Markdown `.md`;
  - texte brut `.txt`;
  - DOCX `.docx`;
  - PDF `.pdf`.
- Fidelite V1:
  - structure simple et honnete;
  - titres, paragraphes et listes basiques si disponibles;
  - pas de mise en page avancee vendue comme livree;
  - refus clair si DOCX/PDF ne peut pas etre genere proprement.
- Limites V1 initiales:
  - contenu source normalise: `120_000` caracteres maximum;
  - artefact genere: `25 MiB` maximum;
  - generation: `180` secondes maximum;
  - PDF genere: `100` pages maximum si le moteur expose un comptage fiable;
  - si une limite ne peut pas etre verifiee proprement, refus;
  - contenu complet ou refus, sans troncature silencieuse.
- Read-model local:
  - table applicative dediee obligatoire `workspace_folder_exports`;
  - rattachement strict a `workspace_folders.id`;
  - distinct de `workspace_files` et `workspace_folder_notes`;
  - metadonnees, refs, hashes, statuts, ETag interne et reason codes;
  - pas de contenu exporte brut stocke localement en V1.
- Surfaces:
  - routes futures sous `/api/workspace-folders/<folder_id>/exports*`;
  - pas de route globale `/api/exports*`;
  - UI minimale sous contexte chat/dossier, sans remplacer le bouton navigateur
    Markdown actuel.
- Nommage:
  - titre utilisateur explicite autorise;
  - sinon nom derive du type source et d'un timestamp UTC;
  - sanitisation obligatoire;
  - extension determinee par le format.
- Collision/versioning:
  - no overwrite;
  - pas de renommage automatique silencieux;
  - collision = refus content-free;
  - versioning automatique hors V1.
- Reutiliser un export existant:
  - retrouver/lister;
  - telecharger/ouvrir;
  - utiliser explicitement comme source d'un nouvel export.
- Reutiliser ne signifie pas:
  - injection automatique dans le chat;
  - lecture implicite;
  - alimentation Memory/RAG/Identity/Summary;
  - conversion implicite;
  - duplication sans action utilisateur explicite.

Si une decision nouvelle apparait pendant un lot, le lot s'arrete avant tout
patch qui figerait ou inventerait cette decision, y compris docs/spec, avant
commit et avant de cocher un lot. Il demande explicitement et ne choisit pas en
avancant.

## Garde-fous runtime graves par la spec Lot 1

- Dossier non `linked` = refus content-free.
- Dossier `deleted` = refus content-free.
- Sous-dossier `Exports` absent, non-collection ou inaccessible = refus
  content-free.
- Collision de nom, sanitisation ou version = conflit explicite.
- Pas d'overwrite.
- Pas de renommage automatique non decide.
- Pas de suppression automatique.
- Pas de contenu exporte dans logs, JSONL, observabilite technique ou preuves.
- Pas de nom sensible brut dans logs, JSONL, observabilite technique ou preuves.
- Pas de chemin DAV, URL DAV, XML ou payload WebDAV brut.
- Pas de secret, token, cookie ou app-password.
- Pas de DB Nextcloud directe.
- Pas de listing Nextcloud large comme preuve.
- Pas de route globale qui contourne `workspace_folders`.
- Pas de reutilisation de `workspace_files` ou `workspace_folder_notes` si cela
  brouille Documents ou Notes.
- Pas de promotion automatique en Memory/RAG/Identity/Summary.
- Pas de reouverture Documents/Notes/Images par confusion.
- Pas de lecture, injection, conversion ou duplication d'un export existant
  sans action utilisateur explicite et sans le sens de reutilisation defini par
  la spec Exports V1.
- Pas d'invention d'une lane de lecture parallele pour Notes ou Documents.
- Pas de lecture de contenu simplement parce qu'un objet est liste ou retrouve.
- Si l'acquisition complete de la source n'est pas disponible proprement,
  l'export est refuse avec reason code content-free.

## Lots proposes

Les lots coches refletent l'etat livre. Pour les prochains lots, ne cocher que
le lot execute et prouve. Chaque lot doit rester borne, testable et reversible.

### Lot 0 - Audit existant exports

- [x] Auditer `app/docs/states/specs/chat-copy-export-contract.md`.
- [x] Auditer les exports conversationnels Markdown existants cote navigateur.
- [x] Auditer l'export Markdown technique des logs admin.
- [x] Auditer les routes, helpers, tests frontend/backend et dependances
  disponibles autour de Markdown, TXT, DOCX et PDF.
- [x] Identifier les patterns reutilisables et leurs limites.
- [x] Identifier les briques a adapter.
- [x] Identifier les briques a eviter pour ne pas confondre Exports V1 avec
  logs admin, Documents, Notes ou simple telechargement navigateur.
- [x] Verifier explicitement que l'export admin logs ne sert pas de modele
  produit, hors patterns limites de reponse HTTP, attachement Markdown ou tests.
- [x] Produire un audit content-free sous `app/docs/states/audits/`.
- [x] Ne livrer aucun runtime.

### Lot 1 - Contrat source-of-truth Exports V1

- [x] Creer `app/docs/states/specs/frida-v1-exports-contract.md`.
- [x] Fermer toutes les decisions ouvertes avant runtime.
- [x] Si une decision produit humaine manque, s'arreter avant d'ecrire ou
  committer la spec, avant de cocher Lot 1, et demander explicitement; Lot 1
  documente les choix deja tranches, mais ne ferme jamais une decision en
  l'inventant.
- [x] Definir le modele produit Export V1.
- [x] Definir les sources exportables V1.
- [x] Definir les formats, limites, messages utilisateur et reason codes.
- [x] Definir le modele local/read-model attendu.
- [x] Definir les routes/API et surfaces UI autorisees.
- [x] Definir la politique de nommage, collision et versioning.
- [x] Definir la politique de generation DOCX/PDF et les dependances.
- [x] Definir les criteres Lot Z.
- [x] Ne livrer aucun runtime.

### Lot 2 - Modele local / read-model exports

- [x] Livrer le modele local exports decide par la spec Lot 1:
  `workspace_folder_exports`.
- [x] Rattacher strictement l'export a `workspace_folders.id`.
- [x] Representer le format, la source, le statut local, le statut Nextcloud,
  refs content-free, hashes, timestamps et reason codes.
- [x] Ne pas stocker de contenu exporte brut localement en V1.
- [x] Produire projections utilisateur et technique content-free.
- [x] Tester conflits locaux, statuts, tombstone si applicable et anti-fuite.
- [x] Ne pas contacter Nextcloud/WebDAV live.

Correctif Lot 2.1 livre:

- `export_v1_technical.source_ref` ne recopie plus de valeur brute arbitraire:
  seules les refs content-free structurees de la spec sont autorisees.
- Un export local cree sans preuve distante nait en
  `nextcloud_sync_state=sync_error`, jamais `linked`.
- Le default DB applicatif `workspace_folder_exports.nextcloud_sync_state` est
  `sync_error` pour les nouvelles lignes.

Dette hygiene: `workspace_folder_exports.py` et
`workspace_folder_exports_store.py` restent proches de 500 lignes. Lot 3 doit
creer des modules dedies pour generation/acquisition Markdown/TXT et ne pas
empiler cette logique dans les modules de read-model.

### Lot 3 - Generation Markdown/TXT bornee fake/local

- [x] Generer Markdown depuis les sources definies par la spec Lot 1.
- [x] Generer TXT depuis les sources definies par la spec Lot 1.
- [x] Acquerir les sources fake/local par payload explicite ou capacite injectee,
  sans store conversationnel reel.
- [x] Appliquer les limites de taille V1.
- [x] Refuser proprement au-dela des limites.
- [x] Ne pas tronquer silencieusement.
- [x] Ne pas ranger encore dans Nextcloud.
- [x] Tester conversion, refus taille, noms, reason codes et anti-fuite.

Lot 3 livre `workspace_folder_export_sources.py`,
`workspace_folder_export_markdown_text.py` et
`workspace_folder_export_generation.py`. Les sources Notes/Documents passent
uniquement par des capacites explicites injectees; aucun lecteur parallele et
aucun WebDAV/Nextcloud live n'est appele par defaut. Un export existant comme
source est refuse proprement sans reader fake/local explicite. Les projections
restent metadata-only et `nextcloud_sync_state=sync_error` tant que Lot 5 n'a
pas prouve le rangement distant.

Correctif Lot 3.1 livre:

- le flag source explicite accepte seulement le booleen strict `true`;
  les chaines `"false"`, `"0"` ou arbitraires sont refusees;
- la generation fake/local exige un `workspace_folder_id` UUID valide avant de
  lire une source;
- l'acquisition conversationnelle Lot 3 est requalifiee honnetement: elle lit
  uniquement les messages fournis explicitement par l'appelant; elle ne prouve
  pas encore la relecture depuis le store conversationnel reel.

### Lot 3.2 - Acquisition conversationnelle store avant route/API

- [ ] Brancher une acquisition conversationnelle reelle depuis le store
  conversationnel existant.
- [ ] Exclure les messages systeme/outils/techniques comme le contrat
  `chat-copy-export-contract.md`.
- [ ] Refuser content-free si la conversation ne peut pas etre relue
  completement.
- [ ] Prouver la lecture store par tests sans route publique nouvelle.
- [ ] Ne pas ouvrir DOCX/PDF, Nextcloud/WebDAV ou UI.

### Lot 4 - Generation DOCX/PDF bornee fake/local

- [ ] Verifier les dependances runtime necessaires a DOCX/PDF.
- [ ] Generer DOCX selon le degre de fidelite defini par la spec Lot 1.
- [ ] Generer PDF selon le degre de fidelite defini par la spec Lot 1.
- [ ] Refuser proprement si une dependance manque ou si la taille depasse les
  limites.
- [ ] Ne pas vendre une conversion partielle comme complete.
- [ ] Ne pas ranger encore dans Nextcloud.
- [ ] Tester generation, absence de dependance, refus taille et anti-fuite.

### Lot 5 - Stockage Nextcloud-first sous Exports

- [ ] Verifier que le dossier Frida est `linked`.
- [ ] Verifier `Exports` par `PROPFIND Depth: 0` et confirmation collection.
- [ ] Ecrire l'export par strategie anti-ecrasement.
- [ ] Accepter uniquement une creation sure.
- [ ] Persister le lien/read-model local apres succes distant.
- [ ] Si ecriture distante reussit puis persistance locale echoue, rollback
  strict de la cible creee par ce flux.
- [ ] Refuser conflit distant sans overwrite ni renommage automatique non
  decide.
- [ ] Produire preuve live synthetique content-free avec cleanup.

### Lot 6 - Liste / retrouver / reutiliser un export existant

- [ ] Lister les exports d'un dossier depuis le read-model local.
- [ ] Retrouver un export selon les criteres definis par la spec Lot 1.
- [ ] Implementer uniquement le sens de "reutiliser" defini par la spec Lot 1.
- [ ] Refuser toute lecture, injection, conversion ou duplication non definie
  par la spec Lot 1.
- [ ] Ne pas lire le contenu exporte sans action explicite et sans le sens de
  reutilisation defini par la spec Lot 1.
- [ ] Distinguer absence, ambiguite, conflit et panne store.
- [ ] Tester liste vide, liste avec formats multiples, lookup, ambiguite,
  refus et anti-fuite.

### Lot 7 - Integration UI ou conversationnelle minimale

- [ ] Ajouter la surface utilisateur autorisee par la spec Lot 1.
- [ ] Ne pas remplacer le bouton export Markdown navigateur existant sans
  decision explicite.
- [ ] Si un lot futur ajoute une reutilisation conversationnelle au-dela du
  contrat V1, ouvrir d'abord un micro-contrat; V1 ne livre pas d'injection chat
  automatique d'exports existants.
- [ ] Afficher statuts, conflits et limites sans fuite technique.
- [ ] Tester frontend si UI modifiee.
- [ ] Ne pas ouvrir Documents, Notes ou Images.

### Lot 8 - Observabilite / smokes content-free

- [ ] Consolider events/read-model techniques content-free pour generation,
  stockage, liste, lookup, reutilisation, conflits et cleanup.
- [ ] Produire un JSONL live synthetique sous
  `app/docs/states/baselines/exports-smokes/`.
- [ ] Prouver Markdown, TXT, DOCX et PDF selon les formats livres.
- [ ] Prouver conflit nom/version sans overwrite.
- [ ] Prouver refus dossier non `linked` par tests ou live propre si naturel.
- [ ] Scanner logs/preuves/docs contre contenu exporte, noms sensibles,
  DAV/XML/payload brut et secrets.
- [ ] Ne toucher aucun contenu utilisateur reel.

### Lot Z - Cloture Exports V1

- [ ] Rejouer ou relire les smokes transverses Exports V1.
- [ ] Verifier create/generate/store/list/lookup/reuse pour chaque format livre.
- [ ] Verifier cleanup distant/local des artefacts synthetiques.
- [ ] Documenter les limites V1 restantes.
- [ ] Mettre a jour roadmap generale et index.
- [ ] Archiver cette TODO seulement si les criteres V1 sont prouves.

## Reason codes initiaux stabilises par Lot 1

Catalogue initial content-free:

- `folder_export_folder_not_linked`;
- `folder_export_folder_invalid`;
- `folder_export_exports_target_missing`;
- `folder_export_exports_target_not_collection`;
- `folder_export_exports_target_unavailable`;
- `folder_export_name_invalid`;
- `folder_export_name_conflict`;
- `folder_export_source_missing`;
- `folder_export_source_ambiguous`;
- `folder_export_source_unsupported`;
- `folder_export_source_unavailable`;
- `folder_export_source_not_prepared`;
- `folder_export_source_read_unavailable`;
- `folder_export_source_read_too_large`;
- `folder_export_format_unsupported`;
- `folder_export_dependency_unavailable`;
- `folder_export_too_large`;
- `folder_export_generation_failed_redacted`;
- `folder_export_create_ok`;
- `folder_export_store_ok`;
- `folder_export_list_ok`;
- `folder_export_lookup_ok`;
- `folder_export_lookup_failed`;
- `folder_export_download_ok`;
- `folder_export_reuse_ok`;
- `folder_export_local_persistence_failed`;
- `folder_export_remote_compensation_ok`;
- `folder_export_remote_compensation_failed`;
- `folder_export_nextcloud_error_redacted`.

## Preuves attendues

Par famille:

- tests unitaires pour sanitisation, noms, limites, conversion et projections;
- tests serveur si une route est ajoutee;
- tests frontend si une UI est ajoutee ou modifiee;
- tests fake transport pour Nextcloud-first, conflit, rollback et compensation;
- smokes live uniquement sur exports synthetiques;
- JSONL content-free sous `app/docs/states/baselines/exports-smokes/`;
- cleanup distant/local des exports synthetiques crees pendant les smokes;
- scans anti-fuite sur diff, JSONL, logs et docs.

Interdits dans preuves techniques:

- contenu exporte brut;
- nom sensible brut;
- chemin DAV;
- URL DAV;
- XML brut;
- payload WebDAV brut;
- secret;
- token;
- cookie;
- app-password;
- base64 ou data URL de document genere.

## Hors-scope V1

- Mise en page avancee non decidee.
- Signature ou validation juridique.
- Publication externe.
- Envoi Mail.
- Editeur Markdown.
- Recherche plein texte riche dans les exports.
- Images generees comme objets produit.
- Documents ingestion / lecture / fallback.
- Notes Markdown runtime.
- Biblio / Catalogue.
- Agenda.
- Memory/RAG/Identity/Summary.
- Suppression automatique d'exports utilisateur.
- Migration ou import d'exports historiques sans lot dedie.
- Listing large de contenu Nextcloud comme preuve.

## Hors-scope courant apres Lot 3

- Pas de route serveur.
- Pas de UI.
- Pas de Nextcloud live.
- Pas de nouvelle migration DB hors lot explicitement dedie.
- Pas de generation DOCX/PDF reelle.
- Pas de smoke live.
- Pas d'archivage.
- Pas de Lot Z.
- Pas de modification des chantiers Documents, Notes ou Images.

## Prochain pas

Ouvrir Lot 3.2 - Acquisition conversationnelle store avant route/API. Ce lot
devra prouver la relecture conversationnelle reelle depuis le store existant,
sans route publique, sans Nextcloud/WebDAV et sans DOCX/PDF.
