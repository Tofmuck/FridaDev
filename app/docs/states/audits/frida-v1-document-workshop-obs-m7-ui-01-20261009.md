# OBS-M7-UI-01 — Diagnostic borné du menu téléphone

9 octobre 2026, Celebrimbor. Diagnostic seul autorisé par Tof, sur
`FridaV1-Document-Workshop-M8-C`. Base exacte
`360521bdcd041a9aec9860d058fc9d2b153ed475`, parent
`970ccb37750af1aa7f53486afcef00774d269c84`. HEAD/upstream/distant égaux,
worktree initial propre, divergence `0/0`. Racine réelle et attendue :
`/opt/platform/fridadev`, commandes locales, sans SSH. Les références locales,
de suivi et distantes M0–M7/main sont capturées dans le
[relevé reproductible](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-20261009.json).

## PLAN

« Existe-t-il un meilleur plan ? » Le mandat est déjà le plus petit plan
vérifiable : un rejeu intact, une observation autonome des quatre variantes,
puis des ordres contrôlés motivés par les mesures. Aucun correctif produit,
CSS, test historique, helper commun, fixture HTTP/SQL/DAV ou configuration.
AUD-01/AUD-02 et OBS-M7-CONC-01 ne sont pas rouverts. Aucun runtime,
rebuild/restart, déploiement, Writer/AF_UNIX, M8-S/M8-A ni lot suivant.

## FINDING

**Défaut d'attente du harnais démontré au HEAD courant.** La fermeture native
après sélection et le clic supplémentaire du helper sont concurrents. Un
ordonnancement suffisant reproduit les deux timeouts téléphone avec le vrai
CSS et le vrai `page.click('#btnSidebarClose')`. Aucun défaut produit ni cause
d'environnement n'est démontré par ces essais. **L'ordonnancement exact des
deux rouges du 7 octobre reste inconnu.** OBS-M7-UI-01 est qualifiée, mais son
correctif reste ouvert et n'est pas appliqué dans ce diagnostic.

Le seul extrait historique disponible est celui **transmis par Tof** dans le
mandat : contre-audit du 7 octobre sur `1732a126`, 11/13, téléphone clair/sombre,
timeout 10 000 ms, topbar interceptant puis bouton hors viewport, helper ligne
75 et séquence M7 ligne 93. Aucun accès aux anciens logs bruts n'est revendiqué.
Les verts du 9 octobre et la baseline verte ci-dessous ne ferment pas cet échec.

### Chemin réel et chronologie

1. `showFolder` utilise le vrai `#btnMenu`, puis le toggle du répertoire.
2. Le clic natif `[data-conversation-id="…"]` appelle le listener de
   `chat_threads_list_renderer.js`, qui attend `onSelect`.
3. `selectThread` (`chat_threads_sidebar.js:994–998`) publie la sélection,
   attend `loadThread`, redessine la liste et appelle `closeSidebar`.
   `loadThread` attend notamment le GET réel `workspace-file-selections`.
4. Le helper `choose` n'attend pas la promesse du listener DOM. Après le clic
   Playwright, il appelle le helper commun : `isVisible()` puis `page.click()`.
5. La fermeture native retire `.open`/`.show` et synchronise
   `aria-hidden="true"` / `aria-expanded="false"`. La transition de sortie
   continue ensuite ; la visibilité CSS ne garantit ni position dans le
   viewport, ni réception du pointer, ni intention d'ouverture.

Dans la sonde sans barrière, `phone dark` échoue au **troisième choose**, retour
vers la conversation initiale, **avant reload**. À 14 724,3 ms de son document,
le clic conversation est reçu ; à 14 800,4 ms, la stack réelle attribue le
retrait de `.open` à `selectThread`. La transition se termine à 15 103,6 ms.
Le bouton passe de `(292, 23, 44, 44)` à `(-78, 23, 44, 44)`, transformation
du menu `translateX(-370px)`. Le log Playwright conserve topbar interceptant,
instabilité puis hors viewport ; aucun pointer de fermeture n'est reçu dans
cette tentative. Le menu est déjà fermé légitimement. Ce rouge courant est
observé avec instrumentation et ne reconstitue pas le rouge historique.

La sonde claire atteint aussi le reload et son dernier choose ; les deux
contrôles bureau atteignent leurs assertions historiques. Les traces capturent
classes, ARIA, présentation, viewport/visual viewport/screen/touch, scroll,
rectangles, styles calculés, animations actives, `elementFromPoint` et sa pile,
événements pointer/click/transition, appels du helper et échanges HTTP
méthode/chemin/status. Le script ne capture ni body, ni header, ni credential.
Les horloges navigateur et Node de la première sonde restent séparées :
l'origine Node n'y avait pas été enregistrée. Les contrôles suivants la portent.

### Hypothèses séparées

| Piste | Mesure et qualification |
| --- | --- |
| Bouton inaccessible alors que le menu doit rester ouvert | Non démontré. Dans le témoin, vrai menu ouvert, clic natif reçu par le bouton et handler de fermeture exécuté. |
| Seconde fermeture pendant/après une fermeture légitime | Démontré au HEAD courant. Stack `selectThread`, ARIA fermé, transition réelle, clic supplémentaire et timeout. |
| Ouverture précédente ou publication tardive | Les chronologies conservent les fermetures précédentes. Le contrôle après transition isole la fermeture du troisième choose ; aucune ancienne fermeture, publication SQL ou mutation DOM n'est injectée. Aucun lien causal renderer/SQL établi. |
| Changement de présentation, viewport ou scroll | Pas de changement explicatif observé dans les fenêtres contrôlées. Téléphone `phone` / `mobile-dialogue`, 390×844 ; scroll fenêtre nul. Deux thèmes stockés, même autorité de présentation mobile. Bureau 1280×900 sans bouton de fermeture visible. |
| Reload nécessaire | Réfuté pour la cause suffisante actuelle : rouge passif et rouges contrôlés avant reload. Un autre rouge courant après reload reste également conservé, sans barrière à ce point. |
| Runner différent | Aucune différence démontrée avec le dernier relevé validé. Le tag d'image `v1.54.0-jammy` contient ici le paquet Playwright réellement chargé **1.59.1**, Node **22.17.0**, Chromium **147.0.7727.15** ; ne pas confondre tag et paquet. Runner historique exact du 7 octobre non accessible. |

## PATCH

Deux programmes autonomes seulement :
`app/tests/support/run_obs_m7_ui_01.py` et `probe_obs_m7_ui_01.js`.
Le runner réemploie les commandes du montage M7 validé avec des noms/racines
possédés. Chaque essai possède un nouveau PostgreSQL et un nouveau Flask.
Le navigateur partage uniquement le namespace réseau du Flask `network none`.
Checkout et rootfs en lecture seule, env vidé, caches navigateur montés en
lecture seule ; seule la racine de preuve est écrivable. Aucun endpoint de
contrôle opérateur, appel OpenRouter/Nextcloud/Writer live ou donnée personnelle.

La copie du test est compilée en mémoire avec son chemin de résolution réel.
Les quatre cas conservés gardent leurs assertions. Les contrôles gardent les
deux cas téléphone ; neuf autres cas M7, puis les deux bureaux, sont exclus
explicitement, sans skip. Chaque copie exacte et son diff sont conservés dans
`source_diffs`. Aucun fichier historique n'est édité. Les snapshots complets
du programme de sonde sont capturés pour les derniers contrôles ; ils ne
l'étaient pas pour les premiers essais, dont les copies/diffs restent conservés.

L'observateur riche ajoute des listeners, un wrapper transparent de
`DOMTokenList.add/remove` pour identifier la stack native, des mesures de style
et de géométrie. Les wrappers Playwright ne rajoutent pas d'attente entre le
résultat `isVisible()` et `click()` dans la variante `passive`. Les mesures
peuvent néanmoins changer le timing ; « passive » signifie ici sans barrière,
pas sans effet d'observation. La baseline n'utilise aucune de ces sondes.

## TEST

Toutes les commandes exactes, IDs, exits, durées, inventaires, empreintes et
logs TAP sont dans `records`/`raw_logs` du relevé. Les traces complètes sont dans
[l'archive JSONL technique](../baselines/document-workshop/frida-v1-document-workshop-obs-m7-ui-01-20261009.trace.jsonl.gz)
(gzip, un objet par session). Deux screenshots synthétiques après résultat sont
conservés ; ils illustrent l'état final et ne prouvent pas la géométrie au clic.

| Essai distinct | Résultat | Exit | Durée navigateur murale |
| --- | --- | --- | --- |
| `baseline` intacte | 13/13 | 0 | 265,955 s |
| `passive` quatre variantes | 3/4 ; phone dark rouge avant reload | 1 | 70,080 s |
| `after-close` retrait de classe | 1/2 ; les deux gestes armés réussissent ; rouge light ultérieur après reload non armé | 1 | 35,586 s |
| `before-close` témoin GET retenu | 2/2 ; assertions historiques complètes | 0 | 27,884 s |
| `after-transition` observateur riche | 2 timeouts au geste armé / 2 cas | 1 | 41,496 s |
| `minimal-after` observateur réduit | 2 timeouts au geste armé / 2 cas | 1 | 40,782 s |
| `minimal-target` cible transition verrouillée | 2 rouges précoces non armés ; contrôle non atteint | 1 | 30,159 s |

Zéro skip/annulation dans chaque essai. Aucun cumul des ciblés avec les treize
natifs. Les cinq natifs M6, dix M6 simulés et la comparaison 1 691/1 691 restent
historiques et distincts ; ils ne sont pas relancés sans delta partagé.

### Contrôles causaux et limites de l'observateur

Le point d'armement est inséré uniquement dans la copie possédée, avant le
troisième choose de la séquence historique ligne 93. Les deux révisions, leur
identité, leurs reçus et les contrôles précédant cette navigation restent réels.

`after-close` attend seulement le retrait réel de `.open` après `isVisible`.
Les deux clics armés passent : le DOM peut déjà annoncer fermé alors que la
géométrie affichée permet encore le clic. Le rouge light est plus tard, après
reload, et n'est **pas** un rouge causal de cette barrière. Ce résultat ne prouve
pas qu'une tentative durant la transition réussisse toujours.

`before-close` retient uniquement le GET réel `workspace-file-selections` attendu
par `loadThread`, puis fait `route.continue()` après le clic natif réussi.
Il ne fabrique ni requête de confirmation, ni réponse HTTP, ni fermeture.
La trace exige un GET retenu, le clic rendu, sa libération puis la réponse 200.
Les deux parcours complets passent. Ce vert diagnostique n'est pas un correctif.

`after-transition` retient seulement l'invocation du helper **après son vrai
isVisible positif**, jusqu'à la fermeture et la fin de transition réelles du
menu. Il ne retire aucune classe et ne change pas le CSS. Les deux traces
riches prouvent `selectThread → remove(open) → transitionend transform sidebar
→ libération → clic natif → Timeout 10000ms`, bouton entièrement hors viewport.
La fin de transition est **suffisante**, sans être prétendue nécessaire.
Ces deux contrôles complémentaires ne sont pas une paire strictement à facteur
unique : l'un retient le réseau, l'autre le helper.

`minimal-after` retire les mesures géométriques/style et les wrappers DOM
pendant le parcours ; restent les wrappers Node, listeners HTTP/pageerror et
la barrière locale bornée. Elle utilise les vrais événements, un frame et
`getAnimations()` pour reconnaître un menu déjà fermé sans transition active.
La mesure géométrique et le screenshot n'arrivent qu'après le résultat.
Les deux mêmes rouges restent présents : la riche instrumentation géométrique
n'est donc pas nécessaire à cette cause suffisante. Un observateur réduit
reste présent ; aucune fréquence spontanée n'est mesurée.

La contre-lecture a demandé `event.target === sidebar` sur `transitionend`,
pour exclure un événement descendant bouillonnant. Les traces riches déjà
capturées confirment que la sidebar elle-même a libéré les barrières précédentes.
`minimal-target` verrouille explicitement cette cible mais ses deux cas échouent
**avant armement** : light au choose initial, zéro reçu ; dark au choix de
l'autre conversation, trois reçus déjà établis. Cette tentative ne prouve donc
pas la nouvelle garde de cible. Le collecteur a d'abord rejeté ces deux rouges
par absence de `barrier-armed` (exit 1, `StopIteration`, 0,076 s), puis a conservé
leur qualification explicite de contrôles non atteints (exit 0, 0,310 s).
Aucun nouveau rejeu après ce constat. La reproduction contrôlée riche reste
validée par la cible native enregistrée dans sa trace ; l'observateur réduit
`minimal-after` avait déjà atteint les deux barrières. Aucun timeout produit
allongé : 10 000 ms exacts ; les bornes
de cinq secondes ne servent qu'à faire échouer une barrière sans événement.
Pas de force, clic DOM sidebar, transition supprimée, assertion affaiblie,
retry de test, polling correctif ou nouvelle mutation documentaire.

Les rouges contrôlés atteints arrêtent au troisième choose : **reload, réhydratation du
reçu après reload, lanes tardives et contrôles finaux ne sont pas atteints dans
ces cas**. Ils ne les valident pas. Trois reçus et trois PUT par cas existent
avant la barrière (cumuls 3 puis 6 dans chaque fixture), zéro DELETE/MKCOL.
La baseline et le témoin complet conservent leurs assertions d'identité,
navigation, reçu et absence de replay. Les traces GET supplémentaires sont
des observations existantes, pas des confirmations ajoutées par la sonde.

### Reproduction

Plugin Browser absent : Playwright local existant, sans installation.
Depuis la racine applicative, utiliser une nouvelle racine de preuve :

```bash
python3 app/tests/support/run_obs_m7_ui_01.py /tmp/fridadev-obs-m7-ui-01-replay baseline
python3 app/tests/support/run_obs_m7_ui_01.py /tmp/fridadev-obs-m7-ui-01-replay probe before-close
python3 app/tests/support/run_obs_m7_ui_01.py /tmp/fridadev-obs-m7-ui-01-replay probe after-transition
python3 app/tests/support/run_obs_m7_ui_01.py /tmp/fridadev-obs-m7-ui-01-replay probe minimal-target
```

Séquencer les commandes. Les deux dernières attendent exit **1**, uniquement
si les deux cas atteignent la barrière puis échouent au clic natif exact ; un
échec de setup, de gate ou antérieur ne compte pas comme reproduction. Les
assertions du collecteur autonome, conservé dans `proof_programs`, rejettent
ces faux rouges et vérifient les inventaires, hashes et branches non atteintes.

## DOCS

Rapport/relevé datés et traces nouveaux ; ajouts de statut ciblés dans la même
roadmap, les contrats M7/M8-C et le hub. Aucun résultat ancien réécrit, ni
requalification de M4 par similarité. OBS-M7-CONC-01 et AUD-01/AUD-02 restent
validés ; clôture globale M8-C et runtime restent hors mandat.

## RISKS, auto-audit et suite bornée

Auto-audit : inventaires distincts, vrais gestes/handlers/CSS/transport,
observation riche séparée de la baseline, rouge naturel instrumenté séparé des
rouges contrôlés, branches non atteintes explicites, aucune nouvelle autorité
de confirmation ou mutation DAV. Les empreintes des **1 041 fichiers historiques
hors documentation** sont comparées à la capture initiale. Les preuves ont
uniquement du contenu technique/synthétique, sans body HTTP, header ou secret.

Incident auxiliaire conservé : premier setup `passive` exit 1 avant tout test,
le contrôle Docker cherchait le navigateur encore inexistant. Sa durée et ses
commandes restent dans `passive-setup-failure` ; cleanup HTTP/PG vérifié vide.
Le contrôle a été corrigé, sans changement produit. La baseline initiale avait
bufferisé le TAP jusqu'au retour (aucun rouge) ; les essais suivants écrivent
directement le TAP dès émission. La contre-lecture a aussi renforcé capture
d'erreurs, ancre de sélection, assertion réelle d'absence et nettoyage continu
malgré un navigateur auto-supprimé par `--rm`.

Contre-lecture indépendante ciblée : statique et lecture des artefacts, aucun
test/Docker supplémentaire revendiqué par le relecteur. Avis final favorable pour ce diagnostic seul, aucun finding substantiel restant
dans le delta relu. La garde finale de cible reste non exercée, explicitement
consignée. Nettoyage final vérifié et enregistré avant livraison Git.
Les conteneurs possédés sont supprimés en `finally`, y compris après les rouges.
La racine temporaire/sockets/captures non retenues est supprimée après collecte ;
les caches partagés sont préservés. Aucun conteneur ni service opérateur touché.

**Suite proposée, non appliquée :** dans un mandat correctif distinct, retirer
du seul chemin M7 `choose` le clic redondant après sélection sur téléphone et
attendre la fermeture par le handler existant, avec ses attributs et sa
transition ; conserver le helper de fermeture explicite pour les parcours où
le menu doit réellement être fermé par l'utilisateur. Éprouver les deux ordres,
le reload, l'ouverture suivante, la fidélité du clic de fermeture explicite et
les assertions M7 complètes, puis choisir les voisins M6 utiles. Pas de patch
CSS, timeout allongé, garde `isVisible` seule ou retour immédiat qui masquerait
un chargement encore actif. Aucun GO implicite pour ce correctif.

L'incident M4 reste ouvert séparément. Les anciens logs/ordres des deux rouges
M7 restent manquants ; aucune attribution rétrospective certaine ni fréquence
de course spontanée. Arrêt après livraison Git, pour contre-audit Codex.
