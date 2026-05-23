# FridaDev Adobe Docs Mode - Evaluation metier Amandine 2026-05-23

Statut: evaluation metier Lot 8
Date: 2026-05-23
TODO source: `app/docs/todo-todo/product/Adobe to do.md`
Spec source: `app/docs/states/specs/fridadev-adobe-docs-mode-contract.md`

## Verdict

Le Lot 8 est valide cote evaluation automatisee: un jeu de tests metier synthetiques couvre Photoshop, Illustrator, release notes, known issues, cas piege, comparaison Adobe actif/inactif et exports content-free.

Cette evaluation ne remplace pas une validation Amandine en atelier. Elle prouve que le mini-pipeline sait chercher une preuve sourcee dans des contenus de forme HelpX quand elle existe, et qu'il signale l'insuffisance de preuve sur une fonctionnalite inventee.

## Meilleur plan retenu

Le plan le plus sur n'etait pas un crawl live large. Le Lot 7 a deja prouve le flux live Crawl4AI et UI.

Le Lot 8 utilise donc:

- des fixtures synthetiques courtes;
- aucun contenu Adobe reel versionne;
- des tests sur source type, evidence et metadata plutot que sur une reponse LLM flatteuse;
- une note explicite des limites avant validation humaine.

## Findings valides

- Les alias metier FR/EN existants etaient trop courts pour certains cas Amandine: `logo vectoriel redimensionnable`, `disque de travail sature`, `detourage`, import/export, impression et suppression.
- L'evaluation devait verifier les sources consultees et l'evidence, sinon le modele pouvait reussir par connaissance generale.
- Les questions version et bug doivent etre liees respectivement a `release_notes` et `known_issues`.
- Les cas pieges doivent produire une preuve insuffisante, pas une confirmation plausible.

## Patch applique

- Ajout de `app/tests/unit/tools/test_adobe_docs_business_eval.py`.
- Extension bornee des alias FR/EN dans `app/tools/adobe_docs_passages.py`.
- Mise a jour du contrat Lot 8 dans la spec.
- Mise a jour de la TODO Adobe.

## Couverture Photoshop

Cas automatises:

- detourage / cheveux / masque de calque -> passage `Layer masks`, source `help_page`;
- calques -> passage `Layers`, source `help_page`;
- Remove Tool / version -> passage `Release notes`, source `release_notes`;
- disque de travail sature -> passage `Scratch disks`, source `help_page`;
- export image web -> passage `Export`, source `help_page`.

Resultat: OK avec fixtures synthetiques.

## Couverture Illustrator

Cas automatises:

- outil plume -> passage `Pen tool`, source `help_page`;
- traces -> passage `Paths`, source `help_page`;
- logo vectoriel redimensionnable -> passage `Vector artwork`, source `help_page`;
- import PSD Photoshop -> passage `Import Photoshop files`, source `help_page`;
- PDF print / impression -> passage `Adobe PDF options`, source `help_page`.

Resultat: OK avec fixtures synthetiques.

## Release notes / known issues

Cas automatises:

- question version/nouveaute -> source `release_notes`;
- question bug/crash connu -> source `known_issues`.

Resultat: OK avec fixtures synthetiques.

## Cas piege / preuve insuffisante

Cas automatise:

- fonctionnalite inventee `outil officiel Licorne vectorielle dans Photoshop 2030` -> evidence `insufficient`, aucun passage selectionne.

Resultat: OK.

## Adobe actif vs inactif

Cas automatise:

- contexte Adobe inactif -> aucun passage, aucune source;
- contexte Adobe Photoshop actif -> lecture synthetique des seeds, suivi borne d'un lien HelpX enfant, selection d'au moins un passage source.

Resultat: OK.

## Privacy / non-stockage

Verifications automatisees:

- les fixtures sont synthetiques;
- `repr()` et `as_content_free_dict()` ne contiennent pas le texte source synthetique;
- aucun markdown Adobe reel n'est ajoute aux tests ou a cette note;
- aucun index, cache documentaire, Biblio, Memory, Identity, Summary ou Active Documents Adobe n'est cree.

## Limites restantes

- Les tests n'evaluent pas la qualite finale d'une reponse LLM redigee.
- Les tests n'evaluent pas l'exhaustivite HelpX.
- Les tests ne garantissent pas les libelles exacts de menus en interface francaise.
- Amandine doit encore valider au moins un cas Photoshop reel et un cas Illustrator reel.
- Une validation live metier bornee pourra etre utile, mais elle doit rester content-free cote logs et ne pas stocker de passages Adobe bruts.

## Commandes / preuves

- `python3 -m py_compile app/tools/adobe_docs_pipeline.py app/core/adobe_docs_prompt_lane.py app/tools/adobe_docs_passages.py`: OK.
- `python3 -m unittest app.tests.unit.tools.test_adobe_docs_sources app.tests.unit.tools.test_adobe_docs_reader app.tests.unit.tools.test_adobe_docs_links app.tests.unit.tools.test_adobe_docs_passages app.tests.unit.tools.test_adobe_docs_pipeline app.tests.unit.tools.test_adobe_docs_business_eval`: OK, 63 tests.
- `python3 -m unittest app.tests.unit.chat.test_adobe_docs_prompt_lane`: OK, 3 tests.
- `python3 -m unittest discover -s app/tests/integration/frontend_chat -p "test_*.py"`: OK, 23 tests.
- Conteneur runtime avec source bind-mount, tests Adobe tools + prompt lane: OK, 66 tests.
- Les preuves finales de commit/rebuild sont dans le retour operatoire du Lot 8.
