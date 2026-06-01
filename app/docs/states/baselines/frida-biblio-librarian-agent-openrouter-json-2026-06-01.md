# Biblio librarian agent - OpenRouter JSON verification

Date: 2026-06-01
Classement: `app/docs/states/baselines/`
Roadmap: `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
Spec: `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
Scope: verification provider pour le Lot 7 agent bibliothecaire, sans smoke
modele reel et sans activation produit.

## URLs consultees

- `https://openrouter.ai/docs/guides/features/structured-outputs`
- `https://openrouter.ai/docs/guides/features/tool-calling`
- `https://openrouter.ai/docs/api/reference/overview`
- `https://openrouter.ai/provider/deepseek`
- `https://openrouter.ai/deepseek/deepseek-v4-pro`

## Constats

- OpenRouter supporte `response_format` avec `type=json_schema`,
  `json_schema.name`, `strict=true` et un schema JSON.
- La documentation recommande de verifier les parametres supportes par modele
  et d'utiliser `provider.require_parameters=true` quand le support structured
  output est requis.
- OpenRouter documente l'interface OpenAI-compatible de tool calling: le modele
  propose des appels, mais l'application execute et valide les outils.
- Le endpoint Chat Completions attend `POST /api/v1/chat/completions`.
- Les finish reasons normalises incluent `tool_calls`, `stop`, `length`,
  `content_filter` et `error`; `length` doit etre traite comme sortie tronquee.
- Le provider DeepSeek liste DeepSeek V4 Pro avec URL modele
  `https://openrouter.ai/deepseek/deepseek-v4-pro`, soit le slug observe
  `deepseek/deepseek-v4-pro`.
- DeepSeek V4 Pro est un candidat agentique possible, pas un default hardcode:
  le modele effectif reste configure par `BIBLIO_LIBRARIAN_AGENT_MODEL`.

## Decision Lot 7

- Construire le payload avec `response_format.type=json_schema`,
  `json_schema.name=biblio_librarian_agent_v1`, `strict=true` et
  `provider.require_parameters=true`.
- Garder le modele vide par defaut et le mode `off` par defaut.
- Ajouter les modes `shadow` et `candidate` comme evaluation non souveraine.
- Ne pas utiliser `active` comme chemin produit dans ce lot.
- Valider en Python le JSON modele meme si structured output est demande.
- Rejeter localement les payloads hors schema: champs racine en trop, champs
  requis absents, `risk_flags` invalides, params inconnus et params hors
  bornes.
- Garder le contrat JSON obligatoire; ne pas exposer de knob operateur pour le
  desactiver dans le Lot 7.
- Tenter le fallback modele configure uniquement quand `max_model_calls >= 2`.
- Ne jamais conserver le prompt complet, le raw JSON modele ou un payload
  provider brut dans le resultat observe.

## Fallbacks exiges

- modele absent ou cle absente: aucun appel provider;
- timeout provider primaire: fallback modele si configure et budgetise, sinon
  fallback deterministe;
- erreur HTTP/provider primaire: fallback modele si configure et budgetise,
  sinon fallback deterministe;
- finish reason `length`: sortie tronquee, fallback deterministe;
- JSON absent, invalide ou texte libre: fallback deterministe;
- schema version inconnue ou outil interdit/inconnu: fallback deterministe;
- budget depasse: fallback deterministe;
- mode `off`: aucun appel modele;
- mode `active`: non active par Lot 7, fallback deterministe sans appel modele.

## Limites

- Aucun smoke modele reel n'est execute dans ce lot.
- Les capacites du modele effectif doivent etre reverifiees avant activation
  produit.
- La disponibilite et la qualite de DeepSeek V4 Pro ne remplacent pas les tests
  produit Biblio.
