# Frida

Frida est un système dialogique personnel de recherche : une instance de
dialogue historiquement constituée, avec mémoire, identité, jugement
herméneutique, outils documentaires et surfaces privées d'inspection. Le dépôt
`FridaDev` contient l'application qui fait fonctionner cette instance ; il ne
s'agit ni d'un chatbot générique, ni d'un scaffold, ni d'un SaaS multi-tenant.

Le projet est en **consolidation stricte sans extension fonctionnelle**. Le
travail courant vise à rendre le système existant plus lisible, cohérent, sûr,
testable et auditable sans lui ajouter opportunément de nouvelles capacités.

> **English summary.** FridaDev is the application repository for Frida, a
> personal, historically constituted dialogical research system. It combines
> conversation, memory, identity, hermeneutic judgment, explicit tool lanes,
> document workspaces, canonical persistence, and private operator
> observability. This README presents the current architecture; the maintainer
> documentation hub is [`app/docs/README.md`](app/docs/README.md).

## Ce que le système fait aujourd'hui

### Dialogue et continuité

- conversation texte et dictée vocale optionnelle ; la dictée reste un blob,
  un upload et une transcription uniques, bornés à cinq minutes ;
- réponses JSON ou streaming `text/plain`, avec un terminal de contrôle unique ;
- persistance canonique des tours utilisateur et assistant, sans canoniser un
  contenu assistant partiel en cas d'interruption ;
- résumés de conversation calculés sur le seul dialogue utilisateur/assistant ;
- Memory/RAG, contexte historique, identité statique et identité mutable ;
- branche herméneutique `stimmung -> primary -> validation`, capable de
  répondre, de suspendre explicitement un jugement ou d'adopter localement le
  régime dialogique `presence` ;
- Continuity Capsule terminale et manifeste content-free
  `main_payload_manifest_v1` pour rendre inspectable la composition du payload
  principal sans exposer son contenu.

### Contextes et agents explicites

Chaque capacité reste activée, absente ou no-op selon son propre contrat. Les
contextes ne sont pas fusionnés dans un RAG indifférencié.

- **Web** : lecture d'URL et recherche ouverte, avec découverte et lecture
  séparées, provenance runtime et garde de preuve ;
- **Documents actifs** : fichiers temporaires liés à une conversation ;
- **Documents workspace** : fichiers persistants sélectionnés explicitement
  pour une conversation ;
- **Notes** : notes Markdown d'un répertoire, sélectionnées explicitement pour
  le prochain tour ;
- **Biblio** : agent bibliothécaire et Catalogue persistants, séparés de Memory,
  du Web et des documents actifs ;
- **Agenda** : agent CalDAV borné, avec confirmations humaines pour les
  mutations externes ;
- **Adobe Docs Mode** : lecture officielle HelpX pour Photoshop/Illustrator,
  séparée de la recherche Web générale ;
- **Images actives** : images fournies comme pièces du tour, dans les limites
  du contrat multimodal existant.

Agenda, Biblio et la présence herméneutique peuvent produire une réponse finale
verrouillée. La priorité actuelle est : **Agenda, puis Biblio, puis présence**.
Un verrou valide court-circuite l'appel au modèle principal ainsi que la
résolution inutile de son secret et de son URL.

### Atelier documentaire

Les conversations peuvent être organisées dans des répertoires de travail.
Chaque répertoire possède des projections locales et, lorsqu'il est raccordé,
des artefacts Nextcloud sous une arborescence logique `/Frida/<répertoire>` :

- `Documents/` : fichiers persistants, inventaire, sélection et OCR bornée ;
- `Notes/` : notes Markdown avec création, lecture et append contrôlé ;
- `Exports/` : exports Markdown, TXT, DOCX ou PDF sans écrasement implicite ;
- `Images/` : images générées durables, séparées des images actives du chat.

Ces artefacts ont des read-models dédiés. Ils ne deviennent jamais
automatiquement Memory, Identity, Summary, Biblio ou contexte du modèle.

### Inspection opérateur

- [`/`](https://fridadev.frida-system.fr/) : chat, conversations, répertoires,
  documents, Notes, Exports, Images et toggles explicites ;
- `/dashboard` : synthèse longue durée et inspection traduite ;
- `/log` : timeline technique et export de debug ;
- `/memory-admin` : état et diagnostic Memory/RAG ;
- `/hermeneutic-admin` : pipeline herméneutique et projections associées ;
- `/identity` : lecture et édition gouvernée de l'identité ;
- `/admin` : réglages runtime et diagnostics applicatifs.

Le hostname public est protégé par Authelia. Les surfaces d'administration
restent privées et relèvent du contrat opérateur documenté ; elles ne sont pas
des API publiques de produit.

## Un tour de chat, en une vue

Le schéma détaillé et normatif se trouve dans
[`app/docs/states/architecture/fridadev-current-runtime-pipeline.md`](app/docs/states/architecture/fridadev-current-runtime-pipeline.md).

```text
Navigateur
  -> route de transport /api/chat
  -> garde des prompts constitutifs
  -> résolution session/conversation
  -> persistance du message utilisateur + résumé éventuel
  -> Memory/RAG + identité + contexte temporel
  -> Web / Adobe / Biblio / Agenda + branche herméneutique
  -> lecture explicite Notes + documents actifs/workspace
  -> construction du payload principal
       base conversationnelle et gardes
       Web -> Notes -> Documents -> Biblio
       arbitrage final lock Agenda > Biblio > présence
       Adobe
       Continuity Capsule terminale si autorisée
       main_payload_manifest_v1 content-free
  -> réponse verrouillée ou appel du modèle principal
  -> barrière de persistance canonique
  -> dérivations Memory / Identity / observabilité après preuve de sauvegarde
  -> réponse JSON ou stream avec terminal done/error unique
  -> réhydratation du chat et read-models opérateur
```

L'ordre ci-dessus décrit des effets observables. Les lanes absentes restent des
no-op ; elles ne doivent ni injecter un message vide ni déplacer les autres
sources. Les différences JSON/streaming s'arrêtent au transport : les règles de
verrou final, de canonisation et de dérivation sont communes.

## Architecture du dépôt

### Composition et transport

- `app/server.py` compose Flask, initialise les stores et enregistre les routes ;
- `app/chat_transport_routes.py` porte la frontière publique `/api/chat` ;
- `app/chat_transcription_routes.py` porte la transcription vocale ;
- `app/workspace_folder_*_routes.py` porte les routes Fichiers, Notes, Exports
  et Images générées ;
- `app/admin/*_routes.py` porte les surfaces d'administration applicatives.

### Orchestration du chat

- `app/core/chat_service.py` reste le coordinateur du tour ;
- `chat_session_flow.py` résout et valide session, conversation et transport ;
- `chat_memory_flow.py` prépare Memory/RAG et l'arbitrage ;
- `chat_prompt_context.py` construit la base et les gardes du prompt ;
- `chat_document_prompt_reads.py` unifie les lectures documentaires explicites ;
- `chat_agent_lane_orchestration.py` normalise observabilité et final locks ;
- `chat_main_payload.py` injecte les lanes tardives, la Capsule et le manifeste ;
- `chat_llm_flow.py` orchestre succès, streaming, erreurs et overrides ;
- `chat_llm_provider_exchange.py` isole l'échange avec le modèle principal ;
- `chat_assistant_finalization.py` porte sauvegarde canonique, rollback et
  effets post-save.

### Domaines

- `app/memory/` : stockage, retrieval, résumés de traces et arbitre ;
- `app/identity/` : identité statique/mutable et frontières de dérivation ;
- `app/agenda/` : agent Agenda, outils, stores temporaires et observabilité ;
- `app/biblio/` : agent bibliothécaire, outils Catalogue et rendu final ;
- `app/observability/` : événements content-free, manifestes et read-models ;
- `app/admin/` : settings runtime et services des surfaces opérateur ;
- `app/tools/` : Web, Adobe et génération d'images ;
- `app/web/` : chat navigateur et frontends opérateur ;
- `app/prompts/` : prompts versionnés ;
- `app/tests/` : tests unitaires, intégration, smoke et fixtures hermétiques ;
- `app/docs/` : contrats vivants, opérations, états, TODO et archives ;
- `benchmark/` : atelier de benchmark séparé du runtime produit.

## Frontières de déploiement et de données

Ce dépôt est la source applicative. Sur l'OVH de référence :

- `/opt/platform/fridadev` est le checkout Git applicatif ;
- `/opt/platform/fridadev-app` et `/opt/platform/fridadev-db` sont des
  sous-stacks runtime ;
- `/opt/platform` porte Docker global, Caddy, Authelia, réseaux, secrets,
  sauvegardes et services partagés.

Une modification du dépôt n'est pas automatiquement une livraison runtime. Les
changements de plateforme, de secret, de base ou de réseau ne relèvent pas de
FridaDev.

Sont versionnés : code, prompts, scripts, tests, documentation et exemples
statiques autorisés. Ne sont pas versionnés : `app/.env`, secrets, conversations,
logs runtime, bases locales, données montées, caches et fichiers d'identité
provisionnés par l'opérateur. Le Compose local monte `state/conv`, `state/logs`
et `state/data` dans le conteneur.

## Démarrage local

Prérequis : Docker avec Compose, un `app/.env` local valide construit depuis
`app/.env.example`, et les dépendances externes réellement requises par les
capacités que l'on veut exercer. Ne jamais committer le `.env` ni un secret.

```bash
cp app/.env.example app/.env
./stack.sh config
./stack.sh up
./stack.sh ps
./stack.sh health
```

Le Compose fourni lie le port publié à l'IPv4 loopback de l'hôte ; le service
local écoute donc sur `http://127.0.0.1:8093/`. Ce chemin ne reproduit pas
l'authentification publique Caddy/Authelia de l'OVH et ne doit pas être
transformé en publication réseau sans protection adaptée. `./stack.sh down`
arrête la stack locale. Ces commandes ne décrivent pas la procédure de
déploiement de l'OVH de production.

## Tests

La suite repose sur `unittest` et doit être exécutée sans provider, secret, DB
opérateur ni accès réseau réel. Dans un environnement Python contenant les
dépendances de `app/requirements.txt` :

```bash
cd app
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover
```

Les validations frontend ciblées utilisent également Node.js ; les commandes
exactes par domaine sont indiquées dans les contrats, TODO et tests concernés.
Les preuves de clôture mainteneur utilisent un conteneur jetable, le checkout
monté en lecture seule, `--network none` et `/tmp` en tmpfs.

## Documentation de référence

Commencer par le
[`hub mainteneur`](app/docs/README.md), puis choisir le contrat vivant du
domaine concerné. Les principales portes d'entrée sont :

- [pipeline runtime courant](app/docs/states/architecture/fridadev-current-runtime-pipeline.md) ;
- [Continuity Payload, manifeste et Capsule](app/docs/states/specs/frida-v1-continuity-payload-contract.md) ;
- [protocole de streaming](app/docs/states/specs/streaming-protocol.md) ;
- [répertoires de travail](app/docs/states/specs/workspace-folders-contract.md) ;
- [documents actifs](app/docs/states/specs/active-conversation-documents-contract.md) ;
- [Biblio native et Catalogue](app/docs/states/specs/frida-biblio-native-catalogue-contract.md) ;
- [agent bibliothécaire](app/docs/states/specs/frida-biblio-librarian-agent-contract.md) ;
- [agent Agenda](app/docs/states/specs/frida-agenda-agent-contract.md) ;
- [observabilité agentique](app/docs/states/specs/frida-v1-agentic-observability-contract.md) ;
- [contrat du juge Identity mutable](app/docs/states/specs/mutable-identity-judge-contract.md).

Les roadmaps et audits terminés vivent dans `app/docs/todo-done/`. Ils
documentent les décisions et preuves historiques ; ils ne remplacent pas le
code, les tests et les contrats vivants comme sources d'état courant.

## Site, contact et licence

- site : [frida-ai.fr](https://frida-ai.fr) ;
- contact : [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr) ;
- licence : [MIT](LICENSE).
