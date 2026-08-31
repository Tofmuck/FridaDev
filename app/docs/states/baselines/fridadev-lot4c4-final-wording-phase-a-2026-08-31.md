# Lot 4C.4 — Phase A du diagnostic de restitution finale

Date: 31 aout 2026
Statut: `Phase A v2 gelee — GO provider separe requis`; 4C.4 reste ouvert
Portee: correction du corpus, du calendrier, du runner et de la notation humaine
Exclusions: runtime, prompts, modeles, settings, frontend, donnees operateur et appels provider reels

## Decision v2

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

## Baseline corrective

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

## Findings correctifs C1 a C6

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

## Corpus et calendrier v2

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

## Runner borne v2

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

## Notation humaine aveugle et finalisation

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

## Scorer v2

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

## Cout v2

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

## Sensibilite v2

Les tests rejettent ou detectent: fait requis absent, liste/paragraphe retire,
pseudo-paire identique, retour a 48 appels, modele ou parametre modifie, retry
ou fallback, execution non autorisee, faux client presente comme provider,
depassement du cout, chemin brut dans le depot, mapping expose, notes partielles
ou fausse provenance, decision avant notes, contenu brut durable, nettoyage
avant validation, Presence tiree du texte, signal Stimmung brut et changement
d'un input pince. Le protocole v1 reste validable avec son ancien manifest,
mais son statut courant est explicitement supersede.

## Preuves correctives executees

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

## Limites v2

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
