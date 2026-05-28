# Frida Catalogue - human metadata editing audit - 2026-05-28

Statut: audit cible lecture seule
Classement: `app/docs/states/audits/`
Chantier lie: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Discipline plateforme: lecture seule sous discipline Sauron

## 1. Question

Avant de brancher FridaDev sur Frida Catalogue, il faut verifier ou vit la surface Catalogue actuelle et si elle permet deja de corriger humainement les metadonnees bibliographiques.

Verdict: la stack Catalogue existe et repond, mais l'edition humaine des metadonnees n'existe pas encore. Elle doit devenir le Lot 0 prioritaire avant le client FridaDev read-only.

## 2. Surface humaine observee

- Homepage expose `FRIDA Catalogue` vers `https://home.frida-system.fr/bibliotheque`.
- Caddy route `/bibliotheque*` vers `doc-library:80`.
- Le front actuel est hors depot FridaDev: `/opt/platform/doc-library/index.html`.
- Cette page affiche une liste `FRIDA Bibliotheque`, des compteurs, une recherche, des liens `Fiche JSON` et `Page 1 JSON`.
- La page appelle `/doc-api/health` et `/doc-api/catalog?limit=500&offset=0&q=...`.
- La fiche ouvrage lisible reste minimale: titre, fichier source, langue, type, pages/sections, chapitres, paragraphes, score QA et TOC.
- Aucune page d'edition metadata n'a ete observee.

## 3. API observee

API: `/opt/platform/doc-pipeline/query_api.py`, FastAPI `FRIDA Doc Pipeline API`, conteneur `platform-doc-pipeline-api`.

Routes utiles observees:

- `GET /health`;
- `GET /catalog`;
- `GET /doc/{doc_id}`;
- `GET /doc/by-title/{title}`;
- `GET /doc/latest`;
- `GET /doc/{doc_id}/page/{page_no}`;
- `GET /doc/{doc_id}/page/{page_no}/para/{para_no}`;
- `GET /doc/{doc_id}/milestones`;
- `GET /doc/{doc_id}/locate`;
- `GET /doc/{doc_id}/context`;
- exports document / chapitre / chunk;
- `GET /search`.

Routes mutatrices observees:

- `PUT /settings`, uniquement pour les reglages OCR/modeles du pipeline;
- `POST /settings/reset`;
- `POST /progress/recent/clear`;
- `DELETE /doc/{doc_id}`;
- `DELETE /doc/{doc_id}/with-files`.

Aucune route `PATCH` ou `PUT` de metadonnees documentaires n'a ete trouvee.

## 4. DB / metadonnees

DB: conteneur `platform-doc-pipeline-db`.

Tables publiques observees:

| table | lignes approx. | taille |
| --- | ---: | ---: |
| `documents` | 10 | 80 kB |
| `document_chapters` | 973 | 424 kB |
| `milestones` | 26 492 | 8 128 kB |
| `pages` | 4 837 | 20 MB |
| `paragraphs` | 101 421 | 70 MB |
| `raw_units` | 378 034 | 215 MB |
| `schema_migrations` | 3 | 32 kB |

Colonnes metadata actuelles de `documents`:

- `id`;
- `title`;
- `source_filename`;
- `source_hash`;
- `created_at`;
- `language_detected`;
- `rules_version`;
- `page_count`;
- `paragraph_count`;
- `llm_json_quality_score`;
- `llm_json_format_valid`;
- `llm_json_safe_for_db`;
- `llm_json_issues`;
- `source_type`;
- `unit_label`;
- `unit_count`;
- `chapter_count`;
- `toc_source`;
- `language_detection`.

Colonnes absentes pour Lot 0:

- titre canonique separe du titre auto;
- titre original;
- auteur(s);
- traducteur(s) / editeur scientifique;
- editeur;
- collection;
- annee;
- type bibliographique;
- notes operateur;
- statut metadata;
- trace de correction humaine.

Aucune table `audit`, `history`, `revision`, `metadata` ou `edit` n'a ete trouvee. Comptage compact de qualite metadata: 10 documents, 1 titre `der`, 2 titres de longueur <= 4, 0 titre vide, 0 langue manquante.

## 5. Suppression DB / fichiers

La page `/bibliotheque` expose deux boutons:

- suppression de la base SQL;
- suppression de la base SQL et des fichiers `job_done`.

L'API supprime en base via `DELETE FROM documents` avec cascades sur les tables dependantes. La route `/doc/{doc_id}/with-files` supprime d'abord en base, puis tente de supprimer les artefacts derives dans le repertoire `job_done`.

Le Lot 0 doit durcir cette surface: confirmation forte, libelles non ambigus, garde contre clic accidentel et audit minimal. Aucune route DELETE n'a ete appelee pendant cet audit.

## 6. Frontiere FridaDev

Le front Catalogue actuel et l'API Catalogue ne vivent pas dans le depot FridaDev.

Etat FridaDev observe:

- pas de client Biblio natif;
- pas de route FridaDev Biblio;
- pas de lane prompt Biblio;
- pas de module FridaDev d'edition Catalogue;
- les documents actifs de conversation restent un module distinct, temporaire et conversation-scoped.

Conclusion de frontiere: le Lot 0 est probablement un lot plateforme Catalogue/doc-pipeline sous discipline Sauron. Le premier lot FridaDev apres Lot 0 doit rester read-only et GET-only.

## 7. Recommandation Lot 0

Ordre recommande:

1. Ajouter un modele SQL de metadonnees humaines, separe des metadonnees auto.
2. Ajouter une table d'audit minimale des corrections.
3. Ajouter une route d'edition metadata explicite, distincte des routes DELETE.
4. Ajouter une fiche ouvrage lisible et un formulaire d'edition.
5. Durcir les confirmations de suppression DB seule et DB + fichiers.
6. Prouver que l'edition metadata ne lance pas de re-OCR et ne branche pas Frida/LLM.

## 8. Preuves lecture seule

Preuves realisees sans secret, sans contenu OCR brut, sans dump d'ouvrage, sans DELETE et sans ecriture SQL:

- `docker ps` content-free sur les conteneurs doc/ocr/catalogue;
- lecture Caddy/Homepage des routes publiques;
- lecture de `/opt/platform/doc-library/index.html`;
- lecture des routes dans `/opt/platform/doc-pipeline/query_api.py`;
- lecture du schema `documents` via `information_schema`;
- comptages et tailles de tables via `pg_stat_user_tables`;
- appels GET content-free a `/health`, `/catalog?limit=2`, `/settings` et `/progress` depuis le conteneur FridaDev.
