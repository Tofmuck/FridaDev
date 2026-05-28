# FridaDev - roadmap produit finale - TODO

Ce document fige la fin de la grande roadmap produit FridaDev.

Mise a jour 2026-05-28: la duplication Amandine est annulee par decision
produit et retiree de cette boussole active. Les paniers Adobe, installation,
externalisation et jobs divers sont archives dans `app/docs/todo-done/product/`.

Il ne lance pas plusieurs implementations maintenant. Il sert de boussole de fin de cycle: les gros chantiers produit restants sont limites aux points ci-dessous. Il pourra encore y avoir des correctifs, des ajustements de comportement, du polish, des preuves operateur ou de petites ameliorations locales, mais aucun nouveau gros chantier produit ne doit etre ajoute par inertie avant decision explicite.

## Perimetre fige

Les chantiers produit majeurs suivis par cette boussole sont:

1. Atelier documentaire / repertoire de travail, livre et archive.
2. Recherche internet, livree avec archives et policy active.
3. Biblio native / catalogue Tulu.
4. Text-to-speech.

Les vrais chantiers encore ouverts depuis cette boussole sont Biblio native et,
si la priorite est confirmee, Text-to-speech.

## Ancien chantier transversal archive

Le panier transversal court est archive:

- `app/docs/todo-done/product/job-divers-todo.md`

Portee: jobs produit courts hors perimetre majeur, avec historique livre du reglage avance borne du reasoning GPT-5.1, du streaming visuel, de la dictee Whisper longue sous surveillance et des petits ajustements UI bornes.

Garde-fou conserve comme historique: un nouveau panier futur ne devra jamais rendre visible, streamer, stocker, persister, exporter ou injecter le raisonnement interne du modele (`reasoning_details` ou equivalent). Les nouveaux jobs devront rester petits, explicites et ne pas elargir la liste des gros chantiers produit.

## Ordre provisoire recommande

1. Atelier documentaire / repertoire de travail.
2. Audit et fiabilisation de la recherche internet.
3. Biblio native Tulu.
4. Text-to-speech selon priorite explicite.

## 1. Atelier documentaire / repertoire de travail

Objectif: creer un espace de travail documentaire ou l'utilisateur garde des fichiers a portee de main, puis choisit ce qui est active ou desactive dans la conversation.

Formule source:

- Documents actifs = ce que Frida peut lire maintenant.
- Atelier documentaire = ce que l'utilisateur garde a portee de main.
- Biblio = ce qui est conserve durablement comme fonds/catalogue.

Distinctions obligatoires:

- ce n'est pas de la memoire;
- ce n'est pas la Biblio;
- ce n'est pas l'historique conversationnel;
- ce n'est pas un RAG automatique.

Le geste produit vise un repertoire de travail lisible: fichiers disponibles, selection explicite, activation/desactivation claire, et aucune contamination automatique de Memory, Identity, Summary, Biblio ou historique conversationnel.

## 2. Recherche internet

Objectif: auditer puis fiabiliser la recherche internet existante.

Le chantier doit d'abord comprendre le contrat actuel:

- declenchement;
- cout;
- logs;
- injection dans le tour;
- non-contamination;
- comportement attendu en cas d'echec ou d'incertitude.

Le but n'est pas de refondre par principe. Si l'existant est correct, le bon resultat peut etre une clarification, quelques garde-fous, de meilleures preuves et une observabilite plus lisible.

Reference d'audit ouverte pour ce chantier:

- `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`

Archive de renforcement local SearXNG/Crawl4AI V0, avec bras benchmark `local_profiled`:

- `app/docs/todo-done/product/fridadev-local-web-search-hardening-todo.md`

Archive source-of-truth du chantier de reconstruction web discovery local-first + Exa de A a Z, avec OpenRouter/Exa comme provider de decouverte URL configure et sans fallback automatique:

- `app/docs/todo-done/product/fridadev-local-web-search-rebuild-todo.md`
- Decision produit associee: `app/docs/states/policies/fridadev-web-search-openrouter-exa-decision-2026-05-22.md`

Note Adobe: le mode Photoshop / Illustrator existe et son TODO est archive dans
`app/docs/todo-done/product/Adobe to do.md`. Il ne constitue plus une condition
active de cette roadmap.

## 3. Biblio native / catalogue Tulu

Objectif principal pour l'instance Tof: construire une Biblio native / catalogue Tulu comme fonds durable, classe, consultable.

Ce chantier est separe de l'atelier documentaire:

- l'atelier documentaire garde des pieces a portee de main pour le travail courant;
- la Biblio conserve un fonds durable et cataloguable;
- les documents actifs restent ce que Frida peut lire maintenant dans un tour donne.

References deja ouvertes:

- `frida-biblio-native-catalogue-audit-plan.md`
- `frida-biblio-native-catalogue-todo.md`

## 4. Text-to-speech

Objectif: chantier de confort et de presence, pas dependance critique.

Sources a relire plus tard:

- implementation deja faite dans Freezer D4;
- plan Swift existant;
- modele, chunks et strategie deja prets cote Swift.

Note produit: si ce chantier est implemente, il peut rester disponible dans l'instance Tof et eventuellement devenir reutilisable ailleurs.

## Hors scope de ce TODO

Ce TODO global ne doit pas implementer les chantiers.

Il ne doit pas:

- creer les TODO detailles maintenant;
- modifier le runtime;
- modifier la DB;
- modifier les prompts;
- modifier le frontend;
- modifier Docker;
- appeler OpenRouter;
- changer les settings live.

## Regle de fin de cycle

Tout nouveau gros chantier produit propose apres ce document doit etre traite comme une decision explicite de reouverture ou d'extension de cycle.

Le risque principal n'est pas de manquer une idee; c'est de laisser la roadmap regonfler par inertie. Ce fichier sert a garder le cap: finir les derniers chantiers choisis, puis stabiliser.
