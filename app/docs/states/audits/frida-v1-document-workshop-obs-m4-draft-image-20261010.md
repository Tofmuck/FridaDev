# M4-Chromium-intermediate-draft-failure — Diagnostic borné

10 octobre 2026, Celebrimbor. Base `d3e1f685af88777e363d075fc7f5207f9008c031`,
parent `2fd60c48a5a01669425fded6a648304fdede45e0`, branche
`FridaV1-Document-Workshop-M8-C`. `pwd` et toplevel Git confirmés à
`/opt/platform/fridadev`, sans SSH. Avant édition : worktree propre,
HEAD = upstream = distant, divergence 0/0 ; 55 références locales/`origin` et
27 branches distantes capturées.

[Relevé durable](../baselines/document-workshop/frida-v1-document-workshop-obs-m4-draft-image-20261010.json).
Sources, commandes/empreintes, sorties brutes synthétiques, événements ordonnés,
intermédiaires, contrôles, limites et nettoyage y sont conservés.

## PLAN

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » Rejouer une fois M4 intact et le seul cas image, puis observer les
transitions réelles avant d'imposer un ordre sur une frontière identifiée.
Aucun correctif produit/test/fixture ; aucune comparaison générale par automatisme.

1. Capturer base, empreintes produit/tests/helpers/dépendances et ressources.
2. Baseline 22 cas, ciblé image exact, puis observation sans barrière.
3. Témoin et ordre adverse au point focus/sélection → insertion réelle.
4. Contrôle réduit pour retirer l'instrumentation détaillée de la conclusion.
5. Conserver les preuves, relire indépendamment, nettoyer, commit/push puis arrêt.

## FINDING

**Fait actuel prouvé : une course de synchronisation du harnais suffit à laisser
le compositeur vide, sans effacement par le produit.** Le texte est inséré dans
le prompt image lorsque son vrai callback différé prend le focus entre la
sélection de `#message` et l'insertion clavier réelle de Playwright. La garde
documentaire continue de refuser l'envoi incompatible, avant tout effet optimiste,
avec zéro préparation, zéro appel au chat normal et zéro génération d'image.

**Inférence bornée :** le harnais suppose que `page.fill` garde sa cible focalisée
jusqu'à l'insertion. Son helper `send` ne synchronise pas le focus différé du
panneau image. Le mécanisme suffit au HEAD courant ; aucun défaut de la garde,
de la fixture de transport ou du runner n'est démontré.

**Inconnue historique :** impossible d'attribuer exactement le 21/22 d'AUD-01
à cette course. L'original dans
`intermediate_records["final-final-baseline-chromium_m4"]` du
[relevé AUD-01 inchangé](../baselines/document-workshop/frida-v1-document-workshop-p2-m8c-aud-01-20261007.json)
porte exit 1, 20,774 s, le brouillon vide et les 22 noms ; ses traces brutes ont
été supprimées selon `raw_logs_policy`. Ni le digest ni les verts ultérieurs
ne reconstituent leur chronologie. Sa qualification historique est conservée.
Aucune fréquence spontanée n'est mesurée dans ce diagnostic.

### Wiring et auteurs

- `index.html` charge `chat_image_generation.js` puis `app.js`. Ce dernier crée
  le vrai contrôleur image. `open` écrit `state.open=true`, rend panneau/ARIA,
  puis programme **`setTimeout(() => promptEl.focus(), 0)`**. Aucun fetch à
  l'ouverture ; seul `submit` image appelle `/api/tools/image-generation`.
- `openWorkshop` clique le vrai menu. Le contrôleur écrit `visible=true`
  synchroniquement, puis attend le contexte. `ready` ne prouve que l'appel
  active-documents ; les contrôles causaux attendent explicitement `editing`.
  Les traces riches lisent aussi les vrais locaux : context-0, prepare=true,
  busy=false, scope conv-a/folder-a, visible=true avant la garde.
- Playwright installé : `injected.fill(textarea)` focalise/sélectionne et renvoie
  `needsinput` ; `dom._fill` attend ce résultat puis appelle `_insertText` ;
  `Keyboard._insertText` délègue à `raw.sendText` sans refocaliser le textarea.
- Le vrai submit de `#ask` appelle `submitCanonicalChatMessage`, puis
  `blocksSubmission`, calcul des modes, `prepareSubmission` et `refuseSubmission`.
  L'effacement `message.value=""` est après l'acceptation et `addMsg` optimiste.
  Cette branche n'est pas atteinte dans les sondes. Le setter seul ne capture
  pas forcément l'insertion native : destination/longueur/égalité synthétique,
  événements input et point de délégation établissent ici l'auteur réel.

## PATCH

Seul ajout hors docs :
`app/tests/support/probe_obs_m4_draft_image.js`, programme diagnostique autonome.
Il extrait en mémoire le préfixe exact du test M4 avant ses registrations, pour
réutiliser `preparationScript`, `ready`, `send`, `openWorkshop`, `openBrowserPage`.
Le test historique et ses 22 assertions/cas ne sont jamais réécrits.

Observation initiale V1 : ajouts de trace dans trois réponses JS en mémoire,
setter délégué et observateur fetch délégué. Sa source exacte est archivée
séparément dans `proof_programs.observe-program.js` ; elle précède la version
avec barrières. Aucun nouveau run du mode `observe` de la source finale revendiqué.

Contrôles riches : mêmes ajouts, plus rétention du vrai callback de focus après
l'expiration du timer natif à zéro, et hook mémoire sur le vrai
`Keyboard.prototype._insertText`. Le hook vérifie que fill a focalisé message,
retient l'insertion, puis délègue exactement une fois à la méthode originale.
Le prototype est restauré dans finally ; processus/conteneur jetables.

Le contrôleur Node libère explicitement le callback et l'insertion ; il n'attend
jamais le brouillon vide pour les libérer. Pas de fake de garde/handler, focus
forcé, clic forcé, sommeil arbitraire, délai fixe ajouté ou timeout augmenté.
Le contrôle réduit ne route que le site du callback dans `chat_image_generation.js` :
aucun hook app/garde, setter, observateur DOM global ou wrapper fetch supplémentaire.
Il conserve les deux barrières et les snapshots minimaux de leur frontière.

**Correction minimale proposée, non appliquée :** dans le seul cas historique
`#btnImageGeneration`, attendre après le clic et avant `send` que
`document.activeElement === document.querySelector('#imageGenerationPrompt')`.
Cette condition observe la fin du vrai callback ; panneau visible/ARIA seuls
ne la prouvent pas. Tout correctif et sa validation relèvent d'un lot distinct.

## TEST

Tous les résultats suivants sont exécutés le 10 octobre par Celebrimbor,
séquencés, sans relance jusqu'au vert. Les sélections se recouvrent et ne sont
pas additionnées à un total de régression.

| Sélection / question | Résultat | Exit | Durée murale |
| --- | --- | --- | --- |
| M4 intact, concurrence 1 | 22/22 ; zéro fail/skip/cancel | 0 | 19,769428 s |
| Cas image exact, concurrence 1 | 1/1 ; 21 exclus par filtre, zéro ignoré | 0 | 1,317375 s |
| Observation V1, séquence historique sans barrière | brouillon16, garde incompatible, trois voies réseau à zéro | 0 | 1,321243 s |
| Témoin : callback avant fill | brouillon16 / prompt0 | 0 | 1,365519 s |
| Adverse : callback entre sélection et insertion | brouillon0 / prompt16 ; assertion exacte rouge | 1 | 1,382525 s |
| Adverse réduit : hooks détaillés retirés | même destination et même rouge après barrières | 1 | 1,368992 s |

Nom réellement sélectionné :
`M4 incompatible #btnImageGeneration preserves draft and active control before optimistic effects`.
TAP échappe `#` en `\#` ; seul cet échappement est normalisé. Les 22 noms de
baseline sont identiques aux 22 noms historiques AUD-01 normalisés.
Les 21 autres cas du ciblé sont **exclus par filtre**, pas exécutés/ignorés.

Chronologie riche témoin : contexte réellement editing → image ouverte → timer
atteint → libération du vrai focus image → fill focalise message → insertion
réelle/input trusted dans message → clic/submit trusted ask → garde incompatible.
Adverse : même contexte → timer atteint et retenu → fill focalise message →
point réel _insertText atteint → libération indépendante du vrai callback image
→ focus image → libération indépendante de l'insertion → input trusted dans
imageGenerationPrompt → clic/submit trusted ask → visible=true,
incompatibleModes=true, refus document_mode_incompatible. Aucun exit/existence
de bouton ne remplace ces préconditions.

Un passage unique de chaque barrière/callback/délégation, ordre vérifié et
`causalChecks=passed` précèdent les deux AssertionError : actual `""`, expected
`"Brouillon intact"`. Toutes les autres assertions métier équivalentes sont
vérifiées **avant** cette assertion rouge : aucun message user optimiste,
préparation/chat normal/image à zéro, incompatibilité visible, image ouverte.
Les lignes du helper de pageerror et les assertions dupliquées après le throw
ne sont pas atteintes dans les négatifs ; aucun succès de ces branches revendiqué.

L'observation riche perturbe le timing. Le réduit retire ses hooks tout en
reproduisant le mécanisme : il écarte leur nécessité, sans transformer
l'ordonnancement imposé en trace spontanée. Le témoin contrôle l'ordre opposé
avec les mêmes deux frontières.

Versions réellement observées : Node v22.17.0, Playwright 1.59.1,
Chromium 147.0.7727.15 ; image existante `mcr.microsoft.com/playwright:v1.54.0-jammy`
figée par ID/digest dans le relevé. La version Playwright provient du node_modules
readonly du checkout, pas du tag de l'image. Empreintes avant instrumentation :
1 600 fichiers suivis, package-lock, packages Playwright et browsers.json ;
toutes intactes avant édition documentaire. Hashes supplémentaires des sources
internes Playwright relevés après lecture, sans leur inventer une capture initiale.
Les surfaces frontend/test/helpers concernés concordent aussi avec les SHA AUD-01.

Transport : **fetch simulé de la fixture historique**, fichiers HTTP statiques
réels ; aucun parcours navigateur → Flask, DB, provider ou Nextcloud.
Six conteneurs distincts `--pull=never`, réseau none, rootfs/checkout/cache readonly,
env vidé, tmpfs /tmp. Inspection effective baseline conservée ; les autres
confinements sont vérifiés dans leurs argv exacts, sans inspection rétroactive
revendiquée. Aucune installation, image reconstruite ou ressource opérateur montée.

### Commandes de reproduction éprouvées

Depuis `/opt/platform/fridadev`, images et dépendances existantes. Choisir une
racine initialement absente et possédée ; l'emplacement ci-dessous était absent
au début du lot et est supprimé avant livraison. Ne supprimer/réutiliser aucune
racine étrangère. Les noms de conteneurs doivent également être libres ; Docker
refuse une collision. Les cinq argv Docker ci-dessous sont les argv réellement
exécutés. La source finale de la sonde est celle des trois contrôles ; V1 reste
un intermédiaire conservé, sans commande courante de reproduction revendiquée.

```bash
set -euo pipefail
m4_root=/tmp/fridadev-obs-m4-draft-image-20261010
test ! -e "$m4_root"
mkdir -- "$m4_root"
docker run --rm --pull=never --name fridadev-obs-m4-draft-image-baseline-20261010 --label fridadev.proof=obs-m4-draft-image-20261010 --network none --read-only --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro -v /home/tof/.cache/ms-playwright:/proof/browsers:ro -w /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node --test --test-concurrency=1 app/tests/integration/frontend_browser/test_frontend_browser_document_preparation_m4.js > "$m4_root/baseline.log" 2>&1
docker run --rm --pull=never --name fridadev-obs-m4-draft-image-targeted-20261010 --label fridadev.proof=obs-m4-draft-image-20261010 --network none --read-only --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro -v /home/tof/.cache/ms-playwright:/proof/browsers:ro -w /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node --test --test-concurrency=1 '--test-name-pattern=^M4 incompatible #btnImageGeneration preserves draft and active control before optimistic effects$' app/tests/integration/frontend_browser/test_frontend_browser_document_preparation_m4.js > "$m4_root/targeted.log" 2>&1
docker run --rm --pull=never --name fridadev-obs-m4-draft-image-witness-20261010 --label fridadev.proof=obs-m4-draft-image-20261010 --network none --read-only --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro -v /home/tof/.cache/ms-playwright:/proof/browsers:ro -w /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node app/tests/support/probe_obs_m4_draft_image.js witness > "$m4_root/witness.log" 2>&1
```

Chaque négatif doit produire exit 1 **et** les barrières/l’erreur ci-dessous.
Un rouge de setup bloque la suite ; aucune commande Git n’est chaînée.

```bash
set -euo pipefail
m4_root=/tmp/fridadev-obs-m4-draft-image-20261010
m4_exit=0
docker run --rm --pull=never --name fridadev-obs-m4-draft-image-adverse-20261010 --label fridadev.proof=obs-m4-draft-image-20261010 --network none --read-only --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro -v /home/tof/.cache/ms-playwright:/proof/browsers:ro -w /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node app/tests/support/probe_obs_m4_draft_image.js adverse > "$m4_root/adverse.log" 2>&1 || m4_exit=$?
test "$m4_exit" -eq 1
python3 - "$m4_root/adverse.log" <<'PY'
import json,sys
from pathlib import Path
lines=Path(sys.argv[1]).read_text().splitlines()
x=json.loads(next(line[14:] for line in lines if line.startswith('M4_DIAGNOSTIC ')))
assert x['exit']==1 and x['causalChecks']['status']=='passed'
assert x['error']['name']=='AssertionError' and x['error']['actual']=='' and x['error']['expected']=='Brouillon intact'
e=x['events'];k=[v['kind'] for v in e]
for name in ['focus-barrier-armed','focus-barrier-reached','insert-barrier-reached','focus-release-before','focus-release-after','independent-insert-release','real-insert-before','real-insert-after']:assert k.count(name)==1,name
assert k.index('focus-barrier-armed')<k.index('focus-barrier-reached')<k.index('insert-barrier-reached')<k.index('focus-release-before')<k.index('focus-release-after')<k.index('independent-insert-release')<k.index('real-insert-before')<k.index('real-insert-after')
assert e[k.index('insert-barrier-reached')]['snapshot']['activeElement']=='message'
assert e[k.index('real-insert-before')]['snapshot']['activeElement']=='imageGenerationPrompt'
s=x['outcome']['snapshot'];assert s['draftLength']==0 and s['imagePromptHasDraft'] and s['imagePromptLength']==16 and s['optimisticUsers']==0
assert x['outcome']['normalCalls']==x['outcome']['documentaryCalls']==x['outcome']['imageCalls']==0
assert 'incompatible' in x['outcome']['status'].lower() and s['imageExpanded']=='true'
print('causal negative verified:',x['mode'])
PY
```

```bash
set -euo pipefail
m4_root=/tmp/fridadev-obs-m4-draft-image-20261010
m4_exit=0
docker run --rm --pull=never --name fridadev-obs-m4-draft-image-adverse-reduced-20261010 --label fridadev.proof=obs-m4-draft-image-20261010 --network none --read-only --tmpfs /tmp:rw,nosuid,nodev -v /opt/platform/fridadev:/workspace:ro -v /home/tof/.cache/ms-playwright:/proof/browsers:ro -w /workspace --entrypoint /usr/bin/env mcr.microsoft.com/playwright:v1.54.0-jammy -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/proof/browsers node app/tests/support/probe_obs_m4_draft_image.js adverse-reduced > "$m4_root/adverse-reduced.log" 2>&1 || m4_exit=$?
test "$m4_exit" -eq 1
python3 - "$m4_root/adverse-reduced.log" <<'PY'
import json,sys
from pathlib import Path
lines=Path(sys.argv[1]).read_text().splitlines()
x=json.loads(next(line[14:] for line in lines if line.startswith('M4_DIAGNOSTIC ')))
assert x['exit']==1 and x['causalChecks']['status']=='passed'
assert x['error']['name']=='AssertionError' and x['error']['actual']=='' and x['error']['expected']=='Brouillon intact'
e=x['events'];k=[v['kind'] for v in e]
for name in ['focus-barrier-armed','focus-barrier-reached','insert-barrier-reached','focus-release-before','focus-release-after','independent-insert-release','real-insert-before','real-insert-after']:assert k.count(name)==1,name
assert k.index('focus-barrier-armed')<k.index('focus-barrier-reached')<k.index('insert-barrier-reached')<k.index('focus-release-before')<k.index('focus-release-after')<k.index('independent-insert-release')<k.index('real-insert-before')<k.index('real-insert-after')
assert e[k.index('insert-barrier-reached')]['snapshot']['activeElement']=='message'
assert e[k.index('real-insert-before')]['snapshot']['activeElement']=='imageGenerationPrompt'
s=x['outcome']['snapshot'];assert s['draftLength']==0 and s['imagePromptHasDraft'] and s['imagePromptLength']==16 and s['optimisticUsers']==0
assert x['outcome']['normalCalls']==x['outcome']['documentaryCalls']==x['outcome']['imageCalls']==0
assert 'incompatible' in x['outcome']['status'].lower() and s['imageExpanded']=='true'
print('causal negative verified:',x['mode'])
PY
```

Ces deux validateurs Python sont exécutés tels que publiés sur les premières
sorties conservées, exit 0 ; les trois blocs shell sont vérifiés par bash -n.
Le contrôle complet supplémentaire `validate_proofs.py`, conservé dans le relevé,
vérifie noms/ordres/empreintes, paire témoin/adverse identique et réduit, sans
rejouer les tests. Aucun total 1 691 ou voisin n'est relancé/attribué à ce lot.

## DOCS

Rapport/relevé dédiés, même roadmap et contrats M4/M8-C mis à jour. Le hub garde
son routage actuel vers ces contrats et la roadmap ; modification sans objet.
Les anciens relevés AUD/P3, traces et résultats demeurent inchangés.

Réserve distincte transmise par Tof lors du mandat du 10 octobre : le dernier
contre-audit Codex de l'archive M7 ancienne n'a atteint qu'une des deux barrières ;
téléphone clair arrêté pendant son choose initial, téléphone sombre armé.
Ce constat reste distinct du record Celebrimbor à deux barrières ; préfixe du
lanceur validé et P3-M7-UI-FIX-01 fermé. Aucun diagnostic/correctif/rejeu de cette
archive ici. AUD-01/AUD-02, concurrence M7 et correctif d'attente UI restent fermés
dans leurs portées. Clôture globale M8-C et runtime toujours distincts.

## RISKS

Cause suffisante actuelle établie, attribution historique exacte inconnue.
Aucun défaut produit établi ni garantie générale sur toutes les interactions
utilisateur ; Chromium/fetch simulé seulement. Le correctif du harnais proposé
n'est ni appliqué ni validé par ce lot. L'observation M4 n'est pas effacée par
les verts, et son attribution historique demeure ouverte.

Auto-audit : précondition réelle atteinte ; tests/assertions/délais historiques
intacts ; frontières et libérations observées une fois ; instrumentation
perturbatrice explicitée et réduite ; aucune causalité attribuée à un seul vert ;
zéro absorption par les trois voies réseau. Recherche auxiliaire de chemins
CSS/Playwright erronés, recherches auxiliaires du relecteur et erreur de lecture
du manifeste conservées dans `incidents`, avec sorties disponibles et limites ; aucune relance de test ni
cause de lancement/collecte/nettoyage ne leur est attribuée.

Le précommit V1 s'est arrêté car sa commande comparait toutes les références
Git aux seules 55 références locales/`origin` initialement capturées : dix refs
internes Codex et une ref d'un autre remote étaient hors de cette sélection.
Les 55 références capturées sont exactement inchangées. V1, sortie et exit 1
sont conservés ; V2 reprend la sélection initiale exacte, sans mutation Git.
V2 passe (exit 0, 0,886549 s), puis le contrôle strict après nettoyage passe
(exit 0, 0,903336 s). Le champ `other_refs_unchanged` de ces sorties couvre
uniquement les 55 références capturées ; les onze hors sélection n'ont pas de
baseline comparative dans ce lot.

Seconde lecture indépendante p3_review : sources/raisonnement/empreintes et
preuves causales puis documents/relevé ; aucun test, Docker ou réseau exécuté
personnellement. Avis causal favorable ; avis documentaire final enregistré
avant commit, sans lui attribuer les contrôles de livraison ultérieurs.

Livraison bloquée tant que l'inventaire exact, les SHA protégés, les liens,
commandes/validators publiés, relecture du diff et git diff --check ne passent
pas. Nettoyage limité à la racine possédée et aux six conteneurs --rm ; preuves
conservées avant retrait. Disparition vérifiée, caches partagés préservés et
32 conteneurs opérateur inchangés. Aucun service redémarré/reconstruit, migration,
OpenRouter/DAV réel, M8-S/M8-A ou correction appliquée. Commit/push requis sur
M8-C ; hash complet, parent, égalité HEAD/upstream/distant 0/0 et préservation des
autres références fournis dans le retour final. Arrêt pour contre-audit Codex.
