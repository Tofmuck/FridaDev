# Biblio Stephanus range diagnostic — 2026-06-02T06:28:19Z

Statut: baseline content-free
Classement: `app/docs/states/baselines/biblio-smokes/`

## Portee

Diagnostic content-free des probes directes Stephanus sur le Catalogue live,
sans affichage de passage, payload brut ni OCR.

## Probes resumees

### Recherche oeuvre

- requete non accentuee oeuvre seule: `result_count=0`;
- requete accentuee oeuvre seule: `result_count=10`;
- docs courts observes dans les premiers resultats accentues:
  - `d1f49f74`
  - `7d025103`
  - `dabfe4a7`

### Locate simple

Sur `d1f49f74`:

- `148e` -> `status=200`, position exploitable presente;
- `151d` -> `status=200`, position exploitable presente;
- `126b` -> `status=200`, position exploitable presente;
- `128a` -> `status=200`, position exploitable presente.

Sur `dabfe4a7`:

- `126b` -> `status=200`, position exploitable presente;
- `128a` -> `status=200`, position exploitable presente.

### Locate range brut

Sur les documents testes:

- `148e-151d` -> non trouve;
- `126b-128a` -> non trouve.

### Context depuis locate

Sur `d1f49f74`, `passage_context` repond `200` apres locate simple sur:

- `148e`
- `151d`
- `126b`
- `128a`

## Lecture technique

- les labels simples Stephanus sont bien indexes comme ancres ponctuelles;
- une plage brute n'est pas indexee comme label unique;
- `locate -> passage_context` fonctionne sur les ancres simples;
- la prise en charge generale d'une plage canonique demande autre chose qu'un
  simple guidage prompt.
