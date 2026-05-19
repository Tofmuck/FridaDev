# Identity periodic Haiku decision - 2026-05-19

## Objet

Preuve compacte de decision apres les trois smokes `identity_periodic_agent`
sur le meme buffer simule de 15 paires, avec le vrai prompt de production.

Les sorties brutes intermediaires ont ete retirees apres lecture et decision.
Cet artefact conserve les metriques utiles, la trajectoire du resserrement de
contrat et la decision runtime sans conserver les dumps complets.

## Decision

`identity_periodic_agent` passe sur `anthropic/claude-haiku-4.5`.

Parametres initiaux du slot dedie:

| Champ | Valeur |
| --- | --- |
| `model` | `anthropic/claude-haiku-4.5` |
| `temperature` | `0.0` |
| `top_p` | `1.0` |
| `max_tokens` | `1400` |
| `timeout_s` | `10` |

Doctrine retenue:

- l'identite `llm` vient de ce que Frida porte ou dit durablement d'elle-meme;
- une attente durable de Tof envers Frida peut rester cote `user` si elle
  decrit une disposition stable de Tof au dialogue, pas une auto-identite de
  Frida.

## Trajectoire des smokes

| Campagne | Prompt | Modele | Latence | Tokens prompt/completion | Cout USD | Finish | Operations `llm` | Operations `user` | Lecture |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `2026-05-19-haiku-smoke` | initial | `anthropic/claude-haiku-4.5` | 6445 ms | 3500 / 746 | 0.007230 | `stop` / `end_turn` | 1 `no_change` | 9 `add` | trop canonisant |
| `2026-05-19-haiku-smoke-ontological` | regle `X est Y` | `anthropic/claude-haiku-4.5` | 4908 ms | 3720 / 522 | 0.006330 | `stop` / `end_turn` | 1 `no_change` | 7 `add` | mieux, encore trop operatoire |
| `2026-05-19-haiku-smoke-ontological-register` | ontologique + registre | `anthropic/claude-haiku-4.5` | 4189 ms | 4031 / 328 | 0.005671 | `stop` / `end_turn` | 1 `no_change` | 3 `add` | acceptable apres lecture humaine |

## Lecture finale

Le dernier run garde `llm` en `no_change` et ne transforme pas les attentes de
Tof en auto-identite de Frida. Il propose trois ajouts cote `user`, qui ont ete
juges acceptables par Tof dans ce contexte: ils decrivent des dispositions
stables de Tof envers les decisions lisibles, la tension concision/preuve, et
la presence dialogique attendue de Frida.

Cette decision ne prouve pas qu'il faille promouvoir toute attente operateur:
le prompt ontologique + registre reste la borne normative. La prochaine preuve
runtime doit verifier que `identity_periodic_model` est bien la source DB
effective du payload periodic.

## Retention

- Artefact compact conserve: ce fichier.
- Artefact structure conserve: `2026-05-19-haiku-periodic-decision.json`.
- Fixture conservee: `benchmark/suites/identity_periodic/fixtures/haiku_smoke_buffer.json`.
- Sorties brutes des trois smokes retirees apres lecture humaine et decision.
