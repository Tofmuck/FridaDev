# FridaDev - workspace folders contract

Statut: spec vivante
Date: 2026-05-20
Classement: `app/docs/states/specs/`
Roadmap active: `app/docs/todo-todo/product/fridadev-workspace-folders-todo.md`
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
- etat selectionne ou decoché;
- suppression automatique ou invalidation claire si le fichier est supprime.

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
- peut etre ouvert par double-clic;
- s'ouvre dans une petite fenetre ou un panneau UI;
- est editable;
- propose une sauvegarde;
- met a jour le Markdown et la reference DB a la sauvegarde.

Le derive OCR peut suivre ensuite le chemin des documents textuels actifs, mais seulement s'il est explicitement selectionne dans la conversation.

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

Suppression d'un repertoire:

- confirmation forte si le repertoire contient fichiers ou conversations;
- fichiers supprimes physiquement apres confirmation si la decision produit le demande;
- conversations non supprimees automatiquement;
- conversations replacees hors repertoire;
- selections liees aux fichiers du repertoire supprimees ou invalidees;
- logs content-free.

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
- `workspace_file_not_selected`;
- `workspace_folder_deleted`;
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
