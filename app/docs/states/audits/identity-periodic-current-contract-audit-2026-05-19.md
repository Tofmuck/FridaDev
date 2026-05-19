# Audit du contrat actuel `identity_periodic_agent` - 2026-05-19

## Objet

Cet audit repond a une question courte: qu'envoie-t-on exactement aujourd'hui a
`identity_periodic_agent`, et pourquoi le smoke test Haiku 4.5 a pu produire
une reponse valide mais tres canonisante (`user`: 9 operations `add`)?

Perimetre:

- lecture du prompt de production;
- lecture du payload runtime construit avant appel modele;
- lecture du garde temporel avant et apres modele;
- lecture de la validation contractuelle et de l'application deterministe;
- lecture de l'artefact de smoke test Haiku.

Hors perimetre dans ce document:

- aucune modification du prompt;
- aucun changement de modele;
- aucun slot runtime `identity_periodic_model`;
- aucune refonte identity.

## Verdict court

Le contrat actuel dit deja explicitement a l'agent periodic de preferer
`no_change`, de garder seulement du signal identitaire durable, de rejeter les
claims temporels faibles et de rejeter les preferences, souhaits de format,
confort conversationnel, guidages locaux et politiques operateur.

Mais le contrat laisse encore beaucoup de travail doctrinal au modele:

- il montre un exemple de sortie ou `user.operations` contient un `add`;
- il autorise plusieurs operations `add` sans plafond explicite par fenetre;
- il ne donne pas de taxonomie nette entre identite durable, preference durable,
  preference de travail, regle operateur, doctrine Frida, role joue et etat local;
- le filtrage post-modele rejette surtout la forme invalide, le temporel faible
  explicite, l'absence totale de source admissible et les propositions trop peu
  supportees lexicalement;
- il ne sait pas, a lui seul, reconnaitre qu'une proposition comme "Tof veut
  benchmark -> decision -> decouplage" est une regle de pilotage de chantier
  plutot qu'une identite canonique.

Conclusion: Haiku canonise trop, mais il le fait dans un espace que notre contrat
lui laisse encore trop facilement. Le probleme n'est pas seulement "le modele";
c'est surtout un contrat qui interdit certaines choses en une phrase, mais ne
les rend pas assez operatoires ni assez verifiables.

## Chemin runtime actuel

### 1. Seuil et construction initiale

Source: `app/memory/memory_identity_periodic_agent.py`.

- `BUFFER_TARGET_PAIRS = 15`.
- La semantique reelle est 15 paires completes `user` / `assistant`, pas 15
  messages isoles.
- Tant que le buffer est sous le seuil, le statut est `buffering`.
- Au seuil, `_build_agent_payload()` fabrique le payload d'agent avec:
  - `buffer_pairs`;
  - `buffer_pairs_count`;
  - `buffer_target_pairs`;
  - `identities.llm.static`;
  - `identities.llm.mutable_current`;
  - `identities.user.static`;
  - `identities.user.mutable_current`;
  - `mutable_budget.target_chars`;
  - `mutable_budget.max_chars`.

Preuves:

- `app/memory/memory_identity_periodic_agent.py:12`
- `app/memory/memory_identity_periodic_agent.py:57`
- `app/memory/memory_identity_periodic_agent.py:137`
- `app/memory/memory_identity_periodic_agent.py:161`
- `app/memory/memory_identity_periodic_agent.py:189`

### 2. Appel modele

Source: `app/memory/arbiter.py`.

`run_identity_periodic_agent()` recoit le payload initial, puis construit le vrai
payload envoye au modele:

```json
{
  "model": "<arbiter_model legacy actuel>",
  "messages": [
    {
      "role": "system",
      "content": "<contenu de app/prompts/identity_periodic_agent.txt>"
    },
    {
      "role": "user",
      "content": "<payload_for_model serialise en JSON indent=2>"
    }
  ],
  "temperature": 0.0,
  "top_p": 1.0,
  "max_tokens": 1400
}
```

Le timeout vient encore de `config.ARBITER_TIMEOUT_S`.

Preuves:

- `app/memory/arbiter.py:813`
- `app/memory/arbiter.py:821`
- `app/memory/arbiter.py:836`
- `app/memory/arbiter.py:851`

Note de transition: au 2026-05-19, le modele du periodic vient encore du slot
legacy `arbiter_model`. Ce document ne change pas cela.

## Prompt systeme exact, structure fidele

Source: `app/prompts/identity_periodic_agent.txt`.

### Role declare

Le prompt dit:

- "You are a periodic identity agent."
- L'agent maintient exactement deux identites mutables canoniques:
  - `llm`;
  - `user`.

Preuve: `app/prompts/identity_periodic_agent.txt:1`.

### Ce qu'il recoit

Le prompt dit que l'agent recoit:

- l'identite statique courante de `llm` et `user`;
- l'identite mutable canonique courante de `llm` et `user`;
- une fenetre bufferisee de paires completes `user` / `assistant`;
- les metadonnees de budget mutable.

Preuve: `app/prompts/identity_periodic_agent.txt:7`.

### But demande

Le prompt lui demande:

- de decider seulement des operations locales d'identite pour chaque sujet;
- de ne jamais reecrire tout le bloc mutable;
- de preferer `no_change` quand la preuve est faible, ambigue,
  contradictoire ou seulement situationnelle.

Preuve: `app/prompts/identity_periodic_agent.txt:13`.

### Clauses qui limitent la canonisation

Le prompt contient deja plusieurs freins:

- garder seulement du signal identitaire durable;
- rejeter les claims temporels faibles;
- ne pas proposer d'operation pour un sujet sans source admissible non relative;
- rejeter preferences, souhaits de format, confort conversationnel, guidage de
  tache locale et politique operateur;
- garder la proposition descriptive et identitaire, jamais prompt-like;
- ne pas repeter ce qui est deja couvert par le statique;
- ne pas inventer ou resoudre de force les contradictions;
- preferer `no_change` quand l'operation sure n'est pas evidente.

Preuves:

- `app/prompts/identity_periodic_agent.txt:19`
- `app/prompts/identity_periodic_agent.txt:20`
- `app/prompts/identity_periodic_agent.txt:21`
- `app/prompts/identity_periodic_agent.txt:22`
- `app/prompts/identity_periodic_agent.txt:23`
- `app/prompts/identity_periodic_agent.txt:27`

### Clauses qui ouvrent la porte aux operations

Le prompt autorise cinq formes:

- `no_change`;
- `add`;
- `tighten`;
- `merge`;
- `raise_conflict`.

Il donne aussi un exemple de top-level ou `user.operations` contient un `add`.
Cet exemple est utile pour le format, mais il peut implicitement normaliser le
geste "si tu vois quelque chose cote user, ajoute une proposition compacte".

Preuves:

- `app/prompts/identity_periodic_agent.txt:30`
- `app/prompts/identity_periodic_agent.txt:41`
- `app/prompts/identity_periodic_agent.txt:57`

## Payload utilisateur exact

Le payload utilisateur est un JSON serialise comme contenu du message `user`.

### Cles principales

Le payload envoye au modele contient:

- `buffer_pairs`;
- `buffer_pairs_count`;
- `buffer_target_pairs`;
- `identities`;
- `mutable_budget`;
- `identity_temporal_policy`.

Le smoke test Haiku conserve un exemple complet de cette forme dans:

- `benchmark/results/identity_periodic/2026-05-19-haiku-smoke.md`;
- `benchmark/results/identity_periodic/2026-05-19-haiku-smoke.json`.

### `identities`

`identities` contient deux sujets:

- `llm.static`;
- `llm.mutable_current`;
- `user.static`;
- `user.mutable_current`.

Ces champs donnent au modele le canon existant. Le prompt lui demande de ne pas
repeter ce qui est deja couvert par le statique, mais cette verification repose
d'abord sur sa lecture.

### `mutable_budget`

`mutable_budget` contient:

- `target_chars`;
- `max_chars`.

Le modele les recoit comme metadonnees. Le controle dur de taille est ensuite
fait cote Python lors de l'application.

### `buffer_pairs`

Le modele lit une liste de paires:

```json
[
  {
    "user": {"role": "user", "content": "...", "timestamp": "..."},
    "assistant": {"role": "assistant", "content": "...", "timestamp": "..."}
  }
]
```

Avant envoi, les messages contenant un marqueur temporel faible ont leur
`content` vide et recoivent:

```json
{"temporal_source_guard": "weak_relative_temporal_claim_removed"}
```

## Politique temporelle

Source: `app/memory/identity_temporal_guard.py` et `app/memory/arbiter.py`.

### Marqueurs faibles

Les marqueurs faibles actuels sont:

- `aujourd'hui`;
- `aujourdhui`;
- `hier`;
- `depuis hier`;
- `en ce moment`;
- `actuellement`;
- `maintenant`;
- `today`;
- `yesterday`;
- `since yesterday`;
- `right now`;
- `currently`.

Preuve: `app/memory/identity_temporal_guard.py:7`.

### Ce qui est retire avant modele

Pour chaque paire, le garde inspecte `user.content` et `assistant.content`.
Si le texte contient un marqueur faible:

- le contenu est remplace par une chaine vide;
- `temporal_source_guard = weak_relative_temporal_claim_removed` est ajoute;
- le compteur `weak_relative_source_count` augmente pour le sujet concerne.

Preuves:

- `app/memory/identity_temporal_guard.py:69`
- `app/memory/identity_temporal_guard.py:90`
- `app/memory/identity_temporal_guard.py:104`

### Ce qui reste visible

Le modele voit:

- les paires admissibles non relatives;
- les messages retires, mais avec contenu vide;
- le fait qu'une source a ete retiree;
- un `source_summary` par sujet:
  - `admissible_source_count`;
  - `weak_relative_source_count`.

### Instruction temporelle ajoutee au payload

`run_identity_periodic_agent()` ajoute:

```json
{
  "relative_claims_are_non_durable": true,
  "reject_markers": [...],
  "source_summary": {...},
  "instruction": "Reject weak relative temporal source claims instead of promoting them to mutable identity. Only propose an operation for a subject when that subject has admissible non-relative source content."
}
```

Preuve: `app/memory/arbiter.py:826`.

### Filtrage temporel apres modele

Apres la reponse modele, `_sanitize_identity_periodic_temporal_claims()` retire:

- toute operation non-`no_change` dont la proposition contient encore un
  marqueur temporel faible;
- toute operation pour un sujet qui n'a aucune source admissible non relative.

Si toutes les operations d'un sujet sont retirees, le sujet retombe sur
`no_change`.

Preuves:

- `app/memory/arbiter.py:754`
- `app/memory/arbiter.py:780`
- `app/memory/arbiter.py:784`
- `app/memory/arbiter.py:793`

## Contrat de sortie attendu

Source: `app/prompts/identity_periodic_agent.txt` et
`app/memory/memory_identity_periodic_apply.py`.

### Format JSON attendu

Le top-level doit contenir exactement:

- `llm`;
- `user`;
- `meta`.

Chaque sujet doit contenir exactement:

- `operations`.

Preuves:

- `app/prompts/identity_periodic_agent.txt:64`
- `app/memory/memory_identity_periodic_apply.py:168`

### Operations autorisees

Operations autorisees:

- `no_change`;
- `add`;
- `tighten`;
- `merge`;
- `raise_conflict`.

Chaque operation a des cles exactes selon son type.

Preuves:

- `app/prompts/identity_periodic_agent.txt:57`
- `app/memory/memory_identity_periodic_apply.py:108`

### Validation formelle

La validation Python rejette:

- top-level invalide;
- sujet sans `operations`;
- `kind` inconnu;
- operation sans `reason`;
- `no_change` avec proposition non vide;
- `add` / `raise_conflict` sans proposition;
- `tighten` sans target;
- `merge` sans targets valides;
- melange de `no_change` avec d'autres operations pour un meme sujet;
- `meta.execution_status` different de `complete`;
- `meta.buffer_pairs_count` incoherent;
- `meta.window_complete` different de `true`.

Preuves:

- `app/memory/memory_identity_periodic_apply.py:87`
- `app/memory/memory_identity_periodic_apply.py:108`
- `app/memory/memory_identity_periodic_apply.py:168`

### Application post-validation

Apres validation formelle:

1. chaque operation est scoree par support lexical dans le buffer;
2. les operations sous seuil sont rejetees ou differees;
3. les doublons du statique ou du mutable sont rejetes;
4. les contradictions detectees peuvent devenir `raise_conflict`;
5. les contenus trop longs ou invalides sont rejetes;
6. le commit canonique est all-or-nothing.

Preuves:

- `app/memory/memory_identity_periodic_scoring.py:9`
- `app/memory/memory_identity_periodic_scoring.py:143`
- `app/memory/memory_identity_periodic_apply.py:521`
- `app/memory/memory_identity_periodic_apply.py:534`
- `app/memory/memory_identity_periodic_apply.py:859`
- `app/memory/memory_identity_periodic_apply.py:890`
- `app/memory/memory_identity_periodic_apply.py:1051`
- `app/memory/memory_identity_periodic_apply.py:1175`

Important: ce scoring mesure surtout la recurrence/support lexical dans le
buffer. Il ne classe pas explicitement "preference operateur" versus "identite
durable".

## Preferences operateur: ce que le contrat dit

Le prompt dit explicitement:

> Reject preferences, response formatting wishes, conversational comfort, local
> task guidance, and operator policy.

Preuve: `app/prompts/identity_periodic_agent.txt:22`.

Donc la doctrine existe deja dans le prompt. Elle couvre en intention:

- les preferences de format de reponse;
- les souhaits locaux de confort conversationnel;
- les consignes de tache locale;
- les politiques operateur;
- les preferences qui ne sont pas des identites.

## Preferences operateur: ce que le contrat ne dit pas assez

Le contrat ne donne pas encore une grille claire pour separer:

- identite durable personnelle;
- preference durable de travail;
- preference locale de reponse;
- regle operateur de chantier;
- doctrine produit de Frida;
- instruction de controle comme "quand je dis stop";
- etat local ou temporaire;
- role joue;
- tension productive a conserver comme tension, sans l'ecrire comme trait.

Il ne dit pas non plus:

- combien d'operations maximum proposer par fenetre;
- qu'un seul passage ne doit presque jamais produire une liste longue de `add`;
- qu'une preference repetitive de pilotage projet peut etre utile au comportement
  de Frida sans appartenir au canon identitaire mutable;
- que les phrases sur Frida / le LLM peuvent decrire une attente de produit ou
  de voix, pas forcement l'identite `llm`;
- que les regles de workflow doivent plutot rester dans les specs / TODO /
  decisions de chantier que dans l'identite mutable.

## Lecture du smoke test Haiku

Artefact:

- `benchmark/results/identity_periodic/2026-05-19-haiku-smoke.md`
- `benchmark/results/identity_periodic/2026-05-19-haiku-smoke.json`

Resultat technique:

- modele: `anthropic/claude-haiku-4.5`;
- JSON valide;
- schema periodic valide;
- `llm`: `no_change`;
- `user`: 9 operations `add`;
- finish reason: `stop`;
- prompt tokens: `3500`;
- completion tokens: `746`.

Le garde temporel a bien fonctionne dans le payload du smoke test:

- `user.admissible_source_count = 11`;
- `user.weak_relative_source_count = 4`;
- les marqueurs faibles retires ne remontent pas dans les propositions finales.

Mais Haiku a transforme beaucoup de preferences de travail en propositions
identitaires:

- lots minuscules et preuves fermees;
- artefacts de benchmark relisibles;
- UI dense et sobre;
- mauvais plans signales sans flatterie;
- sequence benchmark -> decision -> decouplage;
- documentation retrouvable;
- presence dialogique sans psychologie inventee;
- tension court / preuves;
- interruption explicite `stop`.

La plupart sont utiles au pilotage de FridaDev. Elles ne sont pas toutes de
bonnes candidates pour l'identite mutable canonique.

## Lecture courte pour Tof

Haiku a produit 9 `add` parce que notre contrat actuel lui donne deux signaux
en tension:

- d'un cote, il lui dit tres clairement de preferer `no_change` et de rejeter
  les preferences operateur;
- de l'autre, il lui donne une fenetre de 15 paires riche en preferences de
  travail, il autorise `add`, il montre un exemple avec `user.add`, et il ne lui
  fournit pas de taxonomie assez concrete pour ranger "regle de chantier" hors
  identite mutable.

Le code post-modele filtre correctement plusieurs choses dures:

- JSON invalide;
- schema invalide;
- claims temporels faibles explicites;
- sujet sans source admissible;
- proposition sans support lexical suffisant;
- doublons;
- contradictions simples;
- depassements de taille.

Mais il ne filtre pas assez le coeur du probleme observe: une preference de
travail bien formulee, recurrente dans le buffer et lexicalement supportee peut
passer comme "identite durable", meme si elle devrait plutot rester une regle
operatoire, une preference de collaboration ou une doctrine de chantier.

Donc la reponse courte est: Haiku canonise trop, oui, mais il canonise trop dans
un espace que le contrat actuel ne ferme pas assez. Le vrai arbitrage doctrinal
est de decider si `identity_periodic_agent` doit consolider des preferences de
collaboration de Tof, ou seulement des traits identitaires beaucoup plus rares
et stables. Si on veut un periodic prudent, le prochain geste devrait d'abord
resserrer cette frontiere dans le contrat, puis seulement juger le modele.
