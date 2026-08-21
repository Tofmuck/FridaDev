# Criblage GPT-5.6 Luna / Terra pour le fallback Validation

- Date: `2026-08-21`
- Corpus: `validation_presence_corpus_v1`, 24 cas valides humainement
- Appels: `144/144`, une repetition par configuration
- Parametres communs: `temperature=0`, `top_p=1`, `max_tokens=140`, `timeout_s=15`
- Raisonnement demande: `none`, `low`, `medium`, toujours exclu de la reponse
- Runtime FridaDev modifie: `False`
- Retention: aucune sortie brute, raison libre, conversation, justification humaine ou erreur brute

## Resultats

| Modele | Effort | Schema | Pass | Rappel Presence | Faux Presence | Reasoning tokens | Latence moyenne | Cout estime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `openai/gpt-5.6-luna` | `none` | 24/24 | 20/24 | 100 % | 3, dont 2 haute gravite | 0 | 1 258,95 ms | 0,01305155 USD |
| `openai/gpt-5.6-terra` | `none` | 24/24 | 18/24 | 100 % | 2, dont 1 haute gravite | 0 | 1 511,54 ms | 0,12752750 USD |
| `openai/gpt-5.6-luna` | `low` | 19/24 | 17/24 | 100 % | 0 | 1 182 | 2 536,23 ms | 0,01427675 USD |
| `openai/gpt-5.6-terra` | `low` | 24/24 | 19/24 | 100 % | 3, dont 2 haute gravite | 34 | 1 467,55 ms | 0,12797150 USD |
| `openai/gpt-5.6-luna` | `medium` | 17/24 | 14/24 | 100 % | 0 | 1 751 | 2 314,04 ms | 0,01479995 USD |
| `openai/gpt-5.6-terra` | `medium` | 24/24 | 19/24 | 100 % | 2, dont 1 haute gravite | 48 | 1 293,26 ms | 0,12825950 USD |

Cout total mesure du criblage: `0,42588675 USD`.

## Lecture

- `none` est semantiquement insuffisant pour les deux modeles a cause de faux
  Presence haute gravite.
- Terra conserve un schema valide a `low` et `medium`, mais ne corrige pas les
  faux Presence haute gravite et coute environ dix fois Luna sur cette campagne.
- Luna `low` et `medium` suppriment les faux Presence au premier criblage, mais
  consomment respectivement 1 182 et 1 751 tokens de raisonnement et tronquent
  cinq puis sept sorties sous le plafond runtime de 140 tokens.
- Le niveau demande est prouve dans la signature de requete. L'activite de
  raisonnement est observee par `completion_tokens_details.reasoning_tokens`;
  aucun contenu de raisonnement n'est demande ni conserve.

## Suites bornees

Deux configurations Luna ont seules justifie une campagne complete apres un
criblage additionnel avec un plafond plus large:

- `low/max_tokens=300`: seuils franchis sur une repetition, puis rejet sur trois
  repetitions pour faux Presence haute gravite;
- `medium/max_tokens=500`: seuils franchis sur une repetition, puis rejet sur
  trois repetitions pour faux Presence haute gravite et stabilite insuffisante.

Terra n'a pas ete prolonge: aucun de ses trois niveaux ne franchissait le seuil
de securite au premier criblage.

## Sources tarifaires primaires

- Luna: <https://developers.openai.com/api/docs/models/gpt-5.6-luna>
- Terra: <https://developers.openai.com/api/docs/models/gpt-5.6-terra>
- Choix du niveau de raisonnement: <https://developers.openai.com/api/docs/guides/latest-model>
