# FridaDev - generation d'images OpenRouter - TODO

Statut: actif
Date de creation: 2026-05-19
Classement: `app/docs/todo-todo/product/`
Portee: outil autonome de generation d'images dans le frontend FridaDev
Hors-scope du commit de creation: code runtime, route API, frontend, CSS, persistence, memoire, identity, documents actifs, Biblio, rebuild

## 1. Intention produit

Ajouter une generation d'images comme outil autonome integre a l'interface FridaDev:

- petit bouton dans la barre d'outils existante;
- clic -> panneau ou modal natif dans la page;
- textarea de prompt;
- menu modele;
- choix manuel du format / aspect ratio selon le modele;
- bouton generer;
- image affichee dans le panneau;
- bouton telecharger;
- aucun ajout automatique au dialogue Frida;
- aucune memoire, identity, resume, document actif, Biblio ou artefact serveur persistant en V0.

Ce n'est pas un nouveau pouvoir hermeneutique de Frida. C'est un outil lateral de l'application web FridaDev, comparable a un outil frontend adosse a OpenRouter.

Frontiere produit stricte:
- le chantier ne touche pas au prompt principal;
- il ne touche pas a la memoire, identity, summaries, active documents, Biblio, RAG, web search, Stimmung, validation agent, arbitre memoire, pipeline `/api/chat`, conversation history ou persistence conversationnelle;
- il touche seulement: bouton frontend, panneau/modal, route backend outil, module `app/tools/image_generation.py`, transport OpenRouter partage, allowlist/config modeles et logs techniques content-free.

Meme si les modeles image deviennent plus tard configurables en DB/runtime settings, l'outil reste lateral: pas d'injection dans le dialogue, pas de memoire, pas de persistence image serveur en V0.

## 2. Contraintes UI

Le composant doit sembler natif dans FridaDev:

- reutiliser `app/web/styles.css`, variables, boutons, panneaux, etats et typographie existants;
- pas de palette dediee;
- pas de mini-app visuelle autonome;
- pas de carte decorative inutile;
- responsive propre;
- prompt, erreurs, loading, succes, image et boutons sans debordement;
- image apercue dans des dimensions contraintes;
- telechargement navigateur seulement.

## 3. Findings OpenRouter verifies le 2026-05-19

Sources:
- Documentation: `https://openrouter.ai/docs/guides/overview/multimodal/image-generation`
- API modele: `https://openrouter.ai/api/v1/models?output_modalities=image`
- API rejouee en Lot 0 le 2026-05-19: 29 modeles retournes avec `output_modalities=image`.

Contrat observe:
- Endpoint recommande pour V0 FridaDev: `POST /api/v1/chat/completions`, via le transport OpenRouter existant.
- OpenRouter indique aussi le support de l'endpoint Responses, mais le repo FridaDev utilise deja Chat Completions pour ses callers OpenRouter.
- Les modeles image se decouvrent avec `output_modalities=image`.
- Le payload doit inclure `modalities`:
  - `["image", "text"]` pour les modeles image + texte;
  - `["image"]` pour les modeles image-only.
- Les options image passent par `image_config`.
- La reponse image attendue est dans `choices[0].message.images[]`.
- Chaque image est typiquement retournee comme data URL base64 dans `image_url.url`, par exemple `data:image/png;base64,...`.
- Les aspect ratios documentes globalement incluent `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`.
- Les ratios et tailles etendus (`1:4`, `4:1`, `1:8`, `8:1`, `0.5K`) sont documentes pour `google/gemini-3.1-flash-image-preview`.
- L'API modeles expose `input_modalities`, `output_modalities`, `supported_parameters`, `pricing` et `top_provider`, mais ne donne pas une matrice complete fiable des aspect ratios / tailles par modele.

Consequence V0:
- garder une table FridaDev explicite par modele pour `modalities`, `aspect_ratios`, `image_size` et limites connues;
- confirmer chaque modele retenu par un smoke minimal avant exposition UI;
- ne pas pretendre decouvrir automatiquement toutes les contraintes de format depuis l'API modeles.

## 4. Modeles V0 definitifs apres Lot 0

Ne pas chercher le modele "le plus permissif". Le choix V0 couvre des usages distincts, avec une allowlist courte.

### Confirmation API

| Usage | Generator key | Id OpenRouter | Nom API | Modalites input -> output | Parametres API utiles observes | Prix API observe | Smoke Lot 0 | Limite connue |
|---|---|---|---|---|---|---|---|---|
| Meilleur rendu general | `image_generator_openai` | `openai/gpt-5.4-image-2` | OpenAI: GPT-5.4 Image 2 | image,text,file -> image,text | `max_tokens`, `seed`, `response_format`, `temperature` non listee | prompt `0.000008`, completion `0.000015`; pas de prix image dedie dans l'API | OK: image PNG, `finish_reason=stop`, cout observe `0.224556`, latence `163008 ms` | cher/lent meme sur prompt minimal; contraintes image par ratio non detaillees par l'API |
| Rapide / economique | `image_generator_nano_banana` | `google/gemini-2.5-flash-image` | Google: Nano Banana (Gemini 2.5 Flash Image) | image,text -> image,text | `temperature`, `top_p`, `seed`, `max_tokens`, `response_format`, `structured_outputs`, `stop` | image `0.0000003`, prompt `0.0000003`, completion `0.0000025` | OK: image PNG, `finish_reason=stop`, cout observe `0.038706`, latence `4205 ms` | Gemini 3.1 preview non retenu: smoke `1K` sans image puis `0.5K` en erreur provider 400 |
| Illustration / design / style | `image_generator_recraft` | `recraft/recraft-v4.1` | Recraft: Recraft V4.1 | text,image -> image | aucun `supported_parameters` declare dans l'API | API indique prompt `0`, completion `0`; prix image non explicite | OK: image WEBP, `finish_reason=stop`, cout observe `0.04`, latence `7130 ms` | pricing et formats precis non exposes par l'API modeles; pas de sortie texte |
| Option experimentale image-only | `image_generator_flux` | `black-forest-labs/flux.2-pro` | Black Forest Labs: FLUX.2 Pro | text,image -> image | `seed` | API indique prompt `0`, completion `0`; prix image non explicite | OK: image PNG, `finish_reason=stop`, cout observe `0.075`, latence `16485 ms` | reponse base64 volumineuse; pas de sortie texte; contraintes cout/format a verifier hors API modeles |

### Table V0 figee

| generator_key | display_name | openrouter_model_id | openrouter_title | openrouter_referer | modalities | supported_aspect_ratios | supported_image_sizes | pricing_label | pricing_source | is_preview | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `image_generator_openai` | OpenAI Image | `openai/gpt-5.4-image-2` | `FridaDev / Image Generator / OpenAI` | `https://fridadev.frida-system.fr/openrouter/image-generation/openai` | `["image","text"]` | `1:1`, `16:9`, `9:16` en V0 prudente | `1K` en V0 prudente | `prix API observe: prompt 0.000008 / completion 0.000015; prix image non expose` | API modeles + smoke cout observe | non | rendu general; cout observe eleve au smoke |
| `image_generator_nano_banana` | Nano Banana | `google/gemini-2.5-flash-image` | `FridaDev / Image Generator / Nano Banana` | `https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana` | `["image","text"]` | `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` | `1K`, `2K`, `4K` | `prix API observe: image 0.0000003 / prompt 0.0000003 / completion 0.0000025` | API modeles + smoke cout observe | non | candidat rapide/economique; remplace Gemini 3.1 preview non concluant |
| `image_generator_recraft` | Recraft | `recraft/recraft-v4.1` | `FridaDev / Image Generator / Recraft` | `https://fridadev.frida-system.fr/openrouter/image-generation/recraft` | `["image"]` | `1:1`, `16:9`, `9:16` en V0 prudente | `1K` en V0 prudente | `prix image non expose par l'API modeles` | API modeles incomplete + smoke cout observe | non | illustration/design; sortie WEBP observee |
| `image_generator_flux` | Flux | `black-forest-labs/flux.2-pro` | `FridaDev / Image Generator / Flux` | `https://fridadev.frida-system.fr/openrouter/image-generation/flux` | `["image"]` | `1:1`, `16:9`, `9:16` en V0 prudente | `1K` en V0 prudente | `prix image non expose par l'API modeles` | API modeles incomplete + smoke cout observe | non | option experimentale; sortie PNG volumineuse observee |

Notes:
- `openrouter/auto` ne doit pas etre expose en V0: il rend les comparaisons et l'observabilite moins reproductibles.
- Aucun modele preview n'est retenu dans la table V0 apres Lot 0.
- Si un prix image/request n'est pas disponible dans l'API modeles, l'UI V0 ne doit pas afficher un cout previsionnel trompeur.
- Les smokes ont utilise un prompt non sensible et n'ont conserve ni image brute ni base64.

## 5. Prix et affichage UI

Le menu modele doit afficher un `pricing_label` quand l'information est exploitable:

- si l'API OpenRouter expose un prix image/request clair, l'afficher comme prix API observe;
- si l'API expose seulement `prompt=0` / `completion=0` sans prix image/request, ne pas afficher "gratuit";
- afficher plutot: `prix image non expose par l'API modeles`;
- ne pas promettre un cout exact avant generation;
- si OpenRouter renvoie un cout/usage reel dans la reponse, l'afficher apres appel seulement comme information observee;
- ne jamais logger le prompt brut ni la base64 pour calculer ou expliquer le cout.

La future table code V0 doit porter au minimum:
- `generator_key`;
- `display_name`;
- `openrouter_model_id`;
- `openrouter_title`;
- `openrouter_referer`;
- `modalities`;
- `supported_aspect_ratios`;
- `supported_image_sizes`;
- `pricing_label`;
- `pricing_source`;
- `is_preview`;
- `notes`.

Cette table doit etre confirmee en Lot 0 par API + smoke tests avant exposition UI.

## 6. Architecture cible

### Backend

Emplacement cible:
- `app/tools/image_generation.py`
- route dediee, par exemple `POST /api/tools/image-generation`

Responsabilites:
- valider prompt, modele, aspect ratio et taille;
- refuser tout modele hors allowlist;
- construire le payload OpenRouter;
- appeler `llm_client.or_chat_completions_url()` si possible;
- utiliser `main_model.api_key` via le transport existant;
- extraire `choices[0].message.images[0].image_url.url`;
- refuser proprement si aucune image n'est presente;
- retourner une data URL au frontend sans la persister.

Payload cible minimal:

```json
{
  "model": "<model_id>",
  "messages": [
    {"role": "user", "content": "<prompt utilisateur>"}
  ],
  "modalities": ["image", "text"],
  "image_config": {
    "aspect_ratio": "1:1",
    "image_size": "1K"
  },
  "stream": false,
  "metadata": {
    "frida_caller": "image_generator_nano_banana",
    "frida_slot": "image_generation_tool",
    "frida_image_model": "google/gemini-2.5-flash-image"
  },
  "trace": {
    "trace_name": "FridaDev",
    "generation_name": "FridaDev / Image Generator / Nano Banana"
  }
}
```

Attribution OpenRouter cible par generateur:

| Generator key | Title OpenRouter | Referer OpenRouter | metadata.frida_caller |
|---|---|---|---|
| `image_generator_openai` | `FridaDev / Image Generator / OpenAI` | `https://fridadev.frida-system.fr/openrouter/image-generation/openai` | `image_generator_openai` |
| `image_generator_nano_banana` | `FridaDev / Image Generator / Nano Banana` | `https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana` | `image_generator_nano_banana` |
| `image_generator_recraft` | `FridaDev / Image Generator / Recraft` | `https://fridadev.frida-system.fr/openrouter/image-generation/recraft` | `image_generator_recraft` |
| `image_generator_flux` | `FridaDev / Image Generator / Flux` | `https://fridadev.frida-system.fr/openrouter/image-generation/flux` | `image_generator_flux` |

Regles:
- utiliser le meme token et le meme projet OpenRouter partages via `main_model`;
- ne pas utiliser `user` pour nommer les generateurs;
- garder `frida_slot=image_generation_tool` pour signaler que l'outil reste lateral;
- ajouter `frida_image_model=<openrouter_model_id>` pour faciliter l'audit sans lire le prompt.

Decision runtime V0:
- ne pas creer de slot runtime DB dedie par defaut en V0;
- garder une allowlist code documentee, car le modele est choisi manuellement dans l'outil et ne pilote pas le comportement hermeneutique de Frida;
- utiliser `main_model.api_key` et `main_model.base_url` comme source de transport;
- si l'outil devient administrable, creer alors un slot `image_generation_tool` avec default model, timeout, prompt limit et allowlist.

### Frontend

Emplacements probables a confirmer en Lot 1:
- bouton outil dans `app/web/index.html`;
- module JS dedie, par exemple `app/web/chat_image_generation.js`;
- reutilisation stricte de `app/web/styles.css`.

Comportement:
- bouton image dans la zone des outils existants;
- panneau/modal integre;
- textarea prompt;
- select modele;
- select aspect ratio / taille filtre par modele;
- bouton generer;
- etats loading/error/success;
- image apercue avec dimensions contraintes;
- bouton telecharger qui cree un fichier local depuis la data URL;
- fermeture/reouverture sans injection dans le fil de chat.

## 7. Observabilite

Logs content-free uniquement:
- event `image_generation_requested`;
- modele;
- aspect_ratio;
- image_size;
- latency_ms;
- status;
- error_code;
- provider_model si disponible;
- presence ou absence d'image en reponse;
- pricing_label affiche;
- cout/usage reel seulement si OpenRouter le renvoie explicitement.

Interdits de log:
- prompt brut par defaut;
- image base64;
- data URL complete;
- Authorization;
- secret;
- contenu utilisateur injecte dans metadata/trace.

## 8. Securite et garde-fous

- prompt limite en longueur;
- timeout dedie;
- taille max de reponse ou garde sur data URL;
- modele obligatoire dans allowlist;
- aspect ratio obligatoire dans la table du modele;
- refus si `message.images` absent ou vide;
- refus si data URL non image;
- aucune persistence serveur V0;
- aucune injection dans conversation, memoire, identity, summary, active documents ou Biblio;
- aucun secret expose au frontend;
- erreurs provider normalisees et non verbatim si elles contiennent du contenu sensible.

## 9. Lots

### Lot 0 - Decouverte OpenRouter finale

- [x] Rejouer `curl -s "https://openrouter.ai/api/v1/models?output_modalities=image"` avant implementation.
- [x] Confirmer les 3 ou 4 modeles V0 definitifs.
- [x] Confirmer pour chaque modele: `modalities`, `image_config.aspect_ratio`, `image_config.image_size`, pricing utile et limites.
- [x] Faire un smoke technique minimal hors UI avec un prompt non sensible.
- [x] Figer la table V0 des formats/aspect ratios par modele.
- [x] Figer les `pricing_label` et `pricing_source` affiches par l'UI.
- [x] Figer l'attribution OpenRouter par generateur.

### Lot 1 - Backend minimal

- [x] Creer `app/tools/image_generation.py`.
- [x] Ajouter `POST /api/tools/image-generation`.
- [x] Utiliser le transport OpenRouter partage via `main_model`.
- [x] Ajouter l'attribution OpenRouter distincte par generateur.
- [x] Valider prompt, modele, aspect ratio, taille et timeout.
- [x] Extraire la premiere image depuis `choices[0].message.images[0].image_url.url`.
- [x] Retourner une erreur propre si aucune image n'est renvoyee.
- [x] Ajouter logs content-free sans prompt brut ni base64.
- [x] Retourner au frontend le `pricing_label` et l'usage/cout observe si disponible.

Contrat livre en Lot 1:
- route `POST /api/tools/image-generation`;
- payload frontend: `generator_key`, `prompt`, `aspect_ratio`, `image_size`;
- succes: `ok`, generateur, modele, `pricing_label`, format demande, `image_data_url`, `mime_type`, `provider_model`, `usage`;
- erreurs normalisees: `invalid_generator`, `invalid_prompt`, `invalid_aspect_ratio`, `invalid_image_size`, `provider_error`, `no_image`, `invalid_image_data_url`, `timeout`;
- timeout backend dedie: 180 s, pour ne pas couper les generateurs lents observes au smoke Lot 0;
- plafond data URL: 6 000 000 caracteres, garde anti-reponse absurde sans casser les images V0 observees;
- logs uniquement content-free: generateur, modele, format, statut, erreur, latence, usage/cout si disponible, type mime et taille de data URL.

### Lot 2 - Frontend integre Frida

- [ ] Ajouter le bouton outil image dans l'interface existante.
- [ ] Ajouter un panneau/modal natif FridaDev.
- [ ] Ajouter prompt, modele, aspect ratio, taille et bouton generer.
- [ ] Afficher le prix ou `prix image non expose par l'API modeles` dans le select/description modele.
- [ ] Afficher l'image dans un conteneur contraint et responsive.
- [ ] Ajouter telechargement navigateur.
- [ ] Reutiliser les styles existants; aucun style autonome.
- [ ] Gerer loading, error, success et annulation/fermeture.

### Lot 3 - Tests et preuves

- [ ] Tests unitaires backend avec fake OpenRouter response.
- [ ] Test absence d'image en reponse.
- [ ] Test refus modele hors allowlist.
- [ ] Test refus aspect ratio incompatible.
- [ ] Test affichage pricing sans promettre un cout exact quand l'API ne donne pas de prix image.
- [ ] Test attribution OpenRouter distincte par generateur.
- [ ] Test absence de secret et absence de base64 dans logs.
- [ ] Test frontend du panneau avec Playwright ou equivalent.
- [ ] Verification responsive desktop/mobile.
- [ ] Verification telechargement navigateur.

### Lot 4 - Polish et cloture V0

- [ ] Documenter le modele par defaut recommande.
- [ ] Documenter les limites V0: pas de persistence, pas d'edition, pas de memoire.
- [ ] Ajouter captures/preuves UI si demandees.
- [ ] Archiver ce TODO si l'outil V0 est livre, teste et documente.

## 10. Hors scope

- lecture d'images;
- edition d'images;
- stockage serveur;
- galerie;
- persistence d'artefacts;
- integration memoire;
- integration identity;
- integration active documents;
- integration Biblio;
- generation depuis le LLM principal;
- modification du prompt principal;
- modification du pipeline `/api/chat`;
- modification de la conversation history;
- modification de web search, Stimmung, validation agent ou arbitre memoire;
- prompt rewriting automatique par Frida;
- moderation avancee beyond provider;
- multi-image batch;
- video.

## 11. Definition de sortie V0

- Un utilisateur peut ouvrir l'outil image depuis l'UI FridaDev.
- Il peut saisir un prompt, choisir un modele et un format compatible.
- Le menu modele affiche un prix exploitable ou une mention prudente quand le prix image n'est pas expose.
- Le backend appelle OpenRouter sans exposer de secret.
- OpenRouter voit une attribution lisible et stable par generateur.
- L'image est affichee et telechargeable.
- Rien n'est injecte dans le dialogue, la memoire, identity, summary, active documents ou Biblio.
- Les logs prouvent l'appel sans prompt brut ni base64.
- Les tests couvrent backend, erreurs, UI, responsive et absence de secret.
