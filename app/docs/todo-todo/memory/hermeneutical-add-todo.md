# Hermeneutical Add - TODO implementation roadmap (v2)

## Objectif
Implementer une "indetermination orientee" dans Frida-mini:
- laisser le LLM libre sur le contenu,
- contraindre la methode de jugement,
- tracer les decisions,
- limiter les derives elegantes,
- rendre les erreurs explicables et corrigibles.

## Retour Claude integre dans cette V2
- [x] `defer -> accepted` est maintenant operationalise (fenetre, seuils, regles de recurrence).
- [x] Le bloc `indices contextuels recents` est specifie (selection + format + budget).
- [x] Les seuils ont des valeurs par defaut argumentables.
- [x] La contradiction de traits est traitee dans une phase dediee.
- [x] Le maillon faible (classification LLM) est couvert par override humain + feedback loop.

## Definition of done globale
- [ ] Le pipeline distingue explicitement durable vs passager.
- [ ] Le pipeline distingue auto-description vs projection vs role-play/ironie.
- [ ] Le pipeline distingue recurrence vs accident.
- [ ] Le pipeline distingue ce qui qualifie la personne vs la situation.
- [ ] Les decisions arbitre + identite sont journalisees avec motifs et scores.
- [ ] Les identites circonstancielles ne polluent plus le bloc identite durable.
- [ ] Le mode `shadow` produit des metriques comparables avant `enforced`.
- [x] Un operateur humain peut corriger les erreurs de classification.

## Parametres par defaut (a poser en Phase 0)

```env
HERMENEUTIC_SCHEMA_VERSION=v1
HERMENEUTIC_MODE=shadow

ARBITER_MIN_SEMANTIC_RELEVANCE=0.62
ARBITER_MIN_CONTEXTUAL_GAIN=0.55
ARBITER_MAX_KEPT_TRACES=3

IDENTITY_MIN_CONFIDENCE=0.72
IDENTITY_DEFER_MIN_CONFIDENCE=0.58
IDENTITY_MIN_RECURRENCE_FOR_DURABLE=2
IDENTITY_RECURRENCE_WINDOW_DAYS=30
IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS=2
IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS=6

CONTEXT_HINTS_MAX_ITEMS=2
CONTEXT_HINTS_MAX_TOKENS=120
CONTEXT_HINTS_MAX_AGE_DAYS=7
CONTEXT_HINTS_MIN_CONFIDENCE=0.60
```

- [x] Ajouter ces variables dans `config.py` avec fallback robuste.
- [x] Logger les valeurs effectives au demarrage.
- [x] Ajouter un commentaire dans la doc pour expliquer que ces seuils sont des seeds, pas des verites.

## Phase 0 - Baseline technique et dataset de regression
- [x] Sauvegarder les prompts actuels (`arbiter.txt`, `identity_extractor.txt`).
- [x] Exporter 20 a 30 conversations recentes (anonymisees) pour regression.
- [x] Constituer un lot "cas limites" (ironie, role-play, humeur, contradictions).
- [x] Mesurer baseline p50/p95 latence:
- [x] `retrieve`
- [x] `arbiter`
- [x] `identity_extractor`
- [x] Mesurer baseline bruit identitaire:
- [x] taux d'entrees identitaires ensuite supprimees manuellement.
- [x] taux d'entrees scope `situation` injectees comme traits durables.

## Phase 1 - Spec du regime de jugement
- [x] Creer `docs/states/hermeneutic-judgment-spec.md`.
- [x] Definir enums officielles:
- [x] `stability`: `durable | episodic | unknown`.
- [x] `utterance_mode`: `self_description | projection | role_play | irony | speculation | unknown`.
- [x] `recurrence`: `first_seen | repeated | habitual | unknown`.
- [x] `scope`: `user | llm | situation | mixed | unknown`.
- [x] `evidence_kind`: `explicit | inferred | weak`.
- [x] `decision`: `accept | defer | reject`.
- [x] Definir matrice de decision normative (table claire dans la doc).
- [x] Definir 3 exemples positifs + 3 negatifs par dimension.
- [x] Definir la politique "si doute, preferer defer/reject".

## Phase 2 - Contrat JSON strict arbitre memoire
- [x] Mettre a jour `state/data/prompts/arbiter.txt`.
- [x] Exiger ce schema JSON strict:

```json
{
  "decisions": [
    {
      "candidate_id": "0",
      "keep": true,
      "semantic_relevance": 0.91,
      "contextual_gain": 0.72,
      "redundant_with_recent": false,
      "reason": "..."
    }
  ]
}
```

- [x] Ajouter regle: reject si souvenir lexicalement proche mais apport contextuel faible.
- [x] Ajouter regle: penaliser circonstanciel sans utilite de reponse.
- [x] Ajouter regle: si parsing impossible, ne pas sur-injecter.

## Phase 3 - Contrat JSON strict extracteur identitaire
- [x] Mettre a jour `state/data/prompts/identity_extractor.txt`.
- [x] Exiger ce schema JSON strict:

```json
{
  "entries": [
    {
      "subject": "user",
      "content": "...",
      "stability": "durable",
      "utterance_mode": "self_description",
      "recurrence": "repeated",
      "scope": "user",
      "evidence_kind": "explicit",
      "confidence": 0.88,
      "reason": "..."
    }
  ]
}
```

- [x] Ajouter regle explicite: une humeur ponctuelle = `episodic`.
- [x] Ajouter regle explicite: ironie/role-play/projection => non durable par defaut.
- [x] Ajouter regle explicite: limites techniques de l.assistant != trait de personnalite durable.
- [x] Ajouter regle explicite: `unknown` si ambigui te forte.

## Phase 4 - Parser, validation, fallback deterministe
- [x] Implementer validateur schema arbitre (types + bornes + enums).
- [x] Implementer validateur schema identite (types + bornes + enums).
- [x] Rejeter les objets invalides sans faire planter la reponse utilisateur.
- [x] Supprimer fallback "garder tout".
- [x] Fallback arbitre en erreur:
- [x] garder `top 1` seulement si score vectoriel >= `ARBITER_MIN_SEMANTIC_RELEVANCE`.
- [x] sinon garder `0` trace.
- [x] Logger `arbiter_parse_error_count` et `identity_parse_error_count`.

## Phase 5 - Migration DB et traçabilite forte
- [x] Etendre table `identities`:
- [x] `stability TEXT DEFAULT 'unknown'`.
- [x] `utterance_mode TEXT DEFAULT 'unknown'`.
- [x] `recurrence TEXT DEFAULT 'unknown'`.
- [x] `scope TEXT DEFAULT 'unknown'`.
- [x] `evidence_kind TEXT DEFAULT 'weak'`.
- [x] `confidence FLOAT DEFAULT 0.0`.
- [x] `status TEXT DEFAULT 'accepted'` (`accepted|deferred|rejected`).
- [x] `content_norm TEXT`.
- [x] `last_reason TEXT`.
- [x] `override_state TEXT` (`none|force_accept|force_reject`).
- [x] `override_reason TEXT`.
- [x] Creer table `identity_evidence` (toutes candidatures, y compris rejets).
- [x] Creer table `arbiter_decisions` (toutes decisions de tri memoire).
- [x] Creer index sur `conversation_id`, `created_ts`, `status`, `content_norm`.
- [x] Migrations idempotentes (`IF NOT EXISTS`).

## Phase 6 - Politique `defer` operable (point critique)
- [x] Definir la fonction `should_accept_identity(entry, history)`.
- [x] Definir et documenter `defer`:
- [x] `defer` si `confidence` entre `IDENTITY_DEFER_MIN_CONFIDENCE` et `IDENTITY_MIN_CONFIDENCE`.
- [x] `defer` si `stability=durable` mais `recurrence=first_seen`.
- [x] `defer` si `scope=mixed` mais signal potentiellement utile.
- [x] Definir recurrence operationnelle:
- [x] compter seulement occurrences distantes d'au moins `IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS`.
- [x] compter max 1 occurrence par conversation pour la promotion durable.
- [x] promotion exige `IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS` conversations distinctes.
- [x] fenetre de promotion `IDENTITY_RECURRENCE_WINDOW_DAYS`.
- [x] Conditions `defer -> accepted`:
- [x] recurrence atteinte.
- [x] confidence moyenne glissante >= `IDENTITY_MIN_CONFIDENCE`.
- [x] aucune contradiction active de niveau fort.
- [x] Conditions `defer -> reject`:
- [x] expiration fenetre sans recurrence.
- [x] nouvelles evidences `irony`/`role_play`.

## Phase 7 - Gestion des contradictions de traits
- [x] Definir `is_contradictory(a, b)` (heuristique + embedding + regles lexicales).
- [x] Creer table `identity_conflicts`:
- [x] `identity_id_a`, `identity_id_b`, `confidence_conflict`, `reason`, `resolved_state`.
- [x] Politique par defaut en contradiction:
- [x] si conflit faible: baisser poids des deux entrees (`*0.9`) + flag.
- [x] si conflit fort: passer ancienne entree en `deferred` + creer ticket review.
- [x] si override humain existe: priorite override.
- [x] Ajouter test explicite du cas G (contradiction) avec verdict attendu.

## Phase 8 - Spec du bloc "indices contextuels recents"
- [x] Definir ce bloc comme NON durable (jamais fusionne dans identite stable).
- [x] Source candidates: entries `episodic` ou `scope=situation` des 7 derniers jours.
- [x] Selection: top `CONTEXT_HINTS_MAX_ITEMS` par score `recency * confidence`.
- [x] Exclure items `irony`, `role_play`, `unknown`.
- [x] Definir format d'injection:

```text
[Indices contextuels recents]
- [il y a 2 h] Utilisateur: fatigue ce soir (confidence: 0.67)
- [hier] Situation: contrainte de temps (confidence: 0.71)
```

- [x] Limiter a `CONTEXT_HINTS_MAX_TOKENS`.
- [x] Placer ce bloc apres le resume actif et avant la memoire RAG.

## Phase 9 - Injection finale et hygiene de prompt
- [x] `identity.build_identity_block()` n'injecte que `status=accepted`.
- [x] Prioriser injection durable: `durable > repeated > confidence > recency`.
- [x] Exclure `unknown` par defaut (sauf override).
- [x] Budget dedie identite: `IDENTITY_MAX_TOKENS`.
- [x] Ajouter line break et labels stables pour lisibilite des prompts.

## Phase 10 - Override humain et boucle de feedback (point critique)
- [x] Ajouter endpoint admin lecture:
- [x] `/api/admin/hermeneutics/identity-candidates`.
- [x] `/api/admin/hermeneutics/arbiter-decisions`.
- [x] Ajouter endpoint admin action:
- [x] `POST /api/admin/hermeneutics/identity/force-accept`.
- [x] `POST /api/admin/hermeneutics/identity/force-reject`.
- [x] `POST /api/admin/hermeneutics/identity/relabel` (utterance_mode/stability/scope).
- [x] Stocker `override_reason`, `override_actor`, `override_ts`.
- [x] Inclure les overrides dans la logique runtime (priorite sur inference LLM).
- [x] Ajouter export hebdo des erreurs corrigees pour ajuster prompts/seuils.

## Phase 11 - Observabilite et SLO
- [x] Ajouter compteurs:
- [x] `identity_accept_count`, `identity_defer_count`, `identity_reject_count`.
- [x] `identity_override_count`.
- [x] `arbiter_fallback_count`.
- [x] `parse_error_count`.
- [x] Ajouter latence p50/p95 par etape.
- [x] Ajouter dashboard admin simple (JSON suffit au debut).
- [x] Alerte si `parse_error_rate > 5%` ou `fallback_rate > 10%`.

## Phase 12 - Plan de tests (granularite forte)
- [x] Fixtures anonymisees:
- [x] Cas A: preference durable explicite -> accept.
- [x] Cas B: humeur passagere -> reject durable, eventuellement defer contextuel.
- [x] Cas C: ironie explicite -> reject.
- [x] Cas D: role-play -> reject.
- [x] Cas E: projection sur tiers -> reject.
- [x] Cas F: recurrence sur 2 conversations -> promotion defer -> accepted.
- [x] Cas G: contradiction de trait -> conflit logge + baisse poids ou defer.
- [x] Tests unitaires validators JSON arbitre/extracteur.
- [x] Tests unitaires `should_accept_identity` + promotions/expirations defer.
- [x] Tests unitaires `is_contradictory` (positif/negatif).
- [x] Tests integration pipeline complet (chat -> retrieve -> arbiter -> identity write).
- [x] Tests non regression cout/latence.

## Phase 13 - Rollout progressif
- Note de realignement 2026-04-05: le runtime live est deja verifie en `mode=enforced_all` via `GET /api/admin/hermeneutics/dashboard`. Cette phase ne decrit donc plus un rollout a venir; les Steps 2-4 ci-dessous sont requalifies comme absorbes ou depasses par le rollout reel, sans pretendre qu'ils ont ete observes retrospectivement exactement tels qu'ecrits.
- [x] Step 1: deploy `HERMENEUTIC_MODE=shadow` (aucune decision bloquante).
- [x] Step 2: observer 3 a 7 jours, comparer baseline vs shadow.
  Requalification 2026-04-05: cette fenetre d'observation n'est pas documentee a posteriori comme une sequence 3-7 jours menee exactement selon le plan initial; l'etape est fermee comme depassee par le runtime reel deja en `enforced_all`.
- [x] Step 3: activer `enforced` pour identites uniquement.
  Requalification 2026-04-05: ce jalon intermediaire n'est plus un rollout actif a executer; il est absorbe par le passage runtime reel a `enforced_all`.
- [x] Step 4: activer `enforced` memoire + identites si KPIs stables.
  Requalification 2026-04-05: le runtime live est deja passe en `enforced_all`; l'etape est fermee comme etat reel atteint, sans pretendre que le chemin documentaire initial a ete suivi point par point.
- [x] Step 5: garder rollback instantane `HERMENEUTIC_MODE=off`.

## Mapping concret des fichiers a modifier
- [x] `config.py`: nouveaux flags, seuils, fenetres, budgets.
- [x] `memory/arbiter.py`: output structure, validation, fallback deterministe, logging decisions.
- [x] `memory/memory_store.py`: migrations, persistence decisions/evidence/conflicts, policy helpers.
- [x] `identity/identity.py`: filtrage `accepted`, ranking injection, budget tokens.
- [x] `server.py`: orchestration modes, bloc contextuel, endpoints admin.
- [x] `state/data/prompts/arbiter.txt`: contrat JSON et discipline de jugement.
- [x] `state/data/prompts/identity_extractor.txt`: schema epistemique + regles anti-derive.
- [x] `docs/states/hermeneutic-judgment-spec.md`: spec normative.

## Criteres d'acceptation finaux
- [ ] Reduction >= 50% des identites circonstancielles sur corpus test.
- [ ] 0 entree `irony|role_play` en identite durable sans override humain explicite.
- [ ] Rappel memoire utile stable (pas de chute > 10%).
- [ ] p95 latence additionnelle arbitre+extracteur dans la cible definie Phase 0.
- [ ] 0 cas de fallback "garder tout".
- [ ] Chaque souvenir/trait injecte est explicable via logs admin.
- [ ] Overrides humains pris en compte au tour suivant (pas seulement journalises).

## Reliquats fusionnes depuis `memory-todo.md`
- [ ] Verifier en conditions reelles que le bloc `[Contexte du souvenir]` est effectivement exploite dans la reponse et n'ajoute pas de bruit.
- [ ] Monitorer le surcout tokens + latence du pipeline memoire complet (resume actif + contexte + RAG + arbitre), en complement des KPIs arbitre/extracteur deja suivis.
- Note: la comparaison qualite avec/sans arbitre et la latence arbitre restent rattachees au Step 2 requalifie et aux criteres d'acceptation finaux; elles ne sont pas closes par le seul constat runtime `enforced_all`.

## Notes de pilotage
- [ ] Toujours preferer une erreur explicable a une heuristique opaque.
- [ ] Ne jamais bloquer la reponse utilisateur sur erreur hermeneutique.
- [ ] Le prompt seul ne suffit pas: la politique doit vivre dans le code.
- [ ] Toute decision non reversible doit etre precedee d'une periode shadow mesuree.
