# Validation HPS - 2026-05-04

Statut: validation terminee
Classement: `app/docs/todo-done/validations/`
Chantier valide: `app/docs/todo-done/validations/hermeneutical-post-stabilization-todo.md`

## Contexte

Cette note clot le chantier HPS comme validation post-stabilisation automatisee.

Les anciennes conditions de type "observer en production" ont ete remplacees par des tests, fixtures, corpus controles, logs synthetiques et probes read-only rejouables. La validation ne depend pas de donnees conversationnelles privees ni d'une attente passive de production.

Commits principaux verifies:
- `6e4f67112053d12a03b9a3bb8f8919f083068d95`: recadrage HPS automatisable et premier test de contrat.
- `0e920ca835ef4b96d97a4eb96080913e27c0fb5f`: corpus HPS-L2, garde identity `irony|role_play` et preuves associees.

## Commandes executees

```bash
docker exec platform-fridadev python tests/unit/memory/test_hermeneutical_post_stabilization_contract.py
docker exec platform-fridadev python tests/unit/memory/test_memory_store_blocks_phase8bis.py
docker exec platform-fridadev python tests/test_memory_store_phase4.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py
docker exec platform-fridadev python tests/test_server_chat_compact_observability_contract.py
docker exec platform-fridadev python tests/test_server_chat_synthetic_logs_contract.py
docker exec platform-fridadev python tests/test_server_admin_memory_surface_phase10e.py
docker exec platform-fridadev python tests/test_server_admin_hermeneutics_phase4.py
docker exec platform-fridadev python tests/test_server_logs_phase3.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_identity_content_guards.py
docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'
```

## Resultats

Toutes les suites HPS-L1/HPS-L2 et les contrats adjacents ont passe.

Couverture validee:
- `[Contexte du souvenir]` derive uniquement de `parent_summary` dans le contrat teste.
- `no_data`, `retrieve_error` et memoire utile restent distingues dans le chemin aval.
- `prompt_prepared`, `memory_arbitration`, `hermeneutic_node_insertion`, `branch_skipped` et les logs synthetiques restent relisibles.
- Le chemin identity actif ne canonise pas une fenetre `irony|role_play` quand ce signal est extrait.
- Le fallback arbitre reste borne: pas de reinjection globale du panier.
- Les compteurs de cout/latence disponibles sont nommes; le systeme ne pretend pas exposer un cout global unique.
- Le service `platform-fridadev` et sa base sont healthy; `/admin` renvoie vers Authelia sur le hostname public.

## Limites

Cette validation ne pretend pas resoudre toute ambiguite semantique humaine. Les fixtures HPS sont controlees et rejouables; elles ne remplacent pas une future evaluation de qualite sur corpus long.

Le garde `irony|role_play` depend du signal extrait. Si l'extracteur ne marque pas le mode, le garde deterministe ne peut pas deviner seul l'intention dialogique.

Le cout global complet n'existe pas comme metrique unique. Les compteurs disponibles et les stages non agreges sont explicitement traites comme limites, pas comme preuve absente cachee.

Les chantiers `moment_memory`, `Frida_from_herself`, refonte identity et refonte memory_store restent hors HPS et ne sont pas ouverts par cette cloture.

## Decision

HPS est clos comme chantier de post-stabilisation automatisee. Le TODO actif a ete archive dans `app/docs/todo-done/validations/hermeneutical-post-stabilization-todo.md`.
