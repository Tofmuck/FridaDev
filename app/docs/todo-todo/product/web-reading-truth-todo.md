# Web Reading Truth - TODO

Objectif: cadrer un mini-chantier runtime/user-facing pour que Frida dise vrai sur ce qu'elle a reellement lu sur le web, n'assimile plus un snippet a une lecture de page, et n'enfouisse plus une lecture fictive en memoire durable.

## Etat apres tranche docs (2026-04-04)

Cas de reference verifie:
- conversation: `28756d17-061b-4058-8199-cfebfe46075f`
- tour URL Mediapart: `turn-b942ad36-eab8-4cba-8430-b4db2c629dbd`
- URL fournie par l'utilisateur:
  - `https://blogs.mediapart.fr/christophe-muck/blog/030426/apres-la-garde-vue-de-rima-hassan-ce-que-l-occident-refuse-de-voir`

Constats runtime/code deja revalides:
- l'URL explicite fournie par l'utilisateur n'est pas traitee comme source primaire a lire avant la recherche generique;
- le pipeline fait d'abord `reformulate(user_msg)` puis `search(query)`;
- `crawl(url)` peut renvoyer un markdown vide sans faire echouer le tour;
- un `search_snippet` peut alors etre injecte a la place d'une lecture de page;
- `web_search.status=ok` signifie seulement "des resultats existent", pas "la page cible a ete lue";
- le LLM peut ensuite sur-pretendre avoir lu la page;
- cette sur-pretention peut remonter jusqu'a la memoire durable cote Frida.

Point de cadrage central:
- le probleme principal n'est pas seulement la troncature;
- le probleme principal est la verite de lecture web.

## Objectif produit

Frida doit pouvoir dire, pour une page web demandee par l'utilisateur, a quel niveau d'acces elle se trouve reellement:
- page lue;
- page partiellement lue;
- extrait/snippet seulement;
- ou page non lue.

Le produit ne doit plus:
- confondre fallback de recherche et lecture primaire;
- laisser croire que `status=ok` vaut lecture de page;
- produire ou memoriser des formulations qui pretendent une lecture non soutenue.

## Non-objectifs

Hors scope de ce mini-chantier:
- refonte complete du pipeline web;
- remplacement de SearXNG, Crawl4AI ou du provider LLM;
- amelioration generale de qualite de crawl hors question de verite;
- redesign large des prompts backend;
- chantier UI/admin large;
- restart live, changements `.env`, ou migration d'infra;
- reouverture du chantier memoire global hors lien direct avec la verite de lecture web.

## Definition of done

- [ ] Une URL explicite fournie par l'utilisateur est traitee comme source primaire prioritaire.
- [ ] Le runtime produit un `read_state` veridique pour la page cible.
- [ ] Un `search_snippet` n'est plus confondu avec une lecture de page.
- [ ] Frida ne peut plus affirmer avoir lu une page quand `read_state` ne le soutient pas.
- [ ] Une pretention de lecture non soutenue ne devient plus une trace durable cote Frida.
- [ ] Les logs de production permettent de diagnostiquer le cas sans replay manuel du code.

## Vocabulaire runtime a introduire

Statuts cibles minimaux a cadrer:
- [ ] `page_read`
- [ ] `page_partially_read`
- [ ] `page_not_read_crawl_empty`
- [ ] `page_not_read_error`
- [ ] `page_not_read_snippet_fallback`

Contraintes de vocabulaire:
- [ ] definir ce qui autorise une formulation du type "j'ai lu la page";
- [ ] definir ce qui n'autorise qu'une formulation du type "j'ai trouve un resultat / un extrait / un snippet";
- [ ] expliciter qu'un snippet injecte n'est pas une preuve de lecture primaire.

## Sous-chantier 1 - Statut de lecture web veridique

- [ ] Introduire un `read_state` explicite pour la source cible issue du message utilisateur.
- [ ] Faire apparaitre la difference entre:
  - lecture primaire reussie;
  - lecture partielle;
  - echec silencieux avec markdown vide;
  - fallback snippet.
- [ ] Ne plus laisser `status=ok` porter a lui seul une promesse implicite de lecture.
- [ ] Garder ce cadrage petit et borne: pas de taxonomie web generale au-dela de ce qui sert la verite de lecture.

## Sous-chantier 2 - Traitement prioritaire des URLs explicites

- [ ] Detecter de maniere explicite la presence d'une URL fournie par l'utilisateur.
- [ ] Tenter une lecture directe de cette URL avant toute recherche generique.
- [ ] Conserver cette URL comme source primaire nominale, meme si une recherche complementaire est ensuite necessaire.
- [ ] N'utiliser la recherche generique qu'en fallback ou en enrichissement borne.
- [ ] Rendre visible dans les preuves runtime si le tour a suivi le chemin:
  - URL explicite -> lecture directe -> reponse;
  - URL explicite -> lecture vide/erreur -> fallback;
  - pas d'URL explicite -> recherche generique.

## Sous-chantier 3 - Garde anti-mensonge dans la reponse

- [ ] Interdire les formulations de lecture directe si `read_state` n'est pas compatible.
- [ ] Cadrer explicitement des formulations a interdire quand la page n'a pas ete lue:
  - `je l'ai sous les yeux`
  - `j'ai lu l'article`
  - `dans le texte tu dis ...`
- [ ] Cadrer explicitement les formulations encore permises:
  - resultat trouve;
  - extrait disponible;
  - snippet;
  - absence de lecture directe.
- [ ] Eviter le faux bon correctif "prompt only" de surface sans signal runtime veridique.

## Sous-chantier 4 - Garde anti-mensonge en memoire durable

- [ ] Empecher qu'une pretention de lecture non soutenue devienne une evidence identitaire durable cote Frida.
- [ ] Decider ou le filtrage minimal doit vivre:
  - validation amont de l'assertion;
  - non-retention en memoire;
  - ou les deux.
- [ ] Ajouter une preuve cible:
  - le cas Mediapart ne doit plus produire de trace durable du type "claims to have the linked article open and read it".
- [ ] Garder le perimetre strictement borne a la verite de lecture web, sans reouvrir la gouvernance memoire generale.

## Sous-chantier 5 - Observability suffisante

- [ ] Exposer si une URL explicite a ete detectee.
- [ ] Exposer le `read_state` reel.
- [ ] Exposer la difference entre lecture primaire et fallback.
- [ ] Exposer `used_content_kind`.
- [ ] Exposer la longueur de contenu reellement injecte.
- [ ] Exposer si la page cible a produit un crawl vide, une erreur, une lecture partielle, ou un snippet fallback.
- [ ] Faire de cette visibilite un livrable de verite produit, pas un luxe secondaire.

## Preuves attendues pour clore le mini-chantier

- [ ] Reproduction du cas Mediapart avec URL explicite et `read_state` visible.
- [ ] Cas de lecture primaire reussie montrant une difference claire avec le fallback snippet.
- [ ] Cas `crawl_empty` montrant une reponse prudente sans pretention de lecture.
- [ ] Cas de logs prod montrant, sans replay code, l'URL cible, le chemin suivi, le `used_content_kind`, et la longueur injectee.
- [ ] Cas memoire montrant qu'une lecture fictive n'est plus retenue en durable.

## Faux bons correctifs a eviter

- [ ] Requalifier le probleme comme simple bug de troncature.
- [ ] Corriger seulement la phrase du LLM sans introduire de verite runtime.
- [ ] Corriger seulement le crawl sans traiter la garde memoire.
- [ ] Corriger seulement la memoire sans traiter la source primaire et le langage de sur-pretention.
- [ ] Ajouter un log `truncated` de plus sans exposer la lecture primaire vs fallback.
- [ ] Lancer une refonte web complete alors qu'une tranche plus petite suffit.

## Surface probable concernee au prochain cycle

Surface probable du patch cycle suivant, a garder dans un seul mini-chantier:
- `app/tools/web_search.py`
- `app/core/chat_prompt_context.py`
- `app/core/chat_service.py`
- `app/core/chat_llm_flow.py`
- `app/core/hermeneutic_node/doctrine/epistemic_regime.py`
- `app/core/hermeneutic_node/inputs/web_input.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/core/chat_memory_flow.py`
- `app/memory/memory_identity_dynamics.py`
- `app/memory/hermeneutics_policy.py`
- `app/prompts/main_system.txt`
- `app/prompts/main_hermeneutical.txt`
- tests web/chat/logs associes

## Regle de cadrage

Ce TODO pilote un mini-chantier unique et ferme:
- dire vrai sur la lecture web reelle;
- traiter l'URL explicite comme source primaire;
- empecher la sur-pretention dans la reponse;
- empecher la fossilisation de cette sur-pretention en memoire durable;
- rendre le tout visible en production.
