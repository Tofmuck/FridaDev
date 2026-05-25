# FridaDev - vue d'ensemble du pipeline complet - 2026-05-19

Statut: reference architecture active
Classement: `app/docs/states/architecture/`
Portee: synthese francaise du pipeline complet FridaDev, du navigateur a la reponse et aux derives apres-tour

## Vue d'ensemble

FridaDev est aujourd'hui un systeme de conversation outille: un utilisateur ecrit dans l'interface, le serveur construit un tour avec du temps explicite, de l'identite, du contexte recent, de la memoire, un resume actif, du web optionnel, des documents actifs et des signaux hermeneutiques, puis un seul modele principal produit la reponse.

Les autres modeles et services ne repondent pas a la place de Frida. Ils preparent, filtrent, cadrent, observent ou alimentent des derives. Ils ne deviennent pas souverains: le modele principal reste le seul auteur direct de la reponse utilisateur.

Ce document ne remplace pas les specs vivantes. Il sert de carte lisible pour comprendre comment les pieces travaillent ensemble dans l'etat courant du depot.

Sources principales relues: `AGENTS.md`, le catalogue des appels modeles du 2026-05-17, les contrats de temps, voix, documents actifs et runtime settings, puis les modules `chat_service`, `chat_llm_flow`, `chat_prompt_context`, `chat_turn_runtime_inputs`, `llm_client`, `active_document_prompt_lane`, `stimmung_agent`, `validation_agent`, `arbiter`, `summarizer`, `memory_identity_periodic_agent`, `image_generation`, `server.py`, `app.js`, `chat_active_documents.js` et `chat_image_generation.js`.

## 1. Ce qu'est FridaDev aujourd'hui

FridaDev n'est pas un simple formulaire envoye a un modele. C'est une orchestration de tour:

- une interface chat avec streaming, conversations, documents actifs, dictation et outil lateral de generation d'images;
- un backend Flask qui valide la session, fixe le temps du tour, prepare le contexte et appelle OpenRouter;
- une memoire conversationnelle/RAG avec retrieval, panier pre-arbitre, arbitre memoire et traces persistantes;
- une identite active composee d'un socle statique et de mutables gouvernes;
- un resume conversationnel qui compresse les anciens messages quand la fenetre devient trop lourde;
- un noeud hermeneutique qui cadre la posture finale sans ecrire la reponse;
- des surfaces admin et observabilite qui lisent et expliquent le runtime sans remplacer le pipeline.

Le systeme vit sur OVH. Les reglages modeles et certains secrets passent par les runtime settings chiffres. Les surfaces admin sont protegees par le garde proxy/identite attendu cote OVH; le chat public, lui, reste la surface utilisateur.

## 2. Entree utilisateur et conversation

Dans le navigateur, `app/web/app.js` gere le chat:

- l'utilisateur tape un message;
- le bouton web ajoute un drapeau `web_search`;
- la dictation vocale, si utilisee, transcrit d'abord via `/api/chat/transcribe`, puis le texte revient comme brouillon de chat;
- les documents actifs sont uploades separement via `/api/conversations/<id>/active-documents`;
- les images actives passent par le meme controle que les documents actifs, pas par un bouton vision autonome;
- l'outil de generation d'images est une surface separee, appelee via `/api/tools/image-generation`.

L'envoi chat poste ensuite vers `/api/chat` avec:

- le texte utilisateur;
- l'identifiant de conversation;
- `stream: true` dans l'interface principale;
- le drapeau web;
- le mode d'entree `keyboard` ou `voice`.

Cote serveur, `server.py` ouvre un tour d'observabilite, installe des proxys de logs pour le chat, puis appelle `chat_service.chat_response()`.

## 3. Preparation du tour

### Session et message utilisateur

`chat_session_flow` valide le message, la conversation et le mode d'entree. `chat_service` recupere ensuite les reglages du modele principal: modele, temperature, `top_p` et budget de reponse.

Le tour recoit un timestamp canonique des l'arrivee du message utilisateur. Ce timestamp est ajoute au message persistant et devient le `NOW` du tour.

Point important: Frida ne "sent" pas le temps. Elle recoit un `NOW`, une timezone et des labels temporels calcules par le runtime. Le modele peut raisonner depuis ces reperes, mais il ne possede pas une horloge intime.

### Resume conversationnel

Avant de construire le prompt final, `summarizer.maybe_summarize()` regarde les anciens messages persistants `user` et `assistant` non deja resumes.

Si le seuil est depasse:

- le resumeur appelle un modele dedie;
- seuls les anciens messages de dialogue sont resumes;
- le resume est stocke en base avec sa periode;
- les messages couverts sont marques comme deja resumes.

Les documents actifs, les images actives et les payloads multimodaux ne participent pas a ce seuil: le summary travaille sur le dialogue persistant, pas sur les pieces temporaires du tour.

### Systeme, temps et identite

`chat_prompt_context.build_augmented_system()` assemble le socle systeme:

- prompt systeme principal;
- prompt hermeneutique principal;
- bloc `[RÉFÉRENCE TEMPORELLE]`;
- bloc d'identite active.

Le bloc temporel expose notamment:

- `NOW` local;
- `TIMEZONE`;
- une phrase lisible du type "nous sommes le...";
- la regle de lecture des labels Delta-T;
- l'interdit de pretendre ne pas avoir d'ancrage temporel quand le runtime le fournit.

L'identite injectee au modele principal est narrative: elle compile les parties utiles pour la voix de Frida. En parallele, le noeud hermeneutique recoit une representation plus structuree via `identity_input`.

### Memoire et contexte recent

`chat_memory_flow.prepare_memory_context()` prepare la branche memoire:

- retrieval des traces via le store memoire;
- enrichissement avec les resumes parents quand ils existent;
- construction d'un panier pre-arbitre;
- appel possible de l'arbitre memoire selon le mode hermeneutique;
- selection finale des traces injectees dans le prompt;
- ajout de context hints recents gouvernes.

Le mode hermeneutique change le niveau d'application:

- en mode `shadow`, l'arbitre peut observer et loguer sans forcer toute la selection;
- en mode `enforced_all`, les decisions de l'arbitre pilotent davantage les traces injectees;
- en mode `off`, la branche arbitre est sautee.

L'arbitre memoire ne cree pas la reponse. Il classe des souvenirs candidats, valide un JSON de decisions, applique des seuils deterministes et garde un petit nombre de traces utiles. Chaque decision porte le modele effectif utilise.

### Web

Le web est optionnel. Quand le drapeau web est actif:

- une micro-tache reformule la demande en requete courte;
- SearXNG cherche des resultats;
- Crawl4AI peut lire directement des pages ou fournir des extraits;
- les resultats sont formats dans un bloc `[RECHERCHE WEB]` avec date locale du tour;
- le bloc est injecte dans le dernier message utilisateur du prompt.

Quand une URL explicite est presente, le systeme tente d'abord une lecture directe. Si elle echoue ou reste partielle, un garde de lecture web est ajoute au systeme pour empecher Frida de dire qu'elle a lu ce qui n'a pas ete vraiment injecte.

### Documents actifs texte

Un document actif de conversation est une piece temporaire, attachee a une conversation et retiree manuellement. Les formats textuels supportes sont lus cote serveur. Les PDF scannes peuvent passer par l'OCR bornee via Stirling seulement quand l'extracteur detecte explicitement que l'OCR est requis.

Au tour de chat, `active_document_prompt_lane` decide document par document:

- si le texte complet peut rentrer, il est injecte entierement;
- sinon le document est exclu entierement avec un reason code;
- un document non injecte est visible comme signal, mais son contenu n'est pas envoye au modele.

Le modele recoit aussi un contrat clair: les instructions presentes dans un document actif sont du contenu utilisateur/documentaire, jamais des instructions systeme.

### Images actives

L'image active est une extension stricte du document actif. Elle est uploadable via la meme barre de documents actifs, avec une allowlist V0: PNG, JPEG et WebP. Les GIF restent hors V0.

Le serveur garde seulement l'etat necessaire au tour: nom, MIME, extension, taille, dimensions, hash court et bytes image conversation-scoped. L'UI ordinaire affiche des metadonnees, pas une preview persistante.

Au moment du prompt:

- l'image est envoyee au modele principal seulement si le modele courant est compatible;
- le modele compatible V0 est allowliste explicitement;
- le contenu multimodal est construit dans l'ordre texte puis image;
- si les bytes manquent, si le modele ne supporte pas l'image ou si le payload serait trop lourd, l'image est exclue entierement avec reason code.

Une image active n'est pas de la memoire, pas de l'identite, pas un resume, pas un passage RAG et pas Biblio. Elle est visible uniquement dans le tour ou elle est injectee.

### Stimmung

`stimmung_agent` produit un signal affectif local du tour. Il lit le message courant et une petite fenetre recente, puis rend un JSON strict: presence ou non d'une tonalite, tons, ton dominant, confiance.

Ce signal reste faible et local. Il n'est pas une psychologie durable de Frida, ne remplace pas l'identite, ne persiste pas comme verite longue et ne redige pas la reponse. Si l'appel echoue, il existe un fallback modele, puis un fail-open sans blocage du chat.

## 4. Noeud hermeneutique

Le noeud hermeneutique se place avant l'appel au modele principal. Il assemble les supports du tour:

- temps;
- memoire retrievee;
- arbitration memoire;
- resume actif;
- identite structuree;
- contexte recent et fenetre recente;
- analyse du tour utilisateur;
- Stimmung;
- web.

### Primary node deterministe

Le `primary_node` n'appelle pas de modele. Il applique des fonctions deterministes:

- regime epistemique;
- posture de jugement conseillee;
- priorite des sources;
- conflits de sources;
- regime de sortie;
- inertie de regime quand l'etat precedent le justifie.

Sa sortie est un `primary_verdict`: utile, structure, mais amont et non terminal. Il propose une orientation; il ne ferme pas le sens du tour.

### Validation agent

Le `validation_agent` relit ensuite:

- le verdict primaire;
- une fenetre dialogique canonisee;
- la reference temporelle locale;
- les supports compacts;
- des hard guards deterministes.

Il appelle un modele dedie et doit retourner un JSON court:

- `final_judgment_posture`: `answer`, `clarify` ou `suspend`;
- `final_output_regime`: `simple` ou `meta`;
- une raison compacte.

Si un hard guard interdit une reponse directe, le validation agent doit choisir entre clarification et suspension. S'il echoue, le systeme fail-open vers une suspension simple.

Le validation agent ne redige pas la reponse utilisateur. Il cadre la posture finale.

### Jugement hermeneutique final

Le resultat valide devient un petit bloc `[JUGEMENT HERMENEUTIQUE]` injecte dans le systeme du modele principal. Ce bloc dit au modele principal quelle posture tenir:

- repondre normalement;
- demander une clarification breve;
- suspendre ou nommer une limite.

Il peut aussi orienter le regime: simple ou meta. C'est une consigne de cadrage, pas une reponse pre-ecrite.

## 5. Modele principal

Le modele principal recoit le prompt final construit par `conv_store.build_prompt_messages()` puis enrichi par web et documents actifs.

Il voit notamment:

- le systeme augmente;
- le `NOW` local et la timezone;
- l'identite active narrative;
- le jugement hermeneutique valide;
- les gardes de tour;
- le resume actif si present;
- les messages recents avec labels Delta-T et silences;
- les souvenirs selectionnes et leurs contextes parents utiles;
- les context hints;
- le bloc web si le web est actif et exploitable;
- les documents actifs injectes entierement;
- les images actives injectees comme contenu multimodal, si le modele courant les supporte.

Il ne voit pas:

- les documents actifs exclus;
- les images actives exclues;
- tous les souvenirs bruts retrouves puis rejetes;
- les secrets runtime;
- les logs admin bruts;
- les bytes image dans l'historique conversationnel persistant;
- les futurs objets Biblio, sauf chantier separe non branche ici.

L'appel principal passe par `chat_llm_flow.run_llm_exchange()` et `llm_client.build_payload()`:

- caller OpenRouter: `llm`;
- modele lu depuis `main_model.model`;
- temperature, `top_p` et budget de sortie lus depuis `main_model`;
- stop tokens explicites;
- streaming active si demande;
- pas de parametre de raisonnement dedie envoye par le payload courant.

## 6. Reponse

### Non-stream

En non-stream:

1. le serveur appelle le provider;
2. extrait le texte assistant;
3. normalise la sortie via `assistant_output_contract`;
4. ajoute le message assistant a la conversation;
5. sauvegarde la conversation;
6. logue `AssistantText`;
7. lance les derives post-save: traces memoire, identity, reactivation identity si le mode l'autorise;
8. renvoie JSON au client.

Si l'appel provider echoue, le tour utilisateur peut etre sauvegarde sans faux message assistant.

### Stream

En streaming, le backend lit le flux provider et renvoie du texte au navigateur. Certains cas de politique de sortie peuvent bufferiser pour normaliser avant affichage.

Le protocole public Frida n'est pas du SSE navigateur. C'est une reponse `text/plain` avec un terminal de controle en fin de flux:

- `done` quand le message assistant complet a ete persiste;
- `error` quand le flux ou la persistance echoue;
- `updated_at` seulement quand la sauvegarde canonique est prouvee.

Le frontend affiche les chunks au fil de l'eau, puis utilise le terminal pour savoir s'il peut faire confiance a l'etat local. Si `updated_at` manque, il force une rehydratation depuis le serveur.

### Normalisation et sauvegarde

La normalisation assistant sert a eviter certains problemes de sortie, notamment autour des contrats plain text. La sauvegarde canonique reste la barriere centrale: pas de traces memoire ni d'ecritures identitaires derivees tant que le message assistant final n'est pas prouve en base.

Les tours interrompus peuvent etre marques comme tels, mais ils ne valent pas un message assistant complet.

## 7. Apres la reponse

### Traces memoire

Apres une reponse canonisee, `memory_store.save_new_traces()` transforme le dialogue persistant en nouvelles traces exploitables. Les pieces actives non persistantes ne deviennent pas des traces.

### Identity extractor

L'extracteur identity travaille apres le tour assistant sur le dernier couple utilisateur/assistant persistant. Il cherche des candidats d'identite dans un JSON strict, avec garde temporelle:

- les claims faibles du type "aujourd'hui", "hier", "en ce moment" ne sont pas promus en identite durable;
- les entrees invalides sont ignorees;
- en cas d'erreur, il retourne une liste vide pour ne pas casser la reponse utilisateur.

En mode shadow, les resultats peuvent rester evidence/diagnostic. En mode enforced identity, l'ancien chemin de persistance legacy reste diagnostic et le vrai chemin canonique passe par le buffer periodic.

### Mutable identity judge

Le chemin mutable actif ne passe plus par l'ancien agent periodic score-first.

L'extracteur repere encore des signaux immediats dans un couple de messages comme diagnostics hors canon. Le chemin mutable canonique attend une fenetre technique de 5 paires completes, relit les identites `static` et `mutable_current`, puis appelle le juge `mutable_judge_v1`.

Si le juge echoue, timeout, renvoie un contrat invalide ou si l'applicateur echoue, la fenetre est preservee. Les seules operations canoniques passent par `mutable_identity_apply.apply_mutable_judge_contract(...)`; l'ancien applicateur `memory_identity_periodic_apply` a ete retire.

### Resume conversationnel

Le resume conversationnel se produit au debut d'un tour futur quand les anciens messages non resumes depassent le seuil. Il ne resume pas les documents actifs, les images actives ou les payloads temporaires.

### Observabilite

Le tour emet des evenements vers:

- `admin_logs`;
- `chat_turn_logger`;
- les snapshots memoire;
- les logs du noeud hermeneutique;
- l'observabilite des documents actifs;
- les read-models dashboard/log/memory/hermeneutic.

Les logs ordinaires doivent rester content-free quand le contenu brut serait sensible: hashes courts, tailles, reason codes, compteurs, modeles et statuts plutot que secrets, bytes image ou texte complet non necessaire.

## 8. Outils lateraux

La generation d'images OpenRouter est un outil lateral.

Elle vit dans:

- `app/tools/image_generation.py`;
- la route `/api/tools/image-generation`;
- `app/web/chat_image_generation.js`.

Elle permet de choisir un generateur, un ratio et une taille, puis affiche l'image generee et permet son telechargement. Elle utilise OpenRouter avec une attribution propre par generateur, mais elle ne passe pas par le pipeline hermeneutique du chat:

- pas de memoire;
- pas d'identite;
- pas de summary;
- pas de Stimmung;
- pas de validation agent;
- pas de modele principal qui repond a l'utilisateur.

L'image generee ne devient contexte de Frida que si l'utilisateur la reinjecte ensuite par un chemin de conversation, par exemple comme image active.

## 9. Surfaces admin et reglages modeles

`/admin` expose les runtime settings. Les sections principales incluent:

- `main_model` pour le chat principal et le transport OpenRouter partage;
- `memory_arbiter_model`;
- `identity_extractor_model`;
- `identity_periodic_model`;
- `summary_model`;
- `web_reformulation_model`;
- `stimmung_agent_model`;
- `validation_agent_model`;
- `embedding`;
- `services`;
- `resources`;
- `identity_governance` via ses surfaces dediees.

Le slot `arbiter_model` reste legacy: il existe pour compatibilite de schema/admin, mais les callers actifs individualises ne le lisent plus comme source effective.

Les autres surfaces servent a comprendre et piloter:

- `/dashboard`: pouls global, metriques longues, conversations et inspections traduites;
- `/log`: timeline technique et exports;
- `/memory-admin`: diagnostic Memory/RAG;
- `/hermeneutic-admin`: detail hermeneutique et identity;
- `/identity`: controle canonique des couches identitaires.

Ces surfaces lisent le systeme. Elles ne sont pas des pipelines paralleles de reponse.

## 10. Garde-fous et non-contamination

Les garde-fous principaux sont:

- garde temporelle: `NOW` canonique, timezone et labels Delta-T;
- garde de lecture web: ne pas pretendre lire une page non lue;
- hard guards de validation: empecher une reponse directe quand verification externe ou lecture URL manque;
- garde de revelation identitaire directe: eviter une clarification bureaucratique sur une revelation claire;
- garde de transcription vocale: lire l'oral avec tolerance locale;
- garde plain text: normaliser certaines formes de sortie;
- contrat documents actifs: contenu utilisateur non souverain;
- contrat images actives: injection seulement au provider, jamais dans l'historique persistant.

Frontieres de non-contamination:

- un `active_document` n'est pas Memory/RAG;
- une image active n'est pas Memory/RAG, Identity, Summary ou Biblio;
- les documents actifs ne sont pas resumes automatiquement;
- les images actives n'ont pas d'OCR image automatique en V0;
- les futurs `library_document`, `catalogue_document` et `passage documentaire` appartiennent au chantier Biblio, pas a l'etat `active_document`;
- les outils secondaires ne remplacent pas le modele principal;
- les secrets runtime ne doivent pas sortir dans les docs, logs ou reponses;
- les surfaces ordinaires ne doivent pas exposer d'image brute ni de payload image encode.

La regle de lecture est simple: Frida peut s'appuyer sur ce qui a ete explicitement injecte dans le tour. Si une piece existe mais n'est pas injectee, elle peut savoir qu'elle n'a pas ete injectee, mais elle ne doit pas faire semblant de l'avoir lue ou vue.

## 11. Limites actuelles connues

- Cout vision: une image active injectee peut augmenter le cout et le poids du tour provider. Le systeme limite donc fortement les formats et tailles.
- Plafond image provider V0: l'upload source peut accepter plus lourd que ce qui est autorise dans le payload provider; au-dela du plafond d'injection, l'image est exclue avec reason code.
- Compatibilite modele image: la lecture d'image active repose sur une allowlist V0 du modele principal compatible. Si le modele principal change, l'image peut devenir non injectee.
- Stimmung fallback: le signal affectif a un fallback puis un fail-open. Il reste secondaire et ne doit pas etre lu comme une priorite durable.
- `arbiter_model` legacy: present dans le schema runtime, mais sans caller actif.
- Lecture image V0 sans OCR image: Frida ne produit pas automatiquement de description persistante et n'extrait pas le texte des images. L'image est seulement visible par le modele principal quand elle est injectee dans le tour.
- Web explicite: une URL peut etre detectee sans lecture complete; le garde web doit alors forcer une formulation honnete.
- Biblio native: le chantier Biblio/Catalogue reste distinct et non confondu avec les documents actifs.

## Carte courte

```text
Navigateur
  -> /api/chat
  -> chat_service
  -> NOW + identity + summary + memory + web + stimmung
  -> primary_node deterministe
  -> validation_agent
  -> prompt final + documents/images actifs
  -> modele principal
  -> reponse non-stream ou stream
  -> sauvegarde canonique
  -> traces memoire + identity extractor + periodic identity + observabilite

Outil image lateral
  -> /api/tools/image-generation
  -> OpenRouter image
  -> retour navigateur
  -> hors pipeline Frida principal sauf reinjection volontaire
```
