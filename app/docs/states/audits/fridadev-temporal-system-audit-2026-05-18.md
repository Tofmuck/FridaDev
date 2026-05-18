# FridaDev - audit global de verite temporelle - 2026-05-18

## Verdict executif

Question prealable: il existe un meilleur plan qu'un correctif immediat, et c'est bien l'audit global docs-first demande. Les correctifs `54e7760` et `aa129f5` ont ferme la voie principale du prompt chat et des resumes, mais l'audit montre que la propriete "Frida ne se perd pas dans le temps" traverse encore plusieurs lanes secondaires.

Verdict:

- le coeur conversationnel principal dispose maintenant d'un `NOW` canonique de tour, de `FRIDA_TIMEZONE`, de labels Delta-T avec date locale absolue + heure locale + timezone + relatif, et de dates de resume locales;
- la persistance canonique reste correctement orientee UTC / `TIMESTAMPTZ`, ce qui est sain pour le stockage;
- plusieurs surfaces modele et operateur continuent toutefois a exposer soit une date locale implicite navigateur, soit aucun ancrage temporel alors qu'elles peuvent raisonner sur des enonces temporels;
- le risque le plus net etait la lane web; elle est corrigee par le Lot 1 runtime du 2026-05-18, qui derive reformulation web et blocs web du `NOW` de tour en date locale `FRIDA_TIMEZONE`;
- la bonne suite n'est pas une refonte globale, mais un chantier de fermeture cible en lots bornes.

Comptage de l'audit:

| Famille | Nombre audite | Notes |
|---|---:|---|
| Surfaces temporelles applicatives | 45 | inventaire compact reconcilie ci-dessous |
| Slots modele/service | 13 | les 13 slots du catalogue modele du 2026-05-17 |
| Chemins fonctionnels d'inference | 11 | chat, web, arbitre, resume, identity, stimmung, validation, embeddings, Whisper, OCR |
| Findings actifs | 10 | P1 web corrige, 6 P2, 4 P3 |

Inventaire compact des 45 surfaces temporelles auditees:

| # | Surface | Fichier(s) repere(s) | Registre / verdict |
|---:|---|---|---|
| 1 | Horloge UTC de tour chat | `app/core/chat_service.py` | canonique, sain |
| 2 | Payload temps `NOW` / local | `app/core/hermeneutic_node/inputs/time_input.py` | canonique, sain |
| 3 | Bloc `[RÉFÉRENCE TEMPORELLE]` | `app/core/chat_prompt_context.py`, `app/prompts/main_hermeneutical.txt` | prompt principal, sain |
| 4 | Labels Delta-T messages | `app/core/conversations_prompt_window.py`, `time_input.py` | prompt principal, sain |
| 5 | Marqueurs de silence | `app/core/conversations_prompt_window.py` | prompt principal, narratif |
| 6 | Normalisation timestamps conversation | `app/core/conversations_store.py` | UTC stockage, P3 si invalide |
| 7 | Table `conversations` | `app/core/conversations_maintenance.py` | `TIMESTAMPTZ`, sain |
| 8 | Table `conversation_messages` | `app/core/conversations_maintenance.py` | `TIMESTAMPTZ`, sain |
| 9 | Chargement messages pour prompt/API | `app/core/conversations_store.py` | ISO UTC technique, sain si rendu local ensuite |
| 10 | Entete resume actif | `app/core/conversations_prompt_window.py` | date locale Frida, sain |
| 11 | Entete contexte souvenir parent | `app/core/conversations_prompt_window.py` | date locale Frida, sain |
| 12 | Entree dialogue du resumeur | `app/memory/summarizer.py` | date locale Frida, sain |
| 13 | Table summaries memory | `app/memory/memory_store_infra.py` | UTC stockage, sain |
| 14 | Table traces memory | `app/memory/memory_store_infra.py` | UTC stockage, sain |
| 15 | Injection souvenirs prompt principal | `app/core/conversations_prompt_window.py` | Delta-T local, sain |
| 16 | Injection context hints prompt principal | `app/core/conversations_prompt_window.py` | Delta-T local, sain |
| 17 | Candidats arbitre memoire | `app/memory/arbiter.py` | timestamps bruts/tronques, P2 |
| 18 | Recent context arbitre memoire | `app/memory/arbiter.py` | sans timestamp, P2 |
| 19 | Extracteur identity | `app/memory/arbiter.py`, `app/prompts/identity_extractor.txt` | sans ancre, P2 |
| 20 | Buffer pairs identity staging | `app/memory/memory_identity_staging.py` | timestamps bruts, P3 |
| 21 | Agent periodic identity | `app/memory/arbiter.py`, `memory_identity_periodic_agent.py` | pas de NOW local, P3 |
| 22 | Timestamps identity durable/audit | `app/memory/memory_store_infra.py` | `TIMESTAMPTZ`, sain stockage |
| 23 | Validation dialogue context | `app/core/hermeneutic_node/inputs/recent_context_input.py` | timestamp brut, P2 |
| 24 | Summary input du noeud hermeneutique | `app/core/hermeneutic_node/inputs/summary_input.py` | start/end bruts, support secondaire |
| 25 | Stimmung recent window | `app/core/stimmung_agent.py` | timestamps omis, P3 |
| 26 | Source priority time input | `app/core/hermeneutic_node/doctrine/source_priority.py` | exige time canonical, sain |
| 27 | Qualification temporelle du tour | `app/core/hermeneutic_node/inputs/user_turn_input.py` | manque `hier`, P2 |
| 28 | Reformulation web | `app/tools/web_search.py`, `app/prompts/web_reformulation.txt` | date locale Frida explicite, sain apres Lot 1 |
| 29 | Bloc resultats web | `app/tools/web_search.py` | date locale Frida explicite, sain apres Lot 1 |
| 30 | Bloc URL explicite web | `app/tools/web_search.py` | date locale Frida explicite, sain apres Lot 1 |
| 31 | Active documents metadata | `app/core/active_conversation_documents.py` | UTC technique, sain |
| 32 | Active document prompt lane | `app/core/active_document_prompt_lane.py` | pas de timestamp expose, sain |
| 33 | Runtime settings history | `app/admin/runtime_settings_repo.py` | operateur DB, sain |
| 34 | Admin logs | `app/admin/admin_logs.py` | UTC technique, sain |
| 35 | Chat turn logger | `app/observability/chat_turn_logger.py` | UTC technique, sain |
| 36 | Export markdown logs | `app/observability/log_markdown_export.py` | UTC technique, sain |
| 37 | Dashboard backend `today/yesterday` | `app/observability/dashboard_read_model.py` | minuit UTC sous label FR, P2 |
| 38 | Dashboard backend fenetres glissantes | `app/observability/dashboard_read_model.py` | UTC operateur, acceptable |
| 39 | Dashboard analytics projection | `app/observability/dashboard_analytics_projection.py` | UTC explicite, sain |
| 40 | Dashboard web `formatDateTime()` | `app/web/dashboard/main.js` | timezone navigateur implicite, P2 |
| 41 | Dashboard web `formatBucketLabel()` | `app/web/dashboard/main.js` | timezone navigateur implicite, P2 |
| 42 | Chat byline `fmtHour()` | `app/web/app.js` | timezone navigateur implicite, P2 |
| 43 | Date d'accueil chat `fmtDateFR()` / `setHero()` | `app/web/app.js` | timezone navigateur implicite, P2 |
| 44 | Sidebar conversations `formatTimestamp()` | `app/web/chat_threads_sidebar.js` | timezone navigateur implicite, P2 |
| 45 | Export Markdown conversation | `app/web/chat_copy_export.js` | timezone navigateur implicite, P2 |

## Doctrine temporelle actuelle reelle

La doctrine reelle du depot se lit en trois couches:

1. Stockage: conserver les instants techniques en UTC ou `TIMESTAMPTZ`.
2. Dialogue: rendre le temps en local Frida, via `FRIDA_TIMEZONE`, chaque fois qu'un modele ou un humain doit comprendre `hier`, `aujourd'hui`, une reprise ou une periode de conversation.
3. Observabilite operateur: l'UTC est acceptable seulement s'il est explicite, jamais presente comme un "aujourd'hui" dialogique non qualifie.

Source canonique actuelle du tour:

- `app/core/chat_service.py:476-506` fixe `user_timestamp = _now_iso()` puis propage `now_iso_value`;
- `app/core/chat_prompt_context.py:75-90` transmet ce `now_iso` au bloc systeme augmente;
- `app/core/hermeneutic_node/inputs/time_input.py:119-156` construit le payload `time` et le bloc `[RÉFÉRENCE TEMPORELLE]`;
- `app/core/conversations_prompt_window.py:273-379` rend les messages du prompt principal avec les labels Delta-T derives de ce meme `NOW`.

Fonctions ayant autorite:

| Fonction | Autorite | Preuve |
|---|---|---|
| `chat_service._now_iso()` | horloge UTC de tour | `app/core/chat_service.py:35-36` |
| `time_input.build_time_input()` | payload canonique `now_utc_iso`, `timezone`, `now_local_iso`, `local_date`, `local_time` | `app/core/hermeneutic_node/inputs/time_input.py:119-134` |
| `time_input.build_time_reference_block()` | rendu prompt de `[RÉFÉRENCE TEMPORELLE]` | `app/core/hermeneutic_node/inputs/time_input.py:137-156` |
| `time_input.local_date_iso()` | date locale Frida a partir d'un instant | `app/core/hermeneutic_node/inputs/time_input.py:79-85` |
| `time_input.local_date_label_fr()` | libelle francais stable de date locale Frida, option timezone | `app/core/hermeneutic_node/inputs/time_input.py` |
| `time_input.build_delta_info()` / `render_delta_label()` | Delta-T local absolu + relatif | `app/core/hermeneutic_node/inputs/time_input.py:159-259` |
| `conversations_store.ts_to_iso()` | normalisation stockage UTC `Z` | `app/core/conversations_store.py:62-72` |
| `summarizer.summarize_conversation()` | dates locales envoyees au resumeur | `app/memory/summarizer.py:36-47` |
| `conversations_prompt_window._summary_local_date()` | dates locales visibles des resumes prompt | `app/core/conversations_prompt_window.py:42-60` |

Fonctions qui ne devraient plus recalculer un jour dialogique seules:

- tout `datetime.now(timezone.utc).strftime(...)` destine a une phrase modele ou utilisateur;
- toute coupe `(timestamp or "")[:10]` ou `timestamp_iso[:10]` destinee a un jour local;
- tout affichage `today` / `yesterday` humain non qualifie sans `FRIDA_TIMEZONE`;
- tout appel modele secondaire recevant des enonces temporels sans `NOW` ou sans labels locaux.

## Carte des sources, transformations et consommateurs

| Surface | Temps manipule | Format | Source | Consommateur | Verdict |
|---|---|---|---|---|---|
| Horloge de tour chat | instant UTC | `YYYY-MM-DDTHH:MM:SSZ` | `chat_service._now_iso()` | prompt principal, persistence | sain |
| Payload temps canonique | UTC + local Frida | dict structure | `time_input.build_time_input()` | prompt, noeud hermeneutique | sain |
| Bloc `[RÉFÉRENCE TEMPORELLE]` | NOW + TIMEZONE + prose locale | texte prompt | `build_time_reference_block()` | LLM principal | sain |
| Delta-T messages | date locale + heure + timezone + relatif | texte prompt | `build_delta_info()` | LLM principal | sain |
| Silences | duree relative | texte prompt | `render_silence_label()` | LLM principal | correct mais narratif |
| Date locale de resume actif | date locale Frida | `YYYY-MM-DD` | `local_date_iso()` | LLM principal | sain |
| Date locale envoyee au resumeur | date locale Frida | `[YYYY-MM-DD]` | `summarizer.summarize_conversation()` | modele resumeur | sain |
| Web reformulation/context | date locale Frida + timezone | libelle francais stable | `time_input.local_date_label_fr()` depuis `NOW` de tour | modele web + prompt principal | sain apres Lot 1 |
| Dashboard `today/yesterday` | minuit UTC | ISO UTC | `resolve_dashboard_window()` | humain operateur | P2 |
| Surfaces navigateur chat | timezone navigateur | date/heure sans timezone | `fmtDateFR()`, `setHero()`, `fmtHour()` | utilisateur | P2 |
| Sidebar conversations | timezone navigateur | date/heure sans timezone | `formatTimestamp()` | utilisateur | P2 |
| Dashboard web dates/buckets | timezone navigateur | date/heure sans timezone | `formatDateTime()`, `formatBucketLabel()` | operateur/humain | P2 |
| Export Markdown chat | timezone navigateur | date longue fr-FR sans timezone | `Intl.DateTimeFormat()` | utilisateur | P2 |
| Validation dialogue context | timestamp brut | ISO brut | recent context | validation agent | P2 |
| Arbitre memoire | timestamp ISO tronque | `[:25]` | trace memory | modele arbitre | P2 |
| Identity extractor | aucun timestamp | role/content | recent turns | modele identity | P2 |
| Stimmung agent | aucun timestamp visible | role/content | recent window | modele stimmung | P3 |

## Persistence et schemas

| Objet / table | Champs temporels | Source effective | Transformation lecture/ecriture | Risque |
|---|---|---|---|---|
| `conversations` | `created_at`, `updated_at`, `deleted_at` | DB / app UTC | `TIMESTAMPTZ`, normalise via store | sain |
| `conversation_messages` | `timestamp` | `chat_service.user_timestamp` ou messages charges | `TIMESTAMPTZ`, retour ISO UTC | sain |
| normalization messages | `timestamp` | payload message | `conversations_store.ts_to_iso()` | P3 si timestamp invalide fallback `now` silencieux |
| summaries memory | `start_ts`, `end_ts`, `created_at`, `updated_at` | traces/message timestamps | stockage UTC, rendu prompt local | sain apres `aa129f5` |
| traces memory | `timestamp`, `created_at` | messages/source lanes | `TIMESTAMPTZ`, selection UTC | sain stockage, attention rendu modele secondaire |
| arbiter decisions | `created_at`, trace timestamps associes | DB now / trace | UTC operateur | sain stockage |
| identities | `created_ts`, `last_seen_ts` | DB now / staging | `TIMESTAMPTZ` | sain stockage |
| identity mutables | `created_ts`, `updated_ts` | DB now | `TIMESTAMPTZ` | sain stockage |
| identity staging | message timestamps | recent turns | garde timestamp brut en buffer | P3 cote modele periodic |
| active documents | `created_at` | `_now_utc()` / DB | UTC, prompt document sans timestamp | sain |
| runtime settings history | `updated_at` | SQL `now()` | operateur UTC/timestamptz | sain si operateur |
| chat/log observability | `created_at` / event timestamps | UTC logger | ISO UTC / markdown logs | sain si explicitement technique |
| dashboard read-model | `ts_from`, `ts_to`, buckets | UTC | fenetres UTC, labels FR | P2 pour `today/yesterday` |
| frontend export | message timestamps | ISO UTC charge depuis API | rendu navigateur | P2 |

Conclusion persistence: le stockage UTC n'est pas le probleme. Le risque apparait quand une date de jour est derivee d'un instant UTC sans passer par la timezone Frida, ou quand l'UTC operateur est presente par un label humain non qualifie.

## Modeles et callers

| Caller | Recoit un NOW ? | Recoit timezone ? | Recoit timestamps complets ? | Temps aplati/perdu ? | Peut raisonner temporellement ? | Verdict |
|---|---|---|---|---|---|---|
| Chat principal | oui | oui | oui via Delta-T local + UTC NOW | non sur voie principale | oui | sain sur voie principale et web Lot 1 |
| Reformulation web | oui, date locale issue du `NOW` de tour | oui via label `FRIDA_TIMEZONE` | non, jour local seulement | heure volontairement absente | oui, recherche actuelle | sain pour jour local |
| Arbitre memoire | non | non | candidats avec `timestamp_iso` tronque | recent context sans temps | oui, penalise les souvenirs circonstanciels | P2 |
| Resumeur | non explicite | non explicite | non, date locale seule | heure volontairement perdue | oui, mais objectif resume | sain pour date de jour; P3 si besoin futur d'heure |
| Identity extractor | non | non | non | oui | oui, durable vs episodique | P2 |
| Identity periodic agent | non | non | timestamps bruts dans buffer | pas de local/NOW | oui, operations identite | P3 |
| Stimmung agent | non | non | non dans prompt | oui | oui, affect courant | P3 |
| Validation agent | canonical inputs peuvent contenir time, mais secondaire | idem | contexte principal timestamp brut | localite fragile | oui, regime final | P2 |
| Embeddings Memory/RAG | n/a | n/a | n/a | n/a | non temporel | sain |
| Whisper | n/a | n/a | n/a | n/a | non temporel Frida | sain |
| OCR documents actifs | n/a | n/a | n/a | n/a | non temporel Frida | sain |

Notes:

- Le catalogue modele source liste 11 chemins fonctionnels / 13 slots dans `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md:43-61`.
- Les services embeddings, Whisper et OCR ne recoivent pas de temps dialogique et ne raisonnent pas sur `hier` / `aujourd'hui`.
- Les modeles secondaires ne repondent pas toujours a l'utilisateur, mais ils peuvent influencer la selection memoire, le regime hermeneutique, les identites ou le contexte final; ils ne doivent donc pas etre ignores.

## Prompt principal bout en bout

| Brique | Timestamp absolu visible | Relatif visible | Timezone visible | Risque minuit |
|---|---|---|---|---|
| `[RÉFÉRENCE TEMPORELLE]` | oui (`NOW`) + local humain | non | oui | faible |
| messages user/assistant | oui, date locale + heure | oui | oui | faible |
| silence markers | non, duree seulement | oui | non | faible pour jour, narratif |
| resume actif | date locale periode | non | non dans l'entete, mais derive Frida | faible |
| contexte souvenir parent | date locale periode | non | non dans l'entete, mais derive Frida | faible |
| souvenirs injectes | oui via Delta-T | oui | oui | faible |
| indices contextuels recents | oui via Delta-T | oui | oui | faible |
| documents actifs | pas de temps expose | n/a | n/a | faible |
| jugement hermeneutique | indirect, via upstream | non garanti | non garanti | depend validation P2 |
| web context | date locale Frida + timezone | non | oui | faible apres Lot 1 |

Preuve runtime compacte, conteneur vivant `platform-fridadev`:

```text
source_ts = 2026-05-17T22:05:00Z
FRIDA_TIMEZONE = Europe/Paris
local_date = 2026-05-18
delta_t_label = lundi 18 mai 2026 à 0h05 Europe/Paris — aujourd'hui
dashboard_today_start = 2026-05-17T00:00:00+00:00
dashboard_today_end = 2026-05-17T22:05:00+00:00
dashboard_today_label = Aujourd hui
```

Cette preuve valide que le coeur Delta-T est sain et que le dashboard `today` reste UTC sous label francais ambigu.

## Frontend, exports, dashboard, observabilite

| Surface | Destinataire | Temps utilise | Verdict |
|---|---|---|---|
| Chat accueil et byline navigateur | utilisateur | timezone du navigateur via `toLocaleDateString()` et `getHours()` | P2 si different de Europe/Paris |
| Sidebar conversations | utilisateur | timezone du navigateur via `Date.getFullYear()/getHours()` | P2 |
| Export Markdown chat | utilisateur | timezone du navigateur via `Intl.DateTimeFormat` sans `timeZone` | P2 |
| Nom fichier export | utilisateur | timezone du navigateur | P3 |
| Dashboard `24h/7d/30d/90d` | operateur | fenetres UTC glissantes | acceptable si assume |
| Dashboard `today/yesterday` | operateur/humain | minuit UTC, labels "Aujourd'hui"/"Hier" | P2 |
| Dashboard web dates/buckets | operateur/humain | timezone du navigateur via `Intl.DateTimeFormat` sans `timeZone` | P2 |
| Dashboard inspection traduite | operateur | ISO UTC dans details techniques | P3 documentation/label |
| Log module | operateur technique | UTC explicite / logs techniques | sain |
| Runtime settings history | operateur | DB now/timestamptz | sain |
| Active documents admin metadata | operateur | UTC technique | sain |

## Findings et etats

### P1 corrige - TEMP-20260518-P1-001 - La lane web fabriquait une date humaine depuis l'UTC hote

Preuves initiales:

- `app/tools/web_search.py:387` et `app/tools/web_search.py:462` construisent `today = datetime.now(timezone.utc).strftime("%d %B %Y")` pour les blocs `[RECHERCHE WEB - ...]`;
- `app/tools/web_search.py:639-640` fait la meme chose pour le prompt de reformulation web;
- `app/prompts/web_reformulation.txt:1` injecte `Nous sommes le {today}.`

Risque initial: autour de minuit Europe/Paris, la reformulation web et le contexte web pouvaient dire "17 May 2026" pendant que `[RÉFÉRENCE TEMPORELLE]` et Delta-T disaient localement "18 mai 2026". Comme le contexte web est reinjecte dans le prompt principal, c'etait une contradiction temporelle directe.

Etat apres Lot 1 runtime du 2026-05-18: `app/tools/web_search.py` recoit le `now_iso` du tour quand la lane web est appelee depuis le chat, puis rend reformulation, blocs `[RECHERCHE WEB - ...]` et blocs URL explicite via `time_input.local_date_label_fr(..., FRIDA_TIMEZONE, include_timezone=True)`. Le scenario `2026-05-17T22:05:00Z` rend `lundi 18 mai 2026 Europe/Paris`.

### P2 - TEMP-20260518-P2-001 - Le validation agent lit en priorite un contexte horodate en brut

Preuves:

- `app/core/hermeneutic_node/inputs/recent_context_input.py:48-53` garde un `timestamp` brut;
- `app/core/hermeneutic_node/inputs/recent_context_input.py:146-165` construit `validation_dialogue_context` avec ces messages;
- `app/core/hermeneutic_node/validation/validation_agent.py:329-351` compacte ce contexte en gardant `timestamp`;
- `app/core/hermeneutic_node/validation/validation_agent.py:853-860` place ce contexte avant les `canonical_inputs`;
- `app/prompts/validation_agent.txt:10-15` demande explicitement de lire d'abord ce contexte.

Risque: le validation agent peut arbitrer le regime de reponse a partir d'un timestamp UTC brut, alors que le local Frida est la verite dialogique. La presence possible du temps dans `canonical_inputs` ne suffit pas, car cette section est secondaire et bornee.

### P2 - TEMP-20260518-P2-002 - L'arbitre memoire raisonne sur des souvenirs circonstanciels sans ancrage local

Preuves:

- `app/memory/arbiter.py:55-74` liste des marqueurs circonstanciels comme `aujourd'hui`, `hier`, `demain`, `today`, `yesterday`;
- `app/memory/arbiter.py:326-348` envoie au modele un recent context sans timestamp et des candidats avec `timestamp_iso` tronque;
- `app/memory/arbiter.py:448-457` applique ensuite une logique specifique aux souvenirs circonstanciels.

Risque: une memoire "hier soir" ou "aujourd'hui" peut etre selectionnee/penalisee sans que l'arbitre possede le `NOW` local, puis etre reinjectee dans le prompt principal.

### P2 - TEMP-20260518-P2-003 - L'extracteur identity n'a pas d'ancre temporelle

Preuves:

- `app/memory/arbiter.py:580-589` envoie seulement `ROLE: content` a l'extracteur;
- `app/prompts/identity_extractor.txt:31-43` demande de distinguer durable, episodique, projection, mood/state, mais sans fournir de `NOW` ni de date locale.

Risque: des phrases comme "depuis hier", "en ce moment" ou "aujourd'hui je suis..." peuvent etre classees sans ancre locale. La politique conservatrice reduit le risque, mais ne le prouve pas.

### P2 - TEMP-20260518-P2-004 - Dashboard `today/yesterday` en UTC sous labels humains francais

Preuves:

- `app/observability/dashboard_read_model.py:80-127` calcule `today` et `yesterday` depuis `_now_utc()` et minuit UTC;
- `app/web/dashboard/main.js:62-69` affiche `Aujourd'hui` et `Hier`;
- la preuve conteneur ci-dessus montre `2026-05-17T22:05:00Z` local Paris `2026-05-18`, mais dashboard `today` commence au `2026-05-17T00:00:00+00:00`.

Risque: surface humaine/opérateur contradictoire avec la temporalite dialogique. Si le choix UTC est volontaire, le label doit l'assumer explicitement; sinon il faut passer a `FRIDA_TIMEZONE`.

### P2 - TEMP-20260518-P2-005 - Les surfaces navigateur rendent dates/heures en timezone implicite

Preuves:

- `app/web/app.js:82-83` rend la date d'accueil via `toLocaleDateString("fr-FR", ...)` sans timezone explicite, puis `app/web/app.js:165-168` l'injecte avec `setHero()`;
- `app/web/app.js:103-123` affiche les bylines via `new Date(value).getHours()` sans timezone;
- `app/web/chat_threads_sidebar.js:96-102` rend les timestamps de conversations via `getFullYear()`, `getMonth()`, `getDate()`, `getHours()` et `getMinutes()` sans timezone;
- `app/web/dashboard/main.js:110-133` rend les dates et buckets dashboard via `Intl.DateTimeFormat("fr-FR")` sans `timeZone`;
- `app/web/chat_copy_export.js:18-40` utilise `Intl.DateTimeFormat('fr-FR')` sans `timeZone`;
- `app/tests/unit/frontend_chat/test_chat_copy_export_module.js:13-48` teste seulement la presence de `21:54`, dependante du timezone d'execution;
- `app/tests/unit/frontend_chat/test_chat_copy_export_module.js:79-80` fixe un nom de fichier sur le timezone local.

Risque: pour un navigateur hors Europe/Paris, l'utilisateur ou l'operateur peut voir une heure/jour different de la verite dialogique Frida sur l'accueil chat, les bylines, la sidebar, les exports et les dates dashboard. C'est acceptable seulement si l'UI annonce clairement "heure locale navigateur"; ce n'est pas le cas.

### P2 - TEMP-20260518-P2-006 - Le classifieur deterministe du tour ne reconnait pas `hier`

Preuves:

- `app/core/hermeneutic_node/inputs/user_turn_input.py:619-671` reconnait `aujourdhui`, `demain`, `ce soir`, mais pas `hier` comme portee passee/ancrage temporel;
- `app/core/hermeneutic_node/doctrine/output_regime.py:170-182` derive ensuite `time_reference_mode`;
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py:307-315` ne verifie `depuis hier` que comme signal referentiel ambigu, pas comme signal temporel.

Risque: le noeud hermeneutique peut sous-qualifier une demande explicitement ancree dans `hier`, donc affaiblir la re-situation temporelle.

### P3 - TEMP-20260518-P3-001 - Stimmung agent perd les ecarts temporels

Preuves:

- `app/core/hermeneutic_node/inputs/recent_window_input.py:10-15` conserve les timestamps;
- `app/core/stimmung_agent.py:180-208` les omet dans la fenetre envoyee au modele;
- `app/prompts/stimmung_agent.txt:1-13` autorise l'usage d'une fenetre conversationnelle courte pour contextualiser le tour courant.

Risque: un ton affectif peut etre interprete sans savoir s'il suit une minute ou deux jours de silence. Le scope affectif minimal rend ce P3, sauf decision produit contraire.

### P3 - TEMP-20260518-P3-002 - Agent periodic identity recoit des timestamps bruts mais pas de NOW local

Preuves:

- `app/memory/memory_identity_periodic_agent.py:57-75` transmet les `buffer_pairs`;
- `app/memory/memory_identity_staging.py:34-44` conserve les timestamps bruts des messages;
- `app/memory/arbiter.py:635-656` envoie ce JSON au modele sans ancre temporelle;
- `app/prompts/identity_periodic_agent.txt:7-16` demande des operations d'identite durable.

Risque: faible grace a la consigne de durabilite, mais non prouve pour les claims temporels relatifs.

### P3 - TEMP-20260518-P3-003 - Timestamp invalide de conversation peut devenir `now` silencieusement

Preuves:

- `app/core/conversations_store.py:52-59` parse un timestamp et retombe sur `datetime.now(timezone.utc)` en cas d'erreur;
- `app/core/conversations_store.py:62-72` retourne aussi `now_iso_func()` si la normalisation echoue.

Risque: une donnee temporelle invalide peut etre remplacee par le present au lieu d'etre marquee invalide/absente. Ce n'est pas le bug `hier/aujourd'hui`, mais c'est dangereux pour la verite temporelle.

### P3 - TEMP-20260518-P3-004 - Fallback timezone invalide vers UTC trop silencieux

Preuves:

- `app/core/hermeneutic_node/inputs/time_input.py:51-55` retombe sur `timezone.utc` en cas de `ZoneInfo` invalide.

Risque: si `FRIDA_TIMEZONE` est mal configure, le systeme continue en UTC et peut recreer les contradictions de date locale. Un fallback peut rester utile, mais doit etre observable/teste.

## Zones correctes prouvees

| Zone | Pourquoi elle est saine |
|---|---|
| `NOW` de tour chat | `chat_service` fixe un timestamp unique et le propage au prompt. |
| Bloc `[RÉFÉRENCE TEMPORELLE]` | contient `NOW`, `TIMEZONE`, date locale et consigne de ne pas nier l'ancrage temporel. |
| Labels Delta-T messages | tests couvrent aujourd'hui/hier meme heure, minuit local, date absolue et timezone. |
| Resumes actifs | entetes de periode en date locale Frida, plus tests post-`aa129f5`. |
| Contextes de souvenirs parents | dates locales Frida, coherentes avec Delta-T. |
| Entree du resumeur | `[YYYY-MM-DD]` derive de la date locale Frida. |
| Lane web Lot 1 | reformulation web et blocs web utilisent la date locale Frida + timezone issue du `NOW` de tour. |
| Stockage conversations/messages | `TIMESTAMPTZ`/UTC pour instants techniques, sans pretention de jour local. |
| Active documents prompt lane | n'expose pas de timestamp au modele; les timestamps restent metadata/admin. |
| Embeddings/Whisper/OCR | pas de raisonnement temporel Frida. |
| Logs techniques | UTC acceptable tant que registre operateur/debug reste explicite. |

## Incertitudes faute de preuve

| Zone | Incertitude | Traitement recommande |
|---|---|---|
| Dashboard UTC | le choix UTC peut etre intentionnel pour l'operateur, mais les labels `Aujourd'hui` / `Hier` ne le disent pas | decider local Frida vs UTC explicite |
| Surfaces navigateur | le rendu browser-local peut etre un choix UX, mais il n'est ni documente ni labelle pour l'accueil chat, les bylines, la sidebar, l'export et le dashboard web | fixer la doctrine UI et tester un timezone non Paris |
| Stimmung | le prompt dit "fenetre locale" mais ne prouve pas que les gaps temporels sont hors sujet | documenter l'ignorance des gaps ou fournir labels locaux |
| Identity durable | les prompts sont conservateurs, mais il manque une preuve sur les enonces relatifs `depuis hier` / `aujourd'hui` | tests de rejet ou ancrage explicite |
| DST Europe/Paris | les fonctions `ZoneInfo` devraient gerer les changements d'heure, mais la matrice de test ne le prouve pas encore | ajouter tests DST dans le lot de fermeture |

## Tests existants vs tests manquants

Tests existants probants:

- `app/tests/unit/core/test_conv_store_time_labels.py` couvre les labels Delta-T, `19h27` aujourd'hui vs hier, passage de minuit et preservation du contexte prompt;
- `app/tests/unit/chat/test_chat_prompt_context.py` couvre `[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`, date locale et interdiction de nier l'ancrage;
- `app/tests/unit/memory/test_memory_summaries_phase8c.py` couvre `2026-05-17T22:05:00Z -> 2026-05-18` pour resume actif, contexte parent et entree du resumeur;
- `app/tests/test_prompt_loader_phase13.py` couvre la presence des exemples Delta-T dans le prompt principal.
- `app/tests/unit/web_search/test_web_search_phase4.py` couvre la reformulation web et les blocs web sur `2026-05-17T22:05:00Z -> lundi 18 mai 2026 Europe/Paris`, avec absence de date UTC contradictoire.
- `app/tests/unit/core/test_chat_turn_runtime_inputs.py` couvre la propagation du `now_iso` de tour vers la lane web.

Tests manquants:

- validation agent: `validation_dialogue_context` doit exposer des labels locaux ou recevoir `NOW`/timezone en priorite;
- arbitre memoire: candidats et recent context avec ancre locale, test sur memoire `hier` vs `aujourd'hui`;
- identity extractor/periodic: enonces `depuis hier`, `aujourd'hui`, `en ce moment` avec ancre ou politique explicite de rejet;
- stimmung: soit preuve qu'il ignore volontairement les gaps, soit timestamps locaux si la fenetre les utilise;
- dashboard: `today/yesterday` Europe/Paris autour de minuit, ou labels UTC explicites;
- frontend navigateur: accueil chat, bylines, sidebar conversations, export Markdown et dashboard web en rendu Europe/Paris explicite ou label navigateur explicite, avec test timezone fixe;
- `user_turn_input`: `hier`, `depuis hier`, `ce matin`, `ce soir`, `demain` en qualification temporelle;
- timestamp invalide: absence d'invention silencieuse du present;
- DST Europe/Paris: passage heure d'ete/hiver au moins sur labels Delta-T, web date et dashboard.

## Plan de remediation minimal et ordonne

1. Ferme le 2026-05-18: P1 web remplace les dates UTC hote par une date locale Frida partagee et timezone explicite dans reformulation + context blocks.
2. Aligner les modeles secondaires qui influencent le prompt: validation agent et arbitre memoire en premier, avec labels locaux sobres issus du coeur temporel.
3. Fixer la politique UI/operator: dashboard `today/yesterday` local Frida ou UTC explicitement labelle; accueil chat, bylines, sidebar, export et dashboard web en Europe/Paris ou "heure locale navigateur" visible.
4. Corriger le classifieur deterministe `hier`/`depuis hier` et couvrir les tests.
5. Durcir les fallbacks: timestamp invalide et timezone invalide doivent etre observables et ne pas inventer silencieusement un present dialogique.
6. Ajouter une matrice DST/minuit commune aux tests temporels.

Un TODO de fermeture dedie est ouvert dans `app/docs/todo-todo/audits/fridadev-temporal-truth-remediation-todo.md`.

## Condition de cloture forte

On pourra dire honnetement que la temporalite du repo est alignee quand:

- toute surface lisible par un modele qui manipule `hier`, `aujourd'hui`, `demain`, une periode ou un souvenir recoit soit `NOW + TIMEZONE`, soit des labels locaux derives du coeur temporel;
- aucune date de jour destinee au dialogue ou au prompt n'est produite par troncature UTC ou `datetime.now(timezone.utc).strftime(...)`;
- l'UTC reste reserve au stockage, aux logs techniques et aux fenetres operateur explicitement qualifiees;
- l'UI utilisateur et les exports ne peuvent plus afficher silencieusement un autre jour que la temporalite Frida sans l'annoncer;
- les tests prouvent minuit Europe/Paris, DST, timestamp invalide, timezone invalide, web, resumes, memoire, validation, stimmung, dashboard et export;
- le prompt principal, les modeles secondaires, l'admin et les exports racontent le meme instant selon un registre explicite: local Frida pour le dialogue, UTC qualifie pour l'operateur technique.
