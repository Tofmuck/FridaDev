# Frida Biblio role signal proof

Date: 2026-06-02
Statut: baseline de preuve rejouable
Classement: `app/docs/states/baselines/`
Portee: remplace la preuve ad hoc basee sur un helper temporaire copie dans
`/tmp` pour le cran Lot E `document_role_signal`.

## 1. But

Prouver, dans le conteneur qui charge effectivement `db_store.py`, que le
signal faible `document_role_signal`:

- reconnait les formes accentuees utiles;
- reste negatif seulement;
- n'emet rien sur les titres neutres.

Cette preuve ne pretend pas valider tout `doc-pipeline`. Elle ne prouve que le
comportement cible du helper de signal.

## 2. Commande canonique rejouable

```bash
docker exec -w /app platform-doc-pipeline-api python -c "import json,db_store; cases=['Preface','Préface','Introduction','Commentary on Plato','Ion','Chapitre 1','Texte']; values={case: db_store._title_role_signal(case, allow_body=True) for case in cases}; expected={'Preface':'introduction','Préface':'introduction','Introduction':'introduction','Commentary on Plato':'commentary','Ion':'','Chapitre 1':'','Texte':''}; assert values==expected, values; print(json.dumps(values, ensure_ascii=False, sort_keys=True))"
```

## 3. Sortie attendue

```json
{"Chapitre 1": "", "Commentary on Plato": "commentary", "Introduction": "introduction", "Ion": "", "Preface": "introduction", "Préface": "introduction", "Texte": ""}
```

## 4. Notes

- cette commande est rejouable telle quelle dans le conteneur live;
- elle ne depend ni d'un import `tests.*`, ni d'un fichier copie sous `/tmp`;
- l'absence de signal (`""`) ne vaut jamais preuve positive de texte primaire.

## 5. Test Sauron rejouable

Pour rejouer le test `doc-pipeline` lui-meme dans le bon contexte:

```bash
docker exec -w /app platform-doc-pipeline-api python tests/test_biblio_role_signal.py -v
```

Cette commande est canonique pour ce micro-lot:

- elle s'execute dans le conteneur qui embarque `psycopg` et le code live;
- elle n'utilise ni import `tests.*`, ni chemin implicite faux;
- elle ne pretend pas rendre le host Python nu equivalent a l'image runtime.
