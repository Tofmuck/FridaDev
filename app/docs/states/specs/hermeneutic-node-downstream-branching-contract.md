# Hermeneutic Node Downstream Branching Contract

Statut: decision normative historique; branchement aval livre
Portee: troisieme pause normative historique du Lot 9 pour le branchement aval sur verdict valide uniquement

Etat courant: `validation_agent` est l'arbitre final borne et l'aval projette
`validated_output` dans `[JUGEMENT HERMENEUTIQUE]` avant le prompt principal.
Le wiring autoritatif est decrit dans
`app/docs/states/architecture/fridadev-current-runtime-pipeline.md`.

## 1. Purpose

Cette spec ouvre puis ferme la pause normative du Lot 9 sur le branchement aval.

Elle tranche:

- que l'aval ne consomme jamais `primary_verdict` brut
- que `validated_output` reste la source canonique interne du branchement
- que le prompt principal recoit une projection aval en prose, et non un dump technique
- le nom du bloc prompté
- ce qui entre dans ce bloc
- ce qui n'y entre jamais
- la zone runtime concernee par le branchement

A sa redaction, elle ne codait rien et ne fermait ni le wiring runtime effectif,
ni l'observabilite finale, ni les KPI, ni la shadow.

## 2. Repo Grounding

Le repo a deja stabilise:

- `primary_verdict`
- `validation_agent`
- `validated_output`
- `final_judgment_posture`
- `pipeline_directives_final`

Surfaces deja presentes et pertinentes:

- `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- `app/docs/states/specs/hermeneutic-node-validated-output-contract.md`
- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/main_system.txt`
- `app/prompts/main_hermeneutical.txt`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`

A sa redaction, cette spec ne creait aucun wiring. Elle fixait seulement la
frontiere normative du branchement aval, livre depuis.

## 3. Regle Forte De Consommation Aval

L'aval ne consomme jamais directement:

- `primary_verdict`
- `justifications`
- `validation_dialogue_context`
- `node_state`
- les blocs `audit`
- les raisons internes du validateur
- les logs ou evenements techniques

Regle forte:

- `validated_output` est la seule source canonique interne du branchement aval
- le prompt principal ne recoit jamais le dossier interne complet

## 4. Nature Exacte Du Branchement Aval

Le branchement aval est une traduction downstream.

Il ne consiste pas a injecter tel quel:

- un JSON brut de `validated_output`
- un dump de `primary_verdict`
- un bloc composite des artefacts internes

Il consiste a projeter `validated_output` vers:

- un bloc dedie
- redige en prose
- compact
- deterministe
- lisible par le LLM principal

## 5. Nom Retenu Pour Le Bloc Prompté

Nom retenu pour le bloc aval prompté:

- `[JUGEMENT HERMENEUTIQUE]`

Raison:

- le repo utilise deja des briques promptées visibles entre crochets
- cette forme est coherente avec `[RÉFÉRENCE TEMPORELLE]`, `[IDENTITE ...]`, `[Memoire -- ...]`
- elle reste plus propre qu'un transport XML ou qu'un dump JSON brut

## 6. Source Canonique Et Projection Aval

Frontiere retenue:

- `validated_output`
  - reste la surface canonique interne, structuree et testable
- `[JUGEMENT HERMENEUTIQUE]`
  - est la projection aval promptée, en prose, derivee de `validated_output`

Regles fortes:

- le bloc aval derive de `validated_output`
- il ne remplace pas `validated_output`
- il ne rouvre ni la combinaison normative, ni la validation
- le prompt principal ne doit pas re-deduire lui-meme `final_judgment_posture`

## 7. Contenu Minimal Du Bloc Aval

Le bloc prose aval contient au minimum:

- la posture finale validee
- le regime final valide
- une consigne hermeneutique compacte compatible avec cette posture
- une consigne de regime compacte compatible avec ce regime
- les directives finales actives utiles au prompt principal

Decision retenue:

- `validation_decision` peut rester interne comme trace legacy en lot 2
- elle n'a pas besoin d'etre exposee verbatim au prompt principal
- son effet normatif n'est plus souverain
- l'autorite effective du bloc projete vient de `final_judgment_posture`, `final_output_regime` et `pipeline_directives_final`

N'entrent jamais dans ce bloc:

- `primary_verdict` brut
- `justifications`
- `validation_dialogue_context`
- `node_state`
- `audit`
- des raisons longues de validation
- des blocs JSON bruts amont

## 8. Forme Prose Retenue

La prose aval doit rester:

- breve
- normative
- compacte
- stable
- testable

Forme minimale historique retenue avant l'ajout de `presence`:

```text
[JUGEMENT HERMENEUTIQUE]
Posture finale validee: <answer|clarify|suspend>.
Regime final valide: <simple|meta>.
Consigne hermeneutique: <consigne normative compacte deja resolue>.
Consigne de regime: <consigne compacte deja resolue>.
Directives finales actives: <code_1[, code_2, ...]>.
```

Le contrat courant accepte aussi `presence`, uniquement avec
`final_judgment_posture=answer`; cette decision positive locale produit la
sortie exacte `...` et reste distincte de `suspend`.

Discipline minimale:

- pas de blob libre
- pas de justification longue
- pas de sermon
- pas de relecture du dossier amont

## 9. Consignes Minimales Par Posture

Projection minimale retenue:

- `answer`
  - "Tu peux produire une reponse substantive normale."
- `clarify`
  - "Tu ne dois pas repondre directement au fond. Tu dois demander une clarification breve et explicite."
- `suspend`
  - "Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente."

Les `pipeline_directives_final` restent visibles dans la ligne:

- `Directives finales actives: ...`

La prose aval reste donc:

- resolue
- interpretable
- sans exposer la mecanique interne complete

## 10. Zone Runtime Cible Historique

Zone runtime concernee par ce contrat:

- `app/core/chat_service.py`
  - point d'orchestration et de passage du jugement valide vers le montage prompt aval
- `app/core/chat_prompt_context.py`
  - lieu cible historique, desormais effectif, pour construire puis injecter le bloc `[JUGEMENT HERMENEUTIQUE]`
- `app/prompts/main_system.txt`
- `app/prompts/main_hermeneutical.txt`
  - surfaces promptées qui doivent lire ce bloc comme une brique normative supplementaire

Decision retenue:

- le bloc `[JUGEMENT HERMENEUTIQUE]` appartient au branchement prompté aval
- en V1, il doit etre pense comme une brique du prompt augmente
- il ne doit pas etre injecte comme dossier brut dans le dernier message utilisateur

## 11. Non-goals de la pause initiale (historiques)

Lors de sa redaction, cette pause normative ne fermait pas encore:

- le wiring runtime effectif, livre depuis
- l'observabilite finale
- les KPI
- les preconditions shadow
- la shadow globale
- la generation des `justifications`
- la generation de `validation_dialogue_context`
