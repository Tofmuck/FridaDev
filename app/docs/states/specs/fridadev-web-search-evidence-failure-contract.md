# Contrat Phase 7 - preuve web insuffisante locale

Date: 2026-05-22

## Doctrine

Le runtime web FridaDev est local-first: OpenRouter/Exa peut decouvrir les URLs en recherche ouverte quand il est configure, SearXNG reste provider `local`, Crawl4AI lit les URLs, FridaDev profile, rerank et observe. Parallel reste hors runtime.

OpenRouter/Exa comme provider de decouverte n'est pas un fallback automatique: la confiance ne declenche aucun appel externe.

La preuve insuffisante n'est pas une reponse d'echec codee en dur. C'est un signal content-free transmis au modele principal pour qu'il formule naturellement le bon degre de prudence.

## Signal runtime

Module applicatif: `app/tools/web_search_evidence.py`

Champs principaux:

- `web_evidence_policy_kind`: version du contrat.
- `web_evidence_status`: `not_applicable`, `sufficient`, `partial` ou `insufficient`.
- `web_evidence_reason_codes`: raisons content-free.
- `web_evidence_guidance_codes`: consignes content-free pour le modele.
- `web_evidence_can_answer`: Frida peut repondre avec le materiau disponible.
- `web_evidence_requires_caveat`: la reponse doit signaler les limites si elles touchent la conclusion.
- `web_evidence_can_suggest_reformulation`: une relance/reformulation peut etre proposee si utile.
- `web_evidence_url_request_policy`: une URL ne doit etre demandee que si elle est vraiment pertinente.
- `web_evidence_external_fallback_used`: toujours `false`.

## Cas distingues

- Aucun resultat: `no_results`, statut `insufficient`.
- Resultats trouves mais non lus/injectes: `results_found_but_not_read`, statut `insufficient`.
- Materiau snippet-only: `snippet_only_material`, statut `partial`.
- Crawl vide/erreur sur les pages lues: `crawl_empty_or_error_present`, et `crawl_poor_or_absent` si aucun crawl n'a reussi.
- Source attendue absente pour un profil exigeant: `expected_source_material_missing`.
- Source situee/secondaire sans source officielle attendue: `situated_secondary_without_official_material`.
- URL explicite non lue: reason code derive du `read_state` et guidance `do_not_claim_direct_read`.
- Sources mixtes ou tension documentaire visible: `mixed_source_signals_visible`, sans censure ni suppression.

## Injection prompt

`app/core/chat_prompt_context.py` construit `[GARDE DE PREUVE WEB]` uniquement quand le statut est `partial` ou `insufficient`.

Ce bloc:

- rappelle que le signal n'est pas une phrase d'echec prefabriquee;
- demande de formuler naturellement les limites;
- interdit d'inventer une solidite documentaire que le runtime ne montre pas;
- evite le refus automatique ou le mutisme;
- autorise une reformulation ou relance seulement si utile;
- rappelle qu'une demande d'URL n'est pas le reflexe par defaut;
- confirme qu'aucun fallback OpenRouter, Exa ou Parallel n'a ete utilise; un eventuel provider Exa de decouverte doit etre visible via `web_discovery_*`.

## Hard guards hermeneutiques

`app/core/hermeneutic_node/validation/hard_guards.py` doit respecter le contrat Phase 7:

- si `web_evidence_can_answer` vaut `true`, les gardes web ne doivent pas produire `answer_forbidden`;
- si `web_evidence_requires_caveat` vaut `true`, les gardes web peuvent produire `hard_guard_effect=caveat_required`;
- `caveat_required` laisse `answer` dans les postures autorisees, mais rend la prudence non optionnelle pour le validateur;
- une URL explicite non lue peut donc etre commentee avec du materiau fallback/snippet, mais Frida ne doit jamais pretendre avoir lu directement la page;
- si le contrat de preuve web ne permet pas de repondre, les gardes `explicit_url_not_read` et `external_verification_missing` peuvent encore produire `answer_forbidden`.

## Observabilite

Les champs `web_evidence_*` sont propages dans:

- le payload runtime `web_search`;
- l'input canonique `web_input`;
- le logger du noeud hermeneutique;
- le read model pipeline;
- la checklist d'observabilite.

Les logs restent content-free: pas de prompt brut, pas de requete brute, pas de contenu crawle, pas de secret, pas de cookie, pas de HTML, pas de base64.

## Non-objectifs

- Aucun fallback externe.
- Aucun auto-web lexical.
- Aucun score de confiance actionnable.
- Aucune phrase finale scriptée.
- Aucune modification SearXNG ou Crawl4AI globale.
- Aucune suppression de sources.
