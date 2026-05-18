# FridaDev - comprehension temporelle modele - TODO

Source cartographique large: `app/docs/states/audits/fridadev-temporal-system-audit-2026-05-18.md`

## Objectif prioritaire

Ce chantier existe pour que Frida sache toujours correctement quel jour on est quand elle interprete et repond.

Il ne cherche pas a harmoniser toutes les dates visibles dans le produit. Il ne traite que:

- [ ] ce que le modele principal lit;
- [ ] ce que les modeles secondaires injectent ou influencent dans l'interpretation finale;
- [ ] les classifieurs et fallbacks qui peuvent faire croire a Frida qu'un instant appartient au mauvais jour.

Doctrine active de ce TODO: pour la comprehension modele, la verite temporelle est la temporalite locale Frida; les choix timezone des surfaces navigateur ou operateur relevent d'un backlog separe.

## Hors scope pour ce chantier

Ces sujets restent cartographies dans l'audit global, mais ne gouvernent pas le chemin critique courant:

- [ ] hero/date d'accueil du chat;
- [ ] sidebar conversations;
- [ ] export Markdown;
- [ ] nom fichier exporte;
- [ ] dashboard `today/yesterday`;
- [ ] dates et buckets dashboard web, dont `formatDateTime()` et `formatBucketLabel()`;
- [ ] fenetre custom dashboard;
- [ ] toute autre surface purement UI, export ou operateur qui ne modifie pas la comprehension des modeles.

## Lots actifs

- [x] **Lot 1 - Web local time**
  - [x] Corriger la contradiction directe entre la lane web et le prompt principal.
  - [x] Remplacer les dates UTC hote de `app/tools/web_search.py` par une date locale Frida issue du coeur temporel.
  - [x] Ne pas dependre de la locale systeme pour les mois/jours francais.
  - [x] Prouver qu'aucune reformulation web et aucun bloc web ne peut raconter un autre jour que `[RÉFÉRENCE TEMPORELLE]` autour de `2026-05-17T22:05:00Z`.

- [x] **Lot 2 - Modeles secondaires qui influencent l'interpretation**
  - [x] Validation agent: fournir `NOW/TIMEZONE` au bon niveau de priorite ou des labels locaux suffisants dans le contexte qu'il lit d'abord.
  - [x] Arbitre memoire: fournir recent context et candidats avec ancre locale suffisante, ou une politique explicite d'ignorance des claims temporels faibles.
  - [x] Identity extractor: soit fournir une ancre temporelle, soit rejeter explicitement les claims relatifs faibles (`hier`, `aujourd'hui`, `en ce moment`) comme non durables.
  - [x] Identity periodic: statuer sur son influence reelle; si elle peut consolider un claim temporel relatif, appliquer la meme regle d'ancrage ou de rejet.
  - [x] Stimmung: statuer sur son influence reelle; si les gaps temporels influencent le signal, fournir labels locaux, sinon documenter et tester l'ignorance volontaire.
  - [x] Couvrir chaque caller par un test ou une preuve montrant qu'il ne peut pas introduire un jour contradictoire dans l'interpretation finale.

- [x] **Lot 3 - Qualification deterministe et fallbacks**
  - [x] Reconnaitre `hier` et `depuis hier` dans la qualification temporelle du tour.
  - [x] Empecher un timestamp invalide de devenir silencieusement `now` dans une surface qui nourrit la comprehension de Frida.
  - [x] Rendre le fallback timezone invalide observable, pour qu'il ne recree pas silencieusement une verite UTC contradictoire.
  - [x] Tester les cas `hier`, `depuis hier`, timestamp invalide et timezone invalide.

- [ ] **Lot 4 - Fermeture de la verite temporelle modele**
  - [ ] Ajouter une matrice de preuves autour de minuit Europe/Paris.
  - [ ] Ajouter une matrice DST Europe/Paris pour les lanes lisibles par un modele.
  - [ ] Prouver qu'aucune lane pertinente pour la comprehension modele ne peut presenter a Frida deux jours contradictoires pour le meme instant.
  - [ ] Relire l'audit global et requalifier les findings modele comme corriges ou stale avec preuves.
  - [ ] Archiver ce TODO seulement quand la propriete modele est prouvee de bout en bout.

## Condition de non-prolongation

- [ ] Ne pas ajouter de lot UI, dashboard operateur, export, Biblio, provider ou refactor general dans ce TODO.
- [ ] Ouvrir un autre chantier si la coherence temporelle produit hors modele redevient prioritaire.
