# Hermeneutical Post-Stabilization - TODO residuel

Statut: ouvert  
Classement: `app/docs/todo-todo/memory/`  
Portee: reliquat post-rollout / post-stabilisation du pipeline hermeneutique deja livre  
Origine: extraction du chantier archive `app/docs/todo-done/notes/hermeneutical-add-todo.md`

Note de cadrage identity `2026-04-18`:
- ce TODO residuel peut encore servir a suivre les coutures actives avec le noeud hermeneutique et les preuves post-rollout;
- il n'est pas la source de verite du regime identity actif;
- pour la doctrine identity courante et la trace operatoire closee du chantier, utiliser separement `identity-new-contract-plan.md` puis `app/docs/todo-done/refactors/identity-new-contract-todo.md`.

## Objet

Ce document ne reouvre pas la grande implementation hermeneutique.

Il borne seulement les preuves et validations encore utiles apres stabilisation:
- mesurer proprement ce qui a deja ete livre;
- verifier qu'aucune derive silencieuse n'apparait en production;
- clarifier les zones encore ambigues comme le bloc `[Contexte du souvenir]`.

## Cadre deja tenu

- le runtime live est deja en `HERMENEUTIC_MODE=enforced_all`;
- la doctrine de jugement est posee par `app/docs/states/specs/hermeneutic-judgment-spec.md`;
- la policy runtime et ses gates vivent dans `app/memory/hermeneutics_policy.py`;
- le prompt distingue deja `Utilisateur` vs `Situation` dans `app/core/conversations_prompt_window.py`;
- la verite active identity repose maintenant sur `static + mutable narrative` / `identity_mutables`;
- les controles legacy `force_accept`, `force_reject`, `relabel` sont neutralises cote admin legacy et ne pilotent plus l'injection active.

## TODO residuel borne

- [ ] Valider sur corpus post-stabilisation que le bruit identitaire circonstanciel baisse reellement par rapport a la baseline de reference.
- [ ] Verifier sur corpus post-stabilisation qu'aucune entree `irony|role_play` n'arrive en identite durable sans override humain explicite.
- [ ] Mesurer sur conversations longues / corpus de stabilisation que le rappel memoire utile reste stable, sans chute significative.
- [ ] Consolider le surcout global `tokens + latence` du pipeline memoire complet, au-dela des seuls KPIs runtime `retrieve` / `arbiter` / `identity_extractor`.
- [ ] Verifier sur une fenetre durable qu'aucun fallback global ne reapparait.
- [ ] Echantillonner l'explicabilite via les logs admin pour confirmer que les souvenirs / traits injectes restent relisibles et attribuables.
- [ ] Trancher le statut reel du bloc `[Contexte du souvenir]`: sur OVH, `summaries=0`, `parent_summary` reste nul en pratique et le bloc n'apparait pas live hors fixtures/replay.

## Sources de verification a reutiliser

- `app/docs/states/specs/hermeneutic-judgment-spec.md`
- `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- `app/admin/admin_hermeneutics_service.py`
- `app/tests/test_server_admin_hermeneutics_phase4.py`

## Hors scope

- aucun patch runtime dans ce document;
- aucune reouverture du chantier legacy identity/control;
- aucune reecriture globale de la memoire ou du pipeline hermeneutique.
