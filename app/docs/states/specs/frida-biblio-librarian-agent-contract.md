# Frida Biblio librarian agent contract

Statut: spec vivante
Date: 2026-06-02
Classement: `app/docs/states/specs/`
Roadmap active: `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
Matrice d'action produit complementaire: `app/docs/todo-todo/product/frida-biblio-refonte.md`
Audit source: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
Baseline Lot 0: `app/docs/states/baselines/frida-biblio-librarian-agent-lot0-baseline-2026-05-31.md`
Contrat Biblio natif voisin: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Verification OpenRouter Lot 7 historique: `app/docs/states/baselines/frida-biblio-librarian-agent-openrouter-json-2026-06-01.md`
Verification OpenRouter courante: `app/docs/states/baselines/frida-biblio-librarian-agent-openrouter-gpt52-2026-06-02.md`
Portee: contrat normatif de l'agent bibliothecaire, du registre d'outils
GET-only, de la boucle bornee, du socle agentique et de la tranche
agent-first active comme controleur Biblio.

## 1. Statut et portee

Cette spec ferme le Lot 2 documentaire du chantier agent bibliothecaire.
Mise a jour Lot 3: le registre d'outils Catalogue GET-only est livre dans
`app/biblio/librarian_tools.py`.
Mise a jour Lot 4: la boucle/planner bibliothecaire bornee est livre dans
`app/biblio/librarian_planner.py`, sans branchement produit ni modele externe
reel.
Mise a jour Lot 7: le socle agentique OpenRouter / JSON est livre dans
`app/biblio/librarian_agent_contract.py`,
`app/biblio/librarian_agent_openrouter.py` et
`app/biblio/librarian_agent.py`, avec validation stricte et fallback
deterministe.
Mise a jour post-Lot 10: le smoke nominal utilise `active` et la configuration
applicative par defaut demande `openai/gpt-5.2` avec
`reasoning_effort=high`. La tranche agent-first generale remplace l'exception
P03: quand Biblio est activee, un plan agent valide peut executer les outils
Catalogue GET-only allowlistes sous budgets stricts, puis injecter une lane
produit utile. Le deterministe tient les murs et reste fallback.
Mise a jour stabilisation 2026-06-02: le runtime natif Biblio porte maintenant
une verite produit explicite `exact_passage / plausible_candidate /
contextual_approximation / clarification_required`, et la resolution
documentaire FridaDev conserve `work_title` distinct de `document_title` jusque
dans le runtime.
Mise a jour refonte Lot B 2026-06-02: le contrat agent porte maintenant
`case_id` et `product_method`, et le registre declaratif des methodes produit
est livre dans `app/biblio/librarian_product_methods.py`. Les `tool_calls`
restent le sous-plan technique borne de la methode produit.
Mise a jour refonte Lot C minimal 2026-06-02: le runtime agent-first execute
maintenant ses completions bornees via `product_method`; le deterministe peut
encore tenir les murs et fournir des indices de requete, mais il ne doit plus
changer silencieusement la methode produit suivie.
Micro-correction P3 2026-06-02: un follow-up d'origine/provenance de passage
(`D'ou vient ce passage ?`, `source`, `provient`) doit maintenant etre porte
par `passage_origin_check`, distinct de `passage_explain_current`, meme si les
deux familles reutilisent aujourd'hui l'outil technique `passage_context`.
Micro-correction compare_passages 2026-06-02: le fallback dialogue
`compare_passages` doit maintenant porter explicitement
`passage_compare_candidates`, au lieu de retomber sur une inference generique
de type `passage_search_in_work`, tout en restant borne a des appels
`passage_context` content-free.
Elle ne modifie pas le planner, le client Catalogue, les routes, l'UI, la DB ou la plateforme.

Le but est de garder l'agent bibliothecaire livre testable, borne et
reversible:

- entrees explicites;
- sorties versionnees;
- actions allowlistees;
- budgets, timeouts et retries bornes;
- modele runtime-configurable;
- fallback modele et fallback deterministe;
- contrat OpenRouter / JSON a verifier avant implementation;
- observabilite content-free;
- feature flag et rollback;
- criteres GO / NO-GO des lots restants.

L'agent bibliothecaire reste une capacite Biblio. Il ne devient pas Memory/RAG, Web,
workspace, active_document, Identity, Summary, Hermeneutic, AnythingLLM ou
doc-pipeline.

## 2. Decision Lot 2 et etat Lot 3

Decision: GO conditionnel pour ouvrir le Lot 3 outils GET-only, NO-GO pour
coder directement l'agent runtime.

Etat courant: Lot 3 outils GET-only livre, Lot 4 boucle/planner
bibliothecaire bornee livre comme module non branche, Lot 5 comprehension
implicite/dialogue livre, Lot 6 navigation bornee livre, Lot 7 socle
agentique non active livre et Lot R1 ajoute la primitive documentaire
`page_read` cote FridaDev sans patch Catalogue. Lot 8 integre ce socle comme
comparaison runtime observable, sans activation produit par defaut.

Le Lot 3 peut definir le registre d'outils Catalogue bornes si et seulement si:

- l'agent reste off par defaut;
- aucun modele agent n'est appele;
- aucun slug OpenRouter n'est invente;
- aucun outil mutable ou lourd non borne n'est ajoute;
- aucun `latest/page` ou `latest/context` n'est utilise;
- aucune observabilite content-rich n'est creee.

Le remplacement du chemin deterministe reste NO-GO tant que les gates de cette
spec ne sont pas valides. Le socle modele Lot 7 peut etre appele seulement si
le mode runtime le permet; en `shadow` et `candidate`, il ne controle pas la
reponse utilisateur.

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
- aucune activation souveraine de reponse produit ne doit suivre un deploiement
  de code; le mode comparatif `active` peut appeler le modele si le runtime
  settings le demande, avec `used_for_response=false`.

## 4. Configuration modele runtime

Le modele agent ne doit jamais etre hardcode dans le code runtime.

Section runtime settings livree:

- section: `biblio_librarian_agent`;
- champs minimaux:
  - `mode`;
  - `primary_model`;
  - `fallback_model`;
  - `timeout_s`;
  - `temperature`;
  - `top_p`;
  - `max_tokens`;
  - `max_tool_calls`;
  - `max_model_calls`;
  - `max_recent_turns`;
  - `reasoning_effort`.

Contraintes:

- `primary_model` et `fallback_model` viennent des runtime settings ou d'un
  seed versionne, jamais d'un literal cache dans le module agent;
- `openai/gpt-5.2` est le candidat produit courant tant que les preuves
  OpenRouter / JSON / live restent vertes;
- ne pas inventer de compatibilite provider hors verification documentaire et
  preuve live ciblee;
- le slug observe, les capacites et les limites doivent etre documentes dans
  l'artefact OpenRouter / JSON avant implementation ou bascule de modele;
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

Le contrat agent courant est maintenant coupe en deux couches explicites.

### A. Plan agent valide aujourd'hui

Schema valide du plan agent:

```json
{
  "schema_version": "biblio_librarian_agent_v1",
  "case_id": "P01",
  "intent": "string",
  "product_method": "catalog_list_bounded",
  "tool_calls": [],
  "answer_mode": "string",
  "risk_flags": [],
  "fallback_reason": ""
}
```

Champs minimaux du plan:

- `schema_version`: obligatoire, valeur exacte attendue;
- `case_id`: identifiant de cas Biblio si reconnu sans forcer, sinon chaine vide;
- `intent`: intent bibliothecaire normalise, conserve pour compatibilite de
  transition;
- `product_method`: methode produit explicite obligatoire;
- `tool_calls`: sous-plan technique borne, tous verifies par allowlist avant
  execution;
- `answer_mode`: mode de sortie planifie (`passage`, `catalog_list`, `open_work`,
  `toc`, `conceptual_search`, `clarify`, `not_found`, `ambiguous`, `degraded`,
  `refuse_false_certainty` ou equivalent versionne);
- `risk_flags`: reason codes, jamais contenu brut;
- `fallback_reason`: reason code si modele ou schema non utilisable.

Regles:

- Lot B garantit d'abord `product_method`;
- `product_method` est le niveau produit;
- `tool_calls` ne sont plus la grammaire produit;
- `case_id` peut rester vide si plusieurs cas partagent la meme methode et que
  le bibliothecaire ne tranche pas proprement;
- pendant la transition, la reparation legacy peut inferer `product_method`
  sans forcer un `case_id`;
- la reparation legacy ne doit jamais inventer un `case_id` plus precis que ce
  que le payload repare permet d'affirmer honnetement;
- `intent` reste temporairement present pour compatibilite avec le runtime
  actuel.

### B. Resultat structure de methode cible

Le runtime n'execute pas encore souverainement toutes les methodes via ce
contrat sur toute la surface Biblio, mais la couche agent-first execute deja
ses completions bornees par `product_method` et le payload structure minimal
cible reste fige:

- `case_id`
- `product_method`
- `execution_status`
- `reason_code`
- `truth_level`
- `state_update`
- `result_summary`
- `anchors`
- `tool_trace` content-free

`execution_status` et `truth_level` sont separes:

- `execution_status`: `success`, `clarification`, `not_found`, `error`;
- `truth_level`: `exact`, `plausible`, `contextuel`.

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
appel. Le registre declaratif des methodes produit vit maintenant a cote dans
`app/biblio/librarian_product_methods.py`.

Outils autorises au niveau contrat:

| Outil | Source Catalogue | Notes |
| --- | --- | --- |
| `catalog_list` | `GET /catalog` | Liste bornee, pagination explicite, pas de promesse de totalite au-dela de la limite. |
| `catalog_search` | `GET /catalog` ou `GET /search` | Recherche bornee, variantes autorisees, pas de payload brut en observabilite. |
| `search_chapters` | `GET /search/chapters` | Recherche structurelle de chapitres/sections; utile pour trouver le debut d'une section interne sans locator canonique, eventuellement apres resolution d'un volume/corpus. |
| `document_open_summary` | `GET /catalog`, `GET /doc/{id}/metadata` | Resume bibliographique borne; `GET /doc/{id}` lourd interdit par defaut. |
| `document_toc` | `GET /doc/{id}/chapters` | TOC bornee ou paginee, `document_id` explicite. |
| `locate` | `GET /doc/{id}/locate` | Repere explicite, document resolu requis. |
| `passage_context` | `GET /doc/{id}/context` | Contexte borne, document et position explicites. |
| `page_read` | `GET /doc/{id}/page/{page_no}` | Lecture bornee d'une page explicite seulement; `document_id` explicite requis, chars bornes, jamais `latest/page`. |

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

Implementation Lot 3:

- module: `app/biblio/librarian_tools.py`;
- registre expose: `catalog_list`, `catalog_search`,
  `search_chapters`, `document_open_summary`, `document_toc`, `locate`,
  `passage_context`, `page_read`;
- `latest/page`, `latest/context`, `export/chunk` et les routes mutatrices
  sont refuses avant reseau;
- `document_open_summary` n'appelle pas `GET /doc/{id}` et utilise
  `GET /doc/{id}/metadata` ou une resolution compacte via `GET /catalog`;
- les resultats internes ne retiennent pas de `CatalogueResponse.payload` brut;
- `passage_context` peut porter un contexte interne pour le futur agent, mais
  `to_observability()` n'expose que tailles, hash court, positions et ids
  courts.
- correction post-Lot 3: `passage_context` exige que le payload Catalogue
  porte un `document_id` present et egal au `document_id` demande; sinon le
  resultat est `incoherent_catalogue`, content-free, sans contexte interne;
- correction Lot E navigation: `page_read` et `passage_context` peuvent
  maintenant porter en interne un repere TOC borne `chapter_hint` (chapitre
  courant / suivant) quand Catalogue l'expose deja, mais ce repere ne fuit
  jamais brut dans `to_observability()`;
- correction post-Lot 3: les champs content-rich des resultats outils
  (`items`, `document_summary`, `chapter_hint`, `chapters`, `positions`,
  `context_text`) sont exclus de `repr(result)` et des comparaisons dataclass.

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

P03 est maintenant ferme comme cas agent-first nominal:

- le plan agent valide reconnait `case_id=P03` et `product_method=work_lookup`;
- l'execution nominale passe par `catalog_search` puis
  `document_open_summary`, sans fallback deterministe;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p03-agentic-20260603T110117Z.jsonl`.

P09 est maintenant ferme comme cas agent-first nominal:

- le plan agent valide reconnait `case_id=P09` et
  `product_method=document_toc_show`;
- l'execution nominale passe par `catalog_search` puis `document_toc`, avec
  `chapters` cote Catalogue comme sortie documentaire;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p09-agentic-20260603T112010Z.jsonl`.

La navigation complete autour d'une TOC reste separee de cette fermeture:

- fermer `document_toc_show` ne veut pas dire que toute navigation sequentielle
  ou canonique a partir de la TOC est deja un sous-cas livre.

P10 est maintenant requalifie comme case non fermee distinctement:

- le runtime sait encore poser une ancre courante exploitable apres un tour
  exact de type `P04` / `passage_extract_canonical_range`;
- mais le rerun strict montre que `P10` n'est pas aujourd'hui reconnu ni ferme
  comme cas distinct: sur le smoke cible, `agent_plan_case_id=P04`,
  `product_case_id=P04` et le validateur rejette ce croisement comme
  `case_closure_product_method_mismatch`;
- preuves datees:
  `app/docs/states/baselines/biblio-smokes/p04-agentic-rerun-20260603T131029Z.jsonl`
  et
  `app/docs/states/baselines/biblio-smokes/p10-agentic-rerun-20260603T131029Z.jsonl`.

P11 est maintenant ferme comme follow-up agent-first nominal:

- apres une ancre de passage exacte deja posee, le plan agent valide reconnait
  `case_id=P11` et `product_method=passage_explain_current`;
- l'execution nominale passe par un seul `passage_context` borne, sans
  fallback deterministe ni requalification locale du cas;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p11-agentic-20260603T113533Z.jsonl`.

P12 est maintenant ferme comme follow-up agent-first nominal:

- apres une ancre de passage exacte deja posee, le plan agent valide reconnait
  `case_id=P12` et `product_method=passage_show_around_current`;
- si le tool call initial de l'agent est trop fragile mais reste dans la meme
  methode produit, le runtime peut le reparer avec le plan dialogue borne
  homologue, sans redonner la reconnaissance du cas au parseur local;
- l'execution nominale observee reste `agent_first`, avec un seul
  `passage_context` borne autour de l'ancre courante;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p12-agentic-20260603T115629Z.jsonl`.

P13 est maintenant ferme comme navigation documentaire agent-first bornee:

- apres une ancre courante deja posee, le plan agent valide reconnait
  `case_id=P13` et `product_method=passage_move_previous_segment`;
- si `page_no/para_no` sont connus, le runtime privilegie un
  `passage_context` sur le segment precedent de la meme page;
- si le tool call initial de l'agent est trop fragile mais reste dans la meme
  methode produit, le runtime peut le reparer avec le plan dialogue borne
  homologue, sans redonner la reconnaissance du cas au parseur local;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p13-agentic-20260603T120437Z.jsonl`.

P14 est maintenant ferme comme continuation documentaire agent-first:

- apres une ancre courante deja posee, le plan agent valide reconnait
  `case_id=P14` et `product_method=passage_continue_next_segment`;
- l'execution peut rester `passage_context` quand une ancre plus fine est
  exploitable, ou se reparer vers `page_read` quand le meilleur repli borne de
  la meme methode devient page-granulaire;
- dans les deux cas, le controle reste du cote agent-first et le repli ne
  requalifie pas localement le cas;
- preuve isolee datee:
  `app/docs/states/baselines/biblio-smokes/p14-agentic-isolated-from-stateful-20260603T133545Z.jsonl`.

P15 est maintenant ferme comme verification de provenance agent-first:

- apres une ancre courante deja posee, le plan agent valide reconnait
  `case_id=P15` et `product_method=passage_origin_check`;
- l'execution peut verifier l'origine documentaire utile soit par
  `document_open_summary`, soit par `passage_context`, tant que l'ancre
  courante reste la source de verite et que la methode produit ne change pas;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p15-agentic-20260603T121537Z.jsonl`.

P16 est maintenant ferme comme recherche thematique externe agent-first:

- hors oeuvre courante, le plan agent valide reconnait `case_id=P16` et
  `product_method=passage_search_external_work`;
- l'execution bornee atteint une cible documentaire externe puis un
  `passage_context` utile sans fallback deterministe ni requalification locale
  du cas;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p16-agentic-20260603T122008Z.jsonl`.

P17 est maintenant ferme comme reformulation soeur de la meme methode externe:

- une formulation soeur du meme besoin reste reconnue explicitement comme
  `case_id=P17` et `product_method=passage_search_external_work`;
- l'execution observee reste `agent_first`, avec outils GET-only bornes et
  resultat produit utile sur oeuvre externe sans variante opportuniste locale;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p17-agentic-20260603T122300Z.jsonl`.

P18 est maintenant ferme comme troisieme reformulation de la famille externe:

- la troisieme formulation de la meme famille reste reconnue explicitement
  comme `case_id=P18` et `product_method=passage_search_external_work`;
- l'execution peut mobiliser resolution documentaire, ouverture resumee,
  `locate` et `passage_context`, tant que le controle reste du cote
  `agent_first` et que la methode produit ne change pas;
- preuve datee:
  `app/docs/states/baselines/biblio-smokes/p18-agentic-20260603T122300Z.jsonl`.

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

## 15. Lot 3 livre

Lot 3 est livre si les preuves suivantes restent vertes:

- registre d'outils GET-only defini dans `app/biblio/librarian_tools.py`;
- parametres bornes avant reseau;
- allowlist et interdictions testees;
- observabilite content-free;
- aucun appel modele agent;
- aucune activation agent.

NO-GO retroactif Lot 3 si un patch ulterieur reintroduit:

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

## 16. Lot 4 livre

Lot 4 livre uniquement la preparation de boucle/planner bibliothecaire au-dessus
du registre Lot 3.

Implementation Lot 4:

- module: `app/biblio/librarian_planner.py`;
- structures livrees: `BiblioLibrarianPlan`, `BiblioLibrarianToolCall`,
  `BiblioLibrarianLoopRequest`, `BiblioLibrarianStep`,
  `BiblioLibrarianLoopResult`, `BiblioLibrarianPlanner`;
- execution via `BiblioLibrarianToolRegistry`, sans reseau nouveau;
- budgets livres: `max_steps`, `max_tool_calls`, `max_total_duration_ms`,
  `max_clarifications`, `max_context_chars`;
- discipline post-audit: `max_clarifications` ne produit
  `needs_clarification` que si le plan structure le demande explicitement;
  un plan vide reste un fallback deterministe;
- discipline post-audit: une demande `passage_context` est bornee avant
  l'appel outil si `window_chars` depasse le budget `max_context_chars`
  restant, ou refusee avant reseau si la fenetre minimale Catalogue ne peut
  plus etre respectee;
- discipline post-audit: `max_steps` compte strictement les steps conserves;
  le statut final peut signaler `budget_exhausted` sans step additionnel si
  le budget de steps est deja consomme;
- discipline post-audit de responsabilite: `librarian_planner.py` reste centre
  sur les dataclasses publiques et la boucle `BiblioLibrarianPlanner`; les
  helpers de budget/contexte sont dans `librarian_planner_budget.py` et les
  helpers d'observabilite content-free dans
  `librarian_planner_observability.py`;
- statuts livres: `tool_executed`, `needs_clarification`, `not_found`,
  `ambiguous`, `budget_exhausted`, `tool_rejected`, `tool_failed`,
  `fallback_deterministic`;
- refus avant outil pour tool inconnu, `page_read`, `export/chunk`,
  `latest/page`, `latest/context`, methode non GET et nom de route mutatrice;
- observabilite et `repr(result)` / `repr(step)` content-free;
- aucun branchement chat/runtime produit;
- aucun OpenRouter, aucun modele externe reel, aucun slug, aucune activation.

NO-GO retroactif Lot 4 si un patch ulterieur reintroduit:

- accepter un `passage_context` dont le `document_id` Catalogue est absent ou
  divergent;
- exposer passage, titre, auteur, chapitre ou requete brute via `repr(result)`;
- regonfler `librarian_tools.py` sans necessite vitale;
- outil page non borne, sans `document_id` explicite, ou reposant sur
  `latest/page`;
- `export/chunk`;
- navigation complete;
- activation runtime produit;
- appel OpenRouter sans artefact date de verification JSON/tool calling;
- modele hardcode;
- remplacement du chemin deterministe sans preuve comparative;
- fuite content-rich dans logs/admin/dashboard/read-models.

## 17. GO / NO-GO Lot 5

GO conditionnel Lot 5 seulement pour comprehension implicite/dialogue au-dessus
de la boucle Lot 4 non branchee, sans activation produit par defaut.

NO-GO Lot 5 si le patch tente:

- brancher la boucle comme agent produit actif;
- appeler OpenRouter ou introduire un modele externe reel sans gate date;
- hardcoder un modele ou slug;
- ajouter `export/chunk`, `latest/page` ou `latest/context`;
- remplacer le chemin deterministe sans smokes comparatifs;
- declarer l'agent bibliothecaire produit livre.

## 18. Lot 5 livre

Lot 5 livre uniquement la preparation de comprehension implicite/dialogue
au-dessus de la boucle Lot 4.

Implementation Lot 5:

- module: `app/biblio/librarian_dialogue_planner.py`;
- structures livrees: `BiblioDialogueIntent`,
  `BiblioDialoguePlanningRequest`, `BiblioDialoguePlanningResult`,
  `BiblioDialoguePlanner`;
- entree: demande utilisateur interne, etat Biblio conversationnel
  content-free, dialogue recent borne a 6 messages; Lot 5 ne l'utilise pas
  encore comme signal decisionnel;
- sortie: `BiblioLibrarianPlan` executable par la boucle Lot 4, ou
  clarification/fallback structure;
- intentions preparees: `list_catalog`, `search_passage`,
  `search_current_document`, `explain_passage`, `show_table_of_contents`,
  `compare_passages`, `navigate`, `fallback`;
- statuts prepares: `planned`, `needs_clarification`,
  `unsupported_missing_tool`, `fallback_deterministic`;
- une recherche "dans ce livre" reste une recherche Catalogue globale avec
  ancre document courant explicite (`scope_mode=current_document_anchor_global_search`);
- `ce passage` / `le passage` / `reprends ce passage` / `reprends le passage`
  n'ouvrent qu'un `passage_context` borne si `last_result` contient une
  position exploitable;
- une demande de TOC avec titre explicite non resolu clarifie au lieu
  d'utiliser silencieusement le document courant, meme si le titre explicite
  precede ou suit directement les mots `table des matieres` ou `sommaire`;
- les qualificatifs de TOC (`complete`, `detaillee`, `complet`, `general`)
  ne sont pas traites comme des titres explicites quand ils sont seuls; s'ils
  sont suivis d'un titre probable, la demande clarifie;
- les emplois discursifs ou thematiques de `avant` ne sont pas des commandes
  de navigation; seuls les deplacements documentaires explicites restent
  `navigate`;
- la navigation ou la page suivante ne simule aucun outil absent: elle retourne
  `unsupported_missing_tool` ou `needs_clarification`;
- observabilite et `repr(result)` content-free: pas de requete brute, titre,
  auteur, passage, payload Catalogue ou prompt complet;
- aucun branchement chat/runtime produit;
- aucun OpenRouter, aucun modele externe reel, aucun outil page, aucun
  `export/chunk`, aucun `latest/page`, aucun `latest/context`;
- `librarian_planner.py`, `librarian_tools.py` et
  `librarian_planner_observability.py` ne portent pas la comprehension
  dialogue.

NO-GO retroactif Lot 5 si un patch ulterieur reintroduit:

- interpretation dialogue dans `librarian_planner.py`;
- logique dialogue dans `librarian_planner_observability.py`;
- appel OpenRouter ou modele reel sans lot de gate separe;
- outil page non borne ou route `latest`;
- fuite content-rich via observabilite ou `repr(result)`.

## 19. Lot 6 livre

Lot 6 livre uniquement une navigation bibliothecaire bornee au-dessus de
l'etat Biblio conversationnel existant. Il ne cree pas de route Catalogue et,
historiquement, ne simulait pas de lecture page voisine.

Implementation Lot 6:

- module: `app/biblio/librarian_dialogue_navigation.py`;
- classification structuree: `continue`, `page_previous`, `page_next`, `up`,
  `down`, `around_passage`, `nearby_passage`, `generic`;
- `around_passage` peut produire un `passage_context` GET-only si et seulement
  si `last_result` contient une position exploitable et un `document_id`
  explicite;
- le contexte autour utilise une fenetre bornee (`window_chars=1400`) et reste
  soumis aux bornes de la boucle bibliothecaire;
- `continue`, page precedente/suivante, plus haut/bas et passage proche ne sont
  pas inventes dans le Lot 6 historique: ils retournent
  `unsupported_missing_tool` sur etat valide, ou `needs_clarification` si
  l'etat manque;
- une navigation qui nomme un ouvrage explicite non resolu (`dans le Theetete`,
  `dans Platon`, `chez Platon`, `dans l'Apologie`, `de l Apologie`,
  `d'Apologie`) clarifie avec
  `biblio_dialogue_navigation_explicit_reference_unresolved` et ne reutilise
  jamais le document courant;
- `passage proche` reste navigation seulement pour une reprise anaphorique
  (`un autre passage proche`, `passage voisin`); avec un verbe de recherche et
  un theme/ouvrage explicite, la demande reste `search_passage`;
- les formes TOC avec politesses apres qualificatif (`stp`, `merci`,
  `maintenant`, `s il te plait`) restent des TOC du document courant si l'etat
  existe; les formes `qualificatif + titre` clarifient toujours;
- observabilite et `repr(result)` restent content-free;
- aucun `latest/page`, aucun `latest/context`, aucun `export/chunk`, aucun
  OpenRouter, aucun appel modele, aucun branchement runtime produit.

### Mise a jour Lot R1 - navigation documentaire reelle

La navigation documentaire page est maintenant livree cote FridaDev, sans
patch Catalogue:

- `CatalogueClient.page(document_id, page_no)` appelle seulement
  `GET /doc/{id}/page/{page_no}`;
- l'outil `page_read` est allowliste, GET-only, borne, avec `document_id`
  explicite obligatoire;
- le runtime peut resoudre un document/volume explicitement nomme dans une
  requete de navigation page, puis composer cette resolution sur `page_read`;
- `librarian_dialogue_planner.py` et `chat_runtime.py` executent maintenant
  `page suivante / page precedente` et `page 28 a page 32` sur `page_read`
  quand l'etat porte une page ancree; `continue apres ce passage` peut, lui,
  utiliser `passage_context` sur l'ancre de fin d'un range deja extrait quand
  `interval_hint.end_page_no` / `end_para_no` ou `end_paragraph_id` sont
  connus; les formes nommees utilisent l'ancre de page seulement si le
  document resolu est bien le meme que celui deja ancre;
- `autour de ce passage` reste sur `passage_context`, ce qui garde la verite
  produit entre lecture de page et contexte autour d'un passage;
- une oeuvre interne non mappee proprement a des pages documentaires reelles
  (par exemple `Theetete` dans un volume `Platon`) reste hors de ce lot et
  ne doit pas etre promue silencieusement en navigation page supportee;
- `deux pages apres 147c` reste hors contrat tant qu'un lien general
  locator -> page/offset n'est pas prouve;
- `latest/page` et `latest/context` restent interdits.

NO-GO retroactif Lot 6 si un patch ulterieur:

- fabrique un voisin de page/paragraphe par arithmetique sans route sure;
- utilise `latest/page`, `latest/context`, `export/chunk` ou `/doc/{id}` lourd
  comme navigation automatique;
- navigue sans `document_id` explicite;
- reutilise le document courant quand la navigation nomme un autre ouvrage
  non resolu;
- expose passage, prompt, titre brut, requete brute ou payload Catalogue en
  observabilite.

## 20. Lot 7 livre

Lot 7 livre uniquement le socle agentique non souverain du bibliothecaire.

Implementation:

- module contrat: `app/biblio/librarian_agent_contract.py`;
- module OpenRouter: `app/biblio/librarian_agent_openrouter.py`;
- orchestration: `app/biblio/librarian_agent.py`;
- schema sortie agent: `biblio_librarian_agent_v1`;
- modes: `off`, `shadow`, `candidate`, `active`;
- default runtime post-Lot 10:
  section DB `biblio_librarian_agent` seedee avec `mode=active`,
  `primary_model=openai/gpt-5.2`, `timeout_s=240`,
  `max_tokens=16000`, `max_recent_turns=5`, `reasoning_effort=high`;
- avec `provider.require_parameters=true`, le caller bibliothecaire garde
  `reasoning` et `response_format=json_schema`; pour les modeles `openai/gpt-5*`,
  il omet `temperature` et `top_p` si le provider ne les annonce pas comme
  supportes sur ce chemin strict.
- `active` est reconnu comme valeur de mode mais n'est pas utilise comme
  chemin souverain de reponse produit dans ce lot;
- `shadow` et `candidate` peuvent valider un plan JSON mais gardent
  `fallback_deterministic=true` et `used_for_response=false`;
- les variables `BIBLIO_LIBRARIAN_AGENT_*` restent des seeds/bootstrap, pas la
  source runtime principale apres presence de la section DB;
- referer/title dedies: `OPENROUTER_REFERER_BIBLIO_LIBRARIAN` et
  `OPENROUTER_TITLE_BIBLIO_LIBRARIAN`;
- transport OpenRouter: URL et secret viennent du runtime shared
  `main_model` via `llm_client.or_chat_completions_url()` et
  `llm_client.or_headers_custom(...)`; le bibliothecaire ne lit pas
  directement `OPENROUTER_API_KEY`;
- payload OpenRouter: `response_format.type=json_schema`,
  `json_schema.name=biblio_librarian_agent_v1`, `strict=true`,
  `provider.require_parameters=true`, `reasoning={"effort": "...",
  "exclude": true}` si configure. Sur le chemin `openai/gpt-5*`, le caller
  omet `temperature` et `top_p`, n'utilise pas `oneOf` dans
  `tool_calls.items`, et declare un `call_id` nullable ainsi qu'un objet
  `params` ferme a superset nullable des cles Biblio; le validateur local
  FridaDev reste souverain pour filtrer les `null` / vides puis revalider
  l'executabilite par outil contre `librarian_tools.py`;
- le contrat JSON est obligatoire dans le Lot 7; il n'existe plus de setting
  operateur pour le desactiver, et `provider.require_parameters` ne depend
  d'aucune variable d'environnement;
- le fallback modele est tente seulement si un `fallback_model` est configure
  et si `max_model_calls >= 2`;
- le raw prompt, le raw JSON modele et la reponse provider brute ne sont pas
  retenus dans `BiblioLibrarianAgentResult`;
- le plan candidat interne est un `BiblioLibrarianPlan`, dont `repr` et
  `to_observability()` ne sortent pas les params bruts.

### Stabilisation Lot 11

Le test utilisateur live peut reveler des besoins de stabilisation sans
rouvrir l'activation agent-first. Les corrections Lot 11 restent bornees:

- timeout bibliothecaire nominal `240s` pour laisser au modele le temps de
  produire un plan JSON complet;
- prompt bibliothecaire oriente methode: chercher d'abord le texte primaire,
  distinguer commentaire/notice/TOC/candidat/passage exact, et progresser par
  `catalog_search`, resume/TOC si utile, `locate`, puis `passage_context`;
- pour une requete canonique explicite `extract_passage` / `extract_range`
  avec `locator` present, l'agent-first reste compare/observable mais ne
  controle pas la reponse produit tant qu'il ne depasse pas clairement le
  chemin exact existant; le deterministe tient ce mur;
- references canoniques Stephanus: `locate` traite les labels simples; une
  plage doit etre planifiee comme debut/fin separes si un `document_id` est
  disponible ou porte;
- cote deterministe, une plage canonique bornee peut maintenant etre extraite
  sur plusieurs pages quand les deux ancres se resolvent vers des positions
  `page_no` / `para_no` coherentes; ce support reste borne et ne remplace pas
  encore un objet d'intervalle canonique general;
- aucun passage, payload Catalogue, prompt brut, titre/auteur/requete brute ou
  secret ne peut etre conserve dans les preuves techniques.

Le diagnostic date `stephanus-locate-diagnostic-20260601T195136Z.md` constate
content-free que les labels simples peuvent etre localises sur certains
documents, mais qu'une plage brute n'est pas encore un objet Catalogue
exploitable directement. Le correctif immediat est donc le guidage du planner;
le controle produit des locators explicites reste donc deterministe, et le
support range complet reste conditionne a un outil/index/mapping dedie si les
tests live le confirment, meme si le chemin deterministe sait maintenant
assembler un intervalle borne multi-page a partir des ancres resolues et des
pages Catalogue existantes.

Validation:

- JSON absent, invalide, tronque ou texte libre -> fallback deterministe;
- schema version inconnue -> fallback deterministe;
- champs racine en trop, champs requis absents, `risk_flags` invalides,
  call keys en trop -> fallback deterministe;
- `params` absent ou non objet JSON -> fallback deterministe avec schema
  invalid; le validateur ne normalise pas `null`, liste, string, nombre ou
  booleen en `{}`;
- params inconnus, params hors bornes ou params insuffisants pour executer
  l'outil GET-only -> fallback deterministe avec
  `biblio_librarian_agent_tool_not_executable`;
- `catalog_search` exige `q` ou `query`, limite <= 50 et offset 0;
- `catalog_search` peut remonter un signal faible `document_role_signal`
  (`commentary`, `notice`, `introduction`) derive par Catalogue des titres de
  chapitre ou de document; ce signal reste un indice borne de tri, jamais une
  preuve de texte primaire, et son absence ne vaut pas signal positif;
- `document_open_summary` exige un document explicite ou une requete, limite
  <= 20;
- `document_toc` exige un document explicite, limite <= 500;
- `locate` exige un document explicite et un locator/label, limite <= 200;
- `passage_context` exige un document explicite et soit `paragraph_id`, soit
  `page_no` + `para_no`;
- `tool_calls` au-dela du budget -> fallback deterministe;
- outil interdit (`latest/page`, `latest/context`, `export/chunk`,
  mutateurs, ou `page_read` sans `document_id` explicite / hors bornes)
  -> fallback deterministe;
- outil inconnu -> fallback deterministe;
- methode non GET -> fallback deterministe;
- timeout ou erreur provider -> fallback deterministe;
- timeout ou erreur provider primaire -> fallback modele seulement si le
  budget d'appels modele le permet;
- modele ou cle provider absents -> aucun appel provider;
- `model_called` signifie tentative provider reelle (`attempt_count > 0`), pas
  simple invocation de l'adaptateur local;
- `active` -> aucun appel provider dans le Lot 7;
- dialogue recent borne a `BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS`.

Observabilite autorisee:

- mode;
- status / reason code;
- booleens `model_called`, `used_for_response`, `fallback_deterministic`;
- modele effectif expurge;
- fallback model configured/used;
- attempt count;
- primary reason code si fallback utilise;
- finish reason;
- duree;
- status code;
- longueur/hash du JSON modele, jamais le JSON;
- noms d'outils;
- nombre d'appels outil;
- budgets configures.

Observabilite interdite:

- message utilisateur brut;
- dialogue brut;
- prompt agent;
- raw JSON modele;
- params d'outils bruts;
- titre, auteur, locator, passage ou payload Catalogue;
- token, cookie, DSN, `.env`.

NO-GO retroactif Lot 7 si un patch ulterieur:

- fait de l'agent le controleur produit par defaut;
- utilise `active` comme chemin produit sans lot separe;
- execute les outils proposes par le modele dans le chat sans validation
  comparative;
- conserve le raw JSON modele dans un resultat durable;
- annonce `model_called=true` alors qu'aucune tentative provider n'a eu lieu;
- valide un plan que `librarian_tools.py` rejetterait immediatement faute de
  query, document, position ou borne specifique;
- hardcode DeepSeek V4 Pro dans la logique metier au lieu de le garder comme
  default config/env surchargeable;
- remplace le chemin deterministe sans rollback;
- expose un contenu brut dans admin/dashboard/logs/read-model/smokes.

## 21. Lot 8 livre

Lot 8 integre l'agent dans le runtime Biblio uniquement comme comparateur
observable et reversible.

Implementation:

- module comparateur: `app/biblio/librarian_agent_runtime.py`;
- wiring: `app/biblio/chat_runtime.py` apres decision/baseline
  deterministe;
- dialogue recent borne passe depuis `app/core/chat_service.py`;
- projection content-free ajoutee dans l'evenement Biblio sous
  `librarian_agent`;
- aucun outil propose par le modele n'est execute dans le chat produit;
- aucune lane prompt n'est construite depuis le plan agent;
- `used_for_response` reste toujours false;
- `product_response_changed` reste false;
- `deterministic_controller` reste true.

Modes:

- Biblio off -> aucun comparateur agent et aucun appel modele;
- mode agent `off` -> comparateur skipped, aucun appel modele;
- `shadow` -> appel modele possible si modele/provider configures, plan valide
  observe, reponse deterministe inchangee;
- `candidate` -> plan candidat conserve/observe, reponse deterministe
  inchangee;
- `active` -> toujours non active produit, aucun remplacement souverain.

Fallback:

- JSON invalide, outil interdit, plan non executable, timeout provider,
  erreur provider ou exception du comparateur -> fallback deterministe;
- l'erreur du comparateur ne peut pas transformer le tour Biblio en decision
  produit agentique.

Observabilite Lot 8 autorisee:

- mode;
- status / reason code;
- model_called;
- candidate_plan_present;
- deterministic_controller;
- product_response_changed;
- used_for_response;
- hashes/longueurs du message courant et dialogue recent via la requete agent;
- observations agent deja expurgees par Lot 7.
- observation de requete sous la cle `request_observation`, jamais sous
  `request` qui reste une cle redigee globalement.

Observabilite Lot 8 interdite:

- message utilisateur brut;
- dialogue brut;
- prompt agent;
- raw JSON modele;
- params d'outils bruts;
- passage, titre, auteur, locator, payload Catalogue ou secret.

NO-GO retroactif Lot 8 si un patch ulterieur:

- utilise le plan agent pour repondre a l'utilisateur sans lot d'activation
  separe;
- appelle l'agent quand Biblio est desactivee;
- appelle le modele en mode agent `off`;
- transforme `candidate` en decision produit;
- casse le fallback deterministe;
- expose du contenu brut dans les projections techniques.

## 22. Lot 9 livre

Lot 9 rend l'agent bibliothecaire comparatif lisible par les surfaces
operateur sans l'activer comme controleur produit.

Observabilite reelle exposee:

- mode, status, reason code, `model_called`, `candidate_plan_present`;
- `request_observation` avec presence, longueurs, hashes courts et counts du
  message courant et du dialogue recent;
- settings expurges: modele primaire/fallback, timeout, budgets et contrat JSON
  obligatoire;
- observation modele: modele effectif expurge, finish reason, duree, status
  code, response chars, attempt count, fallback model flag;
- observation validation JSON: status, reason code, longueur/hash JSON, noms
  d'outils allowlistes, nombre d'appels outil proposes;
- comparaison produit fallback: `used_for_response=false`,
  `product_response_changed=false`, `deterministic_controller=true`;
- tranche agent-first generale: `execution_scope=agent_first`,
  `used_for_response=true`, `product_response_changed=true`,
  `deterministic_controller=false`, `tool_execution_status=executed`,
  `tool_call_event_count>=1`;
- hors mode agent-first actif, absence d'execution agentique runtime:
  `tool_execution_status=not_executed`, `tool_call_event_count=0`,
  `selection_event_count=0`, `state_update_event_count=0`,
  `final_event_count=0`.

Dashboard/read-model:

- `biblio_json.librarian_agent` persiste une projection compacte content-free;
- les buckets Biblio agregent les modes, statuts, appels modele, tentatives,
  durees, validations, controle deterministe et compteurs d'outil agentique
  executes;
- les metriques agent declarees distinguent le controle deterministe normal
  (`librarian_agent_deterministic_controlled_turns`) des erreurs/fallbacks;
- la story admin mentionne l'agent seulement comme comparaison observee.

Interdits Lot 9:

- inventer des events `tool_call`, `selection`, `state_update` ou `final` si le
  runtime ne les execute pas;
- exposer message brut, dialogue brut, prompt agent, raw JSON modele, params
  d'outils bruts, passage, titre, auteur, locator, payload Catalogue ou secret;
- utiliser le plan agent pour modifier la reponse visible.

NO-GO retroactif Lot 9 si un patch ulterieur:

- transforme un signal `not_executed` en evenement fictif;
- ajoute des projections dashboard content-rich;
- rend `used_for_response` ou `product_response_changed` vrai sans lot
  d'activation separe;
- appelle le modele en mode `off` ou quand Biblio est desactivee.

## 23. Lot 10 livre

Lot 10 ajoute un protocole de smoke produit philosophique. La tranche
post-Lot 10 fait de l'agent actif le controleur principal Biblio sous murs
deterministes GET-only et budgets stricts.

Runner:

- commande canonique:
  `python -m biblio.smoke_librarian_agent_live --jsonl`;
- mode agent par defaut: `active`;
- `off` est reserve aux tests negatifs explicites;
- options explicites: `--agent-mode off|config|active|shadow|candidate`;
- execution agent-first autorisee pour les outils GET-only allowlistes:
  `catalog_list`, `catalog_search`, `search_chapters`,
  `document_open_summary`, `document_toc`, `locate`, `passage_context`,
  `page_read`;
- aucun appel modele en mode `off`;
- `shadow` et `candidate` sont des modes compat/dev; ils ne valent pas preuve
  produit nominale;
- `active` doit appeler le modele; il controle la reponse produit seulement si
  un plan valide, repare, ou un fallback borne issu des signaux
  deterministes/dialogue content-free est execute par le registre d'outils sous
  budgets et `execution_scope=agent_first`;
- sortie JSONL uniquement content-free.

Matrice couverte:

- catalogue complet et question "100 ouvrages";
- recherche/ouverture Platon/Theetete;
- extraction bornee 126b-128a;
- recherche thematique maieutique, sage-femme et images d'accouchement;
- distinction P05/P06 tenue dans la grammaire agentique:
  forme canonique accentuee vs variante ASCII/sans accents, sans
  re-decider le cas dans un parseur local;
- table des matieres;
- reprise conversationnelle: expliquer, autour, plus haut, continuer, origine;
- cas externe Kant / Lumieres / Sapere aude.

Chaque record expose seulement:

- `case_id`, `case_kind`;
- status/reason/query kind;
- counts Catalogue, endpoint kinds, context calls, candidats, selections,
  passages, lane chars;
- ids courts, hashes courts, longueurs;
- observation dialogue/agent content-free;
- `agent_plan_tool_names` pour le plan modele valide et
  `agent_executed_tool_names` pour les outils reellement executes apres
  continuation, carry ou fallback borne;
- statuts separes `runtime_expectation_status`,
  `agent_expectation_status`, `product_expectation_status`;
- flags guardrail: `raw_marker_leaks`, `payload_objects_retained`,
  `forbidden_endpoint_used`;
- `product_expectation_status` (`met`, `partial_required_attention`,
  `failed`) et reason code.

Le runner sort non-zero en mode strict si:

- une fuite brute est detectee;
- un payload Catalogue reste retenu;
- un endpoint lourd interdit comme `document` apparait;
- l'agent est utilise pour la reponse produit sans `execution_scope=agent_first`
  valide;
- la reponse produit change sans `execution_scope=agent_first` valide;
- une execution outil agentique sort des outils GET-only allowlistes ou des
  endpoints bornes;
- l'agent nominal `active` n'appelle pas le modele ou ne produit pas de plan
  candidat valide;
- un fallback borne repare une reponse produit mais est declare comme succes
  pur du plan modele au lieu de `fallback_repaired`;
- un mode compat/dev `shadow` ou `candidate` est utilise comme preuve nominale;
- une attente produit est `failed` ou `partial_required_attention`.

`--no-product-strict` ne desactive pas l'echec agent. Une option debug separee
`--no-agent-strict` existe pour inspection non bloquante, mais elle ne fait pas
partie du chemin de validation normal.

Un plan du dialogue planner local ne suffit jamais a rendre un cas produit
`met`. Il peut seulement aider le diagnostic ou servir de fallback borne apres
appel modele actif invalide/vide, et uniquement si les outils GET-only sont
reellement executes et que la lane produit contient des donnees utiles. Les cas
runtime non trouves doivent rester visibles comme `failed` ou
`partial_required_attention` au lieu de produire un faux vert.

Preuve agent-first P01-P18 courante:

- artefact:
  `app/docs/states/baselines/biblio-smokes/agent-first-full-20260601T181903Z.jsonl`;
- 18/18 records avec `runtime_expectation_status=met` et
  `product_expectation_status=met`;
- correction post-audit: les cas repares par fallback borne ne doivent plus
  etre comptabilises comme `agent_expectation_status=met`; ils doivent exposer
  `fallback_repaired` et des `agent_executed_tool_names` content-free;
- artefact post-correctif:
  `app/docs/states/baselines/biblio-smokes/agent-first-full-post-truth-fix-20260601T185215Z.jsonl`,
  18/18 records avec `runtime_expectation_status=met`,
  `product_expectation_status=met`, `raw_marker_leaks=false`,
  `payload_objects_retained=0`, et statuts agent `met` / `fallback_repaired`;
- artefact historique de cloture Lot E P03-P18, desormais stale comme preuve
  finale:
  `app/docs/states/baselines/biblio-smokes/lot-e-p03-p18-final-20260603T123538Z.jsonl`;
- reruns cibles de coherence `2026-06-03`:
  - `p04-agentic-rerun-20260603T131029Z.jsonl`: `P04` aligne
    `case_id/agent_plan_case_id/product_case_id` sur
    `passage_extract_canonical_range`;
  - `p10-agentic-rerun-20260603T131029Z.jsonl`: `P10` echoue strictement avec
    `case_closure_product_method_mismatch`;
  - `p14-agentic-rerun-stateful-20260603T131342Z.jsonl`: artefact stateful
    mixte utile pour le contexte de reprise, mais pas preuve stricte isolee de
    `P14` parce qu'il contient aussi `P10`;
  - `p14-agentic-isolated-from-stateful-20260603T133545Z.jsonl`: preuve
    stricte isolee de `P14`, extraite d'un rerun live stateful minimal et
    validee seule avec `strict_exit=0`;
- flags `raw_marker_leaks=false`, `payload_objects_retained=0`,
  `forbidden_endpoint_used=false` sur la matrice.

Dette structurelle acceptee hors micro-corrections: plusieurs modules agent
(`librarian_agent_first.py`, `chat_runtime.py`, `librarian_agent_contract.py`,
`librarian_tools.py`) sont gros. Les prochains lots doivent eviter de les
rallonger sans extraction par responsabilite.

Etat apres cleanup Lot D:

- reconnaissance de cas: `query_planner.py`, `librarian_dialogue_planner.py`,
  `conversation_followup.py`;
- registre de methodes: `librarian_product_methods.py`;
- execution runtime: `library_runtime.py`, `librarian_method_runtime.py`,
  `librarian_agent_first.py`, `librarian_navigation_runtime.py`,
  `librarian_dialogue_runtime.py`;
- outils techniques GET-only: `librarian_tools.py`;
- projections runtime / observabilite content-free:
  `librarian_planner_observability.py`, `librarian_runtime_projection.py`,
  `observability.py`.

Interdits Lot 10:

- passage brut;
- OCR brut;
- payload Catalogue;
- prompt complet;
- requete utilisateur brute;
- titre, auteur, locator brut;
- raw JSON modele;
- params d'outil bruts;
- cookie, token, DSN, `.env` ou secret.

NO-GO retroactif Lot 10 si un patch ulterieur:

- affiche les messages de smoke dans le JSONL;
- rend `--agent-mode off` capable d'appeler OpenRouter;
- remet le mode nominal du runner a `off`;
- remet le mode nominal du runner a `candidate` ou `shadow`;
- autorise un record `failed` en strict;
- autorise un record `partial_required_attention` en strict;
- laisse `--no-product-strict` masquer `agent_expectation_failed`;
- contourne les flags content-free par `--no-strict` dans le chemin de
  validation normal.

## 24. Lots 11 et 12 restants

L'agent-first general est livre et corrige par:

- `73ec11d` pour la tranche agent-first generale;
- `6af332a` pour la verite operateur du smoke agent-first;
- artefact post-correctif:
  `app/docs/states/baselines/biblio-smokes/agent-first-full-post-truth-fix-20260601T185215Z.jsonl`.

Le Lot 11 n'est plus une activation produit. Il devient le lot de test
utilisateur live et de stabilisation produit. Le prochain signal source de
verite vient des usages reels de Tof avec Frida:

- demandes naturelles de catalogue, TOC, oeuvre interne, passage exact,
  recherche thematique et reprise conversationnelle;
- reponses pauvres, fausses certitudes, mauvaises citations, lenteurs,
  incomprehensions, ambiguities mal explicitees;
- frequence et utilite des fallbacks `fallback_repaired`;
- qualite de la lane produit et de la reponse visible;
- maintien strict des murs GET-only, content-free hors lane produit et
  rollback/off.

Le Lot 12 est le lot de consolidation et cloture. Il integre les retours du
Lot 11, ferme les derniers ecarts P0/P1/P2 confirmes, documente les dettes
acceptees, puis archive la roadmap seulement si les tests live utilisateur
confirment que Frida se comporte comme une bibliotheque utilisable. Il ne doit
pas promettre de GO final avant cette validation humaine.

Doctrine maintenue:

- le bibliothecaire LLM fait le travail bibliothecaire: interpretation,
  exploration, choix d'outils, consultation et construction de lane produit;
- le deterministe tient les murs: GET-only, allowlist outils, budgets,
  validation JSON, fallback borne, observabilite content-free, anti-fuite et
  rollback;
- un fallback reparateur peut donner un produit vert, mais reste observable
  comme `fallback_repaired`, pas comme succes pur du plan modele.

Dettes a conserver jusqu'a cloture ou lot dedie:

- taille des modules agent et besoin de separation par responsabilite;
- dependance OpenRouter live;
- latence et cout;
- qualite JSON et plans inexecutables;
- absence de lien general locator -> page/offset;
- absence `export/chunk`;
- limites du fonds Catalogue et de ses metadata.

## 25. Hors-scope

- ajout d'outils hors allowlist;
- remplacement des murs deterministes;
- appel OpenRouter en mode `off`;
- reouverture de l'activation agent-first comme si elle n'etait pas livree;
- outil page non borne ou navigation canonique generale;
- navigation complete;
- `export/chunk`;
- modification Catalogue;
- DB migration;
- frontend toggle supplementaire;
- plateforme OVH;
- OCR;
- rebuild/restart;
- declaration que l'agent produit est livre.
