# FridaDev - comprehension temporelle modele - TODO clos

Source cartographique large: `app/docs/states/audits/fridadev-temporal-system-audit-2026-05-18.md`

Statut: archive le 2026-05-18 apres cloture du Lot 4 par la matrice de preuves `app/tests/unit/core/test_temporal_model_truth_closure.py`.

## Objectif prioritaire

Ce chantier existe pour que Frida sache toujours correctement quel jour on est quand elle interprete et repond.

Il ne cherche pas a harmoniser toutes les dates visibles dans le produit. Il ne traite que:

- [x] ce que le modele principal lit;
- [x] ce que les modeles secondaires injectent ou influencent dans l'interpretation finale;
- [x] les classifieurs et fallbacks qui peuvent faire croire a Frida qu'un instant appartient au mauvais jour.

Doctrine active de ce TODO: pour la comprehension modele, la verite temporelle est la temporalite locale Frida; les choix timezone des surfaces navigateur ou operateur relevent d'un backlog separe.

## Hors scope pour ce chantier

Ces sujets restent cartographies dans l'audit global, mais ne gouvernent pas le chemin critique courant:

- [x] hero/date d'accueil du chat classe hors chemin critique modele;
- [x] sidebar conversations classee hors chemin critique modele;
- [x] export Markdown classe hors chemin critique modele;
- [x] nom fichier exporte classe hors chemin critique modele;
- [x] dashboard `today/yesterday` classe hors chemin critique modele;
- [x] dates et buckets dashboard web, dont `formatDateTime()` et `formatBucketLabel()`, classes hors chemin critique modele;
- [x] fenetre custom dashboard classee hors chemin critique modele;
- [x] toute autre surface purement UI, export ou operateur qui ne modifie pas la comprehension des modeles classee hors chemin critique modele.

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

- [x] **Lot 4 - Fermeture de la verite temporelle modele**
  - [x] Ajouter une matrice de preuves autour de minuit Europe/Paris.
  - [x] Ajouter une matrice DST Europe/Paris pour les lanes lisibles par un modele.
  - [x] Prouver qu'aucune lane pertinente pour la comprehension modele ne peut presenter a Frida deux jours contradictoires pour le meme instant.
  - [x] Relire l'audit global et requalifier les findings modele comme corriges ou stale avec preuves.
  - [x] Archiver ce TODO seulement quand la propriete modele est prouvee de bout en bout.

Preuves de cloture du Lot 4:

- [x] `test_midnight_matrix_all_model_lanes_share_frida_local_day`: `2026-05-17T22:05:00Z` reste `2026-05-18` / `lundi 18 mai 2026` dans le prompt principal, web, validation, arbitre, resumes et labels locaux.
- [x] `test_dst_matrix_spring_forward_and_fall_back_keep_same_model_day`: transitions Europe/Paris du 2026-03-29 et du 2026-10-25 sans glissement de jour ni Delta-T incoherent.
- [x] `test_validation_and_arbiter_keep_raw_utc_subordinate_to_local_labels`: timestamps UTC encore presents seulement comme technique, subordonnes aux labels locaux.
- [x] `test_identity_and_stimmung_cannot_create_temporal_day_claims`: identity rejette par provenance les sources temporelles faibles, stimmung les ignore contractuellement.
- [x] `test_deterministic_classifier_and_invalids_close_temporal_fallbacks`: `hier` / `depuis hier`, timestamp invalide et timezone invalide sont verrouilles.

## Condition de non-prolongation

- [x] Ne pas ajouter de lot UI, dashboard operateur, export, Biblio, provider ou refactor general dans ce TODO.
- [x] Ouvrir un autre chantier si la coherence temporelle produit hors modele redevient prioritaire.
