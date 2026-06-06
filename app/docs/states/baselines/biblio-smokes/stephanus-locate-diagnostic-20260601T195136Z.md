# Diagnostic Stephanus Biblio - 2026-06-01T19:51:36Z

## Scope

Diagnostic content-free Lot 11 sur la capacite actuelle `CatalogueClient.locate`
pour une demande Stephanus avec plage.

Interdits respectes: aucun passage OCR, aucun payload Catalogue brut, aucun
prompt, aucun secret, aucun titre/auteur/requete utilisateur brut.

## Methode

- Recherche prealable par variantes du dialogue cible pour obtenir des
  documents candidats.
- Appels GET-only `locate` sur labels simples et chaines de plage.
- Sortie reduite aux ids courts, statuts, counts, presence de position et
  longueurs de labels.

## Resultats content-free

- Documents candidats courts: `d1f49f74`, `7d025103`, `dabfe4a7`.
- Sur `d1f49f74`:
  - label simple longueur 4: `200`, `best_present=true`, position presente;
  - deuxieme label simple longueur 4: `200`, `best_present=true`, position presente;
  - chaine de plage longueur 9: `CatalogueNotFound`;
  - autre label simple longueur 4: `200`, `best_present=true`, position presente;
  - autre chaine de plage longueur 9: `CatalogueNotFound`.
- Sur `7d025103`: labels simples et chaines de plage testes retournent
  `CatalogueNotFound`.
- Sur `dabfe4a7`:
  - un label simple longueur 4 retourne `200`, `best_present=true`, position
    presente;
  - les autres labels/plages testes retournent `CatalogueNotFound`.

## Diagnostic

- Le point Stephanus simple est exploitable via `locate` quand le document est
  le bon.
- La chaine de plage brute n'est pas un locator Catalogue resolu directement.
- Le comportement attendu a court terme est donc: chercher/resoudre le
  document, appeler `locate` sur le debut, appeler `locate` sur la fin si
  utile, puis borner par les outils existants sans inventer un passage exact.

## Suite

- Correction immediate: prompt bibliothecaire Lot 11 explicite sur texte
  primaire, references Stephanus et split debut/fin.
- Non corrige dans ce lot: extraction canonique complete de plage sans mapping
  dedie entre deux locators; cela demande un outil/index/mapping futur si les
  tests live le confirment.
