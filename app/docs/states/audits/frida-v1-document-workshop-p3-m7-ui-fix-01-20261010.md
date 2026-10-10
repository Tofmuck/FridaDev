# P3-M7-UI-FIX-01 — Contrat des racines du lanceur OBS-M7-UI-01

10 octobre 2026, Celebrimbor. Mandat ciblé de Tof : cohérence du lanceur et
reproduction seulement, jusqu'au commit/push sur `FridaV1-Document-Workshop-M8-C`,
puis arrêt pour contre-audit Codex. Racine locale confirmée par `pwd` et Git :
`/opt/platform/fridadev`, sans SSH. Base exacte
`2fd60c48a5a01669425fded6a648304fdede45e0`, parent de cette base
`be9e3a8a0bdbc246659ccde4f286a2a91e2cbab3`. État initial : worktree propre,
HEAD = upstream = distant, divergence 0/0 ; références de toutes les branches
capturées avant édition.

[Relevé P3 dédié](../baselines/document-workshop/frida-v1-document-workshop-p3-m7-ui-fix-01-20261010.json)
et [traces techniques JSONL gzip](../baselines/document-workshop/frida-v1-document-workshop-p3-m7-ui-fix-01-20261010.trace.jsonl.gz).
Le [correctif fonctionnel du 9 octobre](frida-v1-document-workshop-obs-m7-ui-01-fix-20261009.md)
est validé ; ses résultats, JSON, traces et programmes historiques sont conservés.
L'erratum du présent lot ne leur attribue aucun nouveau rejeu Codex.

## PLAN

« Existe-t-il un meilleur plan, plus simple, plus sûr et avec moins d'effets de
bord ? » Le plus petit correctif conserve le namespace de conteneurs déjà
éprouvé, définit le préfixe de racine `fridadev-obs-m7-ui-01-fix-` une seule fois
et le reporte dans la copie du runner interne. Aucun changement du runner
historique, du produit ou du correctif d'attente M7.

1. Capturer Git/empreintes/ressources, puis conserver le premier rouge avant édition.
2. Aligner les deux gardes sans supprimer la restriction directement sous `/tmp`.
3. Vérifier refus avant effets, quatre sondes causales, archive exacte et six modes.
4. Rejouer une seule fois les 18 sélections historiques exactes, voisins séparés.
5. Corriger les exemples par erratum, relire indépendamment, conserver les preuves,
   nettoyer les seules ressources possédées et livrer après contrôles bloquants.

## FINDING

À la base demandée, le lanceur acceptait `fridadev-obs-m7-ui-01-` mais remplaçait
le `PREFIX` du runner par `fridadev-obs-m7-ui-01-fix`. Ce `PREFIX` servait aussi
à sa garde de racine : les exemples `…-replay` et `…-archive-replay` franchissaient
la première garde, puis échouaient après les premières écritures.

Reproduction du 10 octobre, racine initialement absente et possédée :

```text
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-replay-p3-20261010 probe completed
```

**Exit 1 en 0,046 s, AssertionError, aucun browser record**, deux fichiers créés :
`probe-program-run_obs_m7_ui_01_fix.py` et `completed-owned-runner.py`.
La première sortie complète, son empreinte et les deux copies sont conservées.
C'est un échec de lancement, jamais un rouge causal. Aucun conteneur créé.

La reproduction indépendante du 9 octobre transmise par Tof (0,053 s) reste
historique. De même, les résultats Codex transmis — `completed` 4/4, `pending`
2/2, deux rouges `no-wait`, deux timeouts `old-click`, puis M7 natif 13/13 —
valident le correctif d'attente, sans prétention de nouveau rejeu intégral Codex
des 1 691 et 70 + 26 contrôlés dans les artefacts de Celebrimbor.

## PATCH

Seul `app/tests/support/run_obs_m7_ui_01_fix.py` change hors documentation :

- `ROOT_PREFIX = 'fridadev-obs-m7-ui-01-fix-'` ; garde commune avant mkdir/copies,
  extraction Git et tout accès Docker, pour les six modes ;
- même valeur littérale injectée dans la garde de la copie interne, avec ancre
  unique vérifiée ; le contrôle du parent `/tmp` reste présent ;
- `PREFIX = 'fridadev-obs-m7-ui-01-fix'` des conteneurs inchangé ; branche
  comparaison/orchestration inchangée octet pour octet.

Les copies native/probe/historical gardent leurs noms/propriétés de conteneurs,
montages et nettoyage. `neighbors`, `compare` et `compare-neighbors` utilisent
la même garde d'entrée ; leurs programmes internes sont inchangés. Aucune garde
retirée, aucun nouveau mode CLI ou framework. Une racine préexistante n'est pas
appropriable par son seul nom : l'opérateur doit toujours choisir une racine
neuve possédée ; les contrôles de collision de conteneurs restent actifs.

`waitForNativeSelection`, `choose`, sondes JS, assertions métier, fixtures,
CSS, produit, migrations, budgets et leases sont identiques à la base.

## TEST

Toutes les lignes ci-dessous sont **exécutées le 10 octobre par Celebrimbor**.
Chaque premier exit/sortie est persisté avant assertion ; aucune relance de test
jusqu'au vert, aucune découverte générale. Programmes et validations complets
conservés dans `proof_programs` du relevé dédié. Les cinq blocs shell publiés
sont vérifiés syntaxiquement ; leurs trois validateurs Python de traces sont
exécutés tels que publiés, sans nouveau rejeu navigateur.

| Commande | Résultat | Exit | Lanceur, setup/nettoyage inclus | Navigateur |
| --- | --- | --- | --- | --- |
| `probe completed` | 4/4 complets | 0 | 76.236 s | 71.800 s |
| `probe pending` | 2/2 complets | 0 | 36.308 s | 31.596 s |
| `probe no-wait` | 2 rejets causaux attendus | 1 | 30.895 s | 26.465 s |
| `probe old-click` | 2 timeouts causaux attendus | 1 | 45.665 s | 41.027 s |
| `historical after-transition` | 2 timeouts causaux attendus | 1 | 44.983 s | 40.549 s |
| `native p3-native` | 13/13 | 0 | 266.710 s | 262.690 s |
| `neighbors` | 13 M7 + 5 M6 HTTP + 10 M6 simulés, séparés | 0 | 312.843 s | voir relevé par sélection |
| `compare` | 1 691/1 691 + 70 + 26 séparés | 0 | 842.993 s | voir relevé par sélection |
| `compare-neighbors` | 70 + 26, rejeu de mode séparé | 0 | 6.520 s | voir relevé par sélection |

36 rejets instrumentés avant tout effet sur six modes, dont racines hors `/tmp`,
niveau imbriqué, préfixe sans tiret et anciens exemples. Quatre contrôles de
passage des deux gardes native/probe. Six refus réellement lancés, chacun sur
une racine absente : répertoire/copies toujours absents, inventaire Docker
strictement identique avant/après. Le test de régression retrouve d'abord les
six admissions erronées à partir du source Git de la base, sans produire d'effet.

`completed` atteint ses assertions historiques dans les quatre contextes ;
`pending` exige GET retenu → attente pendante → libération indépendante →
continuation → vraie réponse 200 → fin de l'attente dans les deux téléphones.
`no-wait` atteint le GET retenu puis produit exactement deux
`selection-wait-returned-before-real-GET-release`. `old-click` atteint
`closed-before-wait → old-click-call`, puis exactement deux timeouts de 10 000 ms.
Aucun rouge de setup n'est accepté. Les six positifs et quatre mutants de preuve
ne sont pas ajoutés aux 1 691 historiques.

L'archive neuve contient **1460 fichiers `app/` identiques** à
`be9e3a8a0bdbc246659ccde4f286a2a91e2cbab3`. Les argv Flask/navigateur réellement exécutés et
l'inspection Docker des serveurs établissent les montages readonly ; les dépendances
existantes sont montées readonly séparément. Deux `barrier-armed → barrier-enter
→ barrier-observed-real-close` avec raison `native-transitionend`, puis les deux
timeouts attendus. Aucun checkout Git déplacé, aucune archive ou dépendance
partagée modifiée, aucune installation.

Les six modes sont exécutés, et leur wiring est aussi inspecté. Les copies
native/probe/historical diffèrent de la référence seulement par la garde ROOT.
Les trois programmes de comparaison générés sont identiques octet pour octet
à la référence. Sélection, montages, noms/propriété des conteneurs, collisions
et nettoyage sont inchangés. **1045 sources app hors docs :
1044 inchangées, seul le lanceur modifié.** Les JS causaux,
`choose` et `waitForNativeSelection`, le runner historique et les fixtures
communes gardent leurs empreintes initiales.

Une seule comparaison complète, **1 691/1 691** : les mêmes 18 sélections,
1 091 IDs Python et 600 triplets frontend fichier/nom/index exacts, zéro
nouvel ID, skip, échec ou annulation. **70 + 26** voisins distincts, sans
chevauchement avec les 1 691 ; leur rejeu via `compare-neighbors` vérifie le
mode séparé et n'est pas additionné au total. Détail des commandes Docker,
images existantes, versions/empreintes, temps de chaque sélection et IDs dans
le relevé. Réseau externe coupé, checkout/rootfs readonly, environnement vidé,
PostgreSQL/Flask/peers synthétiques possédés, ressources séquencées.

### Commandes corrigées, éprouvées le 10 octobre

Depuis `/opt/platform/fridadev`, avec les images/dépendances existantes et des
racines **initialement absentes** possédées. Ces argv sont ceux réellement
exécutés le 10 octobre. Après nettoyage, leurs noms sont libres ; s'ils sont
occupés au prochain rejeu, choisir un nouveau suffixe en gardant le préfixe,
sans supprimer ni réutiliser une racine étrangère. Exécutions séquencées.
Les deux mutants et l'archive doivent retourner 1 **et** atteindre leurs
barrières ; le programme `execute_p3.py` archivé dans `proof_programs` vérifie
ces conditions immédiatement avant de poursuivre. Aucun exit 1 de setup ne
compte comme rouge causal.

Les négatifs sont présentés séparément : capturer leur exit même en shell
`errexit`, puis vérifier les traces avant toute autre livraison. Les deux
positifs doivent sortir 0 ; toute autre valeur bloque également la suite.

```bash
set -euo pipefail
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010 probe completed
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010 probe pending
```

```bash
set -euo pipefail
p3_exit=0
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010 probe no-wait || p3_exit=$?
test "$p3_exit" -eq 1
python3 - <<'PY'
import json
from pathlib import Path
root=Path('/tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010')
reports=list(root.glob('fix-no-wait-*.json')); assert len(reports)==2
assert (root/'no-wait-browser.log').read_text().count('selection-wait-returned-before-real-GET-release')==2
for p in reports:
 x=json.loads(p.read_text()); k=[e['kind'] for e in x['events']]
 assert not x['complete'] and not x['errors'] and not x['captureErrors']
 assert k.count('barrier-armed')==1 and 'real-GET-held' in k
 assert k.index('wait-return')<k.index('GET-release-independent-of-click')
PY
```

```bash
set -euo pipefail
p3_exit=0
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010 probe old-click || p3_exit=$?
test "$p3_exit" -eq 1
python3 - <<'PY'
import json
from pathlib import Path
root=Path('/tmp/fridadev-obs-m7-ui-01-fix-replay-p3-20261010')
reports=list(root.glob('fix-old-click-*.json')); assert len(reports)==2
assert (root/'old-click-browser.log').read_text().count('Timeout 10000ms exceeded')==2
for p in reports:
 x=json.loads(p.read_text()); k=[e['kind'] for e in x['events']]
 assert not x['complete'] and not x['errors'] and not x['captureErrors']
 assert k.count('barrier-armed')==1 and 'wait-return' not in k
 assert k.index('closed-before-wait')<k.index('old-click-call')
PY
```

```bash
set -euo pipefail
p3_exit=0
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-archive-replay-p3-20261010 historical after-transition || p3_exit=$?
test "$p3_exit" -eq 1
python3 - <<'PY'
import json
from pathlib import Path
root=Path('/tmp/fridadev-obs-m7-ui-01-fix-archive-replay-p3-20261010')
reports=list(root.glob('after-transition-phone-*.json')); assert len(reports)==2
assert (root/'after-transition-browser.log').read_text().count('Timeout 10000ms exceeded')==2
for p in reports:
 x=json.loads(p.read_text()); k=[e['kind'] for e in x['nodeEvents']]
 assert k.index('barrier-armed')<k.index('barrier-enter')<k.index('barrier-observed-real-close')
 assert any(e['kind']=='barrier-observed-real-close' and e.get('reason')=='native-transitionend' for e in x['nodeEvents'])
PY
```

Modes voisins, exécutés séparément après ces contrôles. `compare` inclut les
18 sélections exactes (1 691 identités) et les 70 + 26 voisins séparés ;
`compare-neighbors` vérifie leur mode séparé sans redécouvrir ni rejouer les
1 691. Ce dernier rejeu de 96 est distinct, jamais ajouté au total historique.

```bash
set -euo pipefail
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-native-p3-20261010 native p3-native
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-neighbors-p3-20261010 neighbors
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-compare-p3-20261010 compare
python3 app/tests/support/run_obs_m7_ui_01_fix.py /tmp/fridadev-obs-m7-ui-01-fix-compare-neighbors-p3-20261010 compare-neighbors
```

Les noms de test, IDs et cardinalités exacts sont validés par le driver conservé,
pas déduits d'un seul exit 0. La reproduction complète doit conserver la même
validation et les contrôles de nettoyage avant commit ; aucune commande Git de
livraison n'est chaînée aux négatifs.


## DOCS

Erratum daté du 10 octobre dans le rapport du correctif du 9 octobre : anciens
exemples retirés comme commandes reproductibles, résultats historiques conservés.
La même roadmap, les contrats M7/M8-C et le hub renvoient au présent relevé ;
aucun index concurrent, aucune clôture globale M8-C.

## RISKS

Les branches après un rouge causal ne sont pas validées par ce rouge. Les
positifs et groupes natifs les parcourent séparément. Aucun incident historique
n'est effacé, aucune cause exacte des incidents du 7 octobre n'est inventée.
AUD-01/AUD-02 et concurrence M7 restent fermés. M4, runtime, Writer et clôture
globale M8-C restent distincts. Aucun M8-S/M8-A, installation, rebuild/restart,
déploiement ou appel OpenRouter/DAV réel ; arrêt après la seule livraison Git.


Auto-audit ciblé : refus avant tout effet dans les six modes ; aucune validation
interne divergente ; dix argv de lanceur publiés retrouvés dans les métadonnées
exécutées (dont le rouge initial explicitement qualifié) ; barrières et erreurs
causales exigées ; aucun assert/JS/fixture modifié. Les anciens JSON/gzip et
programmes restent vérifiés par empreinte. Aucun incident de lancement,
collecte ou nettoyage supplémentaire dans les exécutions de preuve ; le premier
rouge est conservé. Les statuts historiques et actuels sont datés, seul ce P3 est fermé.

Incident auxiliaire de relecture conservé : une recherche de clé historique
`current/collect_fix.py` a donné `KeyError`, exit 1 en 0,161417015 s ; la clé
correcte `collect_fix.py` a ensuite permis de vérifier la même empreinte. Sortie
brute originale transmise par le relecteur dans `incidents` du relevé ; aucun
horodatage UTC propre à sa commande capturé. Ce n'est pas un test du lot ni une
relance fonctionnelle ; aucun incident de preuve n'est masqué par cette correction.

Relecture indépendante `p3_review` : source, diff utile, programmes, métadonnées,
bruts, barrières, comptes, documentation et nettoyage. Le lecteur n'exécute
aucun test ou Docker ; son avis ne constitue pas un nouveau rejeu Codex. Les
premières lectures ont confirmé la garde et le bornage des suppressions ; avis
final favorable, aucun finding vivant retenu. Lecture de 117 empreintes
d'exécution, 54 runner records, 45 programmes, 12 traces et dix argv publiés ;
portée exacte et limites conservées dans le relevé. Le lecteur a constaté les
sept racines d'exécution absentes ; retrait du pilotage et contrôles Git finaux
restaient des conditions de livraison, attestées ensuite par Celebrimbor.

Nettoyage vérifié : les sept racines d'exécution, leurs copies, archives,
captures non retenues et sockets sont supprimées après conservation durable et
comparaison des manifestes exacts. Les conteneurs possédés sont absents. La
racine temporaire de pilotage est retirée après conservation de ses programmes
et résultats, avant commit ; cette dernière disparition est aussi attestée dans
le relevé. Aucun chemin préexistant ou étranger supprimé, caches partagés montés
readonly et trois empreintes de dépendances inchangées. Les 32 conteneurs
opérateur conservent nom, ID, image, démarrage et redémarrages ; quatre images
locales de preuve inchangées. Aucune mutation du runtime opérateur.

Contrôles précommit bloquants : inventaire exact des neuf chemins du lot,
empreintes de toutes les autres sources/archives suivies, syntaxe sans pycache,
liens locaux, commandes publiées réellement exécutées, traces et nettoyages,
relecture du diff utile et `git diff --check`. Les branches sont comparées à la
capture initiale ; seul M8-C avance lors de la livraison autorisée. Tout échec
interdit commit/push. Le hash complet, son parent `2fd60c48…`, le push et l'égalité
HEAD/upstream/distant 0/0 sont fournis dans le retour Git final, sans auto-référence
du relevé. Arrêt après cette livraison pour contre-audit Codex.
