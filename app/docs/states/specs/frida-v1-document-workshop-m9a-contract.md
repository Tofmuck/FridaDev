# Atelier documentaire — M9-A, DOCX Frida et pagination Writer

11 octobre 2026. Branche `FridaV1-Document-Workshop-M9-A`, issue du commit
documentaire M8-A poussé `1b14e7dcdf68030c2d1df139eb9ee4c5f825143d`.
Mandat : [roadmap M9-A](../../todo-todo/product/frida-v1-document-workshop-todo.md#m9-a--docx-frida-createcopyupdate-et-pagination-writer).
**Code M9-A initial et runtime, puis runtime d'observabilité, contre-audités
favorablement par Codex le 11 octobre. Correctif `duplicate_stop` ensuite
livré et contre-audité favorablement sur runtime par Codex, selon Tof.
Nouvelle préparation Safari échouée sur `document_envelope_invalid`, sans
confirmation ; règle exacte inconnue. OBS-M9A-PREP-01 ouvert.
Aucune clôture globale M9-A.**

Le runtime M9-A initial audité exécutait `9d423791…`, image applicative `0e196a0dd199…`, renderer
`7a61bd805ca0…` et pins `a788e48f649a…`. Les 28 cas isolés et les deux jobs
riches du contre-audit runtime restent attribués à Codex, sans rejeu ici. Les
mentions de candidate non déployée et de remise Sauron ci-dessous décrivent
les étapes antérieures.

Le premier canari Safari natif du 11 octobre a créé un répertoire/conversation de test.
La garde initiale a refusé les modes incompatibles ; Notes désactivé, une unique
préparation a été soumise. Action `3ac28772-b3de-4ed4-a9be-8c23520fea80` :
1 624 caractères reçus puis `document_provider_incomplete`, sans carte,
confirmation, révision, rendu, journal d'exécution, reçu ou fichier. Lecture
Nextcloud réelle : Documents vide ; 33 conteneurs inchangés. La cause exacte
ne se déduit pas de ce reason_code partagé et les trames terminales manquent.
Aucun retry ni patch ; copie/update/conflit/continuité restent non éprouvés
live. [Preuves du canari](../baselines/document-workshop/frida-v1-document-workshop-m9a-canari-20261011.json).
Ces constats de recette sont attribués à Codex. Diagnostic applicatif
Celebrimbor du 11 octobre, en lecture seule : action/claim et 27 événements
corrélés relus, neuf fichiers du chemin identiques au code runtime audité,
55 lignes serveur corrélées sans terminaison exploitable. Le rejet est localisé
dans le lecteur SSE documentaire, avant validation de l'enveloppe ; sa branche
exacte reste indéterminée (fin sans DONE, stop absent/dupliqué, raison non
reconnue, contenu après stop ou appel d'outil). `upstream_error` est une
projection HTTP applicative, pas la preuve d'une panne OpenRouter. Aucun
correctif fonctionnel justifié sur ces seules traces ; un discriminant fermé
du site de rejet et les témoins stop/DONE/fin HTTP manquent pour départager.
[Rapport du diagnostic et commandes](../baselines/document-workshop/frida-v1-document-workshop-obs-m9a-prep-01-20261011.json).
Arrêt sur limite de preuve pour contre-audit, sans sonde ni nouvel essai live.
OBS-M9A-PREP-01 reste ouvert et non corrigé ; instrumentation éventuelle et
reprise exigent un mandat distinct. M9-A ouvert, M9-B/M10 non commencés.

**Étape historique du 11 octobre — observabilité SSE sur code seulement,
initialement soumise au contre-audit.** Le contre-audit Codex transmis par Tof valide le
diagnostic précédent ; la cause historique reste inconnue. Le rejet SSE
`document_provider_incomplete` porte désormais `sse_rejection` : site fermé
(`tool_call`, `content_after_stop`, `unrecognized_terminal_reason`,
`duplicate_stop`, `done_without_stop`, `sse_without_done`), booléens
`stop_observed`/`done_observed` et `http_end` fermé (`not_observed`,
`chunked_terminated`, `content_length_consumed`, `body_eof`). Le témoin HTTP
décrit uniquement les octets/framing déjà consommés ; aucun drainage ajouté,
aucune terminaison déduite du nettoyage. La raison fournisseur libre n'est pas
copiée. L'exception transmet ces seules preuves au même événement durable
`document_preparation`, corrélé conversation/tour/action/contexte dans
`observability.chat_log_events`, sans nouvelle table ni surface.

Preuves hors ligne Celebrimbor : baseline 65/65 ; rouge préalable sur huit
variantes via lecteur/HTTP réels, puis 71/71 ciblés, 48/48 voisins du garde et
6/6 HTTP/PostgreSQL isolés. Refus, HTTP 503, JSON non streaming, succès,
compteurs, annulation/autorité/nettoyage conservés dans cette sélection.
Sentinelle absente du diagnostic et des événements persistés du tour ; panne
du diagnostic sans changement du refus métier. L'émission garde la garantie
best-effort du canal existant : aucune persistance promise si le sink échoue.
[Relevé compact, commandes et limites](../baselines/document-workshop/frida-v1-document-workshop-obs-m9a-prep-01-observability-20261011.json).
À cette remise sur code : runtime inchangé (`9d423791…`, image `0e196a0dd199…`), aucun appel live,
déploiement ou nouveau canari. OBS-M9A-PREP-01 et M9-A restent ouverts ; aucun
correctif fonctionnel établi. Remise Sauron future : quatre propriétaires
`app/core/document_workshop_{contract,http_transport,provider,turn}.py` et
`app/observability/observability_payload_guard_context_schema.py` ; aucun
raccord runtime autorisé ici. Arrêt pour contre-audit.

**Étape historique du 11 octobre — correctif `duplicate_stop` sur code, runtime
encore inchangé par ce micro-lot.** L'observabilité `fa3ad27a…` a ensuite été
livrée par Sauron, image `958d361bd537…`. Son contre-audit runtime favorable
(code exact, SSE isolé, configuration et voisins préservés) est attribué à
Codex, transmis par Tof et non rejoué ici.

Deuxième préparation Safari, attribuée à Codex : action
`e883206a-9748-4c1e-8e89-38c81d5818b8`, tour
`turn-954f51e4-d681-4f9c-af41-5f354c6de44f`, échec à `12:58:04 UTC` après
27 200 ms et 1 513 caractères reçus. Rejet `document_provider_incomplete`,
`site=duplicate_stop`, stop=true/DONE=false/HTTP=`not_observed`, sans
confirmation, révision, publication ou rendu. Rejet anticipé : DONE et fin
HTTP non observés ne prouvent pas leur absence future. Les trames brutes
manquent ; aucune attribution rétroactive au premier échec.

La [documentation OpenRouter, trame finale usage](https://openrouter.ai/docs/api_reference/streaming#the-final-usage-chunk-chat-completions)
décrit un choix sans contenu répétant la terminaison avant DONE. Incompatibilité
reproduite sur lecteur/HTTP réels avec canonical valide : nominal vert, trame
de comptage refusée `duplicate_stop`. Le seul propriétaire runtime modifié est
`app/core/document_workshop_provider.py` : une unique répétition concordante
de `stop` est traitée en comptage après validation des métadonnées/plafonds,
avec index explicite 0, au moins un compteur standard validé dans cette trame
et delta limité à contenu absent/null/vide et rôle assistant optionnel.
Outil, refus, autre champ de delta, doublon nu ou seconde trame répétant stop
restent refusés. DONE et canonical exact restent requis ; aucun retry,
drainage, modification de modèle/prompt/budget/compteur partagé ou du chat commun.

Preuves Celebrimbor hors ligne : baseline 71/71, rouge causal avec témoin vert,
vert après correctif puis même rouge au retrait de ses seules 12 lignes ;
final 76/76 lecteur/transport/observabilité et 7/7 HTTP/PostgreSQL isolés.
Révision/canonical/empreinte et événement de succès persistés sous le bon
tour/action, sans exécution ; frontières, annulation/inactivité/autorité et
diagnostic borné vérifiés. [Relevé compact et commandes](../baselines/document-workshop/frida-v1-document-workshop-obs-m9a-duplicate-stop-20261011.json).
Cette reproduction justifie le correctif applicatif ; elle ne reconstitue pas
les trames historiques. Aucun déploiement, appel live, Writer ou DAV ici.
OBS-M9A-PREP-01 et M9-A restent ouverts pour contre-audit, livraison runtime
et recette ultérieures ; M9-B/M10 hors mandat.

## État courant — diagnostic d'enveloppe du 11 octobre

Après livraison et contre-audit runtime favorables du correctif `duplicate_stop`
(constats attribués à Codex, transmis par Tof), une seule nouvelle préparation
Safari a été soumise, sans nouvel envoi après l'échec. Code embarqué
`8088571296a81f5182ce60448ed366ee49450524`, image `5d28d36f5000…`.
Action `bdb3bc4c-0dd2-4e62-b9a9-784359e9ad8b`, tour
`turn-f3ff770b-0669-4154-9623-420c7d2ce10d` : échec
`document_envelope_invalid` à `15:44:46.993963Z`, 1 510 caractères reçus,
20 370 ms journalisés. Zéro révision, confirmation, reçu, snapshot, fichier
et journal d'exécution ; claim terminé. Ces observations Codex sont corrélées
en lecture seule aux 27 événements et objets SQL existants, sans DAV.

[Diagnostic Celebrimbor, requête/validateur et sources officielles](../audits/frida-v1-document-workshop-envelope-diagnostic-20261011.md) :
15 propriétaires runtime/commit/checkout concordants. Rejet dans la frontière
enveloppe, qui fusionne parsing, structure et gardes locales ; réponse exacte
absente des traces consultées. Stop/DONE déduits du chemin, aucune capture
terminale et aucun second stop affirmé. Consigne textuelle présente, mais aucun
`response_format`/schéma/strict ; `allow_fallbacks=false`, sans
`require_parameters`. Écart de garantie établi, cause historique non établie.
115/115 tests ciblés hermétiques, sans modification produit ni sonde nouvelle.
Proposition seulement : identifiant fermé de la première règle rejetée dans
un micro-lot distinct, sans contenu ; ni instrumentation ni reprise ici.
OBS-M9A-PREP-01 et M9-A restent ouverts ; M9-B/M10 hors périmètre.

## Raccord retenu

Les propriétaires existants sont étendus ensemble : enveloppe/préparation et
capacités, confirmation/claim M3, client/session/snapshots M8-A, publication
M5/M7, reçus/historiques, inventaire et lecture fraîche M2. Aucun second
pipeline, moteur, validateur, inventaire, route ou détecteur lexical de demande.
Le modèle, le compteur partagé et les budgets restent inchangés.

- Entrée documentaire explicite, compréhension agentique, proposition durable,
  confirmation humaine puis exécution unique. Une copie exige une demande
  explicite ; aucune copie implicite ou copie de secours d'un update.
- Create/copy : cible confirmée sous Documents, un seul DOCX, PUT
  `If-None-Match: *`. Compensations M5 conservées exclusivement sous autorité
  valide, création prouvée et ETag fort d'origine.
- Update : provenance depuis la révision courante Frida, rendu, snapshot,
  journal et reçu durables concordants, puis octets fraîchement lus. Ni nom,
  extension ni déclaration ne prouvent cette origine. Source absente ou
  désynchronisée : refus honnête, aucun reclassement en externe.
- La source temporaire est liée au canonical de sa **révision source** ; le
  canonical candidat confirmé appartient à une révision distincte. Le renderer
  reçoit seulement ces octets admissibles et le contrat source M8-C.
- La vraie session valide le DOCX final rechargé et paginé Writer, le PDF de
  contrôle du même état et leurs empreintes, fige la paire immutable en SQL,
  puis attend la libération acquittée. Le journal précède toute mutation DAV.
  Un snapshot conservé après refus de libération ne vaut jamais publication.
- Après Writer : autorité, identité et version revérifiées. Le PUT d'update
  conserve l'ETag préparé exact en `If-Match`. Changement : conflit, sans
  préparation automatique, refresh d'ETag, second PUT, DELETE ou restauration.
  Succès : mêmes ID, nom, chemin et lien ; anciennes révisions et reçus intacts.
- Seul le DOCX confirmé est publié. Le PDF compagnon reste interne. Le
  téléchargement prouve la révision courante et prend son MIME depuis le
  format validé serveur. Reload sans mutation, reçu de métadonnées seul au
  tour suivant ; aucun contenu documentaire dans les facultés.

Canonical : 10 000 mots/75 000 points de code. Profil A4, 12 points,
interligne 1,5, marges 2,5 cm ; maximum 20 pages mesurées Writer, sans troncature
ni réduction silencieuse. Aucune pagination universelle Microsoft Word.
Markdown conserve son parcours et son téléchargement sans Writer.
DOCX externe en update (M9-B) et publication PDF (M10) restent fermés.

## Migration et capacités

[Migration M9-A explicite](../../../core/sql/document_workshop_docx_m9a.sql),
additive en capacités : contraintes format actions/reçus/rendus étendues à
Markdown/DOCX, liaison format/serializer et journal `frida_writer_v1`.
Aucune migration appliquée antérieurement n'est réécrite ; aucun startup ou
GET n'applique cette migration. Répétition et préservation des lignes testées
sur PostgreSQL jetable. Son seul chemin est ajouté à Git malgré `*.sql`, sans
changer `.gitignore`. Aucune migration opérateur dans ce mandat.

DOCX est annoncé seulement avec schéma M9-A effectif et session/client munis
des pins locaux attendus ; incompatibilité du worker refusée avant submit.
Le statut et les limitations projetées suivent ces capacités, sans annoncer
PDF ni retravail externe. Markdown reste disponible en l'absence de Writer.

## Défauts applicatifs repris et corrigés

- Téléchargement DOCX anciennement `text/plain` : rouge sur la vraie route,
  puis MIME DOCX issu du format prouvé, attachment et `nosniff` préservés.
- Statut limité à Markdown et limitation de carte contradictoire avec DOCX :
  rouges navigateur/route, puis projection cohérente, sans réécrire les
  limitations historiques persistées.
- Risque d'extraction après PUT **confirmé causalement** : panne OSError du
  vrai worker de métadonnées provoquée uniquement à cette frontière, après
  un rendu réussi ; WIP initial effectuait un PUT dans chacune des trois
  opérations avant l'erreur. Correction minimale : extraction unique sur les
  octets figés avant journal/mutation, puis métadonnées transmises à la
  publication. Même panne : zéro PUT/DELETE et aucun reçu pour create/copy/update.
  Le fallback de réparation SQL reste dans `PublicationFailure`, sans mutation DAV.
- Régression du WIP M2 : octets temporaires ajoutés au dataclass atteignaient
  une sérialisation Jsonb Markdown du harnais ; ils sont désormais réservés
  au DOCX et exclus des projections documentaires par liste de champs.
- Sondes M8-A : collisions NOWAIT avec les vraies gardes SQL courtes. Le
  harnais synchronise ses quatre observations, conserve chaque vrai check et
  démontre avec PostgreSQL que la sonde brute voit la garde courte bloquée et
  que la sonde synchronisée détecte toujours une transaction retenue ailleurs.
  Aucun sleep ajouté ni garde produit assouplie.

Revue indépendante en lecture seule : deux findings (texte candidat non
asserté, limitation Markdown) corrigés et revus ; aucun autre finding établi.
Le test riche vérifie désormais le nouveau paragraphe et exclut l'ancien dans
le DOCX final, en plus de l'égalité stricte snapshot/PUT/téléchargement.

## Candidate et attribution plateforme

`M9A-RENDERER-SOURCE-01` fermé **sur candidate non déployée**, par contre-audit
Codex du 10 octobre transmis par Tof. Docker config ID :
`sha256:7a61bd805ca0e371873184f9b050ad47945ee32562c952437b65c793a6f4da10`.
Manifeste OCI local contractuel, distinct de ce config ID :
`sha256:61502c57d2fafbeb41e194a0f46087e65fcea7d32be431a09ec5f848cc412c93`.
Pins complets :
`/opt/platform/backups/writer-m9a-source01-20261010T201715Z/candidate-m9a-source01-pins.json`,
SHA-256 `a788e48f649a84eed24af05ab340c1f2f080fe1f14c1827a86cf95d2a2900021`.
Ces trois identités ont été vérifiées localement avant consommation isolée.

Report **attribué, pas exécuté ici** : Codex a reproduit le refus riche sur
l'ancienne image, validé 19 jobs candidats (neuf paires, dix refus, toutes
libérations acquittées), un refus client avant submit et le corpus 32/32.
Le parcours riche reprend les octets exacts avec leur canonical source puis
modifie un texte. Rapport transmis :
`/Users/tof/codex-fridadev/audits/2026-10-10-m9a-source01-counteraudit/rapport.md`.
Son absence dans l'IDE ne bloque pas ce report ; il n'est pas présenté comme lu.

## Preuves propres et histoire conservée

[Relevé du 11 octobre](../baselines/document-workshop/frida-v1-document-workshop-m9a-20261011.json) :
commandes composables, IDs uniques, exits/durées, rouges et incidents, identités,
frontières HTTP réelles/simulées et nettoyage. Les tests consomment les vrais
propriétaires applicatifs, jamais une capacité DOCX réservée aux fixtures.

- Vrais create → copie explicite → update riche avec client DAV de production,
  DAV HTTP synthétique, PostgreSQL et Writer candidat isolés. Structure, styles,
  listes, tableau, liens, pagination, candidat distinct, identité et anciens
  reçus, octets exacts et PDF non publié.
- Sources/canonical/hash et pins discordants, 20 pages acceptées/21 refusées,
  ETag changé pendant rendu sans PUT, vrai 412 observé avec If-Match préparé.
  Rollback SQL DOCX compensé avec le seul ETag de création ; réponse DAV perdue
  maintenue inconnue, sans replay ni faux reçu.
- Mêmes 128 identifiants de baseline comparés après corrections ; annulation,
  répétition, perte d'autorité, libération non acquittée, rollbacks et réponses
  perdues réutilisent les preuves M3/M5/M7/M8-A. Résultats et incidents exacts
  dans le relevé, sans addition de runs répétés.
- Chromium desktop clair : carte/confirmation/reçu/téléchargement/reload et
  continuité via composition et HTTP réels, provider/facultés synthétiques.
  Aucun fetch remplacé. Parcours Markdown sans montage Writer séparé.
  Voisins reader DOCX/Exports et Notes/ETag, admission/provenance ciblés.
  Aucun rejeu des 1 691 tests ni des stress M8-S.

L'[historique arrêté du 10 octobre](../baselines/document-workshop/frida-v1-document-workshop-m9a-20261010.json)
est conservé sans réécriture : 128 verts alors exécutés, essais rouges de
create/copy/update et arrêt approuvé par Tof. Ancienne image durable inchangée :
`sha256:f3067a8fa6787e72a81cd72f94eb276c3887adf2e7907331a79aec98ca1c1487`.
Son premier refus isolé portait sur `w:rStyle`/`w:start`/`w:end` omis de la garde
source, pas sur une non-conformité applicative démontrée.
[DOCX synthétique exact conservé](../../../tests/fixtures/document_renderer_v1/m9a-frida-rich-source.docx) :
8 967 octets, SHA-256 `99deac658b3aae599572b732a82cd3c88d54a925cfd6619de5370c85948e5ae9`.
Les 128 verts historiques et les preuves Codex ne sont jamais ajoutés aux
nouveaux résultats Celebrimbor.

## Remise Sauron après contre-audit Git

Utiliser le commit applicatif M9-A remis en fin de mandat, la migration
explicite ci-dessus et **la candidate avec ses pins complets qualifiés**.
Livraison runtime à autoriser séparément : raccord socket/pins/migrations,
health et capacités DOCX réelles, gardes d'identité et refus sur pin discordant,
Markdown sans Writer, carte/confirmation/téléchargement et libération acquittée.
Puis canari Nextcloud create/copy/update/conflits et continuité, avec GO distinct.
Les recettes DAV/Versions des lots antérieurs restent distinctes.

Aucun déploiement, rebuild/restart durable, remplacement de pins durables,
migration opérateur, appel OpenRouter réel ou DAV live effectué ici.
Les seules ressources de preuve possédées sont nettoyées et leur disparition
vérifiée dans le relevé. Arrêt après livraison Git pour contre-audit Codex.
