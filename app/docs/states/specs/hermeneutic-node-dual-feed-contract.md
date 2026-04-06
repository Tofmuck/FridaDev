# Contrat de double alimentation du noeud hermeneutique

Date: 2026-03-31
Statut: spec normative active
Scope: contrat minimal de circulation parallele entre le pipeline LLM principal et le futur noeud hermeneutique

## Purpose

Le dual feed existe pour une raison precise:

- les briques runtime existantes ne doivent pas cesser d'alimenter le LLM principal;
- ces memes briques doivent aussi etre relues par le noeud;
- le noeud ne produit pas la reponse finale;
- le noeud produit un cadrage structurel qui oriente la reponse finale.

Le noeud n'est donc ni un remplacement du prompt principal, ni une simple "tonalite".
Sa sortie doit cadrer au minimum le regime de reponse, la posture de jugement, le poids relatif des sources, et le niveau de prudence ou de suspension attendu.

## Inputs

Dans l'etat actuel du repo, les familles d'entrees concernees par le dual feed sont:

- `temps`
- `memory_retrieved`
- `memory_arbitration`
- `resume`
- `identite`
- `contexte_recent`
- `web`

Leur forme canonique est actuellement portee par:

- `app/core/hermeneutic_node/inputs/time_input.py`
- `app/core/hermeneutic_node/inputs/memory_retrieved_input.py`
- `app/core/hermeneutic_node/inputs/memory_arbitration_input.py`
- `app/core/hermeneutic_node/inputs/summary_input.py`
- `app/core/hermeneutic_node/inputs/identity_input.py`
- `app/core/hermeneutic_node/inputs/recent_context_input.py`
- `app/core/hermeneutic_node/inputs/web_input.py`

Pour `identity`, le canon actif a bascule en `v2`:

- `static`
- `mutable`

Le dual feed ne relit donc plus `dynamic[]` comme forme canonique active pour l'identite.

## Flow

Le contrat de dual feed impose le flux suivant:

1. Les briques existantes continuent d'alimenter le pipeline principal.
2. En parallele, ces memes briques sont exposees sous forme canonique au seam hermeneutique.
3. Le noeud relit ces entrees canoniques et produit une synthese de cadrage.
4. Le LLM principal reste le producteur de la reponse finale, mais il doit etre cadre par cette synthese.

Dans le repo actuel, le seam de reference est deja fige dans `app/core/chat_service.py`:

- apres `prepare_memory_context(...)`
- avant `build_prompt_messages(...)`
- via `_run_hermeneutic_node_insertion_point(...)`

Le dual feed ne supprime donc pas le flux principal; il ajoute une lecture parallele normative au meme moment du pipeline.

## Node Output Contract

La sortie attendue du noeud doit etre compacte, structuree, testable, et orientee cadrage.

Elle ne doit pas se limiter a une ambiance discursive. Elle doit exprimer au minimum:

- le regime de reponse a adopter;
- la posture de jugement (`answer | clarify | suspend` au minimum);
- le poids relatif ou la priorite effective des sources utiles au tour;
- le niveau de prudence, de preuve, ou d'incertitude requis;
- d'eventuelles directives provisoires de cadrage pour la reponse finale.

La sortie du noeud ne redige pas la reponse finale utilisateur. Elle produit un contrat de reponse / posture / regime.

## LLM Relationship

Le LLM principal garde les entrees directes du pipeline.

Le contrat impose donc:

- pas de remplacement des briques directes par la seule sortie du noeud;
- pas de masquage irreversible des sources d'entree du LLM principal;
- pas de fusion qui ferait du noeud une autorite opaque et souveraine;
- oui a un cadrage explicite de la reponse finale par la sortie du noeud.

Tant que le branchement aval n'est pas implemente, le repo reste dans un etat preparatoire:

- les entrees sont deja doublement alimentees;
- la sortie du noeud n'est pas encore consommee par le LLM principal en production.

## Current Repo Grounding

Cette spec est grounded dans l'etat reel du repo au 2026-03-31:

- `app/core/chat_service.py` construit deja les objets canoniques et les expose au seam hermeneutique;
- `app/core/chat_memory_flow.py` separe deja `memory_retrieved` de `memory_arbitration`;
- `app/core/chat_prompt_context.py` continue a construire le contexte systeme et l'injection web pour le LLM principal;
- `web` reste une phase d'injection tardive apres `build_prompt_messages(...)`, mais sa matiere canonique existe deja et doit rester lisible comme telle;
- `web_input` expose maintenant `activation_mode = manual|auto|not_requested`, ce qui distingue le forcage manuel, l'auto-activation bornee et l'absence de declenchement;
- l'injection web dans le prompt principal depend du runtime web reel, pas du seul booleen HTTP `web_search`.

Le dual feed formelise donc un etat reel deja en place partiellement dans le code, au lieu d'inventer un dispositif fictif.

## Non-goals / Out of Scope

Cette spec ne tranche pas encore:

- la taxonomie finale complete des regimes discursifs;
- la doctrine detaillee de priorite des sources;
- la resolution complete des conflits inter-sources;
- le contrat `demande_utilisateur` du Lot 2;
- l'integration `Stimmung / M6`;
- le contrat final du validation agent;
- le branchement aval runtime de la sortie du noeud.

## Invariants

Les invariants suivants ne doivent pas etre violes par la suite:

- une entree canonique du noeud ne doit pas remplacer l'entree directe correspondante du LLM principal;
- le noeud doit relire les determinants, pas les dissoudre dans un texte opaque;
- la sortie du noeud doit cadrer la reponse finale, pas se substituer au LLM principal;
- la sortie du noeud doit rester compacte, testable, auditable;
- le dual feed doit rester mappe 1:1 au pipeline reel du repo;
- tant que l'aval n'est pas branche, aucune implementation ne doit faire semblant que le noeud complet pilote deja la reponse finale.
