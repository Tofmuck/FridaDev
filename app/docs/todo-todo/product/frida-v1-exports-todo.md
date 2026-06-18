# Frida V1 - Exports / creation documentaire - TODO

Statut: TODO detaillee, aucun lot runtime ouvert.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Sources de verite

- Roadmap finale Frida 1.0:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
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
detourner sans decision explicite Lot 1.

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
- reutiliser un export existant dans une conversation ou dans une action
  utilisateur explicite, sans le confondre avec Documents ou Notes.

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

## Decisions ouvertes avant runtime

Aucun lot runtime Exports V1 ne doit demarrer tant que ces decisions ne sont pas
gravees dans une spec source-of-truth Exports V1.

Decisions produit bloquantes:

- Source exacte exportable en V1:
  - conversation complete;
  - selection de messages;
  - reponse courante;
  - note;
  - document;
  - brouillon genere par Frida;
  - combinaison explicite de plusieurs sources.
- Surface utilisateur primaire:
  - bouton dans le chat;
  - action dans un dossier;
  - action sur une note;
  - action sur un document;
  - API d'abord.
- Niveau de selection utilisateur:
  - export direct du dossier courant;
  - export d'une conversation liee au dossier;
  - export d'un sous-ensemble explicitement selectionne.
- Politique de nommage et versioning:
  - nom fourni par l'utilisateur;
  - nom derive du titre/source/date;
  - suffixe versionne;
  - refus de collision sans renommage automatique.
- Read-model local exports:
  - table dediee obligatoire ou derive strictement d'une table existante;
  - relation a `workspace_folders.id`;
  - relation optionnelle a conversation, note, document ou source d'origine;
  - stockage ou non d'un hash de contenu.
- Degre de fidelite DOCX/PDF attendu:
  - texte simple;
  - structure Markdown conservee;
  - titres/listes/tableaux;
  - images et pieces jointes hors V1 ou incluses.
- Moteur de generation DOCX/PDF:
  - dependances disponibles;
  - installation/runtime;
  - fallback si dependance absente.
- Limites de taille V1:
  - caracteres source maximum;
  - taille fichier exporte maximum;
  - duree maximum de generation;
  - nombre de pages PDF maximum si applicable.
- Reutilisation d'un export existant:
  - sens exact du verbe "reutiliser":
    - telecharger / ouvrir;
    - joindre a une conversation;
    - lire/injecter le contenu dans le tour courant;
    - convertir vers un autre format;
    - dupliquer / repartir d'un export comme source;
    - autre comportement explicitement decide;
  - critere de resolution:
    - par titre;
    - par format;
    - par dossier;
    - par hash/ref de contenu;
    - par dernier export;
    - par selection explicite dans une liste.
  - Aucune lecture du contenu exporte, injection conversationnelle, conversion
    ou duplication ne doit etre deduite du simple mot "reutiliser".
- Visibilite utilisateur des noms d'exports:
  - titres/noms visibles en UI;
  - affichage dans les reponses conversationnelles;
  - redaction stricte dans les surfaces techniques.
- Politique de contenu exporte:
  - contenu complet ou refus;
  - pas de troncature silencieuse;
  - message utilisateur en cas de limite.

Si une decision nouvelle apparait pendant un lot runtime, le lot s'arrete avant
patch et ouvre un micro-lot docs/spec. Il ne choisit pas en avancant.

## Garde-fous runtime a graver dans la spec Lot 1

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
- Pas de route globale qui contourne `workspace_folders` sans decision explicite
  Lot 1.
- Pas de reutilisation de `workspace_files` ou `workspace_folder_notes` si cela
  brouille Documents ou Notes.
- Pas de promotion automatique en Memory/RAG/Identity/Summary.
- Pas de reouverture Documents/Notes/Images par confusion.
- Pas de lecture, injection, conversion ou duplication d'un export existant
  sans decision Lot 1 et action utilisateur explicite.

## Lots proposes

Ne cocher aucun lot dans cette reecriture. Chaque lot doit rester borne,
testable et reversible.

### Lot 0 - Audit existant exports

- [x] Auditer `app/docs/states/specs/chat-copy-export-contract.md`.
- [x] Auditer les exports conversationnels Markdown existants cote navigateur.
- [x] Auditer l'export Markdown technique des logs admin.
- [x] Auditer les routes, helpers, tests frontend/backend et dependances
  disponibles autour de Markdown, TXT, DOCX et PDF.
- [x] Identifier les briques reutilisables telles quelles.
- [x] Identifier les briques a adapter.
- [x] Identifier les briques a eviter pour ne pas confondre Exports V1 avec
  logs admin, Documents, Notes ou simple telechargement navigateur.
- [x] Verifier explicitement que l'export admin logs ne sert pas de modele
  produit, hors patterns limites de reponse HTTP, attachement Markdown ou tests.
- [x] Produire un audit content-free sous `app/docs/states/audits/`.
- [x] Ne livrer aucun runtime.

### Lot 1 - Contrat source-of-truth Exports V1

- [ ] Creer `app/docs/states/specs/frida-v1-exports-contract.md`.
- [ ] Fermer toutes les decisions ouvertes avant runtime.
- [ ] Si une decision produit humaine manque, s'arreter avant tout patch
  runtime et demander explicitement; Lot 1 documente les choix deja tranches,
  mais ne choisit pas en avancant.
- [ ] Definir le modele produit Export V1.
- [ ] Definir les sources exportables V1.
- [ ] Definir les formats, limites, messages utilisateur et reason codes.
- [ ] Definir le modele local/read-model attendu.
- [ ] Definir les routes/API et surfaces UI autorisees.
- [ ] Definir la politique de nommage, collision et versioning.
- [ ] Definir la politique de generation DOCX/PDF et les dependances.
- [ ] Definir les criteres Lot Z.
- [ ] Ne livrer aucun runtime.

### Lot 2 - Modele local / read-model exports

- [ ] Livrer le modele local exports decide par la spec Lot 1.
- [ ] Rattacher strictement l'export a `workspace_folders.id`.
- [ ] Representer le format, la source, le statut local, le statut Nextcloud,
  refs content-free, hashes, timestamps et reason codes.
- [ ] Ne pas stocker de contenu exporte localement sauf decision explicite Lot 1
  avec limites et tests anti-fuite.
- [ ] Produire projections utilisateur et technique content-free.
- [ ] Tester conflits locaux, statuts, tombstone si applicable et anti-fuite.
- [ ] Ne pas contacter Nextcloud/WebDAV live.

### Lot 3 - Generation Markdown/TXT bornee fake/local

- [ ] Generer Markdown depuis les sources decidees Lot 1.
- [ ] Generer TXT depuis les sources decidees Lot 1.
- [ ] Appliquer les limites de taille V1.
- [ ] Refuser proprement au-dela des limites.
- [ ] Ne pas tronquer silencieusement.
- [ ] Ne pas ranger encore dans Nextcloud.
- [ ] Tester conversion, refus taille, noms, reason codes et anti-fuite.

### Lot 4 - Generation DOCX/PDF bornee fake/local

- [ ] Verifier les dependances runtime necessaires a DOCX/PDF.
- [ ] Generer DOCX selon le degre de fidelite decide Lot 1.
- [ ] Generer PDF selon le degre de fidelite decide Lot 1.
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
- [ ] Retrouver un export selon les criteres decidees Lot 1.
- [ ] Implementer uniquement le sens de "reutiliser" decide par Lot 1.
- [ ] Refuser toute lecture, injection, conversion ou duplication non decidee
  par Lot 1.
- [ ] Ne pas lire le contenu exporte sans action explicite et decision Lot 1.
- [ ] Distinguer absence, ambiguite, conflit et panne store.
- [ ] Tester liste vide, liste avec formats multiples, lookup, ambiguite,
  refus et anti-fuite.

### Lot 7 - Integration UI ou conversationnelle minimale

- [ ] Ajouter la surface utilisateur decidee Lot 1.
- [ ] Ne pas remplacer le bouton export Markdown navigateur existant sans
  decision explicite.
- [ ] Si Lot 1 decide une reutilisation conversationnelle, prouver que la
  lecture/injection est explicite, bornee, content-free en observabilite et
  separee de Memory/RAG/Identity/Summary.
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

## Reason codes initiaux a stabiliser en Lot 1

Catalogue indicatif, non definitif avant Lot 1:

- `folder_export_folder_not_linked`;
- `folder_export_exports_target_missing`;
- `folder_export_exports_target_not_collection`;
- `folder_export_exports_target_unavailable`;
- `folder_export_name_invalid`;
- `folder_export_name_conflict`;
- `folder_export_source_missing`;
- `folder_export_source_ambiguous`;
- `folder_export_source_unsupported`;
- `folder_export_format_unsupported`;
- `folder_export_too_large`;
- `folder_export_generation_failed_redacted`;
- `folder_export_create_ok`;
- `folder_export_store_ok`;
- `folder_export_list_ok`;
- `folder_export_lookup_ok`;
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

## Hors-scope de cette reecriture

- Pas de runtime.
- Pas de route serveur.
- Pas de UI.
- Pas de Nextcloud live.
- Pas de migration DB.
- Pas de generation DOCX/PDF reelle.
- Pas de smoke live.
- Pas de rebuild.
- Pas d'archivage.
- Pas de Lot Z.
- Pas de modification des chantiers Documents, Notes ou Images.

## Prochain pas

Ouvrir Lot 0 - Audit existant Exports V1. Ce lot devra rester read-only /
docs-only, auditer les exports conversationnels/admin existants, inventorier les
dependances de generation documentaire, et produire un audit content-free avant
toute spec Exports V1 ou runtime.
