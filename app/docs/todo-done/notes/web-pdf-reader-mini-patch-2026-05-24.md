# Web PDF reader mini-patch - 2026-05-24

Statut: mini-patch livre, runtime web FridaDev.

## Finding valide

Crawl4AI `/md` ne lit pas correctement certaines URLs PDF directes, meme quand le PDF est accessible en HTTP et annonce `application/pdf`. Le cas observe etait une URL `presscorner` de la Commission europeenne: l'extraction directe par le lecteur PDF Python interne fonctionne, mais le pipeline web passait encore par Crawl4AI et pouvait finir en `page_not_read_snippet_fallback`.

## Patch

FridaDev intercepte maintenant les URLs web clairement PDF avant Crawl4AI:

- URL explicite PDF: lecture directe par `app/tools/web_pdf_reader.py`;
- resultat de recherche avec URL `.pdf`: lecture directe PDF pour les resultats dans le budget de lecture;
- HTML et autres pages: chemin Crawl4AI conserve.

Le reader PDF utilise l'extracteur interne `app/core/active_document_text_extraction.py`, donc le parsing reste aligne avec les documents actifs textuels.

## Bornes MVP

- telechargement en memoire seulement;
- pas de stockage durable;
- pas de cache applicatif;
- pas d'OCR;
- taille max explicite;
- pages max explicites;
- chars max injectes;
- timeout court;
- fallback actuel conserve en cas d'echec.

Si un PDF est scanne, non extractible, trop gros, trop long ou invalide, FridaDev ne pretend pas l'avoir lu: le chemin retombe sur le statut web existant, avec caveat via evidence/confiance.

## Observabilite

L'observabilite reste content-free:

- `web_pdf_read_summary`;
- `web_pdf_read_attempted_count`;
- `web_pdf_read_status_counts`;
- `web_pdf_read_reason_codes`;
- pages, bytes, chars, elapsed_ms;
- aucun texte PDF brut dans les logs ordinaires.

## Frontieres

Ce lot ne change pas Crawl4AI, SearXNG, Exa/OpenRouter, la plateforme Docker, les documents actifs, l'OCR Stirling, Biblio, RAG documentaire ni le stockage de fichiers.
