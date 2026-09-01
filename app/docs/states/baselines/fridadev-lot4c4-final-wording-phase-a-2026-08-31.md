# Lot 4C.4 — Diagnostic causal final v2.4/v2.5

Date: 1 septembre 2026
Statut: 4C.4 ferme `inconclusive`; decision `keep_current_v2.3`; F4 `partiel`; `surface_only_v1` rejetee et inactive
Portee: diagnostic causal v2.3, candidate v2.4, replication v2.5 et decision produit sans correction runtime
Exclusions: runtime actif, prompts actifs, modeles, settings, frontend et donnees operateur

## Decision v2.3

V2.2 est supersede avant toute generation: son unique GET de metadonnees a
retourne HTTP 200, cinq endpoints et zero route compatible, puis le runner
s'est arrete avant POST, inference, campagne ou cout. Le payload envoyait
encore `stop`, tandis que le preflight exigeait aussi des sorties structurees
sans envoyer `response_format`; ces deux exigences etaient artificielles.

V2.3 retire seulement `stop` du payload et limite les capacites requises a
`reasoning` et `max_tokens`, les deux parametres effectivement envoyes et
routes. Modele `openai/gpt-5.1`, reasoning `high` exclu, plafond `8192`,
timeout `900`, `allow_fallbacks=false`, `require_parameters=true`, absence de
sampling, retry, Batch, Flex et Priority restent inchanges. Corpus, messages,
scorer, seuils et calendrier `24 + 12 = 36`, avec canari en sequence 1, gardent
leurs empreintes.

Le gel autoritatif devient
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_3.json`.
Cette passe n'execute aucun GET ou POST provider et coute zero. V2.3 attend un
nouveau GO provider separe; F4 n'est pas classe et 4C.4 reste ouvert.

Les preuves ciblees v2/v2.1/v2.3 passent `27/27`, les tests cibles du client
OpenRouter `2/2`, et le dry-run reste `ready_offline` avec `36` appels,
budget `3.58238925 USD` et cap absolu `4.00 USD`. Aucune suite Python complete,
JavaScript ou Chromium n'est executee.

## Ratification humaine content-free de la campagne v2.3

Tof confirme et ratifie explicitement la notation assistee realisee par Codex:

- `36/36` appels provider valides;
- contre-cas adequats `12/12`;
- amelioration de delicatesse cote traitement `5/12`;
- amelioration generale de formulation cote traitement `6/12`;
- deux defaillances critiques cote traitement.

La decision humaine autoritative est F4 `partiel`: l'effet causal de la
directive derivee est reel et utile, mais sa traduction finale est
insuffisamment bornee. Cette section consigne la ratification content-free de
Tof; elle ne pretend pas reconstruire cryptographiquement le paquet aveugle,
les reponses ou le mapping v2.3, supprimes apres ratification conformement au
protocole. Les 36 appels v2.3 ne doivent jamais etre rejoues.

4C.4 reste ouvert pour une unique candidate benchmark-only, strictement
expressive et non active. Sa qualification reduite exige un nouveau gel Git,
une campagne separee de 24 appels maximum et une nouvelle notation/ratification
avant tout cutover runtime. 4O.Z et les lots suivants restent non commences.

## Candidate bornee v2.4 — non active

Les six hypotheses sont confirmees au HEAD du gel. Le regime epistemique
supprime `stimmung_input` avant son calcul; la posture produit separement
`delicate_expression/stimmung/affective_transition`; Validation conserve cette
separation. La perte de borne se situe dans la traduction finale active de
`chat_prompt_context.py`: elle permet encore une prudence de formulation et ne
pose ni priorite exhaustive du fond, ni budget expressif ferme, ni repli no-op.
Les goldens anterieurs verrouillent le raccord, Presence, les final locks et
les enveloppes, mais ne suffisent pas a garantir l'integrite semantique de la
reformulation; la ratification v2.3 en a observe deux violations critiques.

La candidate unique porte l'identite `surface_only_v1`. Son contrat ferme:

- subordonne tout effet a la demande, aux faits, preuves, hard guards et au
  regime epistemique, avec reponse directe avant ajustement dialogique;
- permet seulement choix lexical, connecteurs et rythme, a longueur comparable
  et avec au plus une breve reprise dialogique;
- preserve reponse demandee, faits, sources, hypotheses, inferences,
  conclusions, actions, certitude et regimes de preuve;
- interdit ajout ou retrait de proposition, reserve, raison ou conclusion,
  diagnostic, conseil non demande, attribution psychologique et masquage de
  question, demande, risque ou action;
- impose le no-op si l'ajustement risque d'atteindre le fond.

Le texte exact n'est pas recopie dans ce rapport: il est construit depuis le
contrat ferme, borne a 900 caracteres, puis pince avec sa version et son
SHA-256 dans
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_4.json`.
Il n'est pas injecte dans le runtime actif. Aucun caller, agregateur, contrat
Validation, modele, parametre, guard, signal Stimmung brut ou branche `none`
n'est modifie.

L'observabilite active transporte `enunciation_effect` de l'evenement aux
read-models et aux deux renderers, sans identite de politique. Le gel declare
donc `surface_only_v1` comme identite content-free future et explicitement
inactive. Si la campagne, la notation et la ratification autorisent un cutover,
sa propagation devra etre atomique sur evenement, garde, reader,
read-model/API et renderers, sans prompt, reponse, tonalite, raisonnement ou
dialogue brut.

## Protocole reduit v2.4

Le corpus v2 et ses faits provider-visibles restent inchanges. Seuls les six
cas `transition_delicate` sont programmes: consigne runtime courante contre
candidate bornee, deux repetitions et ordre A/B contrebalance, soit exactement
`6 x 2 x 2 = 24` appels. Les six contre-cas ne sont pas rappeles: le test
compare byte-for-byte leur construction v2.3 et courante et leur resultat
ratifie `12/12` reste autoritatif.

Le runner, le transport OpenRouter partage, le preflight, le canari en sequence
1, les checkpoints atomiques, la politique de reprise et le workflow aveugle
sont reutilises. Modele `openai/gpt-5.1`, reasoning `high` exclu,
`max_tokens=8192`, timeout `900`, `allow_fallbacks=false` et
`require_parameters=true` restent inchanges; aucun sampling, stop, retry,
fallback, Batch, Flex, Priority, Validation, Stimmung ou modele juge n'est
ajoute. Le plafond calcule est `2.17482500 USD`, le budget avec marge
`2.39230750 USD` et le cap absolu `3.00 USD`.

Le scorer compare uniquement candidate et consigne active. Psychologisation,
changement de certitude, verite ou preuve et cible masquee sont critiques; une
seule occurrence cote candidate force `fail`. Les sorties synthetiques ne
peuvent produire aucun verdict provider. Une campagne complete s'arrete a
`human_rating_required`, avant notation, deblindage ou decision. La candidate
reste non active et 4C.4 ouvert jusqu'a notation et ratification separees.

Les preuves hermetiques du gel passent `34/34` sur candidate, corpus,
protocole, runner, reprise, paquet, notation et historique v1-v2.3, puis
`120/120` sur les goldens 4C.3/4C.4, Stimmung, doctrine, Validation, payload,
manifest et observabilite. Elles rejettent notamment derive du contrat ou de
son empreinte, signal Stimmung brut, modification des gardes provider, branche
`none` rappelee, cap superieur a 24/3 USD et acceptation d'une seule defaillance
critique. Le dry-run annonce `24` appels, `12` comparaisons, budget
`2.39230750 USD`, cap `3.00 USD` et `provider_campaign_required`. Aucun appel
provider, rebuild, restart, deploiement ou changement runtime n'est effectue
pendant le gel.

## Replication GPT-5.2 v2.5 — candidate toujours inactive

V2.5 repete exactement la comparaison causale v2.4 avec une variable unique:
le payload remplace `openai/gpt-5.1` par `openai/gpt-5.2`. Un adaptateur etroit
importe les constructeurs, validateurs et runner v2.4; il ne recopie ni
calendrier, corpus, messages, candidate, scorer, checkpoints ni paquet aveugle.
Les 24 messages et l'ordre A/B gardent leurs empreintes v2.4, et la candidate
reste `surface_only_v1`, SHA-256
`72d7b887b49f0e8d7d3e2ff0ba91a65e2772448f885f03455ffbd47f45b2d143`,
inactive dans le runtime.

Le profil force `reasoning={effort: high, exclude: true}` et conserve
`max_tokens=8192`, timeout `900`, l'absence de sampling et de `stop`, ainsi que
`allow_fallbacks=false` et `require_parameters=true`. Aucun retry, fallback,
Batch, Flex, Priority, contre-cas, Validation, Stimmung ou modele juge n'est
autorise. Une provenance observee GPT-5.1 ne peut pas satisfaire le ledger
GPT-5.2.

Avant le premier POST, le preflight relit les endpoints du slug exact et la
fiche modele OpenRouter content-free. Il exige une route annoncant `reasoning`
et `max_tokens`, l'effort `high`, au moins `400000` tokens de contexte,
`128000` de sortie maximale et les prix geles `1.75/14 USD` par million de
tokens input/output. Le calendrier reste `6 x 2 x 2 = 24`, avec le canari en
sequence 1. Le plafond calcule est `3.04475500 USD`, le budget avec marge
`3.34923050 USD` et le cap absolu `4.00 USD`.

Le manifest autoritatif est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_5.json`.
Les preuves hermetiques v2.5 couvrent variable unique, effort `high`, prix et
capacites, refus de provenance GPT-5.1, reutilisation du runner et arret
synthetique a `human_rating_required`: `7/7` preuves v2.5 et `50/50` sur
l'ensemble cible v1-v2.5, dans l'image applicative locale, checkout read-only,
reseau coupe et `/tmp` en tmpfs. Le dry-run annonce `24` appels, budget
`3.34923050 USD`, cap `4.00 USD` et `provider_campaign_required`. Le commit et
le push du gel precedent obligatoirement tout POST. La campagne autorisee
s'arrete au paquet aveugle: notation, deblindage, decision, cutover et
fermeture de 4C.4 restent separes.

Aucun runtime actif, prompt, setting, frontend ou observabilite produit n'est
modifie. Aucun rebuild, restart ou deploiement n'est effectue; 4O.Z et les lots
suivants restent non commences.

## Finalisation ratifiee v2.4/v2.5

Les deux campagnes reduites sont completes, notees puis ratifiees. Le workflow
offline a valide les empreintes exactes, deblinde seulement apres ratification,
ecrit et relu les artefacts durables content-free, puis supprime les deux
espaces temporaires prives et de revue. Aucun appel provider supplementaire
n'a ete execute pendant cette finalisation.

| Campagne | Modele | Delicatesse | Formulation | Defaillances critiques | Decision | Cout observe |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| v2.4 | `openai/gpt-5.1` | 4/12 | 6/12 | 3 | `fail` | 0.389553 USD |
| v2.5 | `openai/gpt-5.2` | 4/12 | 5/12 | 5 | `fail` | 0.25418820 USD |

Les deux series ont `24/24` sorties valides, `12/12` comparaisons notees et
zero dimension non notee. GPT-5.2 ne sauve donc pas la candidate: il conserve
le meme faible gain de delicatesse, reduit le gain de formulation et augmente
les defaillances critiques. L'echec n'est pas imputable au seul GPT-5.1; la
politique `surface_only_v1` n'est pas une correction robuste.

Les artefacts autoritatifs sont:

- `benchmark/results/stimmung/2026-09-01-lot4c4-final-wording-v2-4-gpt-5-1.json`,
  SHA-256 `7bcfd7f15b7941a3b1257594c3c0f694148a3aa4e1a3c4daba6cf1e182cdd2be`;
- `benchmark/results/stimmung/2026-09-01-lot4c4-final-wording-v2-5-gpt-5-2.json`,
  SHA-256 `4a6b0f6f1f38c6917a3dfd50ceeb992ca6a61a4ce1c20afcfaefcfdc3a6dc5da`.

F4 reste `partiel`: Stimmung produit parfois un benefice de formulation, mais
la candidate evaluee ne separe pas ce benefice des dommages au fond. La decision
humaine de Tof est `keep_current_v2.3`: conserver la consigne active et prendre
le dialogue quotidien comme epreuve qualitative principale de son effectivite.
Les benchmarks restent des gardes diagnostiques et ne remplacent pas le
dialogue. La frontiere active conservee est
`app/core/chat_prompt_context.py`, SHA-256
`9781ee92cf7f779debec0d11a9d6487278083824f3a77c3d9b7d17c7c3aaa169`,
identique dans le checkout et le conteneur. 4C.4 est donc ferme `inconclusive`,
sans cutover ni changement du
runtime, du prompt actif, du modele actif, de l'observabilite produit ou du
frontend. Une nouvelle candidate ou campagne ne constitue pas la continuation
automatique de ce micro-lot et exige une decision distincte. 4O.Z reste non
commence.

## Archive Phase A v2.2 supersedee

## Decision v2.2

La campagne v2.1 autorisee depuis
`ce320fa3acda1caf562948dc6f64f554f5490c59` s'est terminee
`campaign_incomplete`: les 36 requetes ont recu HTTP 404, aucune inference n'a
eu lieu et le cout provider observe est nul. Le ledger conserve
`3.25671750 USD` comme comptage conservateur de tentatives, pas comme cout
facture. Les preuves historiques sous
`/tmp/lot4c4-final-wording-v2.1-ce320fa3acda-private` restent intactes; cette
campagne n'est ni relancee ni reutilisable.

La cause deja etablie est bornee: le payload v2.1 exigeait
`temperature=0.7`, `top_p=1.0` et `require_parameters=true`, alors qu'aucun
endpoint GPT-5.1 annonce les deux parametres de sampling. V2.2 retire uniquement
`temperature` et `top_p`. Modele `openai/gpt-5.1`, raisonnement `high` exclu,
`max_tokens=8192`, timeout `900`, sorties structurees,
`allow_fallbacks=false`, `require_parameters=true`, messages, corpus, scorer,
notation et seuils restent inchanges.

Avant toute future generation, le runner interroge seulement l'endpoint de
metadonnees exact du modele. Sa synthese content-free exige au moins une route
annoncant reasoning, sorties structurees/response format, `max_tokens` et
`stop`, sans exposer endpoint, secret ou reponse brute. Sans route compatible,
la campagne s'arrete avant tout POST. Le client live ne charge plus le
catalogue generique de prix avant ce preflight.

La sequence 1 des 36 sert de canari, sans appel supplementaire. Si elle est
valide, les 35 restantes suivent automatiquement. Une erreur 401/403 devient
`provider_auth_error`, une 404 de routage `provider_routing_error`, une autre
4xx invalide `provider_request_error`; chacune arrete immediatement un canari
sans retry, paquet ou notation. `transport_error` est reserve aux erreurs
reseau, DNS, connexion et exceptions de transport.

Le gel autoritatif est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_2.json`.
Il pince le client OpenRouter, les modules v2 existants, les gels historiques,
le corpus et le calendrier inchange de 36 appels. Cette passe a execute zero
appel provider et coute zero. V2.2 attend un nouveau GO provider separe; F4
n'est pas classe et 4C.4 reste ouvert.

Commande offline de controle:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_execution_v2 \
  --repo-root "$PWD" \
  --freeze-commit <commit-v2.2-pousse> \
  --dry-run
```

Les six reproductions v2.2 ont d'abord produit neuf echecs et une erreur sur
le comportement v2.1: sampling present, preflight absent ou ignore, 404 classe
transport, poursuite apres canari invalide et historique manquant. Les memes
six preuves sont vertes apres correction, y compris route faussement
compatible refusee et canari valide suivi d'exactement 35 autres sequences.
Les suites v1/v2/v2.1 voisines, les tests de reprise/provenance et les six
preuves v2.2 passent ensemble `36/36`; les tests cibles du client OpenRouter
passent `2/2`, hermetiquement et sans reseau. Le
dry-run final annonce exactement `36` appels, budget `3.58238925 USD` et cap
absolu `4.00 USD`. Aucune decouverte Python complete, suite JavaScript ou
Chromium n'est executee dans cette passe ciblee.

## Archive Phase A v2.1 supersedee

### Decision v2.1

La Phase A v2 livree par
`9d6b66be05fb89561961deaa4d64f6acbbb42e48` est supersedee avant tout appel
provider. Son corpus, son calendrier de 36 appels, son scorer et ses parametres
restent valides, mais son runner n'enregistrait rien durablement avant le 36e
retour, supprimait le repertoire de preuve sur exception et acceptait
`codex_for_tof` sous la provenance mensongere `delegated_human_review`. Paquet
aveugle et mapping prive partageaient aussi le meme repertoire. V2 ne porte
aucun resultat provider.

V2.1 est le protocole autoritatif. Il ne classe toujours pas F4: la decision
reste `provider_campaign_required`, 4C.4 reste ouvert et les 36 appels exigent
un GO provider separe. Zero appel provider reel n'a ete execute pendant cette
passe.

## Journal durable et reprise

Le runner conserve le calendrier v2 et ajoute une machine d'etat fermee par
sequence: `planned`, `attempt_started`, `completed` et
`attempt_outcome_unknown`. Le ledger content-free est ecrit en `0600`, avec
flush, `fsync`, remplacement atomique depuis le meme repertoire et `fsync` du
repertoire. `attempt_started` est durable avant la frontiere externe; le
resultat prive necessaire a la notation est ensuite checkpointé separement,
puis le resultat content-free `completed` est ecrit sans attendre le 36e
appel.

Une reprise exige exactement le meme protocole, commit de gel, corpus,
calendrier, modele, parametres et empreintes. Elle saute toute sequence
`completed`. Une sequence restee `attempt_started` devient
`attempt_outcome_unknown`, n'est jamais rappelee, compte dans les 36 tentatives
et consomme son plafond de cout calcule. La campagne devient alors
`campaign_incomplete`; elle ne construit aucun paquet, n'accepte aucune note
et ne produit aucune decision semantique. Les checkpoints ne sont jamais
supprimes sur `Exception`, `KeyboardInterrupt` ou autre interruption.

Le compteur et le cout sont recalcules depuis les 36 enregistrements, jamais
depuis l'invocation courante. Le 37e essai et tout cout cumule superieur au cap
de `4.00 USD` sont refuses. Pour le chemin live, les repertoires prive et de
revue ont des noms uniques derives du commit de gel; choisir simplement un
autre chemin ne permet pas de repartir a zero.

Cette garantie n'est pas un exactly-once provider: OpenRouter ne fournit pas
ici de cle d'idempotence. Une coupure apres envoi peut donc laisser le resultat
inconnu. V2.1 garantit seulement qu'une sequence durablement marquee commencee
n'est jamais rappelee. Une suppression volontaire des preuves temporaires par
un operateur reste hors de la garantie du runner et rendrait la campagne
inauditable; le runner lui-meme ne les supprime jamais avant finalisation
valide.

## Provenance de notation et ratification

Les seules provenances de revue non synthetiques sont maintenant:

- `tof_human_review`, avec `rater_id=tof`, qui satisfait directement la
  condition humaine si le paquet et les 24 notes sont complets;
- `codex_assisted_review_for_tof`, avec `rater_id=codex_for_tof`, qui n'est
  jamais nommee revue humaine et s'arrete a `human_ratification_required`.

La seconde voie exige avant deblindage une ratification creee hors runner:
`ratifier_id=tof`, empreintes exactes du paquet et du fichier de notes, puis
decision fermee `accept` ou `refuse`. Un refus conserve les preuves et ne
deblinde rien. Une acceptation valide permet seulement alors de charger le
mapping, scorer et finaliser. `delegated_human_review`, un agent se declarant
humain, une mauvaise empreinte ou une notation partielle sont rejetes. Les
tests `synthetic_test` restent explicitement synthetiques et ne peuvent jamais
produire de verdict provider.

## Paquet remis au notateur

L'espace prive de campagne `0700` contient le ledger, les sorties privees et
`blind_mapping.json`. Un second repertoire `0700`, qui peut etre remis sans
donner acces au premier, contient initialement uniquement
`rating_packet.json`. Ce paquet expose le dialogue synthetique, A/B ou
`single`, les sorties et la grille; il ne contient ni bras actif, ni variante,
ni directive, ni mapping. Les deux espaces sont lies par SHA-256.

Cet aveuglement est organisationnel et cryptographiquement lie, non une
isolation forte contre un operateur qui choisirait volontairement de lire les
deux repertoires. Apres readback valide de l'artefact durable content-free, les
sorties brutes, le paquet et le mapping sont supprimes; jamais avant.

## Gel et commande future v2.1

Le manifest autoritatif est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_1.json`.
Il pince les trois modules, le corpus v2, le manifest v2 historique, les
entrees produit, la machine de reprise et les mutations v2.1. Le manifest v2
reste immuable dans Git mais n'est plus courant.

Apres un GO separe et seulement depuis le commit v2.1 pousse, les deux chemins
doivent reprendre les douze premiers caracteres du commit de gel:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_execution_v2 \
  --repo-root "$PWD" \
  --freeze-commit <commit-v2.1-pousse> \
  --execute-live \
  --output-dir /tmp/lot4c4-final-wording-v2.1-<commit12>-private \
  --review-export-dir /tmp/lot4c4-final-wording-v2.1-<commit12>-review
```

Une reprise emploie exactement la meme commande et ajoute `--resume`. Aucune
commande live n'a ete executee pendant cette Phase A v2.1.

Apres `human_rating_required`, le notateur recoit seulement le repertoire de
revue et cree `ratings.json` en `0600`. La finalisation offline emploie:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_rating_v2 \
  --campaign-dir /tmp/lot4c4-final-wording-v2.1-<commit12>-private \
  --rating-packet /tmp/lot4c4-final-wording-v2.1-<commit12>-review/rating_packet.json \
  --ratings /tmp/lot4c4-final-wording-v2.1-<commit12>-review/ratings.json \
  --durable-output benchmark/results/stimmung/<date>-lot4c4-final-wording-v2.1.json
```

Pour `codex_assisted_review_for_tof`, cette premiere invocation rend seulement
`human_ratification_required`. Tof cree ensuite le petit JSON content-free de
ratification, hors runner provider, et relance la meme commande avec
`--tof-ratification <chemin-ratification-tof>`. Aucun mapping n'est charge
avant la validation de cette ratification.

## Preuves v2.1

- reproductions rouges initiales: `8` tests, `11` erreurs attendues avant
  implementation; elles montraient l'absence d'API de reprise, d'export
  separe, d'ecriture atomique et de ratification;
- deux sensibilites supplementaires ont ete ajoutees pendant le contre-audit:
  retour provider sans checkpoint final et cumul du cap de cout apres reprise;
- les `10` tests v2.1 couvrent les quatre fenetres de crash, exception Python,
  `KeyboardInterrupt`, preservation des preuves, reprise sans rappel, cap de
  36 appels et `4 USD`, gel change, atomicite, faux humain, ratification,
  deblindage et export sans mapping;
- baseline avant patch: Python `2848/2848`, JavaScript `140/140`, Chromium
  `19/19`;
- protocole historique v1 et v2 courant avant les preuves v2.1: `20/20`; avec
  les dix preuves v2.1: `30/30`;
- suites Stimmung, campagnes et goldens historiques: `101/101`;
- doctrine, Validation et payload principal: `149/149`;
- Presence, final locks, capsule, manifest, JSON/streaming, persistance et
  observabilite voisine: `186/186`;
- decouverte Python complete apres patch: `2858/2858` en `735.657 s`, soit
  exactement les `2848` tests de baseline plus les `10` nouvelles preuves;
- JavaScript et Chromium n'ont pas ete relances apres patch: aucun asset
  frontend n'a ete touche et leurs baselines restent `140/140` et `19/19`;
- aucune preuve n'utilise un provider, un secret ou une DB operateur.

La dette de taille reste explicite: le harness v1 historique n'est pas
agrandi, mais les modules v2.1 atteignent respectivement `919` lignes pour le
protocole, `941` pour l'execution et `1014` pour la notation/finalisation. La
passe conserve leurs responsabilites existantes et n'introduit ni framework
generique ni refactor de taille hors du correctif; une reduction ulterieure ne
pourrait etre engagee que dans un lot borne distinct.

## Archive Phase A v2 supersedee

### Decision v2

Le protocole v1 livre par le commit
`d31df3be0fbae632e084359955cf6ad86c753748` est supersede avant toute campagne.
Il n'a produit aucun appel ni resultat provider. Ses fichiers restent
byte-for-byte inchanges et continuent de documenter l'historique Git; ils ne
constituent plus le protocole autoritatif.

La Phase A v2 corrige les defauts de protocole sans classer F4. La decision
reste `provider_campaign_required`: les fakes prouvent le raccord, mais seule
une campagne du modele principal actif suivie d'une notation humaine aveugle
peut mesurer l'effet final. Le runner v2 est executable, mais offline par
defaut et inutilisable en live sans `--execute-live`, commit pousse exact,
worktree propre et repertoire temporaire explicite sous `/tmp`.

Zero appel provider a ete execute pendant cette passe corrective. 4C.4 reste
ouvert jusqu'au GO separe, aux 36 appels eventuels, puis a la notation humaine
deleguee separement a Codex pour Tof et a la finalisation content-free.

### Baseline corrective v2

- racine et toplevel Git: `/opt/platform/fridadev`;
- branche `main`; HEAD local, upstream et distant
  `d31df3be0fbae632e084359955cf6ad86c753748`; divergence `0/0`; worktree
  propre avant patch;
- 4C.3 ferme; 4C.4 ouvert apres Phase A v1; aucun resultat provider 4C.4;
  4O.Z et les lots suivants non commences;
- Python `2837/2837`, JavaScript `140/140`, Chromium `19/19` avant patch;
- runtime inchange: image
  `sha256:be0e5d4abb0f923e51d92ec2c83c14b528c2572f7a9506ec78ce35ce1edeb2e7`,
  `StartedAt=2026-08-31T11:53:13.70842987Z`, HTTP interne `200`, healthy,
  restart `0`, OOM false;
- settings live non secrets: `openai/gpt-5.1`, `temperature=0.7`,
  `top_p=1.0`, `response_max_tokens=8192`, raisonnement `high`; timeout du
  caller principal `900 s`.

### Findings correctifs C1 a C6

- C1 valide: les douze bases factuelles v1 n'etaient jamais ajoutees aux
  messages. Tous les cas provider v2 possedent des faits litteraux relies par
  `source/index` a un message effectivement transmis. Les cas 001 a 012
  exposent respectivement: faits independants et preuve invalidee; resultat
  negatif; operandes; trois points a recapituler; cause reproduite; affect
  cite; affect rapporte; preuve sourcee; paragraphe a reecrire; risque; contenu
  de brouillon et interdiction de mutation; mesures et absence de controle.
- C2 valide: v1 produisait douze pseudo-paires byte-for-byte identiques sur
  les six contre-cas. V2 ne compare que les six transitions et execute un seul
  bras runtime actif par contre-cas.
- C3 valide: v1 annoncait une notation aveugle sans paquet, mapping, ingestion
  ni nettoyage. V2 livre ces quatre etapes, avec validation transactionnelle.
- C4 valide: le CLI v1 ne possedait aucun chemin live. V2 fournit un runner
  borne qui reutilise `benchmark.core.openrouter.OpenRouterClient`; aucune
  execution n'a lieu sans flag explicite et preflight du gel pousse.
- C5 valide: `estimated_max_cost_usd` etait en realite un plafond majore. V2
  separe cout prompt calcule, plafond completion, plafond total calcule, budget
  avec marge et cap absolu.
- C6 valide: v1 etant deja pousse, il n'est pas reecrit. Le manifest v2 declare
  la supersession et pince separement corpus v1, corpus v2, builder historique,
  trois modules v2 et entrees produit.

### Corpus et calendrier v2

Le corpus autoritatif est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v2.json`.
Il derive explicitement du corpus v1 pince par SHA-256, sans recopier ses
attentes. Ses 14 cas gardent les familles et les souverainetes de stage v1.
Presence et le hard guard restent non eligibles au provider principal.

Chaque `factual_basis` v2 contient uniquement un identifiant, un literal deja
present et son emplacement `history[index]` ou `user`. Le validateur retrouve
ce literal dans les messages provider-visibles construits; il rejette un fait,
une liste ou un paragraphe retire. Cette metadata ne constitue ni canal cache
ni reponse attendue. Le corpus ne copie aucun prompt, ne fixe aucune sortie et
n'utilise aucune regex semantique.

Le calendrier est ferme a `36` appels:

- transitions `delicate_expression`: `6 cas x 2 bras x 2 repetitions = 24`;
- contre-cas runtime actifs: `6 cas x 1 bras x 2 repetitions = 12`;
- Presence et hard guard: `0` appel principal;
- total et cap absolu: `36`.

L'ordre A/B des transitions est contrebalance. Le paquet de notation ne porte
que A/B; le mapping controle/traitement est dans un fichier distinct. Les
contre-cas ont une sortie `single`, sans fausse attribution causale de leur
variance de decodage. Pour chaque paire causale, la normalisation prouve que
seule la directive d'enonciation autorisee differe; le signal Stimmung brut est
absent et la Continuity Capsule reste unique et terminale.

### Runner borne v2

Le module `benchmark.suites.stimmung.final_wording_execution_v2` construit le
protocole et le calendrier avant tout acces au client. Il impose:

- le seul modele `openai/gpt-5.1`, les parametres runtime actifs, le transport
  standard, `allow_fallbacks=false`, `require_parameters=true`;
- aucun retry, fallback, Batch, Flex, Priority, Validation, Stimmung ou juge;
- HEAD et upstream egaux au commit de gel pousse, worktree propre;
- `36` tentatives maximum et controle du cout avant chaque appel;
- classification fermee `valid`, `transport_error`, `timeout`, `refusal` ou
  `length`; une sortie absente n'est jamais un resultat semantique;
- repertoire vierge explicite sous `/tmp`, mode `0700`, fichiers `0600`;
- aucun paquet brut sous le checkout.

Dry-run hermetique:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_execution_v2 \
  --repo-root "$PWD" \
  --freeze-commit <commit-v2-pousse> \
  --dry-run
```

Commande future, uniquement apres GO separe:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_execution_v2 \
  --repo-root "$PWD" \
  --freeze-commit <commit-v2-pousse> \
  --execute-live \
  --output-dir /tmp/lot4c4-final-wording-v2
```

Le runner s'arrete ensuite avec `human_rating_required`. Il ne produit aucun
score semantique.

### Notation annoncee en v2

Le repertoire temporaire contient exactement le paquet aveugle, le mapping
cache et le ledger content-free. Le paquet fournit le dialogue synthetique,
les sorties A/B ou `single`, les statuts et la grille fermee; il ne contient ni
`control`, ni `treatment`, ni `variant`. Le ledger conserve seulement statuts,
route, finish reason, tokens, cout, longueurs et SHA-256.

Le notateur recoit uniquement `rating_packet.json`. Il rend un `ratings.json`
mode `0600`, portant le SHA-256 du paquet, les 24 identifiants et
`rating_source=delegated_human_review`. La notation est realisee dans une passe
separee par Codex pour Tof; le runner ne remplit jamais ce fichier. Une source
fake, provider, runner, agent generique, auto-declaree ou une grille partielle
est rejetee avant deblindage; l'identite explicite `codex_for_tof` reste admise
pour cette delegation.

Apres validation complete des notes, le finalizer joint le mapping, calcule les
compteurs, ecrit et relit l'artefact durable content-free, puis seulement alors
supprime paquet, mapping, ledger et notes temporaires:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_rating_v2 \
  --campaign-dir /tmp/lot4c4-final-wording-v2 \
  --ratings /tmp/lot4c4-final-wording-v2/ratings.json \
  --durable-output benchmark/results/stimmung/<date>-lot4c4-final-wording-v2.json
```

En cas de validation incomplete ou d'echec de readback durable, aucun materiel
temporaire n'est supprime. Les tests de cette Phase A utilisent uniquement des
sorties `SYNTHETIC_TEST_RESPONSE_*` et des notes `synthetic_test`; leur decision
reste obligatoirement `provider_campaign_required`.

### Scorer v2

Les transitions mesurent comparativement delicatesse, adequation,
psychologisation, certitude, verite/preuve et cible masquee. Les contre-cas
mesurent absolument adequation, precaution artificielle, psychologisation,
certitude, verite/preuve et cible masquee. Une faute `both` compte une fois par
dimension et item, jamais deux fois par bras.

Les seuils restent `0.80` pour l'amelioration de delicatesse et `0.75` pour
l'amelioration de formulation; les douze contre-cas doivent etre adequats,
avec zero precaution artificielle et zero faute critique. Presence et
l'autorisation d'appel ne sont jamais deduites du texte provider: elles restent
prouvees par les goldens fakes de leurs stages.

Les seules decisions sont `pass`, `fail`, `inconclusive`,
`human_rating_required` et `provider_campaign_required`. `pass` ou `fail`
exigent 36 tentatives, 36 sorties completes avec provenance exacte et 24 notes
humaines valides. Une preuve technique ou de notation incomplete donne
`inconclusive`; une simulation conserve `provider_campaign_required`.

### Cout v2

Prix publics OpenRouter revus le 31 aout 2026: `1.25 USD/M` token d'entree et
`10 USD/M` token de sortie. Sur les 36 payloads exacts:

- estimation prompt: `246078` tokens, soit `0.30759750 USD`;
- plafond completion: `294912` tokens (`36 x 8192`), soit `2.94912000 USD`;
- plafond total calcule: `3.25671750 USD`;
- budget avec marge de securite de 10%: `3.58238925 USD`;
- cap absolu: `4.00 USD`.

Ce budget n'est pas une estimation probable. Le runner additionne le cout
provider observe quand il existe, sinon le plafond calcule de l'appel, et
refuse l'appel suivant s'il depasserait le cap.

### Sensibilite v2

Les tests rejettent ou detectent: fait requis absent, liste/paragraphe retire,
pseudo-paire identique, retour a 48 appels, modele ou parametre modifie, retry
ou fallback, execution non autorisee, faux client presente comme provider,
depassement du cout, chemin brut dans le depot, mapping expose, notes partielles
ou fausse provenance, decision avant notes, contenu brut durable, nettoyage
avant validation, Presence tiree du texte, signal Stimmung brut et changement
d'un input pince. Le protocole v1 reste validable avec son ancien manifest,
mais son statut courant est explicitement supersede.

### Preuves correctives executees en v2

Tous les tests utilisent le checkout read-only, `--network none`, `/tmp` en
tmpfs et `PYTHONDONTWRITEBYTECODE=1`:

- baseline avant patch: Python `2837/2837`, JavaScript `140/140`, Chromium
  `19/19`;
- corpus, protocole, mutations, runner, paquet, notation et finalisation v2:
  `11/11`;
- protocole historique v1 et protocole v2 ensemble: `20/20`;
- suites Stimmung, campagnes et goldens historiques: `101/101`;
- doctrine, Validation et payload principal: `147/147`;
- Presence, final locks, capsule, manifest, JSON/streaming, persistance et
  observabilite voisine: `128/128`;
- decouverte Python complete apres patch: `2848/2848` en `458.239 s`, soit
  exactement les `2837` tests de baseline plus les `11` nouveaux tests v2;
- JavaScript et Chromium n'ont pas ete relances apres patch, conformement au
  perimetre: aucun asset frontend n'a ete touche; leurs baselines avant patch
  restent respectivement `140/140` et `19/19`.

### Limites v2

- F4 reste non classe et 4C.4 reste ouvert;
- aucun resultat provider n'est attache a v1 ou v2;
- la dette de taille n'est pas masquee: le harness v1 historique reste a
  `1379` lignes et les responsabilites v2 sont separees entre protocole
  (`878` lignes), execution (`498`) et notation/finalisation (`672`). Ce
  decoupage evite d'allonger v1 et ne constitue pas un framework generique;
  aucun refactor de taille supplementaire n'est engage dans ce micro-lot;
- aucun runtime, prompt, modele, setting, frontend ou donnee n'est modifie;
- aucun rebuild, restart ou deploiement n'est effectue;
- 4O.Z et tous les lots suivants restent non commences.

## Archive Phase A v1 supersedee

La suite de ce document conserve le rapport livre dans v1. Ses nombres de
`48` appels et `5.00 USD` sont historiques et ne doivent plus etre utilises
pour une campagne.

### Decision

La Phase A ne permet pas de classer F4 valide, invalide ou corrige. Les preuves
existantes demontrent que la directive derivee arrive correctement au modele
principal, mais une reponse assistant scriptable par le fake ne renseigne pas
son effet sur la formulation finale. La decision bornee est donc
`provider_campaign_required`.

Cette decision maintient 4C.4 ouvert. Une campagne reelle exige un GO separe de
Tof apres commit et push du present gel. Aucun appel provider reel n'a ete
execute pendant la Phase A.

### Baseline revalidee avant edition

- racine et toplevel Git: `/opt/platform/fridadev`;
- branche `main`; HEAD local, upstream et distant
  `d208d3e300bacfcb836d71e5adb8001384b32776`; divergence `0/0`; worktree
  propre;
- roadmap: 4C.3 ferme; 4C.4 ouvert et non commence; 4O.Z et les lots suivants
  non commences;
- Python `2828/2828`, JavaScript `140/140`, Chromium `19/19`;
- runtime inchange: image
  `sha256:be0e5d4abb0f923e51d92ec2c83c14b528c2572f7a9506ec78ce35ce1edeb2e7`,
  `StartedAt=2026-08-31T11:53:13.70842987Z`, HTTP interne `200`, healthy,
  restart `0`, OOM false.

Le healthcheck autoritatif du conteneur vise le port interne `8089`. L'essai
initial sur le port hote `8093` depuis le conteneur etait mecaniquement
incompatible; l'invocation equivalente sur `127.0.0.1:8089` a produit le `200`
attendu, sans ecart de baseline.

### Inventaire autoritatif

Le chemin effectivement execute est le suivant:

1. `judgment_posture.build_enunciation_directive` derive un triplet ferme:
   absence `none/not_applicable/stimmung_absent`, stabilite
   `none/stimmung/stimmung_stable`, transition
   `delicate_expression/stimmung/affective_transition`;
2. le verdict primaire separe ce triplet de `epistemic_effect`;
3. Validation V2 recoit le signal Stimmung canonique pour sa relecture puis
   recopie les deux effets sans les confondre;
4. `chat_prompt_context.build_hermeneutic_judgment_block` projette exactement
   un effet d'enonciation et, pour `delicate_expression`, une seule consigne
   bornee a la delicatesse, au rythme et a la prudence de formulation;
5. cette consigne interdit explicitement de diminuer certitude, regime de
   preuve ou posture d'incertitude;
6. `chat_service.chat_response` injecte le bloc dans le systeme augmente puis
   appelle le vrai `chat_main_payload.prepare_main_payload`;
7. le payload principal ne contient ni `stimmung_input`, ni `active_tones`, ni
   `dominant_tone`, ni autre signal Stimmung brut;
8. la Continuity Capsule reste un unique message systeme terminal et
   `main_payload_manifest_v1` decrit le payload sans contenu brut;
9. Presence et les final locks sont resolus avant l'appel principal. Un lock
   valide contourne le secret, l'URL et le provider principal; Presence
   persiste exactement `...` avec provenance `final_lock`;
10. sans lock, JSON et streaming utilisent le meme payload principal, puis une
    seule reponse assistant finale est persistee avec provenance `main_model`.

L'observabilite 4C.3 est deja synchrone du runtime aux deux surfaces admin:
evenements `primary_node`, `validation_agent` et `prompt_injection`, garde,
reader, read-model/API, `/log` et `/hermeneutic-admin`. La Phase A n'ajoute
aucun evenement, contenu, tonalite, prompt ou reponse provider. Si une future
correction runtime etait prouvee necessaire, cette chaine complete devrait
etre modifiee et testee dans le meme micro-lot.

Les actifs reutilises sont le support transverse
`app/tests/support/stimmung_dialogic_pipeline.py`, les goldens 4C.3, le corpus
dialogique 4S.0, `dialogic_semantics.py`, `dialogic_campaign.py`, les lecteurs
content-free de campagnes et les goldens existants Presence, final locks,
capsule, manifest, streaming, persistance et observabilite. Aucun second
framework provider n'est introduit.

### Hypotheses F4.1 a F4.5

- F4.1 — validee: le raccord structurel transporte deja un unique triplet
  derive et borne; le signal brut est absent du payload principal.
- F4.2 — validee: les fakes prouvent transport, cardinalite, ordering,
  persistance et provenance, mais pas l'effet semantique du texte final.
- F4.3 — validee: le fake principal renvoie
  `LOT4_SYNTHETIC_ASSISTANT_XX` independamment du payload. Le scorer rejette
  donc toute annotation semantique de provenance `fake`.
- F4.4 — validee: aucune preuve ne justifie d'ajouter le signal Stimmung brut;
  son ajout est une mutation rejetee.
- F4.5 — validee pour la porte diagnostique: faute de preuve autoritative sur
  la formulation finale, seule une campagne appariee du modele principal
  actif peut classer F4. Cette validation n'est pas une validation de F4.

### Corpus apparie

Le corpus versionne est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v1.json`
(SHA-256 `de8f63c6de4ec8d51a47db868e188b06a83d66ed8b07fb2278a5a47734f4f139`).
Il contient 14 cas synthetiques francais, dont 12 eligibles a la comparaison
du modele principal. Les deux autres portent Presence et hard guard au stage
qui en est souverain; ils ne fabriquent pas d'appel principal.

Les quatre etats sont representes: aucun effet applicable, no-op stable,
transition `delicate_expression` et fail-open Validation sans verdict
exploitable. Les familles couvrent delicatesse legitime, contre-cas sans
prudence supplementaire, ironie, affect cite ou rapporte, question, demande,
risque, action materielle, Presence eligible, contre-Presence, hard guard,
certitude et preuve inchangees.

Le corpus ne contient ni prompt copie, ni sortie exacte attendue. Chaque paire
garde la meme histoire, le meme tour, la meme base factuelle et la meme matiere
epistemique. Pour une transition, seule la projection bornee de la directive
d'enonciation distingue controle et traitement. Pour absence, stabilite et
fail-open, les deux bras restent des no-op identiques.

Les attentes sont separees en trois classes:

- texte final directement mesurable: effet de delicatesse, adequation de
  formulation, psychologisation, variation de certitude, alteration de
  verite/preuve, masquage et surapplication;
- autre stage: decision Presence et autorisation d'appeler le modele principal;
- contrat seulement: matiere identique, hard guards, absence de signal brut,
  capsule, manifest, persistance/provenance et parite JSON/streaming.

### Scorer

`benchmark.suites.stimmung.final_wording_diagnostic` valide le corpus, produit
le calendrier apparie et score uniquement des annotations humaines structurees
et aveugles. Il n'interprete jamais le texte par regex et n'appelle aucun
modele juge.

Les seuils geles sont:

- amelioration de delicatesse sur au moins `0.80` des paires de transition;
- amelioration d'adequation sur au moins `0.75` de ces paires;
- degradation d'adequation sur les contre-cas: `0.0`;
- tolerance zero pour psychologisation, changement de certitude,
  verite/preuve alteree, cible masquee et regression Presence;
- surapplication aux contre-cas: `0.0`.

Sans resultat provider, la decision est `provider_campaign_required`, ou
`non_required` seulement avec une preuve semantique autoritative explicitement
fournie. Une provenance fake avec annotations semantiques est invalide. Apres
un ledger complet des tentatives reelles, tous les seuils verts donnent
`pass`, un seuil semantique manque donne `fail`, et une reponse/annotation
indisponible donne `inconclusive`.

### Preuves fakes et sensibilite

Les nouveaux goldens traversent `/api/chat`, le caller Stimmung, le noeud
primaire, Validation, le vrai coordinateur chat, le vrai constructeur du
payload principal, la persistance et les surfaces JSON/streaming. Ils prouvent:

- matiere dialogique et effet epistemique identiques entre stable et
  transition;
- directive presente une seule fois en transition et no-op stable explicite;
- signal brut absent;
- une Continuity Capsule terminale, un manifest coherent et un seul assistant
  final par tour;
- parite du payload JSON/streaming, terminal streaming unique, persistance et
  provenance conservees;
- fail-open Validation sans bloc invente ni Presence;
- aucun appel principal sous Presence/final lock via les goldens reutilises.

La matrice de mutations rejette directive retiree ou dupliquee, signal brut,
effet epistemique modifie, final lock contourne, capsule absente/deplacee/
dupliquee, manifest incoherent et faux resultat semantique fake. Ces preuves
restent structurelles: la chaine assistant scriptée ne devient jamais une
preuve de qualite finale.

### Campagne provider gelee, non executee

Le gel autoritatif est
`benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v1.json`.
Le CLI n'accepte que `--dry-run`; toute execution live s'arrete en demandant le
GO separe.

Plan exact apres ce GO eventuel:

- modele unique: `openai/gpt-5.1`, le modele principal actif;
- parametres actifs: `temperature=0.7`, `top_p=1.0`,
  `max_tokens=8192`, `reasoning={effort: high, exclude: true}`;
- timeout `900 s`; transport standard uniquement;
- `12 cas x 2 bras x 2 repetitions = 48 appels`, plafond absolu `48`;
- deux repetitions sont le minimum retenu pour exposer une variance de
  decodage isolee tout en restant sous le plafond ferme de 48 appels;
- ordre controle/traitement contrebalance entre cas et repetitions;
- aucun retry, fallback modele ou provider, Batch, Flex ou Priority;
- aucun appel Validation, Stimmung ou juge supplementaire;
- estimation prompt gelee `326588` tokens; plafond de sortie issu du contrat
  reel `393216` tokens (`48 x 8192`);
- prix publics OpenRouter observes le 31 aout 2026: `1.25 USD/M` input et
  `10 USD/M` output;
- maximum theorique `4.340395 USD`; marge prudente `10%`; estimation maximale
  `4.7744345 USD`; plafond absolu `5.00 USD`;
- artefact durable content-free: IDs, bras aveugles, statuts, model/provider,
  finish reason borne, tokens, cout, longueur et SHA-256 des reponses, scores
  structures; aucun dialogue, prompt, reponse, raisonnement ou exception brute;
- les textes provider necessaires a la notation restent ephemeres en tmpfs,
  sont relies par hash, puis supprimes apres notation et validation de
  l'artefact content-free.

Dry-run hermetique:

```bash
PYTHONPATH="$PWD:$PWD/app" python3 -m \
  benchmark.suites.stimmung.final_wording_diagnostic \
  --repo-root "$PWD" \
  --freeze-commit <commit-phase-a-pousse> \
  --dry-run
```

### Preuves executees

Tous les runners Python utilisent l'image applicative locale, le depot monte
read-only, `--network none`, `/tmp` en tmpfs et
`PYTHONDONTWRITEBYTECODE=1`:

- nouveaux corpus, scorer, mutations, protocole et vrai raccord fake: `9/9`;
- Stimmung et campagnes/goldens historiques: `101/101`;
- doctrine, Validation, contexte et payload principal: `118/118`;
- Presence, final locks, capsule, manifest, JSON/streaming, persistance,
  provenance et observabilite voisine: `151/151`;
- decouverte Python complete: `2837/2837`, soit la baseline `2828` plus les
  neuf nouveaux tests;
- dry-run du gel: `provider_campaign_required`, 24 paires, 48 appels futurs,
  estimation maximale `4.7744345 USD`, plafond absolu `5.00 USD`.

JavaScript `140/140` et Chromium `19/19` ont ete revalides dans la baseline
avant patch. Ils ne sont pas relances apres patch, conformement au contrat de
preuve, car aucun asset ou contrat frontend n'est touche.

### Limites restantes

- F4 reste non classe jusqu'a une campagne autorisee ou une nouvelle preuve
  semantique autoritative suffisante;
- aucune efficacite de formulation n'est inferee des fakes;
- aucun changement runtime, prompt, modele, fallback, setting, normaliseur,
  agregateur, Presence, final lock, hard guard, projection Validation V2,
  frontend ou DB n'a ete effectue;
- aucun rebuild, restart ou deploiement n'a ete effectue;
- 4O.Z et tous les lots suivants restent non commences.
