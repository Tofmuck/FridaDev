# FridaDev - lecture d'images comme documents actifs - TODO

Statut: ouvert
Date de creation: 2026-05-19
Classement: `app/docs/todo-todo/product/`
Branche de travail initiale: `feature/active-image-documents`
Spec source: `app/docs/states/specs/active-conversation-documents-contract.md`
Roadmaps sources archivees:
- `app/docs/todo-done/product/active-conversation-documents-todo.md`
- `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- `app/docs/todo-done/product/fridadev-image-generation-openrouter-todo.md`
Portee: lecture d'images par Frida comme extension stricte des documents actifs de conversation
Hors-scope initial: generation d'images, edition d'images, galerie, stockage durable, agent vision separe, OCR automatique image, Biblio, memoire, identity, summary, RAG

## 1. Intention

Permettre a Frida de recevoir une image et de la comprendre dans le tour de chat principal, sans inventer un nouveau paradigme "vision".

Decision de cadrage:

- l'image est une piece active de conversation;
- l'image prolonge le contrat des `active_document`;
- l'image n'est pas un outil lateral comme la generation d'images OpenRouter V0;
- l'image n'est pas une memoire;
- l'image n'est pas une entree Identity;
- l'image n'est pas un resume;
- l'image n'est pas une Biblio;
- l'image n'est pas un passage RAG ou un embedding.

La capacite visee est donc:

```text
upload image utilisateur -> piece active de conversation -> injection multimodale entiere si possible -> lecture par le modele principal
```

et non:

```text
upload image -> agent vision autonome -> description persistante -> memoire / identity / summary
```

## 2. Decisions deja prises

Preuve technique prealable du 2026-05-19:

- le modele principal live verifie est `anthropic/claude-sonnet-4.6`;
- OpenRouter declare ce modele en `text+image+file -> text`;
- l'API modeles declare `input_modalities = text, image, file` et `output_modalities = text`;
- le payload teste utilise `POST /api/v1/chat/completions`;
- le message teste transporte `content` comme tableau avec une part `text` et une part `image_url`;
- la doc OpenRouter recommande d'envoyer le texte avant les images dans le tableau `messages[].content`;
- appel non-stream OK avec une image PNG 32x32 non sensible;
- appel stream OK avec la meme structure multimodale;
- une image PNG 1x1 a echoue avec `Could not process image`;
- une image PNG 32x32 a reussi;
- `app/core/llm_client.py` conserve deja `messages` tel quel dans `build_payload()`;
- les headers, metadata et trace OpenRouter du caller principal restent utilisables;
- `/api/chat` et le frontend chat restent text-only aujourd'hui: ils n'acceptent que `message` texte et ne portent aucune image.

Consequence:

- il n'est pas necessaire de changer de modele principal avant d'ouvrir le chantier;
- le vrai travail est de faire porter l'image par le contrat `active_document`, puis par le payload multimodal final;
- le chantier devra prouver que le mode stream reste compatible.

## 3. Contrat produit

Une image active est une piece active de conversation.

Proprietes obligatoires:

- conversation-scoped;
- activee par action utilisateur;
- visible comme piece active dans la conversation courante;
- retirable explicitement par l'utilisateur;
- injectee seulement si elle est active;
- exclue si elle ne peut pas etre injectee proprement;
- jamais reutilisee hors de la conversation active;
- pas de stockage serveur durable en V0;
- pas de memoire automatique;
- pas d'identity;
- pas de summary;
- pas de Biblio;
- pas de RAG;
- pas d'embedding;
- pas d'agent vision separe en V0;
- pas de description automatique ou OCR automatique en V0 sans lot ulterieur explicitement contracte.

L'image doit rester un contenu fourni par l'utilisateur, non souverain, comme les documents actifs textuels. Une image peut contenir du texte, des consignes ou une capture d'ecran: ces elements doivent etre traites comme contenu utilisateur, jamais comme instruction systeme.

## 4. Politique d'injection

Regle centrale conservee:

```text
injection entiere ou exclusion entiere
```

Implications pour les images:

- pas de troncature silencieuse;
- pas de downscale silencieux presente comme image originale;
- pas de base64 dans le prompt texte;
- la data URL base64 est autorisee uniquement dans `image_url.url` au moment de l'appel provider;
- jamais de base64 dans les logs;
- jamais de base64 dans l'historique conversationnel;
- jamais de base64 dans les read-models/dashboard;
- jamais de base64 dans les docs ou artefacts de preuve;
- pas de conversion automatique en description texte en V0;
- pas de chunking visuel;
- pas de resume image de substitution;
- l'image est transmise comme contenu multimodal au modele principal;
- l'ordre obligatoire V0 dans le tableau multimodal est `text` puis `image_url`;
- ne pas envoyer l'image avant le texte sauf decision future tres explicite;
- si l'image ne peut pas etre transmise, elle est entierement exclue;
- si elle est exclue, Frida recoit un signal compact d'exclusion avec reason code;
- Frida ne doit jamais pretendre avoir vu l'image si elle n'a pas ete injectee.

Payload minimal OpenRouter brut attendu pour `/api/v1/chat/completions`:

```json
{
  "role": "user",
  "content": [
    {
      "type": "text",
      "text": "Décris cette image."
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "data:image/png;base64,..."
      }
    }
  ]
}
```

Regle de nommage:

- dans le JSON brut OpenAI-compatible envoye a OpenRouter, utiliser `image_url`;
- ne pas utiliser `imageUrl` dans notre payload brut;
- `imageUrl` peut apparaitre dans certains exemples SDK, mais ne doit pas devenir la forme JSON runtime de FridaDev.

Reason codes probables a stabiliser:

- `image_type_unsupported`;
- `image_too_large`;
- `image_too_small_for_provider`;
- `image_dimensions_unsupported`;
- `image_input_not_supported_for_model`;
- `image_runtime_unavailable`;
- `image_not_injected_for_turn`;
- `image_read_error`.

La regle `PNG 1x1 echoue, PNG 32x32 reussit` doit devenir un test utile: le produit doit refuser ou signaler proprement les images trop petites / non traitables au lieu de laisser Frida pretendre les lire.

## 5. Architecture probable

Surfaces a relire et probablement toucher dans les lots d'implementation:

### Active documents core

- `app/core/active_conversation_documents.py`
- `app/core/active_document_upload_service.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/active_document_text_extraction.py` seulement pour verifier la frontiere texte/image

Objectif:

- ajouter un type de piece active image sans transformer le store en Biblio;
- conserver les metadonnees content-free;
- eviter de melanger `text_content` et payload image;
- garder un etat court conversation-scoped.

### Chat runtime

- `app/core/chat_service.py`
- `app/core/chat_llm_flow.py`
- `app/core/llm_client.py`
- `app/server.py`

Objectif:

- construire un payload final OpenRouter capable de porter texte + image;
- maintenir le stream;
- maintenir l'attribution OpenRouter `main_chat`;
- ne pas faire entrer l'image dans les messages persistants de conversation;
- ne pas contaminer Memory/RAG/Identity/Summary.

### Frontend

- `app/web/chat_active_documents.js`
- `app/web/app.js`
- `app/web/index.html`
- `app/web/styles.css`

Objectif:

- integrer l'upload image dans l'UI des documents actifs;
- garder une experience native FridaDev;
- ne pas creer un outil "vision" separe;
- afficher metadonnees, etat actif, retrait, erreur;
- ne pas afficher ni stocker de base64 brut dans l'UI hors preview locale necessaire.

### Observabilite

- `app/observability/active_documents_observability.py`
- read-models/dashboard documents si besoin;
- logs admin compacts.

Objectif:

- content-free strict;
- pas de base64;
- pas d'image brute;
- pas de prompt image complet;
- seulement type, bytes, dimensions, hash court, statut, injected/excluded, reason code, provider capability si utile.

## 6. Lots proposes

### Lot 0 - Spec active documents image

- [x] Mettre a jour `app/docs/states/specs/active-conversation-documents-contract.md`.
- [x] Definir le vocabulaire stable: image active, media_kind image, injection multimodale, exclusion image.
- [x] Graver que l'image prolonge `active_document`.
- [x] Graver la frontiere avec generation d'images OpenRouter V0.
- [x] Graver la frontiere Memory/RAG/Identity/Summary/Biblio.
- [x] Graver la regle: base64 autorisee seulement dans `image_url.url`, jamais logs/docs/read-models/dashboard/historique.
- [x] Graver l'ordre OpenRouter V0: `text` puis `image_url`.
- [x] Graver les reason codes image initiaux.
- [x] Graver les limites V0: pas de stockage durable, pas de description/OCR automatique, pas d'agent vision separe.

### Lot 1 - Upload image actif et validation

- [x] Accepter les images seulement dans le chemin documents actifs de conversation.
- [x] Documenter que OpenRouter supporte `image/png`, `image/jpeg`, `image/webp`, `image/gif`.
- [x] Autoriser une courte allowlist V0 FridaDev: `image/png`, `image/jpeg`, `image/webp`.
- [x] Garder `image/gif` hors V0 sauf decision explicite, afin d'eviter animations, poids, comportement provider variable et surface de tests plus large.
- [x] Valider extension, MIME/dimensions sniffes, taille bytes et dimensions.
- [x] Refuser proprement image vide, trop petite, trop lourde ou type non supporte.
- [x] Stocker seulement l'etat court necessaire a la reinjection active.
- [x] Ne pas retourner de base64 dans les reponses ordinaires.
- [x] Garder l'activation conversation-scoped et le retrait manuel.
- [x] Tester upload nominal, type refuse, image trop petite, image trop lourde, retrait.

Limites V0 livrees:

- taille source maximale: `32 MiB` (`33554432` bytes);
- taille maximale du body multipart avant parsing: `40 MiB` (`41943040` bytes);
- dimensions minimales: `32 x 32 px`;
- dimension maximale par cote: `16000 px`;
- surface maximale: `100 megapixels`;
- pas de downscale silencieux;
- validation par sniff conteneur/dimensions, sans promettre le decodage provider futur;
- retrait manuel d'une image active: effacement des bytes image, conservation des metadonnees content-free;
- une image acceptee par l'upload reste non injectee dans le modele principal tant que le Lot 2 n'est pas livre.

### Lot 2 - Lane multimodale vers modele principal

- [x] Etendre la lane documents actifs pour produire des messages multimodaux quand une image est active et injectable.
- [x] Transporter l'image comme part OpenRouter `image_url`, pas comme texte base64.
- [x] Produire le tableau multimodal dans l'ordre exact `text` puis `image_url`.
- [x] Tester explicitement l'ordre exact du tableau multimodal.
- [x] Utiliser `image_url` dans le JSON brut, pas `imageUrl`.
- [x] Conserver le contrat systeme des documents actifs.
- [x] Ajouter un signal compact si le modele/provider courant ne supporte pas l'image.
- [x] Verifier que `anthropic/claude-sonnet-4.6` reste compatible avant appel.
- [x] Conserver le mode stream.
- [x] Tester payload multimodal exact.
- [x] Tester exclusion propre si capability absente.
- [x] Tester que Frida ne pretend pas avoir vu l'image exclue.

Lot 2 livre:

- les images actives restent injectees au meme point que les autres documents actifs, apres les signaux amont/validation et avant l'appel OpenRouter principal;
- elles ne sont jamais ajoutees a `conversation["messages"]`;
- le message provider contient un tableau multimodal `content[0]=text`, puis `content[1]=image_url`;
- la compatibilite V0 est allowlistee sur le modele principal verifie `anthropic/claude-sonnet-4.6`;
- l'upload actif accepte toujours les images source jusqu'a `32 MiB`, mais l'injection provider V0 est bornee a `8 MiB` pour eviter un JSON OpenRouter base64 geant;
- si le modele courant n'est pas compatible, l'image est exclue entierement avec `reason_code=image_model_unsupported`;
- si les bytes actifs manquent, l'image est exclue entierement avec `reason_code=image_bytes_missing`;
- si l'image depasse le plafond d'injection provider, elle est exclue entierement avec `reason_code=image_too_large_for_provider_payload`;
- l'evenement `active_documents` reste content-free et indique `decision`, `media_kind`, dimensions, hash court, `provider_model` et `payload_order`.

### Lot 3 - Frontend integre dans l'UI documents actifs

- [x] Ajouter l'upload image dans le controle documents actifs existant.
- [x] Afficher nom, type, taille, dimensions, statut, retrait.
- [x] Afficher une preview locale ou metadata selon le moindre risque produit.
- [x] Garder le langage visuel FridaDev existant.
- [x] Ne pas creer de bouton "vision" autonome.
- [x] Ne pas injecter l'image dans le champ texte du chat.
- [x] Tester desktop/mobile.
- [x] Tester retrait et reload navigateur.

Lot 3 livre:

- l'input documents actifs accepte `.png`, `.jpg`, `.jpeg`, `.webp` et ne propose pas `.gif`;
- l'image reste dans la barre native des documents actifs, sans bouton vision autonome et sans mini-app separee;
- l'UI affiche filename, extension/type, taille, dimensions et statut `Image active` ou `Image non injectee`;
- la V0 retient le choix metadata-only plutot qu'une preview image, afin d'eviter toute URL/base64 persistante cote frontend;
- le retrait utilise le mecanisme existant `DELETE /api/conversations/<id>/active-documents/<document_id>`;
- un reload navigateur recharge l'etat actif depuis le serveur/mock de test, sans base64 frontend;
- l'upload image seul ne poste rien vers `/api/chat` et ne modifie pas le champ texte.

### Lot 4 - Tests de non-contamination et observabilite

- [x] Prouver qu'une image active n'alimente pas Memory/RAG.
- [x] Prouver qu'elle n'alimente pas Identity.
- [x] Prouver qu'elle n'alimente pas Summary.
- [x] Prouver qu'elle n'alimente pas Biblio.
- [x] Prouver qu'elle n'entre pas dans `conversation["messages"]` comme contenu persistant.
- [x] Prouver l'absence de base64 dans logs, dashboard, read-models et docs.
- [x] Prouver que les logs restent content-free.
- [x] Prouver l'injection entiere ou exclusion entiere par tour.

Lot 4 livre:

- le stream chat prouve que l'image active peut etre envoyee au provider en payload multimodal sans entrer dans `conversation["messages"]`;
- les chemins `save_new_traces()`, identity turn pair, summary et embeddings ne recoivent que le dialogue persistant, jamais `data:image`, `image_url`, `image_content` ou `binary_content`;
- aucune surface runtime active image ne cable `library_document`, `catalogue_document` ou `passage documentaire`;
- l'observabilite `active_documents` couvre les decisions `injected` et `excluded`, avec `media_kind`, MIME, bytes, dimensions, hash court, provider model, payload order et reason code;
- les payloads de logs/read-models restent content-free: pas de base64, pas de data URL, pas de bytes image, pas de prompt utilisateur complet;
- la preuve distingue explicitement image injectee et image exclue pour taille provider V0.

### Lot 5 - Smoke provider minimal

- [ ] Faire un smoke OpenRouter avec image non sensible, sans committer l'image brute.
- [ ] Tester non-stream.
- [ ] Tester stream.
- [ ] Tester image trop petite ou non traitable.
- [ ] Tester une image nominale type PNG 32x32 ou fixture equivalente.
- [ ] Conserver seulement une preuve compacte: modele, statut, finish reason, usage, reason compact.
- [ ] Ne jamais conserver de base64 dans les artefacts.

## 7. Tests attendus

Preuves minimales du chantier:

- validation MIME;
- validation extension;
- validation dimensions;
- image trop petite refusee ou exclue proprement;
- image trop lourde refusee ou exclue proprement;
- absence de logs base64;
- absence de prompt base64 textuel;
- aucune injection memoire;
- aucune injection identity;
- aucune injection summary;
- aucune injection Biblio;
- aucun RAG / embedding;
- payload multimodal correct;
- payload multimodal dans l'ordre exact `text` puis `image_url`;
- payload brut avec `image_url`, pas `imageUrl`;
- fallback exclusion propre si modele/provider non compatible;
- stream toujours OK;
- frontend responsive;
- retrait image actif;
- reload navigateur sans perte d'etat actif;
- dashboard/read-models content-free.

Commandes a adapter par lot:

```bash
git status --short
git diff --check
git diff --cached --check
python3 -m py_compile app/core/active_conversation_documents.py app/core/active_document_upload_service.py app/core/active_document_prompt_lane.py app/core/chat_service.py app/core/chat_llm_flow.py app/core/llm_client.py app/server.py
python3 -m unittest app.tests.test_server_active_documents_contract
python3 -m unittest app.tests.unit.core.test_active_document_prompt_lane
python3 -m unittest app.tests.unit.core.test_active_document_non_contamination_lot5
node --check app/web/chat_active_documents.js
node app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
grep -RIn "data:image/.*base64\\|Bearer\\|OPENROUTER_API_KEY\\|sk-or-" app/tests app/web app/core app/docs 2>/dev/null || true
```

Si l'hote OVH manque des dependances Python, utiliser le conteneur applicatif comme pour les autres lots.

## 8. Hors scope

Ce chantier ne doit pas livrer:

- generation d'images;
- edition d'images;
- galerie;
- stockage serveur durable;
- agent vision separe;
- OCR automatique image;
- description automatique par un modele vision separe;
- Biblio;
- `library_document`;
- `catalogue_document`;
- `passage documentaire`;
- memoire;
- identity;
- summary;
- RAG;
- embeddings;
- ingestion documentaire persistante;
- integration dans la generation d'images V0;
- modification du modele principal sans decision separee.

## 9. Notes de vigilance

- Le modele principal est compatible aujourd'hui, mais le chantier doit verifier la capability effective au runtime ou au moins documenter clairement la dependance.
- Les images peuvent contenir des visages, documents prives, captures d'ecran, textes injonctifs ou secrets visibles: ne pas exposer le brut dans les logs ou le dashboard.
- Une description automatique d'image serait une interpretation, pas l'image elle-meme; elle exige un contrat ulterieur.
- Toute normalisation image, comme redimensionnement ou conversion, doit etre explicite. Sinon, elle viole potentiellement la regle injection entiere.
- Le contrat `injection entiere ou exclusion entiere` doit rester comprehensible pour l'utilisateur: si Frida ne voit pas l'image, elle doit pouvoir le dire simplement.
