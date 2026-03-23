# Frida

## English

Frida is an independent research and development project in artificial intelligence.

This repository captures a working state of the project as of **March 23, 2026**. It brings together an autonomous software base for `Frida`, structured around a dedicated Docker stack, a separate PostgreSQL memory layer, a sober web interface, and a minimal layer of technical validation.

Frida is not conceived here as a simple conversational product. The project takes up a more demanding question: **what can a machine genuinely understand?**

### Website and contact

- website: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### Repository state as of March 23, 2026

Current repository state:

- dedicated Docker stack: `fridadev`
- main container: `FridaDev`
- Flask-served web application
- user interface in `app/web/`
- business memory stored in PostgreSQL
- memory, identity, and hermeneutic logic in `app/core/`, `app/memory/`, and `app/identity/`
- minimal validation layer available in `app/minimal_validation.py`

What the repository versions:

- application code
- the Docker stack
- operational scripts
- static system prompts
- web assets
- configuration examples
- working documentation

What the repository does **not** version:

- `app/.env`
- runtime state in `state/`
- conversations, logs, and local data
- real secrets, tokens, and DSNs
- backups and parasitic system files

Current documentation layout:

- `app/docs/states/`: reference states, baselines, specs, and situation documents
- `app/docs/todo-done/`: completed audits, validations, and finished workstreams
- `app/docs/todo-todo/`: roadmaps, open work items, and action briefs

This repository therefore represents a **living state of an ongoing worksite**, not a frozen product release.

### Essential structure

- `docker-compose.yml`: stack definition
- `stack.sh`: operational commands (`up`, `restart`, `ps`, `health`, etc.)
- `app/`: main application code
- `app/web/`: user interface and admin interface
- `app/prompts/`: static system prompts
- `app/docs/`: structured working documentation

### The project

Frida is an independent research and development project in artificial intelligence. At the crossroads of hermeneutic philosophy, software architecture, and language models, it takes up a decisive question: **what can a machine genuinely understand?**

The project does not merely seek to produce answers. It examines the conditions of possibility for an artificial intelligence capable of continuity, structured memory, the hierarchical ordering of evidence, and coherence over time. An artificial intelligence organized not around plausibility alone, but around interpretive rigor: making its uncertainty explicit, acknowledging incomprehension, and suspending its response when the conditions of validity are not met.

Frida starts from an observation: current systems often excel at generation, yet still struggle to sustain genuine interpretive stability. Between a plausible answer and situated understanding, the gap remains immense, and it constitutes one of the major aporias of contemporary language models. It is this gap that Frida takes as its object.

Designed by a philosopher, philosophy teacher, and independent developer, the project articulates technical experimentation, transmission, and theoretical rigor. The aim is less to make a machine speak than to build an architecture capable of assuming a more rigorous relation to language, memory, context, and dialogue.

Frida is less a product than a worksite: a living inquiry into the possibility of an interpretive artificial intelligence.

### Research axes

#### 1. Understanding and interpretation

Distinguish between a plausible answer and situated understanding. Articulate the conditions under which a machine may be said to understand, and not merely to generate.

#### 2. Structured memory and continuity

Build a memory architecture capable of maintaining coherence over time, distinguishing traces according to their evidential value, and managing their obsolescence.

#### 3. Rigor and suspension of response

Develop the capacity not to answer when the conditions of validity are not met. Explicit uncertainty as an epistemic stance, not as a system defect.

#### 4. Hermeneutic architecture

Design layers of arbitration and inference that operate on contextualized, hierarchized, revisable traces, rather than on mere surface probabilities.

### Architecture — overview

Frida’s architecture distinguishes three fundamental layers:

- structured memory
- contextual interpretation
- arbitration module

The arbitration module is responsible for evaluating the coherence of inferences before any response is given, making residual uncertainty explicit, and suspending processing when the available evidence is insufficient.

The separation between **generation** and **validation** is one of the project’s central invariants.

### Starting the stack

Local stack operations:

```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

The `app/.env` file is not versioned. It must be created locally from `app/.env.example`, then adjusted to match the target infrastructure.

### Contribution

The project is open to serious exchanges and contributions.

Frida is not an open project in the vague sense of the term: it is an exacting worksite, open to discussion and useful contribution. Rigor matters more than quantity.

Profiles from complementary backgrounds are especially welcome:

- philosophy
- language models
- software architecture
- memory and context
- systems design
- documentation
- epistemology

### License

This repository is distributed under the **MIT License**. See [LICENSE](LICENSE).

## Français

Frida est un projet indépendant de recherche et de développement en intelligence artificielle.

Ce dépôt correspond à un état de travail du projet au **23 mars 2026**. Il rassemble une base logicielle autonome pour `Frida`, structurée autour d'une stack Docker dédiée, d'une mémoire PostgreSQL séparée, d'une interface web sobre, et d'une couche minimale de validation technique.

Frida n'est pas pensé ici comme un simple produit conversationnel. Le projet prend pour objet une question plus exigeante : **qu'est-ce qu'une machine peut réellement comprendre ?**

### Site et contact

- site : [https://frida-ai.fr](https://frida-ai.fr)
- contact : [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### État du dépôt au 23 mars 2026

État actuel du repo :

- stack Docker dédiée : `fridadev`
- conteneur principal : `FridaDev`
- application web servie par Flask
- interface utilisateur dans `app/web/`
- mémoire métier stockée en PostgreSQL
- logique mémoire, identitaire et herméneutique dans `app/core/`, `app/memory/` et `app/identity/`
- couche minimale de validation disponible dans `app/minimal_validation.py`

Ce que le dépôt versionne :

- le code applicatif
- la stack Docker
- les scripts d'exploitation
- les prompts système statiques
- les assets web
- les exemples de configuration
- la documentation de travail

Ce que le dépôt **ne** versionne pas :

- `app/.env`
- l'état runtime dans `state/`
- les conversations, logs et données locales
- les secrets, tokens et DSN réels
- les backups et fichiers parasites du système

Organisation documentaire actuelle :

- `app/docs/states/` : états de référence, baselines, specs et documents de situation
- `app/docs/todo-done/` : audits, validations et chantiers déjà bouclés
- `app/docs/todo-todo/` : feuilles de route, travaux ouverts et briefs d'action

Ce dépôt représente donc un **état vivant du chantier**, pas une version produit figée.

### Arborescence essentielle

- `docker-compose.yml` : définition de la stack
- `stack.sh` : commandes d'exploitation (`up`, `restart`, `ps`, `health`, etc.)
- `app/` : code applicatif principal
- `app/web/` : interface utilisateur et interface admin
- `app/prompts/` : prompts système statiques
- `app/docs/` : documentation de travail structurée

### Le projet

Frida est un projet indépendant de recherche et de développement en intelligence artificielle. À la croisée de la philosophie herméneutique, de l'architecture logicielle et des modèles de langage, il prend pour objet une question décisive : **qu'est-ce qu'une machine peut réellement comprendre ?**

Le projet ne cherche pas seulement à produire des réponses. Il interroge les conditions de possibilité d'une intelligence artificielle capable de continuité, de mémoire structurée, de hiérarchisation des preuves et de cohérence dans le temps. Une intelligence artificielle qui ne soit pas organisée autour de la seule plausibilité, mais autour de la rigueur interprétative : expliciter son incertitude, assumer l'incompréhension, suspendre la réponse lorsque les conditions de validité ne sont pas réunies.

Frida part d'un constat : les systèmes actuels excellent souvent dans la génération, mais peinent encore à soutenir une véritable stabilité interprétative. Entre réponse plausible et compréhension située, l'écart reste immense et constitue l'une des apories majeures des modèles de langage contemporains. C'est cet écart que Frida prend pour objet.

Conçu par un philosophe, enseignant de philosophie et développeur indépendant, le projet articule expérimentation technique, transmission et exigence théorique. Il s'agit moins de faire parler une machine que de construire une architecture capable d'assumer un rapport plus rigoureux au langage, à la mémoire, au contexte et au dialogue.

Frida est moins un produit qu'un chantier : une recherche vivante sur la possibilité d'une intelligence artificielle interprétative.

### Axes de recherche

#### 1. Compréhension et interprétation

Distinguer réponse plausible et compréhension située. Articuler les conditions sous lesquelles une machine peut être dite comprendre, et non seulement générer.

#### 2. Mémoire structurée et continuité

Construire une architecture mémorielle capable de maintenir la cohérence dans le temps, de distinguer les traces selon leur valeur probante et de gérer leur obsolescence.

#### 3. Rigueur et suspension de réponse

Développer la capacité à ne pas répondre lorsque les conditions de validité ne sont pas réunies. L'incertitude explicite comme posture épistémique, non comme défaut du système.

#### 4. Architecture herméneutique

Concevoir des couches d'arbitrage et d'inférence qui opèrent sur des traces contextualisées, hiérarchisées, révisables, et non sur de simples probabilités de surface.

### Architecture — aperçu

L'architecture de Frida distingue trois couches fondamentales :

- mémoire structurée
- interprétation contextuelle
- module d'arbitrage

Le module d'arbitrage est chargé d'évaluer la cohérence des inférences avant toute réponse, d'expliciter l'incertitude résiduelle, et de suspendre le traitement lorsque les preuves disponibles sont insuffisantes.

La séparation entre **génération** et **validation** est l'un des invariants centraux du projet.

### Démarrage de la stack

Exploitation locale de la stack :

```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

Le fichier `app/.env` n'est pas versionné. Il doit être créé localement à partir de `app/.env.example`, puis ajusté en fonction de l'infrastructure cible.

### Contribution

Le projet est ouvert aux échanges et aux contributions sérieuses.

Frida n'est pas un open project au sens vague du terme : c'est un chantier exigeant, ouvert à la discussion et à la contribution utile. La rigueur prime sur la quantité.

Des profils venant d'horizons complémentaires sont particulièrement bienvenus :

- philosophie
- modèles de langage
- architecture logicielle
- mémoire et contexte
- design de systèmes
- documentation
- épistémologie

### Licence

Ce dépôt est distribué sous **licence MIT**. Voir [LICENSE](LICENSE).
