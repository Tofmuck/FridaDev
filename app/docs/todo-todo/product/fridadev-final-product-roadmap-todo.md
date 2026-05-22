# FridaDev - roadmap produit finale - TODO

Ce document fige la fin de la grande roadmap produit FridaDev.

Il ne lance pas cinq implementations maintenant. Il sert de boussole de fin de cycle: les gros chantiers produit restants sont limites aux cinq points ci-dessous. Il pourra encore y avoir des correctifs, des ajustements de comportement, du polish, des preuves operateur ou de petites ameliorations locales, mais aucun nouveau gros chantier produit ne doit etre ajoute par inertie avant decision explicite.

## Perimetre fige

Les cinq chantiers produit majeurs restants sont:

1. Atelier documentaire / repertoire de travail.
2. Recherche internet.
3. Biblio native / catalogue Tulu.
4. Text-to-speech.
5. Duplication FridaDev pour Amandine.

L'ordre peut etre ajuste par decision explicite, mais le perimetre produit majeur reste fige a ces cinq chantiers.

## Ordre provisoire recommande

1. Atelier documentaire / repertoire de travail.
2. Audit et fiabilisation de la recherche internet.
3. Preparation de la duplication Amandine.
4. Duplication effective Amandine.
5. Ensuite seulement: Biblio native Tulu ou Text-to-speech selon priorite.

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

Piste produit a garder pour Amandine:

- etudier un mode/connecteur Adobe Docs dedie, expose eventuellement comme bouton ou profil explicite `Adobe`, pour envoyer les requetes Photoshop/Illustrator directement vers les documentations officielles Adobe ou leurs APIs publiques si elles sont exploitables;
- ce point ne doit pas bloquer le renforcement web local en cours: il faudra l'auditer comme sous-chantier specialise, avec cout, API disponibles, conditions d'usage, fallback local et non-contamination.

## 3. Biblio native / catalogue Tulu

Objectif principal pour l'instance Tof: construire une Biblio native / catalogue Tulu comme fonds durable, classe, consultable.

Ce chantier est separe de l'atelier documentaire:

- l'atelier documentaire garde des pieces a portee de main pour le travail courant;
- la Biblio conserve un fonds durable et cataloguable;
- les documents actifs restent ce que Frida peut lire maintenant dans un tour donne.

Pour Amandine, le besoin est different: une bibliotheque existe deja cote stack Docker. Son chantier devrait donc plutot etre un branchement ou une integration de l'existant, pas la creation de la Biblio Tulu.

References deja ouvertes:

- `frida-biblio-native-catalogue-audit-plan.md`
- `frida-biblio-native-catalogue-todo.md`

## 4. Text-to-speech

Objectif: chantier de confort et de presence, pas dependance critique.

Sources a relire plus tard:

- implementation deja faite dans Freezer D4;
- plan Swift existant;
- modele, chunks et strategie deja prets cote Swift.

Note produit: ce chantier n'est pas indispensable pour Amandine. S'il est implemente, il peut rester disponible dans l'instance Tof et eventuellement devenir reutilisable ailleurs.

## 5. Duplication FridaDev pour Amandine

Objectif: creer une instance soeur plutot qu'un multi-utilisateur.

Principe:

- duplication applicative;
- nouvelle base de donnees separee;
- purge ou seed propre;
- nouveaux conteneurs;
- nouveau lien;
- projet OpenRouter separe;
- adaptation utilisateur/personnalisation;
- separation nette des donnees.

Besoin specialise a conserver pour Amandine:

- acces fiable aux documentations Adobe Photoshop / Illustrator, idealement via un mode ou connecteur explicite Adobe Docs plutot que par une recherche web generale fragile.

Responsabilites:

- Sauron: conteneurs, DB, hostname, Caddy/Authelia, secrets, reseau, backups, projet OpenRouter et runtime plateforme.
- Celebrimbor: code applicatif, seed/purge, identite utilisateur, settings, docs et differences produit eventuelles.

## Hors scope de ce TODO

Ce TODO global ne doit pas implementer les chantiers.

Il ne doit pas:

- creer les cinq TODO detailles maintenant;
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
