# FridaDev - workspace folders contract

Statut: spec vivante
Date: 2026-05-20
Classement: `app/docs/states/specs/`
Roadmap archivee: `app/docs/todo-done/product/fridadev-workspace-folders-todo.md`
Portee: atelier documentaire / repertoires de travail, conversations, fichiers persistants, ressources OCR derivees, selection explicite et injection via documents actifs.

## 1. Verdict

Les repertoires de travail organisent ce que l'utilisateur garde a portee de main. Ils ne donnent pas a Frida une nouvelle memoire, une nouvelle Biblio, un RAG documentaire par repertoire, un prompt de projet, une identite, un resume ou un espace cognitif separe.

Formule source:

```text
Documents actifs = ce que Frida peut lire maintenant.
Atelier documentaire = ce que l'utilisateur garde a portee de main.
Biblio = ce qui est conserve durablement comme fonds/catalogue.
```

La memoire/RAG existante reste globale et transversale. Il n'y a pas de memoire/RAG par repertoire.

## 2. Modele conceptuel

Un repertoire de travail organise:

- des conversations;
- des fichiers persistants;
- des ressources OCR derivees.

Il ne cree pas:

- memoire separee;
- RAG documentaire par repertoire;
- identite;
- resume;
- Biblio;
- prompt de repertoire;
- doctrine;
- personnalite;
- espace cognitif separe.

Termes normatifs:

- `workspace_folder`: repertoire de travail visible dans la sidebar et represente par un identifiant stable serveur.
- `workspace_file`: fichier persistant rattache a un repertoire de travail.
- `workspace_file_selection`: selection explicite d'un fichier pour une conversation donnee.
- `workspace_ocr_derivative`: fichier Markdown `.ocr.md` derive d'une image ou d'un PDF source.
- `active_document`: etat d'injection de conversation existant, temporaire et conversation-scoped.

La future implementation doit reutiliser le contrat `active_document` pour l'injection au modele, mais elle ne doit pas reutiliser la table courte duree des documents actifs comme stockage durable de fichiers de repertoire.

## 3. Modele DB cible

La forme SQL finale peut etre ajustee en Lot 1/Lot 2, mais le modele cible doit garder ces responsabilites.

`workspace_folders`:

- `id`: identifiant stable, non derive du nom humain;
- `display_name`: nom logique affiche a l'utilisateur;
- `icon_key`: cle d'icone allowlistee;
- `description`: description courte UI, non injectee au modele;
- `sort_order`: ordre manuel dans la sidebar;
- `created_at`, `updated_at`, `deleted_at`;
- `status` si necessaire pour distinguer actif, supprime, tombstone.

Relation conversations:

- V0 recommandee: `conversations.workspace_folder_id` nullable, ou table de relation equivalente si une migration l'impose;
- une conversation appartient a zero ou un repertoire;
- les conversations existantes restent implicitement hors repertoire;
- le soft delete conversationnel existant doit rester preserve.

`workspace_files`:

- `id`: identifiant stable;
- `workspace_folder_id`: repertoire parent;
- `display_name`: nom logique utilisateur;
- `internal_path` ou `storage_key`: reference interne serveur;
- `content_kind` ou `media_kind`: texte, PDF, image, Markdown OCR derive;
- `mime_type`;
- `byte_size`;
- `sha256` ou hash complet, avec hash court possible pour les read-models;
- `source_kind`: upload utilisateur, OCR derive, autre source autorisee;
- `source_file_id`: fichier source si derive OCR;
- `created_at`, `updated_at`, `deleted_at`;
- `status`: actif, supprime, tombstone si besoin.

`workspace_file_selections`:

- `conversation_id`;
- `workspace_file_id`;
- `selected_at`, `updated_at`;
- `deleted_at` pour decochage/invalidation content-free;
- `last_injected_turn_id`, `last_excluded_turn_id`, `last_excluded_reason_code`;
- etat selectionne ou decoche;
- suppression automatique ou invalidation claire si le fichier est supprime, si le repertoire est supprime ou si la conversation change de repertoire.

La DB est la source applicative des listings, etats et metadonnees. Le disque stocke les bytes. Aucun chemin physique interne ne doit devenir une API utilisateur.

## 4. Modele disque cible

Chaque repertoire de travail doit correspondre a un espace physique dedie cote serveur ou a un prefixe stable reserve a ce repertoire.

Regles:

- ne jamais construire le chemin fiable a partir du nom humain du repertoire ou du fichier;
- utiliser un identifiant stable cote serveur;
- garder un espace disque dedie ou un prefixe stable par `workspace_folder.id`;
- garder le chemin physique interne hors UI;
- afficher seulement le nom logique, le type, la taille, l'etat et les metadonnees utiles;
- stocker en DB le lien entre nom logique, repertoire, fichier, `internal_path` ou `storage_key`;
- prevoir une strategie de reconciliation DB/disque.

Incoherences a gerer:

- ligne DB presente, fichier disque absent;
- fichier disque present, ligne DB absente;
- tombstone DB presente, bytes encore presents;
- bytes supprimes, suppression DB echouee;
- source OCR absente mais derive `.ocr.md` present;
- derive `.ocr.md` absent mais source presente;
- selection stale vers un fichier supprime ou deplace.

Les logs de reconciliation doivent rester content-free.

## 5. Contrat sidebar

La sidebar gauche porte les repertoires de travail au-dessus des conversations hors repertoire.

Regles UX:

- afficher les repertoires au-dessus des conversations hors repertoire;
- afficher une ligne de separation tres fine entre les deux zones;
- creer un repertoire;
- renommer un repertoire;
- supprimer un repertoire;
- gerer un ordre manuel des repertoires;
- utiliser des icones allowlistees;
- afficher une description courte si elle existe;
- permettre le deplacement conversation -> repertoire, idealement par glisser-deposer;
- permettre la sortie d'une conversation vers hors repertoire;
- conserver le renommage manuel des conversations;
- migrer implicitement les conversations existantes en "hors repertoire".

Supprimer un repertoire ne supprime pas automatiquement les conversations. Les conversations reviennent hors repertoire, sauf decision future explicitement documentee.

Implementation Lot 5 livree:

- les repertoires restent affiches au-dessus des conversations hors repertoire avec separation fine;
- les repertoires sont repliables/depliables depuis leur ligne;
- le deplacement des conversations se fait par glisser-deposer, sans select de repertoire dans les conversations;
- le glisser-deposer de conversations vers un repertoire est supporte;
- le glisser-deposer vers la separation `Conversations hors repertoire` sort la conversation du repertoire;
- les icones restent allowlistees (`icon_key`), rendues comme mini-repertoires SVG locaux, sans chargement externe ni upload d'icone custom;
- l'ordre manuel reste porte par `sort_order` et les actions monter/descendre;
- les etats vides `Aucun repertoire`, `Aucun fichier`, `Aucune conversation` sont visibles;
- les etats fichier `OCR requis`, `Fichier absent`, `Supprimé`, `Erreur` sont affiches par libelles humains content-free;
- les conversations restent compactes, lisibles comme etiquettes distinctes, avec clic simple pour charger et affordance visible de renommage manuel;
- aucun contenu fichier, chemin disque, base64, prompt ou description de repertoire n'est injecte ou expose dans le DOM;
- le nommage automatique des conversations reste un futur mini-lot non-LLM tant qu'aucune decision explicite ne l'ouvre.

## 6. Description courte

La description courte d'un repertoire est autorisee uniquement comme metadonnee UI.

Formulation normative:

```text
La description est une metadonnee UI. Elle n'est pas un prompt, ne gouverne pas la reponse et n'est pas injectee au modele en V0.
```

Si une version future l'utilise, elle doit etre traitee comme provenance faible, jamais comme instruction systeme ni doctrine.

## 7. Contrat fichiers persistants

Un fichier de repertoire est durable, contrairement a un document actif de conversation.

Types attendus en V0 cible:

- documents texte supportes par le systeme actuel: `TXT`, `MD`, `PDF`, `DOCX`, `ODT`;
- images `PNG`, `JPEG`, `WEBP`;
- fichiers Markdown OCR derives `.ocr.md`;
- autres types seulement si le systeme les supporte explicitement.

Le contrat minimal d'un fichier:

- id stable;
- `workspace_folder_id`;
- nom logique utilisateur;
- `internal_path` ou `storage_key`;
- kind contenu/media;
- MIME;
- taille;
- hash;
- source kind;
- source file id si derive OCR;
- dates creation/mise a jour/suppression;
- etat actif/supprime/tombstone si besoin.

Les fichiers persistants ne sont pas automatiquement visibles par le modele. Ils deviennent lisibles seulement via selection explicite et injection controlee.

## 8. Contrat selection/injection

Regles normatives:

- aucun fichier n'est injecte par defaut;
- le repertoire rend les fichiers disponibles, pas visibles au modele;
- une conversation ne recoit que les fichiers explicitement coches;
- la selection est conversation-scoped;
- une fois coche dans une conversation, le fichier reste selectionne jusqu'a decochage explicite;
- une autre conversation du meme repertoire ne recoit pas automatiquement cette selection;
- un fichier non selectionne est invisible pour le modele;
- integration future avec la lane `active_document`;
- injection entiere ou exclusion entiere;
- jamais de troncature silencieuse;
- reason code obligatoire si le fichier est exclu.

Frida ne doit jamais pretendre avoir lu un fichier non selectionne, exclu, supprime, absent ou trop lourd pour le tour.

La selection persistante doit survivre aux refresh UI et aux tours suivants de la meme conversation, puis disparaitre uniquement au decochage explicite, a la suppression du fichier, a la suppression du repertoire ou a une invalidation documentee.

Implementation Lot 3 livree:

- table `workspace_file_selections` conversation-scoped;
- routes content-free `GET/POST/DELETE /api/conversations/<conversation_id>/workspace-file-selections`;
- validation que le fichier appartient au repertoire de la conversation;
- invalidation des selections si la conversation sort du repertoire ou change de repertoire;
- suppression/invalidation des selections liees lorsqu'un fichier est supprime;
- UI sidebar avec case par fichier, active seulement pour la conversation courante du repertoire;
- conversion des fichiers selectionnes en items de la lane `active_document` au moment du prompt;
- lecture des bytes depuis le stockage interne uniquement pendant la preparation du tour;
- injection texte entiere ou exclusion entiere;
- injection image multimodale `text` puis `image_url`;
- correction post-cloture: si un PDF de repertoire selectionne est en statut `ocr_required`, Frida tente une injection PDF visuelle multimodale `text` puis `file`, sous allowlist modele et plafond provider, sans OCR automatique;
- si le PDF visuel est trop lourd, absent ou non supporte par le modele/provider, il est exclu entierement avec un reason code explicite;
- si la lecture des fichiers selectionnes echoue alors que d'autres documents actifs restent injectables, la lane conserve les injections possibles mais signale explicitement `read_status=error` et le `reason_code` content-free;
- aucune copie de contenu extrait dans `conversation_messages`, memoire, identity, summary, Biblio ou RAG;
- observabilite content-free pour selection, decochage, injection, exclusion et stale/missing/deleted/disk_missing;
- le chemin OCR `.ocr.md` reste distinct: l'injection PDF visuelle ne cree pas de Markdown derive, ne stocke pas d'OCR et ne promet pas une lecture textuelle complete.

## 9. Contrat OCR images/PDF

L'OCR ne concerne pas seulement les PDF. Il doit aussi couvrir les images:

- captures d'ecran;
- photos de pages;
- notes manuscrites;
- scans image.

Regles:

- OCR image manuel ou semi-manuel;
- pas d'OCR automatique global sur toutes les images;
- action UI explicite du type `Extraire le texte`;
- manuscrit considere incertain;
- OCR presente comme extraction imparfaite, jamais comme verite visuelle totale.

Contrat d'artefact:

```text
photo-page-12.jpg
photo-page-12.ocr.md
```

Le fichier `.ocr.md`:

- garde un lien de provenance vers l'image ou le PDF source;
- est visible dans le repertoire a cote de la source;
- est selectionnable comme fichier texte;
- peut etre ouvert par double-clic ou action explicite;
- s'ouvre dans une petite fenetre ou un panneau UI;
- est editable;
- propose une sauvegarde;
- met a jour le Markdown et la reference DB a la sauvegarde.

Le derive OCR peut suivre ensuite le chemin des documents textuels actifs, mais seulement s'il est explicitement selectionne dans la conversation.

Implementation Lot 4 livree:

- action OCR explicite sur fichier workspace compatible image PNG/JPEG/WEBP ou PDF;
- reutilisation du client OCR existant: PDF OCR via Stirling et image -> PDF via Stirling (`ACTIVE_DOCUMENT_IMAGE_TO_PDF_URL`, defaut `http://platform-stirling-pdf:8080/pdf/api/v1/convert/img/pdf`) avant OCR PDF;
- creation ou mise a jour d'un vrai `workspace_file` derive en Markdown `.ocr.md`;
- `source_kind=ocr_derived` et `source_file_id` vers le fichier source;
- listing du derive dans le repertoire et selection possible par le chemin texte Lot 3, sans injection automatique;
- ouverture/edition/sauvegarde du `.ocr.md` via panneau UI, avec mise a jour bytes disque + metadonnees DB/hash/taille/texte;
- suppression du fichier source ne supprime pas automatiquement le derive: le Markdown OCR reste un fichier durable distinct avec provenance tombstonee/content-free;
- observabilite content-free pour succes/echec OCR et edition, sans texte OCR brut, bytes, chemin disque, `storage_key`, base64, prompt, memoire, identity, summary, Biblio ou RAG.

## 10. Contrat suppression

Suppression utilisateur d'un fichier:

- bytes physiques serveur supprimes;
- fichier absent des listings actifs;
- selections liees supprimees ou invalidees;
- fichier non selectionnable;
- fichier non injectable;
- anciennes references rendues inoffensives par reason code;
- tombstone DB eventuelle uniquement content-free;
- aucune conservation de contenu brut dans la tombstone;
- aucun chemin physique expose dans la tombstone ou l'UI.

Test attendu plus tard:

```text
suppression fichier -> non liste, non selectionnable, non injectable, bytes absents
```

Suppression d'un repertoire (contrat courant depuis Lot 4 Frida V1 Nextcloud
folders):

- confirmation UI explicite pour la suppression du dossier;
- soft delete/tombstone du `workspace_folder`;
- conversations non supprimees automatiquement;
- conversations replacees hors repertoire;
- fichiers et documents workspace preserves: aucun byte fichier n'est supprime
  par `DELETE /api/workspace-folders/<id>`;
- suppression physique d'un fichier uniquement par action fichier explicite,
  via `DELETE /api/workspace-folders/<folder_id>/files/<file_id>`;
- l'ancien comportement "suppression dossier supprime d'abord les fichiers
  actifs" est historique et supersede, pas le contrat runtime courant;
- `workspace_folder_file_delete_failed` reste un reason code historique ou
  fichier/batch, mais n'est pas le resultat attendu de
  `DELETE /api/workspace-folders/<id>` dans le contrat courant;
- selections liees aux fichiers: aucune suppression de bytes par effet de bord;
  toute invalidation future doit rester explicite, content-free et documentee;
- logs content-free.

Transition V1: voir aussi
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`.

## 11. Reason codes

Premiere liste stable pour les futurs lots:

- `workspace_file_missing`;
- `workspace_file_deleted`;
- `workspace_file_disk_missing`;
- `workspace_file_db_missing`;
- `workspace_file_too_large`;
- `workspace_file_type_unsupported`;
- `workspace_file_unreadable`;
- `workspace_file_ocr_required`;
- `workspace_file_ocr_failed`;
- `workspace_file_pdf_visual_model_unsupported`;
- `workspace_file_pdf_visual_bytes_missing`;
- `workspace_file_pdf_visual_too_large`;
- `workspace_file_runtime_unavailable`;
- `workspace_file_not_selected`;
- `workspace_folder_not_found`;
- `workspace_folder_deleted`;
- `workspace_folder_files_preserved`;
- `workspace_folder_file_delete_failed` (historique Lot 2 ou action fichier/batch,
  non attendu pour `DELETE /api/workspace-folders/<id>` depuis Lot 4);
- `workspace_selection_stale`;
- `workspace_file_tombstone`;
- `workspace_file_source_missing`.

Ces codes doivent rester content-free et apparaitre dans les decisions d'exclusion, les read-models techniques et les tests. Ils ne doivent jamais contenir de chemin physique, contenu brut, base64 ou extrait utilisateur long.

## 12. Non-contamination

Le chantier impose:

- pas de memoire automatique;
- pas d'identity automatique;
- pas de summary automatique;
- pas de Biblio automatique;
- pas de RAG documentaire par repertoire;
- pas de memoire/RAG par repertoire;
- pas de contenu brut en observabilite;
- pas de base64 image dans logs, read-models, historique ou dashboard;
- pas d'injection silencieuse;
- pas de troncature silencieuse;
- pas de prompt de repertoire;
- pas de description injectee;
- pas de promotion automatique d'un OCR derive en connaissance durable.

Formulation de garde:

```text
pas de mémoire/RAG par répertoire
```

Cette phrase doit rester visible dans les roadmaps et tests documentaires du chantier.

## 13. Migration des conversations existantes

La migration initiale doit etre conservatrice:

- toutes les conversations existantes restent accessibles;
- elles sont considerees hors repertoire;
- aucun fichier n'est rattache automatiquement a un repertoire;
- aucun document actif existant n'est transforme en fichier persistant;
- aucun contenu conversationnel n'est copie dans un repertoire;
- aucun resume, identity ou trace memoire n'est segmente par repertoire.

Si la migration DB echoue, le chat doit rester capable de lister et ouvrir les conversations existantes sans repertoire.

## 14. Tests et preuves attendus

Futurs lots DB/disque:

- creation, renommage, suppression de repertoire;
- ordre manuel stable;
- icon key allowlistee;
- description non injectee;
- conversations existantes hors repertoire;
- conversation rattachee puis sortie du repertoire;
- suppression repertoire sans suppression automatique des conversations.

Futurs lots fichiers:

- upload fichier dans repertoire;
- stockage disque sous identifiant stable;
- listing par DB;
- chemin interne absent des payloads UI;
- suppression fichier -> non liste, non selectionnable, non injectable, bytes absents;
- suppression repertoire avec fichiers -> tombstone du repertoire, conversations
  replacees hors repertoire, fichiers/documents workspace preserves et reason
  code content-free `workspace_folder_files_preserved`;
- suppression physique de fichier -> action fichier explicite separee;
- incoherence DB presente/disque absent;
- incoherence disque present/DB absente;
- tombstone content-free.

Futurs lots selection/injection:

- aucun fichier injecte par defaut;
- selection conversation-scoped persistante jusqu'a decochage;
- autre conversation du meme repertoire sans selection automatique;
- integration avec la lane `active_document`;
- injection entiere ou exclusion entiere;
- reason code sur exclusion;
- absence de troncature silencieuse;
- absence de contenu brut et base64 dans logs/read-models/historique/dashboard.

Futurs lots OCR:

- OCR PDF vers `.ocr.md`;
- OCR image vers `.ocr.md`;
- provenance source conservee;
- edition UI du Markdown;
- sauvegarde met a jour disque et DB;
- OCR manuscrit signale comme incertain;
- `.ocr.md` selectionnable comme texte seulement apres selection explicite.

## 15. Frontieres avec l'existant

Documents actifs:

- surface temporaire, conversation-scoped;
- injection au modele;
- exclusion entiere si trop lourd, absent ou non supporte;
- pas de stockage durable serveur comme atelier documentaire.

Atelier documentaire:

- surface durable de rangement et disponibilite;
- fichiers persistants DB + disque;
- selection explicite pour rendre un fichier lisible maintenant;
- pas de lecture automatique par le modele.

Biblio:

- fonds/catalogue durable separe;
- pas ouvert par ce chantier;
- pas a confondre avec les fichiers de travail gardes a portee de main.

## 16. Mise en oeuvre Lot 1

Lot 1 livre le 2026-05-20:

- table `workspace_folders`;
- colonne nullable `conversations.workspace_folder_id`;
- conversations existantes implicitement hors repertoire;
- relation conversation -> repertoire en V0 zero ou un repertoire;
- creation, renommage, suppression soft de repertoire;
- suppression de repertoire sans suppression automatique des conversations;
- remise hors repertoire des conversations rattachees lors de la suppression;
- `icon_key` allowliste;
- description courte persistante et non injectee;
- `sort_order` manuel;
- routes `GET/POST/PATCH/DELETE /api/workspace-folders`;
- rattachement/sortie de conversation via `PATCH /api/conversations/<conversation_id>`;
- sidebar V0 avec repertoires au-dessus, conversations hors repertoire sous separation fine, et deplacement par select.

Decision Lot 1:

- le glisser-deposer conversation -> repertoire reste au Lot 5 / polish;
- aucun fichier persistant, stockage disque, selection multi-fichiers, OCR `.ocr.md` ou injection documentaire n'est ouvert par Lot 1.

## 17. Mise en oeuvre Lot 2

Lot 2 livre le 2026-05-20:

- table `workspace_files`;
- stockage des bytes sous un prefixe disque stable par `workspace_folder.id`;
- racine disque par defaut `WORKSPACE_FILES_DIR`, pointee vers le volume persistant `/app/conv/_workspace_files` en runtime OVH;
- `storage_key` interne construit avec `workspace_folder.id` + `workspace_file.id`, jamais avec les noms humains;
- routes `GET/POST/DELETE /api/workspace-folders/<folder_id>/files`;
- upload multipart d'un fichier de repertoire;
- reutilisation du plafond d'upload actif `40 MiB`, applique comme
  `MAX_CONTENT_LENGTH` Flask avant materialisation multipart meme sans longueur
  fiable, puis comme lecture fichier par blocs jusqu'a `40 MiB + 1 octet`;
- acceptation de la limite fichier exacte et refus de `limite + 1` avant
  extraction, ecriture disque, persistence ou Nextcloud, sans reutiliser le
  prefixe lu;
- reutilisation de `active_document_text_extraction` pour `TXT`, `MD`, `PDF`, `DOCX`, `ODT`;
- reutilisation de `active_document_image_validation` pour `PNG`, `JPEG`, `WEBP`, avec refus GIF V0;
- stockage metadata content-free: nom logique, MIME, extension, taille, hash court, dimensions image, statut, reason code;
- listing par repertoire sans contenu brut, sans chemin physique, sans `storage_key`;
- suppression utilisateur d'un fichier avec suppression physique des bytes puis tombstone DB content-free;
- detection de l'incoherence DB presente / disque absent via statut de listing `disk_missing` et reason code `workspace_file_disk_missing`;
- historique Lot 2 supersede: la suppression d'un repertoire tentait d'abord de supprimer tous les fichiers actifs du repertoire;
- historique Lot 2 supersede: si tous les fichiers actifs etaient supprimes, le repertoire etait supprime et les conversations restaient conservees / replacees hors repertoire;
- historique Lot 2 supersede: si un fichier actif echouait, l'API retournait `workspace_folder_file_delete_failed` avec compteurs `requested`, `deleted`, `failed` et le repertoire n'etait pas presente comme pleinement supprime;
- contrat runtime courant depuis Lot 4 Frida V1 Nextcloud folders: `DELETE /api/workspace-folders/<id>` tombstone le repertoire, replace les conversations hors repertoire, preserve les fichiers/documents workspace et retourne `workspace_folder_files_preserved`;
- la suppression physique d'un fichier reste une action explicite via `DELETE /api/workspace-folders/<folder_id>/files/<file_id>`;
- observabilite content-free pour upload succes/echec, delete succes/echec, listing `disk_missing` et resume de suppression de repertoire;
- UI minimale dans la sidebar: liste compacte des fichiers du repertoire, ajout explicite, suppression explicite.

Decision Lot 2:

- l'upload `active_document` de conversation reste l'action existante et continue a creer un document actif de conversation;
- l'upload `workspace_file` est une action separee de repertoire et ne cree pas d'`active_document`;
- aucun fichier de repertoire n'est selectionne, injecte, resume, memorise ou lu par le modele dans Lot 2;
- les logs Lot 2 restent content-free: ids, types, MIME, taille, dimensions, hash court, statuts, reason codes et compteurs, sans contenu brut, bytes, chemin disque complet, `storage_key`, base64, secret ou prompt;
- les PDF scannes peuvent etre conserves comme fichiers de repertoire avec statut `ocr_required` / reason code `workspace_file_ocr_required`; s'ils sont explicitement selectionnes, la preparation de tour peut tenter un payload visuel PDF `text` puis `file`;
- le derive `.ocr.md` reste le chemin OCR durable separe: il n'est cree que par action OCR explicite et non par la selection du PDF;
- les fichiers de repertoire ne nourrissent ni memoire, ni identity, ni summary, ni Biblio, ni RAG documentaire par repertoire.
- leur usage conversationnel reste document entier ou absent: aucune
  troncature, le tour continue apres exclusion et Frida recoit le signal qui lui
  permet de dire honnetement que le fichier n'a pas ete injecte.
