# Dialogic Identity - Closure

Document de cloture du mini-lot dialogique / identite ferme le 2026-04-04 pour reduire la surclarification bureaucratique, mieux classer certains tours fictionnels/speculatifs, rendre une revelation identitaire utilisateur plus operatoire au tour suivant, filtrer certaines ecritures durables Frida meta/pipeline, et refermer le reliquat de couture `logs/identity`.

## Contexte de depart

Conversation source revalidee avant correctif:
- conversation: `0d4086f2-8fd6-4820-a4e9-7bca1f2b3222`
- tours de reference:
  - `turn-4cc8fc1d-cacb-4c04-9ad9-5a9b1d5bca12`
  - `turn-b411dc1a-e62f-47c2-a4d2-4afb53e6b0ff`
  - `turn-e024ff68-a7dd-4490-9520-d47fddd123c3`
  - `turn-14661e9d-9d3e-4ca6-87db-22f83220605f`
  - `turn-0123cb1a-9f4e-4295-bb57-99bf95737f98`

Symptomes revalides avant la tranche:
- la validation surclarifiait encore certains gestes evidents, notamment une revelation utilisateur du type `Je suis Christophe Muck`;
- une question fictionnelle claire (`Imagine que tu es une extraterrestre...`) pouvait etre classee trop severement en `a_verifier` / `verification_externe_requise`;
- une revelation identitaire explicite etait bien ecrite cote user, mais revenait peu operatoirement au tour suivant;
- certaines ecritures durables cote Frida retenaient encore des artefacts locaux de pipeline ou de roleplay ephemere;
- un reliquat de couverture `logs/identity` etait reste rouge apres la reecriture de la selection runtime d'identite.

## Correctifs retenus

Cloture technique portee par trois commits:
- `52c3b20` - `Tighten dialogic classification and identity retention`
- `918ae22` - `Reserve identity budget for dynamic entries`
- `ea81da4` - `Fix identity logger seam test coverage`

### 1. Reduction de la surclarification sur les gestes evidents

Correctif retenu:
- `app/core/hermeneutic_node/validation/validation_agent.py` normalise maintenant un `clarify` excessif quand le tour est un geste direct peu ambigu;
- `app/core/chat_prompt_context.py` et `app/core/chat_service.py` injectent une garde compacte de revelation identitaire explicite, pour eviter de rebureaucratiser des tours du type `Je suis Christophe Muck`.

Effet produit retenu:
- une revelation identitaire explicite et non ambigue n'est plus requalifiee par defaut en demande de cadrage;
- une vraie clarification reste possible quand des signaux de cadrage ou d'ambiguite existent reellement.

### 2. Meilleure classification des questions fictionnelles/speculatives

Correctif retenu:
- `app/core/hermeneutic_node/inputs/user_turn_input.py` n'utilise plus de simple substring fragile pour certaines heuristiques;
- la classification primaire ne traite plus par defaut des tours fictionnels clairs comme s'ils exigeaient une verification externe.

Effet produit retenu:
- une question imaginative/speculative claire peut rester dans un regime de reponse substantive;
- une vraie demande factuelle necessitant verification externe reste prudente hors de ce scope.

### 3. Revelation identitaire utilisateur plus operatoire au tour suivant

Correctif retenu:
- `app/memory/hermeneutics_policy.py` accepte explicitement une revelation utilisateur confiante de type identitaire;
- `app/identity/identity.py` reserve un budget utile aux entrees dynamiques, pour qu'elles ne soient plus etouffees par le bloc statique.

Effet produit retenu:
- une entree du type `Je suis Christophe Muck` peut revenir dans `identity.build_identity_input()` et dans le bloc identitaire suivant;
- la revelation n'est plus seulement "ecrite quelque part", elle redevient utile au tour suivant.

### 4. Filtrage de certaines ecritures durables Frida meta/pipeline

Correctif retenu:
- `app/memory/hermeneutics_policy.py` filtre certaines ecritures durables Frida de type:
  - meta-pipeline local
  - justification circonstancielle de tour
  - roleplay ephemere local

Effet produit retenu:
- le systeme n'archive plus comme identite durable des formulations du type `Unable to provide...`, `rules did not allow...` ou des auto-descriptions roleplay locales non stables;
- le lot ne pretend pas avoir refondu toute la gouvernance memoire, seulement ce perimetre borne.

### 5. Fermeture du reliquat de couture `logs/identity`

Correctif retenu:
- `ea81da4` n'a pas modifie le runtime identite;
- il a realigne le test `app/tests/unit/logs/test_chat_turn_logger_phase2.py` sur la vraie couture encore utilisee, en patchant `_select_ranked_entries()` plutot qu'un seam legacy devenu inactif.

Effet produit retenu:
- la couverture logs/identity redevient coherente avec l'implementation actuelle;
- la fermeture finale de ce reliquat est documentaire et de test seam, pas une nouvelle correction produit.

## Surface effectivement concernee

Surface applicative principale:
- `app/core/chat_prompt_context.py`
- `app/core/chat_service.py`
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/memory/hermeneutics_policy.py`
- `app/identity/identity.py`

Surface de preuves/tests:
- `app/tests/test_server_phase14.py`
- `app/tests/unit/chat/test_chat_memory_flow.py`
- `app/tests/unit/chat/test_chat_prompt_context.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py`
- `app/tests/unit/logs/test_chat_turn_logger_phase2.py`

## Preuves retenues

### Preuves live de revalidation

Conversation de revalidation apres patch:
- conversation: `a2bebfd3-96d3-4088-b622-6495461f534a`
- tours utiles:
  - `turn-0626ef06-1a66-4dd6-8b48-f15052b307d1`
  - `turn-82dae3b3-1114-496c-9fe5-fa13ea935055`

Lectures retenues:
- sur la revelation identitaire, la reponse n'est plus une clarification bureaucratique;
- sur le tour fictionnel, la posture finale redevient une reponse substantive normale;
- les ecritures durables Frida meta/pipeline polluantes ne redeviennent pas des identites stables.

### Preuves tests

Preuves structurelles retenues dans le repo:
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py`
  - `Je suis Christophe Muck` reste classe en `exposition`, sans faux positif de regulation;
  - `biodiversite` n'est plus traitee comme provenance web.
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`
  - une question imaginative claire ne tombe plus en `verification_externe_requise`.
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`
  - la validation garde `answer` pour une revelation identitaire peu ambigue;
  - elle garde `clarify` quand un vrai signal de cadrage existe.
- `app/tests/unit/chat/test_chat_prompt_context.py`
  - la garde de revelation identitaire explicite interdit la clarification bureaucratique quand le tour est non ambigu.
- `app/tests/unit/chat/test_chat_memory_flow.py`
  - une revelation utilisateur explicite peut etre acceptee et enregistree comme entree identitaire legitime.
- `app/tests/test_server_phase14.py`
  - les entrees dynamiques user redeviennent visibles dans `identity.build_identity_input()` et `build_identity_block()`.
- `app/tests/unit/logs/test_chat_turn_logger_phase2.py`
  - la couture logs/identity est revalidee sur le seam reel actuel.

## Faux bons correctifs evites

- ne pas empiler un hack lexical sur une seule chaine `Je suis ...`;
- ne pas corriger seulement la validation si la mauvaise classification vient plus en amont;
- ne pas "reparer" l'identite utilisateur via un contournement ad hoc du prompt final;
- ne pas reintroduire une indirection runtime artificielle juste pour sauver un monkeypatch legacy de test;
- ne pas sur-vendre ce lot comme une refonte complete du systeme dialogique.

## Statut final honnete

Ce mini-lot est ferme pour son scope:
- moins de `clarify` bureaucratique sur certains gestes evidents;
- meilleure lecture des tours fictionnels/speculatifs clairs;
- revelation identitaire utilisateur plus operatoire au tour suivant;
- filtrage borne de certaines ecritures durables Frida meta/pipeline;
- reliquat `logs/identity` referme proprement.

Ce mini-lot ne pretend pas avoir resolu:
- toute la politique dialogique de Frida;
- tous les cas limites de roleplay ou de style de reponse;
- toute la gouvernance memoire au-dela des ecritures durables explicitement visees;
- toute future evolution de la couture interne `identity` si la selection runtime change encore.
