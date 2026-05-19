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

Ce n'est pas un nouveau pouvoir hermeneutique de Frida. C'est un outil utilisateur lateral, comparable a un outil frontend adosse a OpenRouter.

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

## 4. Modeles candidats V0

Ne pas chercher le modele "le plus permissif". Le choix V0 doit couvrir des usages distincts, avec une allowlist courte.

| Usage | Id OpenRouter | Nom API | Modalites input -> output | Parametres API utiles observes | Formats / tailles | Prix API observe | Raison de selection | Limite connue |
|---|---|---|---|---|---|---|---|---|
| Meilleur rendu general | `openai/gpt-5.4-image-2` | OpenAI: GPT-5.4 Image 2 | image,text,file -> image,text | `max_tokens`, `seed`, `response_format`, `temperature` non listee | A verifier en Lot 0; commencer par `1:1`, `16:9`, `9:16` seulement si smoke OK | prompt `0.000008`, completion `0.000015`; pas de prix image dedie dans l'API | option generale haut de gamme, large contexte, multimodale | probablement plus couteux; contraintes image par ratio non detaillees par l'API |
| Rapide / economique | `google/gemini-3.1-flash-image-preview` | Google: Nano Banana 2 (Gemini 3.1 Flash Image Preview) | image,text -> image,text | `temperature`, `top_p`, `seed`, `max_tokens` | ratios globaux + ratios etendus documentes; `0.5K`, `1K`, `2K`, `4K` documentes | prompt `0.0000005`, completion `0.000003`; pas de prix image dedie dans l'API | bon candidat par defaut V0: rapide, flexible, support formats etendus documente | modele preview; verifier stabilite et reponse image sur FridaDev |
| Illustration / design / style | `recraft/recraft-v4.1` | Recraft: Recraft V4.1 | text,image -> image | aucun `supported_parameters` declare dans l'API | description API: ~1K et multiples aspect ratios; table exacte a maintenir apres smoke | API indique prompt `0`, completion `0`; prix image non explicite | orientation design / esthetique, utile pour illustrations et assets | pricing et formats precis non exposes par l'API modeles; pas de sortie texte |
| Option experimentale image-only | `black-forest-labs/flux.2-pro` | Black Forest Labs: FLUX.2 Pro | text,image -> image | `seed` | A verifier en Lot 0; table FridaDev requise | API indique prompt `0`, completion `0`; prix image non explicite | image-only haute qualite, bon contrepoint aux modeles texte+image | pas de texte; contraintes cout/format a verifier hors API modeles |

Notes:
- `openrouter/auto` ne doit pas etre expose en V0: il rend les comparaisons et l'observabilite moins reproductibles.
- Les modeles preview doivent etre marques comme tels dans le menu si exposes.
- Si un prix image/request n'est pas disponible dans l'API modeles, l'UI V0 ne doit pas afficher un cout previsionnel trompeur.

## 5. Architecture cible

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
    "frida_caller": "image_generation",
    "frida_slot": "image_generation_tool"
  },
  "trace": {
    "trace_name": "FridaDev",
    "generation_name": "FridaDev / Image Generation"
  }
}
```

Attribution OpenRouter cible:
- caller: `image_generation`;
- title: `FridaDev / Image Generation`;
- referer: `https://fridadev.frida-system.fr/openrouter/image-generation`;
- metadata: `frida_caller=image_generation`, `frida_slot=image_generation_tool`.

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

## 6. Observabilite

Logs content-free uniquement:
- event `image_generation_requested`;
- modele;
- aspect_ratio;
- image_size;
- latency_ms;
- status;
- error_code;
- provider_model si disponible;
- presence ou absence d'image en reponse.

Interdits de log:
- prompt brut par defaut;
- image base64;
- data URL complete;
- Authorization;
- secret;
- contenu utilisateur injecte dans metadata/trace.

## 7. Securite et garde-fous

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

## 8. Lots

### Lot 0 - Decouverte OpenRouter finale

- [ ] Rejouer `curl -s "https://openrouter.ai/api/v1/models?output_modalities=image"` avant implementation.
- [ ] Confirmer les 3 ou 4 modeles V0 definitifs.
- [ ] Confirmer pour chaque modele: `modalities`, `image_config.aspect_ratio`, `image_config.image_size`, pricing utile et limites.
- [ ] Faire un smoke technique minimal hors UI avec un prompt non sensible.
- [ ] Figer la table V0 des formats/aspect ratios par modele.

### Lot 1 - Backend minimal

- [ ] Creer `app/tools/image_generation.py`.
- [ ] Ajouter `POST /api/tools/image-generation`.
- [ ] Utiliser le transport OpenRouter partage via `main_model`.
- [ ] Ajouter l'attribution `FridaDev / Image Generation`.
- [ ] Valider prompt, modele, aspect ratio, taille et timeout.
- [ ] Extraire la premiere image depuis `choices[0].message.images[0].image_url.url`.
- [ ] Retourner une erreur propre si aucune image n'est renvoyee.
- [ ] Ajouter logs content-free sans prompt brut ni base64.

### Lot 2 - Frontend integre Frida

- [ ] Ajouter le bouton outil image dans l'interface existante.
- [ ] Ajouter un panneau/modal natif FridaDev.
- [ ] Ajouter prompt, modele, aspect ratio, taille et bouton generer.
- [ ] Afficher l'image dans un conteneur contraint et responsive.
- [ ] Ajouter telechargement navigateur.
- [ ] Reutiliser les styles existants; aucun style autonome.
- [ ] Gerer loading, error, success et annulation/fermeture.

### Lot 3 - Tests et preuves

- [ ] Tests unitaires backend avec fake OpenRouter response.
- [ ] Test absence d'image en reponse.
- [ ] Test refus modele hors allowlist.
- [ ] Test refus aspect ratio incompatible.
- [ ] Test absence de secret et absence de base64 dans logs.
- [ ] Test frontend du panneau avec Playwright ou equivalent.
- [ ] Verification responsive desktop/mobile.
- [ ] Verification telechargement navigateur.

### Lot 4 - Polish et cloture V0

- [ ] Documenter le modele par defaut recommande.
- [ ] Documenter les limites V0: pas de persistence, pas d'edition, pas de memoire.
- [ ] Ajouter captures/preuves UI si demandees.
- [ ] Archiver ce TODO si l'outil V0 est livre, teste et documente.

## 9. Hors scope

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
- prompt rewriting automatique par Frida;
- moderation avancee beyond provider;
- multi-image batch;
- video.

## 10. Definition de sortie V0

- Un utilisateur peut ouvrir l'outil image depuis l'UI FridaDev.
- Il peut saisir un prompt, choisir un modele et un format compatible.
- Le backend appelle OpenRouter sans exposer de secret.
- L'image est affichee et telechargeable.
- Rien n'est injecte dans le dialogue, la memoire, identity, summary, active documents ou Biblio.
- Les logs prouvent l'appel sans prompt brut ni base64.
- Les tests couvrent backend, erreurs, UI, responsive et absence de secret.
