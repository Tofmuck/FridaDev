# OBS-M7-UI-01 — Correctif du harnais de navigation M7

9 octobre 2026, Celebrimbor. Autorité : mandat correctif explicite de Tof,
tests/preuves/documentation seulement. Branche inchangée
`FridaV1-Document-Workshop-M8-C`, racine confirmée `/opt/platform/fridadev`,
sans SSH. Base exacte `be9e3a8a0bdbc246659ccde4f286a2a91e2cbab3`, parent
`360521bdcd041a9aec9860d058fc9d2b153ed475`. État initial : HEAD = upstream =
distant, divergence 0/0, worktree propre. Toutes les références locales et
distantes ont été capturées avant édition, pas seulement M0–M7/main.

[Relevé reproductible du correctif](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-fix-20261009.json)
et [traces techniques JSONL gzip](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-fix-20261009.trace.jsonl.gz).
Le [diagnostic antérieur](frida-v1-document-workshop-obs-m7-ui-01-20261009.md),
son relevé, ses programmes et ses résultats restent inchangés.

## PLAN

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d’effets de
bord ? » Le changement minimal est local au `choose` M7 : retirer son clic
supplémentaire, attendre la fermeture native sur téléphone et conserver le
helper partagé de fermeture explicite. Aucun changement du produit, du CSS,
des handlers, des fixtures HTTP/SQL/DAV, de configuration/migration ou de lease.

1. Capturer état Git, empreintes, références, versions et runtime opérateur.
2. Rejouer les treize natifs intacts et le rouge causal avant édition.
3. Modifier uniquement la navigation M7 et éprouver deux ordres, les gestes
   suivants et les contrôles négatifs dans des copies possédées.
4. Conserver une reproduction isolée des anciens programmes sur leur base.
5. Rejouer M7 natif, M6 natif et M6 simulé ; terminer par les mêmes 1 691
   identités et les 70 + 26 voisins distincts de la référence prescrite.
6. Auto-audit, contre-lecture indépendante, nettoyage vérifié et contrôles
   précommit bloquants ; commit/push autorisés puis arrêt pour Codex.

## FINDING

**Défaut d’attente du harnais corrigé ; comportement produit inchangé.** Le
listener natif appelle `selectThread`, qui attend `loadThread`, redessine la
liste puis ferme le menu. L’ancien `choose` appelait aussi `closeSidebar` :
`isVisible()` ne garantissait pas que le bouton resterait dans le viewport.
Le rouge contrôlé montre la fermeture légitime par `selectThread`, la fin de
transition réelle, puis le timeout du second clic. Aucun défaut produit,
lien renderer/SQL ou cause d’environnement du défaut M7 n’est établi.

L’ordre exact des deux incidents du 7 octobre reste inconnu. Les extraits
anciens et les contre-audits Codex sont des éléments **transmis par Tof**,
sans accès revendiqué à leurs logs bruts. Dans le mandat courant, Codex a
communiqué `before-close` 2/2 en 27,554 s et deux timeouts causaux
`after-transition` en 40,920 s, avec filtre de cible exercé. La tentative
historique `minimal-target` demeure non concluante, ses erreurs précédant
l’armement. La baseline 13/13 du diagnostic antérieur était celle de
Celebrimbor, pas un nouveau rejeu intégral revendiqué par Codex.

Avant édition dans ce correctif : baseline native 13/13 ; sonde historique
`after-transition` rouge dans les deux cas, **dark causal atteint, light
échoué au choix initial avant armement**. Ce dernier rouge est conservé et
ne compte pas comme preuve de la barrière. Aucun rejeu jusqu’au vert.

## PATCH

`test_frontend_browser_document_http_m7.js` supprime l’import inutilisé et
l’appel redondant du helper partagé dans `choose`, puis ajoute un petit helper
local `waitForNativeSelection` :

- ligne active portant l’ID exact de la conversation demandée ;
- distinction téléphone/bureau par `data-presentation-context`, autorité
  existante du contrôleur de présentation, sans branche sur le thème ;
- téléphone : `.sidebar` sans `.open`, `aria-hidden=true`, menu
  `aria-expanded=false`, backdrop sans `.show` et effectivement `display:none` ;
- aucune transition `transform` directe du menu en cours ou pending, rectangle
  du menu entièrement sorti à gauche (`right <= 0`).

L’état réel est échantillonné avec le timeout historique de 10 000 ms, sans
attente temporelle arbitraire ni dépendance à un `transitionend` futur. Une fin
déjà passée est reconnue. La marque active seule ne démontre pas `loadThread` :
sur téléphone, la fermeture native complète après sa lecture reste nécessaire.
Le bureau garde sa sidebar visible et `aria-hidden=false`. Le helper partagé
et tous ses consommateurs hors de ce chemin sont conservés.

Les helpers métier et tous les corps de tests après `choose` sont identiques
à la base. Identités, deux révisions, ETag, inventaire, reçus, réhydratation,
provenance, budgets, isolation des facultés et absence de replay restent
assertés. Les doubles confirmations DOM historiques sont conservées ; aucun
nouveau clic de confirmation n’est ajouté par la sonde.

Deux programmes autonomes nouveaux : `probe_obs_m7_ui_01_fix.js` et
`run_obs_m7_ui_01_fix.py`. Les copies de preuve conservent les quatre cas M7
stables et leurs assertions, avec des noms distincts. Neuf autres cas M7 sont
exclus explicitement ; pour les contrôles téléphone, les deux bureaux le sont
aussi. Chaque copie exacte, son diff et les programmes exécutés sont archivés.
Les fichiers historiques de diagnostic ne sont pas adaptés silencieusement.

## TEST

Toutes les commandes, sélecteurs, identités, exits, durées, versions effectives,
empreintes et premières traces sont conservés dans le relevé. Les ciblés, les
mutants et la comparaison complète sont séparés. Zéro skip/annulation dans
les groupes de cas exécutés ; les incidents de setup ne sont pas des cas M7.

Hôte des runners : Python 3.13.5, Git 2.47.3, x86_64.
Versions conteneurisées effectives : Docker 26.1.5+dfsg1 ; Python 3.11.15, Flask 3.0.3,
psycopg 3.3.4 et Requests 2.32.3 ; Node 22.17.0, Playwright 1.59.1 et Chromium
147.0.7727.15 ; PostgreSQL 16.12 et pgvector/PostgreSQL 17.9. Le tag de l'image
navigateur reste `v1.54.0-jammy` ; il ne décrit pas la version effective du
package monté depuis le checkout. Digests et commandes de mesure dans le relevé.

| Essai | Résultat | Exit | Durée |
| --- | --- | --- | --- |
| Baseline avant édition | 13/13 | 0 | 259.473 s |
| Ancien ciblé avant édition | 2 rouges : dark causal, light non armé | 1 | 31.293 s |
| Corrigé : vrai GET en cours | 2/2 téléphone | 0 | 31.013 s |
| Corrigé : état déjà observable | 4/4 téléphone/bureau | 0 | 71.613 s |
| Mutant sans attente | 2 rouges attendus, barrière atteinte | 1 | 26.234 s |
| Mutant ancien clic | 2 timeouts attendus, barrière atteinte | 1 | 41.876 s |
| Archive historique 1 | 0 cas M7 ; échec de chargement du fichier | 1 | 0.278 s |
| Archive historique 2 | 0 cas M7 ; échec de montage Docker | 125 | 0.189 s |
| Archive historique 3 | 2 timeouts causaux attendus | 1 | 40.934 s |
| Voisin ciblé m7-native-http | 13/13 | 0 | 263.958 s |
| Voisin ciblé browser-native-http | 5/5 | 0 | 27.318 s |
| Voisin ciblé browser-simulated | 10/10 | 0 | 11.511 s |
| Comparaison historique complète | 1 691/1 691, identités exactes | 0 | 828.573 s (somme) |
| Voisins distincts neighbors70 | 70/70 | 0 | 0.661 s |
| Voisins distincts exports-readers26 | 26/26 | 0 | 0.559 s |

Durées des commandes navigateur/tests, hors setup et nettoyage ; la comparaison
indique la somme de ses 18 sélections. Horodatages UTC et commandes de chaque
sous-processus, y compris setup/nettoyage, dans le relevé. Ces groupes ne sont
pas cumulés pour annoncer un nouveau total historique.

Sélecteurs étudiés : `[data-conversation-id="<ID synthétique>"]`,
`#threads li.active`, `.sidebar`, `#sidebarBackdrop`, `#btnMenu` et
`#btnSidebarClose`. La sélection reste un clic natif Playwright ; seul le
GET synthétique ciblé est retenu, sans endpoint opérateur.

### Deux ordres et gestes natifs

`completed` retarde seulement l’observation du helper corrigé au troisième
choose jusqu’à la fermeture réelle déjà achevée. Le marqueur
`closed-before-wait` précède l’appel du vrai helper ; `wait-enter` désigne
l’entrée du wrapper de preuve, avant cette barrière d’ordonnancement.
Les deux téléphones observent le bouton à X −78 px pour 44 px de largeur,
puis terminent le parcours. Le helper n’attend pas un nouvel événement de fin.
Les deux bureaux terminent leurs assertions historiques ; l’assertion ARIA
est exécutée dans le parcours, et le collecteur vérifie ensuite les mesures
sauvegardées : contexte desktop, viewport 1280×900, géométrie visible de la
sidebar (X 0, bord droit 272). Le téléphone garde 390×844, isMobile/hasTouch,
les deux thèmes et le timeout exact de la suite.

`pending` retient uniquement le vrai GET `workspace-file-selections` de la
sélection étudiée. L’attente réelle est démarrée, puis deux frames du navigateur
permettent de vérifier qu’elle n’a pas abouti. La requête est libérée par
l’ordonnanceur **indépendamment de tout clic de fermeture**, avec
`route.continue()`, sans réponse ni handler substitués. Les étapes exigées sont
GET retenu → attente encore pendante → libération indépendante → continuation
→ réponse réelle 200 → attente terminée. Le menu reste ouvert pendant la lecture.

Après ces contrôles téléphone, un vrai clic `#btnMenu` rouvre le menu, puis le
helper partagé utilise le vrai `#btnSidebarClose` ; son événement trusted est
vérifié. Le parcours d’origine reprend ensuite reload, réhydratation et lanes.
Les snapshots avant/après cette navigation et ce geste explicite sont égaux
pour confirmations, actions, reçus, rendus, fichiers et mutations DAV.
Les assertions historiques après reload vérifient également l’absence de PUT
supplémentaire. Aucun champ/body/header HTTP ni contenu personnel n’est capturé.

### Négatifs causaux et effet de l’observateur

`no-wait` supprime l’attente seulement dans la copie possédée au point armé.
Les deux cas atteignent le vrai GET retenu, puis l’assertion
`selection-wait-returned-before-real-GET-release` échoue. Le GET est néanmoins
libéré dans `finally`. Une absence d’attente ne peut donc produire le vert.

`old-click` réintroduit l’ancien helper de fermeture au même point, après fin
réelle de transition. Les navigations précédentes gardent l’attente corrigée,
pour ne pas échouer avant la barrière. Les deux cas atteignent
`closed-before-wait → old-click-call`, puis le clic natif expire exactement
après 10 000 ms. La stack native attribue la fermeture à `selectThread`.
Aucun mutant n’est livré dans le produit ou dans le test M7 normal.

Les branches après un rouge ne sont pas validées : dans les négatifs, reload,
réhydratation et lanes tardives restent non atteints. Les positifs et le groupe
M7 normal les atteignent. Les listeners/wrappers et mesures de la sonde peuvent
modifier le timing ; `completed` fournit volontairement l’ordre après fermeture.
Le négatif `no-wait` refuse une attente prématurée avec le GET retenu ; le groupe
normal complet n’utilise aucune instrumentation de la sonde. Aucune fréquence
spontanée de course n’est mesurée.

### Reproduction de la base ancienne et incidents

Les anciens programmes dépendent de l’ancien texte de M7. Les lancer directement
sur HEAD corrigé ne reproduit plus leur base : une barrière attendant le clic
supprimé peut ne jamais être atteinte. Le nouveau mode `historical` crée une
archive Git de `app/` au commit exact `be9e3a8a…`, sans checkout ni branche
supplémentaire. Flask **et** navigateur montent cette archive en lecture seule.
Le cache `node_modules` existant est monté séparément en lecture seule ; aucune
installation ni copie de dépendance. Les empreintes de toutes les sources
archivées sont comparées à la capture initiale.

La revue a signalé un bind Flask encore dirigé vers le checkout courant ; il
a été corrigé avant le premier essai d’archive. Essai archive 1 : échec de
chargement Playwright, zéro cas M7 ; essai archive 2 : échec Docker 125, cible
du bind absent sous le montage read-only. Ces traces sont conservées. La
construction finale crée ce répertoire vide dans la seule archive possédée.
L’essai archive 3 atteint les deux barrières et retrouve les deux timeouts
causaux, avec les bons binds enregistrés et aucun changement des sources.

Autres incidents auxiliaires conservés : découverte AGENTS initialement trop
large, permissions refusées hors dépôt, puis recherche limitée au dépôt ;
inspection de version utilisant d’abord un tag vector `pg16` absent, corrigé
vers le `pg17` de la référence sans téléchargement ; premier relevé de version
vector sans son répertoire binaire dans PATH. Pour ce dernier, l’assertion
précédait la persistance du stderr : exit du driver 1 observé, exit du sous-
processus/durée/stderr non conservés, aucune prétention de preuve. La commande
corrigée conserve sa sortie avant assertion. Le premier collecteur final a bloqué (exit 1) sur le nom M4 contenant `#` :
TAP le publie avec `\#`, alors que l’inventaire source garde `#`. Les noms TAP
exécutés étaient identiques aux noms TAP de référence. Programme fautif, sortie
et métadonnées sont conservés ; le collecteur décode seulement cet échappement
pour la correspondance aux IDs source inchangés, et conserve la comparaison
exacte des noms TAP bruts. Toute la validation est rejouée après correction,
sans rejeu de tests. Aucun incident de validation n’autorise un commit.

### Commandes reproductibles et comparaison

Depuis la racine applicative, avec de nouvelles racines possédées, commandes
séquencées et images/caches existants aux empreintes du relevé :

```bash
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay probe completed
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay probe pending
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay probe no-wait
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay probe old-click
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-archive-replay historical after-transition
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay neighbors
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay compare
```

Les deux négatifs et le rejeu historique attendent exit 1 **avec barrières
atteintes et erreur exacte** ; un setup ou un rouge antérieur ne compte pas.
`collect_fix.py`, conservé dans `proof_programs`, vérifie les étapes, inventaires,
hashes et limites avant de produire le relevé. Les trois groupes `neighbors`
restent 13 M7 natifs, 5 M6 HTTP natifs et 10 M6 simulés séparés.

La comparaison finale reprend exactement les 18 sélections de la référence
OBS-M7-CONC-01-fix : 1 091 IDs Python et 600 triplets frontend
fichier/nom/index, **1 691 historiques exacts, aucun nouvel ID dans cette
comparaison**. Les six cas de preuve positifs et quatre mutants sont comptés
séparément. Les 70 + 26 voisins forment 96 IDs distincts, sans chevauchement.
Lors de ce lot, une omission de leur orchestration a été repérée pendant le
lancement des 18 sélections : ces 96 cas ont ensuite été exécutés une seule
fois, dans un environnement indépendant, par la commande supplémentaire
`python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-neighbors-20261009 compare-neighbors`.
La version livrée de `compare` inclut aussi ces deux groupes ; le mode séparé
permet de reproduire exactement leur exécution courante sans rejouer les 1 691.
Les groupes partageant un schéma sont séquencés ; chaque nouveau montage
possède ses PostgreSQL/Flask/peers synthétiques. Commandes complètes dans le
relevé, montages read-only, environnement vidé et réseau externe coupé.

## DOCS

Ce rapport/relevé/traces sont nouveaux. La même roadmap, les contrats M7/M8-C
et le hub portent la correction ciblée. Aucun artefact diagnostique ou résultat
historique n’est réécrit. AUD-01/AUD-02 et OBS-M7-CONC-01 restent fermés.
L’incident M4, la clôture globale M8-C et les obligations runtime restent séparés.

## RISKS, auto-audit, contre-lecture et livraison

Les sources produit/CSS/handlers/config/migrations sont identiques à la base.
La comparaison des empreintes porte désormais sur **1 043 fichiers historiques
app hors docs : 1 042 inchangés, un test M7 modifié avec autorisation**. Les
1 041 empreintes inchangées du diagnostic antérieur ne sont pas réutilisées
comme déclaration d’invariance après ce correctif.

Auto-audit : aucun assert métier affaibli, aucune attente par délai arbitraire,
force, retry, clic DOM du menu, transition supprimée, timeout augmenté ou erreur
absorbée. Les barrières et leurs contre-cas atteints sont exigés explicitement.
Les preuves sont synthétiques/content-free à leurs frontières ; aucun secret,
credential, cookie, body HTTP ou contenu personnel brut. Les captures écran
temporaires non retenues sont supprimées après conservation des traces utiles.

Contre-lecture indépendante ciblée : agent `ui_fix_review`, lecture seule des
sources, copies, bruts et documents. Aucune exécution de tests/Docker par ce
lecteur ; cette revue ne constitue pas un nouveau rejeu intégral Codex. Ses
points de provenance/collecteur/documentation ont été corrigés : bind Flask de
l’archive, réponse 200 située entre continuation et retour, contrôle des deux
barrières dans la boucle et description des bureaux encore visibles. Aucun
finding fonctionnel retenu ; portée finale précisée dans le relevé.

Nettoyage effectif : cinq racines possédées supprimées, sockets et captures non
retenues disparus, tous les conteneurs de preuve absents. Digests des dépendances
partagées inchangés. Les 32 conteneurs opérateur gardent exactement leurs nom,
ID, image, instant de démarrage et nombre de redémarrages ; aucun endpoint
opérateur n’a été appelé. Commandes, sorties, exits et durées du nettoyage sont
persistés dans le relevé avant vérification. Les caches partagés sont préservés.

Contrôles précommit bloquants : inventaire exact des dix chemins autorisés
(underscores admis), empreintes, assertions métier, syntaxe, liens, traces,
statuts, références et `git diff --check`. Leurs résultats sont conservés dans
`validation.precommit` ; aucun commit n’est autorisé par un contrôle échoué.
Les 66 références initiales et 27 têtes distantes sont conservées pour la
comparaison finale, hors avancement explicite de la seule branche M8-C.

Seul le défaut d’attente OBS-M7-UI-01 est corrigé dans ce lot. Aucune attribution
certaine aux circonstances exactes du 7 octobre, aucun correctif M4 ou extension
produit. Aucun restart/rebuild/déploiement, Writer/AF_UNIX, M8-S/M8-A ou lot suivant.
Arrêt après livraison Git pour contre-audit Codex ; hash/parent/push et égalité
post-push sont fournis dans le retour final sans auto-référence de l’artefact.
