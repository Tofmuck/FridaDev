# Frida Biblio librarian agent contract

Statut: spec vivante
Date: 2026-05-31
Classement: `app/docs/states/specs/`
Roadmap active: `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
Audit source: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
Baseline Lot 0: `app/docs/states/baselines/frida-biblio-librarian-agent-lot0-baseline-2026-05-31.md`
Contrat Biblio natif voisin: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Portee: contrat normatif du futur agent bibliothecaire, sans implementation runtime.

## 1. Statut et portee

Cette spec ferme le Lot 2 documentaire du chantier agent bibliothecaire.
Elle ne livre pas l'agent runtime.
Elle ne modifie pas le planner, le client Catalogue, les routes, l'UI, la DB ou la plateforme.

Le but est de rendre le futur agent testable avant d'etre branche:

- entrees explicites;
- sorties versionnees;
- actions allowlistees;
- budgets, timeouts et retries bornes;
- modele runtime-configurable;
- fallback modele et fallback deterministe;
- contrat OpenRouter / JSON a verifier avant implementation;
- observabilite content-free;
- feature flag et rollback;
- criteres GO / NO-GO du Lot 3.

Le futur agent reste une capacite Biblio. Il ne devient pas Memory/RAG, Web,
workspace, active_document, Identity, Summary, Hermeneutic, AnythingLLM ou
doc-pipeline.

## 2. Decision Lot 2

Decision: GO conditionnel pour ouvrir le Lot 3 outils GET-only, NO-GO pour
coder directement l'agent runtime.

Le Lot 3 peut definir le registre d'outils Catalogue bornes si et seulement si:

- l'agent reste off par defaut;
- aucun modele agent n'est appele;
- aucun slug OpenRouter n'est invente;
- aucun outil mutable ou lourd non borne n'est ajoute;
- aucun `latest/page` ou `latest/context` n'est utilise;
- aucune observabilite content-rich n'est creee.

Le runtime agentique, la boucle modele et le remplacement du chemin
deterministe restent NO-GO tant que les gates de cette spec ne sont pas
valides.

## 3. Feature flag, modes et rollback

Le futur agent doit etre desactive par defaut jusqu'a validation produit.

Modes autorises:

- `off`: aucun appel agent, chemin Biblio deterministe actuel conserve;
- `shadow`: l'agent peut etre evalue sans influencer la reponse utilisateur;
- `candidate`: l'agent peut proposer une lane candidate comparee au chemin
  deterministe, sans remplacement implicite;
- `active`: mode produit seulement apres smokes comparatifs, preuve anti-fuite
  et rollback documente.

Regles:

- le toggle utilisateur `biblio_enabled` autorise Biblio, mais ne force pas le
  futur agent tant que le mode agent n'est pas valide;
- un feature flag runtime distinct controle l'agent;
- rollback simple: repasser le mode a `off` doit restaurer le chemin
  deterministe sans migration, rebuild, purge DB ou changement Catalogue;
- le chemin deterministe actuel doit rester disponible, ou etre remplace
  seulement apres preuve comparative de non-regression;
- aucune activation par defaut ne doit suivre un deploiement de code.

## 4. Configuration modele runtime

Le modele agent ne doit jamais etre hardcode dans le code runtime.

Section runtime settings cible, nom indicatif:

- section: `biblio_librarian_agent`;
- champs minimaux:
  - `enabled`;
  - `mode`;
  - `primary_model`;
  - `fallback_model`;
  - `timeout_s`;
  - `temperature`;
  - `top_p`;
  - `max_tokens`;
  - `max_tool_calls`;
  - `max_model_calls`;
  - `max_total_duration_s`;
  - `json_contract_enabled`;
  - `provider_payload_profile`;
  - `structured_output_profile`;
  - `fallback_to_deterministic`;
  - `shadow_compare_enabled`.

Contraintes:

- `primary_model` et `fallback_model` viennent des runtime settings ou d'un
  seed versionne, jamais d'un literal cache dans le module agent;
- DeepSeek V4 Pro est seulement un candidat produit si OpenRouter le rend
  disponible et adapte;
- ne pas inventer de slug OpenRouter pour DeepSeek V4 Pro;
- le slug observe, les capacites et les limites doivent etre documentes dans
  l'artefact OpenRouter / JSON avant implementation;
- le fallback modele doit etre configurable;
- si le modele principal est indisponible, trop lent, refuse, produit du JSON
  invalide ou ne respecte pas le tool schema, le runtime doit degrader
  proprement.

Observabilite autorisee pour le modele:

- provider logique;
- modele effectif expurge;
- source de configuration;
- fallback utilise ou non;
- timeout;
- retries;
- budget consomme;
- status;
- reason code.

Observabilite interdite:

- cle API;
- headers;
- prompt complet;
- raw JSON modele;
- message utilisateur brut;
- passages, titres, auteurs ou payload Catalogue.

## 5. Gate OpenRouter / JSON

Avant toute implementation qui appelle OpenRouter pour l'agent, un artefact
date doit etre produit sous `app/docs/states/baselines/` ou dans une spec
dediee.

Cet artefact doit contenir:

- date de verification;
- URLs OpenRouter consultees;
- modele candidat et slug observe;
- statut de disponibilite;
- capacites confirmees ou infirmees:
  - JSON mode;
  - structured outputs;
  - tool schema;
  - tool calls;
  - contraintes de streaming;
  - limites de tokens;
  - timeouts et erreurs provider attendues;
- payload provider attendu, sans secret;
- decision d'utilisation ou de rejet;
- fallback modele;
- fallback deterministe;
- tests associes.

Tests obligatoires avant runtime:

- JSON absent;
- JSON invalide;
- JSON tronque;
- JSON valide mais hors schema;
- texte libre au lieu de JSON;
- refus modele;
- timeout modele;
- erreur provider;
- fallback modele;
- fallback deterministe;
- budget depasse;
- absence de fail suspend.

Regle dure: un echec JSON ou provider ne doit jamais produire un `fail suspend`.
Le dialogue doit continuer par clarification, reponse degradee,
non-utilisation de Biblio ou erreur propre content-free.

## 6. Entrees agent

Le futur agent recoit seulement des entrees structurees et bornees:

- `schema_version`;
- `conversation_id_present`;
- `turn_id` ou identifiant technique content-free si disponible;
- message courant pour interpretation interne, jamais pour observabilite brute;
- fenetre de dialogue recente bornee, si necessaire a l'anaphore;
- etat Biblio content-free Lot 1 / Lot 1 bis;
- registre d'outils Catalogue GET-only;
- budgets effectifs;
- mode agent effectif;
- feature flags;
- contraintes de sortie;
- signaux de fallback disponibles;
- configuration modele effective expurgee.

L'etat Biblio Lot 1 est la source technique pour la reprise:

- `current_document`;
- `current_work`;
- `page_no`;
- `para_no`;
- `paragraph_id`;
- `last_passage_hash`;
- `last_result`;
- `last_candidates`;
- `last_ambiguity`;
- `last_intent`.

L'agent peut lire cet etat, mais il ne peut pas inventer une continuite. Si
l'etat manque, est contradictoire ou ne porte pas les ancres necessaires, la
sortie doit clarifier.

## 7. Sortie agent

Schema conceptuel interne, version initiale:

```json
{
  "schema_version": "biblio_librarian_agent_v1",
  "intent": "string",
  "tool_plan": [],
  "tool_calls": [],
  "answer_mode": "string",
  "state_update": {},
  "clarification": {},
  "confidence": {},
  "risk_flags": [],
  "fallback_reason": ""
}
```

Champs minimaux:

- `schema_version`: obligatoire, valeur exacte attendue;
- `intent`: intent bibliothecaire normalise;
- `tool_plan`: plan declaratif borne, non execute par le modele lui-meme;
- `tool_calls`: appels demandes, tous verifies par allowlist avant execution;
- `answer_mode`: `passage`, `catalog_list`, `open_work`, `toc`,
  `conceptual_search`, `clarify`, `not_found`, `ambiguous`, `degraded`,
  `refuse_false_certainty` ou equivalent versionne;
- `state_update`: ancres content-free uniquement;
- `clarification`: question produit si resolution insuffisante;
- `confidence`: signal borne, non souverain;
- `risk_flags`: reason codes, jamais contenu brut;
- `fallback_reason`: reason code si modele ou schema non utilisable.

La sortie ne doit pas contenir:

- passage brut durable;
- payload Catalogue brut;
- prompt;
- message utilisateur brut en observabilite;
- titre ou auteur brut dans les surfaces techniques;
- secret;
- route non allowlistee;
- methode mutable.

La lane produit finale peut contenir titres, auteurs ou passages uniquement
quand ils sont necessaires a la reponse de Frida et restent hors
observabilite/admin/logs/read-models.

## 8. Registre d'outils GET-only

Le futur registre d'outils doit etre explicite, borne et verifie avant tout
appel.

Outils autorises au niveau contrat:

| Outil | Source Catalogue | Notes |
| --- | --- | --- |
| `catalog_list` | `GET /catalog` | Liste bornee, pagination explicite, pas de promesse de totalite au-dela de la limite. |
| `catalog_search` | `GET /catalog` ou `GET /search` | Recherche bornee, variantes autorisees, pas de payload brut en observabilite. |
| `document_open_summary` | `GET /catalog`, `GET /doc/{id}/metadata` | Resume bibliographique borne; `GET /doc/{id}` lourd interdit par defaut. |
| `document_toc` | `GET /doc/{id}/chapters` | TOC bornee ou paginee, `document_id` explicite. |
| `locate` | `GET /doc/{id}/locate` | Repere explicite, document resolu requis. |
| `passage_context` | `GET /doc/{id}/context` | Contexte borne, document et position explicites. |
| `page_read` | route page future seulement | Hors Lot 3; autorise plus tard seulement si route/client sure, GO separe, `document_id` explicite, borne de chars, tests, jamais `latest/page`. |

Interdictions:

- toute methode `POST`, `PUT`, `PATCH`, `DELETE`;
- `PUT /settings`;
- `POST /settings/reset`;
- `POST /progress/recent/clear`;
- `DELETE /doc/{id}`;
- `DELETE /doc/{id}/with-files`;
- `PUT /doc/{id}/metadata`;
- `GET /doc/{id}` automatique ou non borne;
- `latest/page`;
- `latest/context`;
- route parametrique sans `document_id` explicite resolu;
- OCR;
- export complet automatique;
- `export/chunk` automatique ou opportuniste;
- modification de `/opt/platform/doc-pipeline`.

`export/chunk` n'appartient pas au registre initial du Lot 3. Tout usage futur
necessite un GO separe, des bornes explicites et des tests dedies.

Chaque appel outil doit produire une observation content-free:

- tool name;
- endpoint kind;
- status;
- duration bucket;
- retry count;
- result count;
- chars count si applicable;
- doc ids courts;
- positions;
- hashes;
- reason code.

## 9. Budgets, timeouts et retries

Budgets nominaux a stabiliser dans les runtime settings ou constantes de
contrat testees:

- duree totale agent par tour;
- nombre maximum d'appels modele;
- nombre maximum d'appels outils;
- nombre maximum de variantes de recherche;
- nombre maximum de candidats Catalogue;
- nombre maximum de contextes lus;
- nombre maximum de passages injectes;
- limite de chars par contexte;
- limite de chars de lane produit;
- timeout modele;
- timeout par outil Catalogue;
- retries transitoires bornes.

Regles:

- un budget depasse produit `budget_exhausted` et degradation propre;
- un timeout Catalogue ne bloque pas tout le chat si une clarification ou une
  reponse degradee est possible;
- un timeout modele tente le fallback modele seulement si le budget restant le
  permet;
- les retries ne doivent pas multiplier une route lourde;
- les budgets effectifs sont observables sans contenu brut.

## 10. Fallback deterministe

Le chemin actuel `chat_runtime.py` / `library_runtime.py` / `query_planner.py`
reste le fallback deterministe nominal.

Fallback obligatoire si:

- feature flag agent off;
- modele non configure;
- OpenRouter indisponible;
- slug non verifie;
- JSON absent, invalide ou hors schema;
- tool schema non respecte;
- budget depasse avant resultat utile;
- outil requis absent;
- fail anti-fuite;
- mode rollback.

Le fallback peut produire:

- une consultation deterministe existante;
- une clarification;
- une reponse Biblio non utilisee;
- une erreur propre content-free.

Il ne doit pas produire:

- suspension technique;
- certitude documentaire inventee;
- route `latest/page` ou `latest/context`;
- appel mutable;
- contenu brut en observabilite.

## 11. Etat conversationnel Biblio

Le futur agent doit respecter le contrat Lot 1 / Lot 1 bis:

- l'etat vit dans `message.meta.biblio_state`;
- l'attachement est conditionnel a une transition Biblio utile;
- l'ancien etat reste dans l'historique mais n'est pas recopie sur chaque
  message;
- toggle Biblio off: aucun nouvel etat attache;
- tour non utilise: pas de recopie d'etat;
- persistance garantie seulement apres sauvegarde normale reussie;
- avant sauvegarde ou si l'etat manque: clarification propre.

L'agent peut proposer `state_update`, mais le runtime doit la valider:

- schema version attendu;
- ids et positions content-free;
- pas de titre brut;
- pas d'auteur brut;
- pas de passage;
- pas de prompt;
- pas de payload Catalogue;
- pas de requete utilisateur brute;
- reason codes allowlistes.

## 12. Observabilite content-free

Events conceptuels futurs:

- `agent_start`;
- `model_call`;
- `model_json_validated`;
- `tool_plan`;
- `tool_call`;
- `selection`;
- `state_update`;
- `fallback`;
- `final`.

Champs autorises:

- schema version;
- mode agent;
- feature flag;
- effective model expurge;
- provider logique;
- source de configuration;
- status;
- reason code;
- endpoint kind;
- tool name;
- counts;
- durations buckets;
- retry count;
- budget requested/used;
- ids courts;
- positions content-free: `page_no`, `para_no`, `paragraph_id`, offsets
  bornes;
- hashes;
- booleens de presence.

Champs interdits:

- raw user query;
- dialogue brut;
- prompt agent;
- raw agent JSON;
- passage;
- page text ou page content;
- titre brut;
- auteur brut;
- payload Catalogue;
- headers;
- token;
- secret;
- DSN;
- cookie;
- `.env`;
- OpenRouter request/response brute.

Toute projection admin/dashboard/log/read-model doit etre testee avec des
fixtures anti-fuite.

## 13. Cas produit couverts par le contrat

Le contrat supporte les familles de sortie suivantes:

- liste catalogue complete jusqu'a la limite produit;
- ouverture d'un ouvrage;
- table des matieres;
- recherche conceptuelle de passages;
- extraction par repere;
- navigation future autour d'une ancre technique;
- verification d'origine;
- clarification d'ambiguite;
- refus de fausse certitude;
- degradation propre.

P03 et P09 restent des surveillances:

- P03 depend encore du planner/intention et ne devient pas une promesse de
  correction automatique par le contrat agent;
- P09 depend d'un outil page et d'une route/client sure qui n'existent pas
  encore cote FridaDev.

## 14. Tests exiges avant runtime

Avant tout branchement runtime agentique:

- validation schema sortie agent;
- rejet schema version inconnue;
- rejet tool call non allowliste;
- rejet methode non GET;
- rejet `latest/page`;
- rejet `latest/context`;
- rejet `GET /doc/{id}` automatique;
- JSON absent/invalide/tronque/hors contrat;
- texte libre/refus/timeout provider;
- fallback modele;
- fallback deterministe;
- budget depasse;
- anti-fuite observabilite;
- agent off conserve chemin deterministe;
- rollback restaure chemin deterministe;
- smokes comparatifs avec chemin actuel.

## 15. GO / NO-GO Lot 3

GO conditionnel Lot 3:

- definir un registre d'outils GET-only;
- borner les parametres;
- tester allowlist et interdictions;
- produire observabilite content-free;
- ne pas appeler de modele agent;
- ne pas activer l'agent.

NO-GO Lot 3 si le patch tente:

- activation agent par defaut;
- modele hardcode;
- slug DeepSeek invente;
- appel OpenRouter sans artefact date;
- tool schema non verifie;
- fail suspend sur JSON invalide;
- route mutante;
- `latest/page` ou `latest/context`;
- outil page sans route/client sure;
- navigation complete;
- remplacement du chemin deterministe sans preuve comparative;
- fuite content-rich dans logs/admin/dashboard/read-models.

## 16. Hors-scope

- runtime agent;
- appel OpenRouter;
- verification live OpenRouter;
- nouveau model caller;
- outil page;
- navigation complete;
- modification Catalogue;
- DB migration;
- frontend toggle supplementaire;
- plateforme OVH;
- OCR;
- rebuild/restart;
- declaration que l'agent produit est livre.
