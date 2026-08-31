# Lot 4C.4 — Phase A du diagnostic de restitution finale

Date: 31 aout 2026
Statut: Phase A livree; decision `provider_campaign_required`; 4C.4 reste ouvert
Portee: inventaire, corpus/scorer, preuves fakes, gel d'une campagne eventuelle
Exclusions: runtime, prompts, modeles, settings, frontend, donnees operateur et appels provider reels

## Decision

La Phase A ne permet pas de classer F4 valide, invalide ou corrige. Les preuves
existantes demontrent que la directive derivee arrive correctement au modele
principal, mais une reponse assistant scriptable par le fake ne renseigne pas
son effet sur la formulation finale. La decision bornee est donc
`provider_campaign_required`.

Cette decision maintient 4C.4 ouvert. Une campagne reelle exige un GO separe de
Tof apres commit et push du present gel. Aucun appel provider reel n'a ete
execute pendant la Phase A.

## Baseline revalidee avant edition

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

## Inventaire autoritatif

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

## Hypotheses F4.1 a F4.5

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

## Corpus apparié

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

## Scorer

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

## Preuves fakes et sensibilite

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

## Campagne provider gelee, non executee

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

## Preuves executees

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

## Limites restantes

- F4 reste non classe jusqu'a une campagne autorisee ou une nouvelle preuve
  semantique autoritative suffisante;
- aucune efficacite de formulation n'est inferee des fakes;
- aucun changement runtime, prompt, modele, fallback, setting, normaliseur,
  agregateur, Presence, final lock, hard guard, projection Validation V2,
  frontend ou DB n'a ete effectue;
- aucun rebuild, restart ou deploiement n'a ete effectue;
- 4O.Z et tous les lots suivants restent non commences.
