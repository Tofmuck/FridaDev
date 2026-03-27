# Docs Cleanup Plan (plan + execution status)

Date: 2026-03-27
Scope: cartographie complete de `app/docs` + plan de rangement/nettoyage.

Execution status:
- Lot 1 (rangement structurel faible risque): execute
- Lot suivant (archivage legacy evident + suppression faible valeur, sans fusion des roadmaps ouvertes): execute
- Lot 3 (fusion controlee des roadmaps ouvertes): execute
- Restant: ajustement futur de `.gitignore` dans une tranche dediee

## 1) Methode et preuves de lecture

Contraintes maintenues sur les lots deja executes:
- pas de modification de contenu metier des documents
- aucune modification de `.gitignore`
- fusion des roadmaps limitee aux reliquats ouverts utiles (pas de fusion massive de contenu obsolete)

Inventaire lu (31 fichiers):
- racine `app/docs/*.md`
- `app/docs/states/*`
- `app/docs/todo-done/*`
- `app/docs/todo-todo/*`

Points legacy explicitement verifies dans le contenu:
- references `frida-mini`, `kiki-mini`, `Olive`, anciens chemins `/home/tof/apps/kiki-mini`, ancien service `frida-mini.service`
- redondances de roadmap entre `todo-todo/*` et le pilotage courant `fridadev_refactor_todo.md`

## 2) Regles de classement retenues

Actions du plan:
- `garder ici`
- `deplacer`
- `fusionner`
- `supprimer`

Qualification par fichier:
- `canonique`
- `historique utile`
- `chantier ouvert`
- `obsolete / legacy`
- `doublon / faible valeur`

## 3) Structure cible proposee (stricte)

Objectif: garder la logique actuelle (`states/`, `todo-done/`, `todo-todo/`) mais la rendre lisible rapidement pour un humain.

```text
app/docs/
  README.md
  docs_cleanup_plan.md

  # Canoniques actifs conserves a la racine (liens deja references dans le repo)
  admin-todo.md
  admin-implementation-spec.md
  admin-runtime-settings-schema.md
  admin-operations.md
  fridadev_repo_audit.md
  fridadev_refactor_todo.md
  fridadev_refactor_closure.md
  fridadev_conventions.md
  fridadev_memory_store_refactor_plan.md

  states/
    architecture/
    specs/
    operations/
    project/
    baselines/
    policies/
    legacy/

  todo-done/
    audits/
    validations/
    migrations/
    notes/

  todo-todo/
    admin/
    memory/
    product/
    migration/
```

Pourquoi conserver les docs canoniques a la racine:
- ces chemins sont deja references explicitement dans les routines de travail (`AGENTS.md`, prompts de pilotage, scripts de verification)
- les deplacer maintenant augmenterait le risque de casse de process sans gain immediate

## 4) Matrice fichier par fichier

Matrice de decision initiale (avant execution des lots de rangement/nettoyage):

| Chemin actuel | Qualification | Lecteur principal | Action proposee | Destination cible (si move/fusion) | Justification courte | Risque / reserve |
| --- | --- | --- | --- | --- | --- | --- |
| `app/docs/README.md` | canonique | tout contributeur | garder ici | n/a | point d'entree clair sur la logique `states/todo-done/todo-todo` | faible |
| `app/docs/admin-todo.md` | canonique | backend/admin maintainer | garder ici | n/a | feuille de route autoritative admin deja referencee | deplacement casserait des references de process |
| `app/docs/admin-implementation-spec.md` | canonique | backend/admin maintainer | garder ici | n/a | spec d'implementation active et reliee a `admin-todo.md` | faible |
| `app/docs/admin-runtime-settings-schema.md` | canonique | backend/admin maintainer | garder ici | n/a | schema de reference runtime settings | faible |
| `app/docs/admin-operations.md` | canonique | operateur/admin maintainer | garder ici | n/a | guide operationnel V1 du nouvel admin | faible |
| `app/docs/fridadev_repo_audit.md` | canonique | maintainer/reviewer | garder ici | n/a | source d'audit initiale citee partout | faible |
| `app/docs/fridadev_refactor_todo.md` | canonique | maintainer/reviewer | garder ici | n/a | pilotage actif des phases | faible |
| `app/docs/fridadev_refactor_closure.md` | canonique | maintainer/reviewer | garder ici | n/a | preuve de cloture croisee | faible |
| `app/docs/fridadev_conventions.md` | canonique | tous devs | garder ici | n/a | conventions minimales transverses | faible |
| `app/docs/fridadev_memory_store_refactor_plan.md` | historique utile | maintainer memory | garder ici | n/a | plan de refacto memory_store finalise et encore utile en reference | a requalifier en archive si plus consulte |
| `app/docs/states/Frida-State-french-23-03-26.md` | historique utile | maintainer produit/fr | deplacer | `app/docs/states/project/Frida-State-french-23-03-26.md` | snapshot de reference daté, utile mais a ranger comme etat projete | faible |
| `app/docs/states/Frida-State-english-23-03-26.md` | historique utile | maintainer produit/en | deplacer | `app/docs/states/project/Frida-State-english-23-03-26.md` | meme role que la version FR, audience differente | faible |
| `app/docs/states/Migration_FridaDev-baseline.md` | historique utile | maintainer migration | deplacer | `app/docs/states/baselines/Migration_FridaDev-baseline.md` | baseline pre-migration importante pour comparaison | faible |
| `app/docs/states/hermeneutic-judgment-spec.md` | canonique | maintainer memory/hermeneutics | deplacer | `app/docs/states/specs/hermeneutic-judgment-spec.md` | vraie spec normative, doit etre dans `specs/` | faible |
| `app/docs/states/phase0-baseline-report.md` | historique utile | maintainer memory/hermeneutics | deplacer | `app/docs/states/baselines/phase0-baseline-report.md` | rapport baseline technique date | faible |
| `app/docs/states/PROJET.md` | obsolete / legacy | operateur historique | deplacer | `app/docs/states/legacy/PROJET-frida-mini.md` | references runtime obsolete (`frida-mini`, anciens chemins) | risque de confusion si laisse dans zone active |
| `app/docs/states/sanity-frida-mini.md` | obsolete / legacy | maintainer historique | deplacer | `app/docs/states/legacy/sanity-frida-mini.md` | plan ancien centré `frida-mini`; utile comme trace, pas comme reference active | risque de faux pilotage si reste visible au meme niveau |
| `app/docs/todo-done/Frida-conv-store-hybrid-audit.md` | historique utile | maintainer backend | deplacer | `app/docs/todo-done/audits/Frida-conv-store-hybrid-audit.md` | audit termine, a classer par type | faible |
| `app/docs/todo-done/Frida-db-only-validation-report.md` | historique utile | maintainer backend/QA | deplacer | `app/docs/todo-done/validations/Frida-db-only-validation-report.md` | rapport de validation ferme, reference de preuve | faible |
| `app/docs/todo-done/Frida-memory-db-only-audit.md` | historique utile | maintainer backend | deplacer | `app/docs/todo-done/audits/Frida-memory-db-only-audit.md` | audit finalise a ranger avec les audits | faible |
| `app/docs/todo-done/Frida-minimal-validation.md` | historique utile | maintainer QA | deplacer | `app/docs/states/operations/Frida-minimal-validation.md` | guide operatoire plus qu'artefact "done" | verifier coherence avec script actuel |
| `app/docs/todo-done/Frida-data-policy.md` | canonique | maintainer data/backend | deplacer | `app/docs/states/policies/Frida-data-policy.md` | politique normative active, pas juste archive de chantier | faible |
| `app/docs/todo-done/Frida-conversations-retention-policy.md` | canonique | maintainer data/backend | deplacer | `app/docs/states/policies/Frida-conversations-retention-policy.md` | politique de retention active | faible |
| `app/docs/todo-done/Frida-traces-summaries-retention-policy.md` | canonique | maintainer data/memory | deplacer | `app/docs/states/policies/Frida-traces-summaries-retention-policy.md` | politique active traces/resumes | faible |
| `app/docs/todo-done/Frida-identities-governance-policy.md` | canonique | maintainer memory | deplacer | `app/docs/states/policies/Frida-identities-governance-policy.md` | gouvernance identitaire durable | faible |
| `app/docs/todo-done/patch_done.md` | doublon / faible valeur | maintainer historique | supprimer | n/a | log ponctuel ancien, contenu partiellement obsolete et redondant avec git history | risque faible (perte de contexte mineur seulement) |
| `app/docs/todo-todo/Frida-installation-config.md` | chantier ouvert | maintainer product/ops | deplacer | `app/docs/todo-todo/product/Frida-installation-config.md` | vrai chantier ouvert infra/config produit | faible |
| `app/docs/todo-todo/Migration_FridaDev-todo.md` | doublon / faible valeur | maintainer migration | fusionner | `app/docs/fridadev_refactor_todo.md` (open items) + archive `app/docs/todo-done/migrations/` | roadmap quasi closee, overlap fort avec pilotage refactor actuel | risque de perdre un reliquat ouvert si fusion baclee |
| `app/docs/todo-todo/hermeneutical-add-todo.md` | chantier ouvert | maintainer memory | deplacer | `app/docs/todo-todo/memory/hermeneutical-add-todo.md` | roadmap encore exploitable, a ranger par domaine | faible |
| `app/docs/todo-todo/memory-todo.md` | doublon / faible valeur | maintainer memory | fusionner | `app/docs/todo-todo/memory/hermeneutical-add-todo.md` (extraire seulement residuels utiles) | overlap massif + architecture obsolete dans le bas du doc | risque de perdre un detail residuel si extraction non rigoureuse |
| `app/docs/todo-todo/smart-todo.md` | obsolete / legacy | personne (historique) | supprimer | n/a | references directes `kiki-mini`, `Olive`, chemins legacy non cibles | risque faible (interet historique tres limite) |

## 5) Fichiers suspects / obsoletes majeurs (priorite revue humaine)

1. `app/docs/todo-todo/smart-todo.md`
- legacy explicite: `kiki-mini`, `Olive`, `/home/tof/apps/kiki-mini`, `frida-mini.service`
- statut propose: `obsolete / legacy` -> suppression

2. `app/docs/states/PROJET.md`
- presente `frida-mini` comme architecture active (chemins/ports/services obsoletes)
- statut propose: archive legacy (ou suppression apres validation externe)

3. `app/docs/states/sanity-frida-mini.md`
- plan cible `frida-mini` et chemins historiques; valeur surtout historique
- statut propose: archive legacy

4. `app/docs/todo-done/patch_done.md`
- trace ponctuelle ancienne (`Frida-Mini/*`) redondante avec l'historique Git
- statut propose: suppression

5. `app/docs/todo-todo/memory-todo.md`
- roadmap tres longue, partiellement obsolete et redondante avec `hermeneutical-add-todo.md`
- statut propose: fusion partielle puis suppression

## 6) Fichiers a conserver comme references fortes

- Pilotage canonique:
  - `app/docs/fridadev_repo_audit.md`
  - `app/docs/fridadev_refactor_todo.md`
  - `app/docs/fridadev_refactor_closure.md`
  - `app/docs/fridadev_conventions.md`
- Admin canonique:
  - `app/docs/admin-todo.md`
  - `app/docs/admin-implementation-spec.md`
  - `app/docs/admin-runtime-settings-schema.md`
  - `app/docs/admin-operations.md`
- Specs/baselines etats a conserver (apres rangement):
  - `app/docs/states/hermeneutic-judgment-spec.md`
  - `app/docs/states/Migration_FridaDev-baseline.md`
  - `app/docs/states/phase0-baseline-report.md`
  - `app/docs/states/Frida-State-french-23-03-26.md`
  - `app/docs/states/Frida-State-english-23-03-26.md`
- Politiques a reclasser en references durables:
  - `Frida-data-policy.md`
  - `Frida-conversations-retention-policy.md`
  - `Frida-traces-summaries-retention-policy.md`
  - `Frida-identities-governance-policy.md`

## 7) Strategie de migration proposee (4 petits lots)

### Lot 1 (faible risque) — Rangement structurel sans suppression [FAIT]
- Creer les sous-dossiers cibles dans `states/`, `todo-done/`, `todo-todo/`
- Deplacer les documents clairement classes (audits/validations/policies/specs/baselines)
- Mettre a jour `app/docs/README.md` avec la nouvelle arborescence
- Ne supprimer aucun fichier dans ce lot

### Lot 2 (risque controle) — Archivage legacy + suppression faible valeur, sans fusion [FAIT]
- Archiver les documents legacy evidents dans `states/legacy/`:
  - `PROJET.md`
  - `sanity-frida-mini.md`
- Supprimer les documents a tres faible valeur:
  - `todo-done/patch_done.md`
  - `todo-todo/smart-todo.md`
- Laisser volontairement en place pour lot ulterieur:
  - `todo-todo/Migration_FridaDev-todo.md`
  - `todo-todo/memory-todo.md`

### Lot 3 (risque moyen) — Consolidation des roadmaps ouvertes [FAIT]
- Fusionner les doublons de roadmap:
  - `Migration_FridaDev-todo.md` -> archive en `todo-done/migrations/` (aucun reliquat vivant transfere vers `fridadev_refactor_todo.md`)
  - `memory-todo.md` -> reliquats ouverts utiles fusionnes dans `todo-todo/memory/hermeneutical-add-todo.md`, puis archive en `todo-done/migrations/`
- Archiver les versions historiques utiles en `todo-done/migrations/`
- Verifier qu'aucun item ouvert n'est perdu

### Lot 4 (risque controle) — De-ignorisation `states` + hygiene finale [RESTE]
- Finaliser la politique de versionning de `app/docs/states/`:
  - retirer l'ignore global
  - ne garder que des ignores cibles pour artefacts generes/temporaires
- Revalidation documentaire (contre-audit externe) avant merge final

## 8) Reserves restantes

- Plusieurs chemins de docs canoniques sont appeles explicitement dans les routines de travail; les deplacer sans mise a jour coordonnee casserait les workflows.
- Les archives de migration conservent des checklists historiques; elles ne doivent plus etre traitees comme roadmap ouverte de pilotage.
- La suppression de l'ignore `app/docs/states/*` doit etre faite uniquement apres rangement effectif pour eviter de versionner du bruit brut.
