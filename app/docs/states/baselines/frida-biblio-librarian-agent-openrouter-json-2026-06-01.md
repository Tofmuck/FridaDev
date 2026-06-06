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
  le modele effectif reste configure par la section runtime settings
  `biblio_librarian_agent`; les variables `BIBLIO_LIBRARIAN_AGENT_*` restent des
  seeds/bootstrap.
- OpenRouter documente `reasoning` comme map optionnelle pour les modeles qui
  supportent les tokens de raisonnement; FridaDev envoie
  `reasoning={"effort":"high","exclude":true}` quand le champ runtime
  `reasoning_effort` vaut `high`, et n'envoie plus de champ top-level
  `reasoning_effort` sur ce caller.

## Decision Lot 7

- Construire le payload avec `response_format.type=json_schema`,
  `json_schema.name=biblio_librarian_agent_v1`, `strict=true` et
  `provider.require_parameters=true`.
- Garder le modele vide par defaut et le mode `off` par defaut dans le Lot 7
  initial; le mini-lot post-Lot 10 bascule ensuite le default applicatif vers
  `active` + `deepseek/deepseek-v4-pro`.
- Ajouter les modes `shadow` et `candidate` comme evaluation non souveraine.
- Ne pas utiliser `active` comme chemin produit dans ce lot.
- Valider en Python le JSON modele meme si structured output est demande.
- Rejeter localement les payloads hors schema: champs racine en trop, champs
  requis absents, `risk_flags` invalides, params inconnus et params hors
  bornes; `params` doit rester un objet JSON et ne doit pas etre normalise
  silencieusement depuis `null`, liste, string, nombre ou booleen.
- Rejeter localement les plans schema-valid mais non executables par
  `librarian_tools.py`: query manquante pour `catalog_search`, document_id
  manquant pour TOC/locate/context, position manquante pour
  `passage_context`, bornes par outil et offset search non nul.
- Garder le contrat JSON obligatoire; ne pas exposer de knob operateur pour le
  desactiver dans le Lot 7. Le payload OpenRouter force toujours
  `provider.require_parameters=true`.
- Tenter le fallback modele configure uniquement quand `max_model_calls >= 2`.
- Ne jamais conserver le prompt complet, le raw JSON modele ou un payload
  provider brut dans le resultat observe.
- Observer `model_called=true` seulement quand une tentative provider a eu
  lieu (`attempt_count > 0`), pas sur une sortie locale modele/cle absente.

## Fallbacks exiges

- modele absent ou cle absente: aucun appel provider et `model_called=false`;
- timeout provider primaire: fallback modele si configure et budgetise, sinon
  fallback deterministe; la tentative provider reste observable avec
  `attempt_count=1`;
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

## Note post-Lot 10

Cette baseline de Lot 7 reste historique pour le socle OpenRouter/JSON. Le
contrat de smoke live Lot 10 est plus strict: le mode nominal du runner est
`active`, `active` appelle le modele et valide le JSON, et `shadow`/`candidate`
ne valent plus preuve produit nominale. Le plan agent reste toutefois observe
seulement: `used_for_response=false`, outils non executes et reponse produit
deterministe inchangee jusqu'a lot separe.

## Note configuration active post-Lot 10

La configuration applicative non secrete demandee par l'operateur est portee par
la section runtime settings DB `biblio_librarian_agent`:

- `mode=active`;
- `primary_model=deepseek/deepseek-v4-pro`;
- `temperature=0`;
- `top_p=1`;
- `max_tokens=16000`;
- `max_recent_turns=5`;
- `timeout_s=120`;
- `reasoning_effort=high`.

Les variables `BIBLIO_LIBRARIAN_AGENT_*` restent des seeds/bootstrap historiques;
elles ne sont pas l'autorite runtime quand la DB est disponible. Le secret
OpenRouter n'est pas duplique: l'appel Biblio reutilise `main_model.api_key` via
`llm_client` et les headers custom `biblio_librarian`. Le modele n'est pas
hardcode dans la logique metier. `active` signifie modele appele et JSON valide
pour le smoke agent, pas execution des outils agentiques ni remplacement de la
reponse produit.
