# Frida - Configuration d'installation

Objectif: definir ce qui doit etre configurable a l'installation pour rendre `Frida` publiable, sans garder des dependances cachees ou trop liees a l'infra actuelle.

## Etat apres tranche docs (2026-03-29)

Livre maintenant:
- guide operatoire d'installation/exploitation initiale publie:
  - `app/docs/states/operations/frida-installation-operations.md`

Reste ouvert dans ce TODO:
- conception d'une vraie surface produit/admin pour l'installation;
- scenarios de tests de connectivite orientee operateur (LLM, DB, embeddings, web/crawl);
- simplification UX d'installation pour reduire la charge manuelle sur clone neuf;
- decisions de perimetre entre bootstrap externe (`.env`) et configuration admin durable.

## 1. Ce qui sort du produit

- Meteo: retiree completement. Ce n'est pas une brique centrale pour un assistant de travail et de recherche.

## 2. Classification des briques conservees

- Recherche web (`SearXNG`): capacite configurable, mutualisee assumee ou dediee selon l'installation.
- Enrichissement web (`Crawl4AI`): capacite configurable et optionnelle, mutualisee assumee ou dediee selon l'installation.
- Embeddings / memoire semantique: capacite configurable, idealement dediee ou clairement mutualisee et documentee.
- Provider LLM (`OpenRouter` aujourd'hui): capacite configurable, externe assumee, remplacable par un autre provider compatible.
- Base de donnees (`PostgreSQL`): infrastructure d'installation, preferee dediee pour un produit publiable.

## 3. Principe produit

Tout ce qui est necessaire au fonctionnement de `Frida` doit etre range dans une configuration d'installation explicite.

Cette configuration ne doit pas supposer:

- un provider LLM impose,
- un moteur web impose,
- un endpoint embeddings impose,
- une base de donnees imposee,
- une infra locale particuliere deja presente.

## 4. Structure cible de la future page d'installation

### A. Informations generales

- Nom du produit: `Frida`
- Mode d'installation: developpement / production
- URL publique de l'application
- Fuseau horaire

### B. Provider LLM

- Type de provider
- URL d'API
- Cle API ou token (masque)
- Modele principal
- Modele d'arbitrage
- Modele de resume
- Timeout
- Bouton de test de connectivite

### C. Recherche web

- Recherche web active: oui/non
- Type de moteur
- URL du moteur
- Token ou header si necessaire
- Nombre de resultats
- Bouton de test

### D. Enrichissement / Crawl

- Crawl actif: oui/non
- URL du service
- Token
- Nombre maximum de pages ou resultats enrichis
- Taille maximale de contenu extrait
- Bouton de test

### E. Embeddings et memoire

- Memoire semantique active: oui/non
- URL du service d'embeddings
- Token
- Dimension attendue
- `top_k`
- Bouton de test

### F. Base de donnees

- Type de base
- DSN ou champs separes (host, port, base, user)
- Statut de connexion
- Verification des migrations
- Bouton de test

Note: cette partie releve plutot d'une configuration d'installation ou de maintenance que d'un reglage quotidien.

## 5. Regles de securite et d'ergonomie

- Les secrets doivent etre affiches masques.
- Chaque bloc doit indiquer s'il exige un redemarrage.
- Chaque bloc doit proposer un test de connexion.
- Les reglages critiques doivent etre valides avant sauvegarde finale.
- Les dependances optionnelles doivent pouvoir etre desactivees proprement.

## 6. Recommandation d'implementation

- Commencer par une page "Installation / Infrastructure" simple.
- Stocker la configuration dans un fichier ou une table dediee.
- Ne pas rendre tous les reglages modifiables a chaud.
- Distinguer:
  - reglages produit,
  - reglages provider,
  - reglages d'infrastructure.

## 7. Position retenue a ce stade

- Meteo: sortie du produit.
- Recherche web: gardee et configurable.
- Crawl4AI: garde et configurable.
- Embeddings: gardes et configurables.
- OpenRouter / provider LLM: garde et configurable.
- Base de donnees: configurable a l'installation, pas forcement en admin quotidien.
