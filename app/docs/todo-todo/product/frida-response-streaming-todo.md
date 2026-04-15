# Frida Response Streaming TODO

Statut: ouvert
Classement: `app/docs/todo-todo/product/`
Nature: TODO canonique produit — fiabilisation du streaming des reponses Frida
Portee: `/api/chat`, transport de reponse, UX frontend, persistance, observabilite

## Contexte

Le streaming des reponses de Frida existe **deja de bout en bout**.

Ce n'est pas un chantier "ajouter le streaming", mais un chantier "fiabiliser, durcir et completer l'existant".

Le systeme actuel fonctionne dans la configuration suivante:
- le frontend envoie toujours `stream: true` a `POST /api/chat` depuis `sendToServer()` dans `app/web/app.js`;
- le backend parse la SSE OpenRouter dans `event_stream()` de `app/core/chat_llm_flow.py`;
- le texte extrait est envoye au navigateur en flux brut `text/plain; charset=utf-8` par la branche stream de `app/server.py`;
- le frontend lit le corps via `ReadableStream + TextDecoder` dans `sendToServer()` de `app/web/app.js`;
- la persistance conversation se fait dans le `finally` de `event_stream()` dans `app/core/chat_llm_flow.py`.

## Etat actuel

### Ce qui fonctionne
- Le flux texte arrive bien du LLM au navigateur incrementalement (en mode non-bufferise).
- Les tests couvrent le stream normal, le stream normalise plain text, et le stream structure (`app/tests/test_server_phase14.py:175-390`).
- Le turn logger suit correctement le cycle de vie stream (`app/server.py:545-605`).
- La politique de buffering (`assistant_output_contract`) est fonctionnelle: plain text = bufferise en un bloc final, structure/code = stream progressif.

### Ce qui reste fragile ou incomplet
- **Pas de signal de fin applicatif**: le frontend ne distingue pas fin normale de coupure reseau — il ne voit que la fermeture TCP.
- **Pas de signal d'erreur mid-stream**: une `RequestException` dans `chat_llm_flow.py:213` est loggee mais ne produit aucun signal visible cote frontend. Le texte partiel accumule est envoye sans indication d'erreur.
- **UX du buffering**: en mode plain text (cas le plus frequent), le frontend n'affiche qu'une bulle d'attente minimale (`…`) sans distinguer preparation, buffering et reponse effectivement visible. Le texte utile arrive ensuite d'un coup en fin de generation.
- **Pas de `X-Conversation-Updated-At` dans le stream**: les headers initiaux du stream omettent cette metadonnee (`chat_session_flow.conversation_stream_headers()`). Le frontend recupere bien `updated_at` apres rehydratation/fetch secondaire, mais pas via le flux lui-meme ni via un signal terminal explicite.
- **Persistance inconditionnelle en cas d'erreur**: si le stream avorte avec 3 caracteres de texte, ces 3 caracteres sont sauvegardes comme message assistant complet en DB.
- **Observabilite asymetrique**: les erreurs `RequestException` dans le generateur ne remontent pas au turn logger. Le turn se termine avec `status='ok'` meme si une erreur LLM s'est produite.
- **Comptage chars dans le wrapper**: le comptage `stream_response_chars` (`server.py:554-556`) est correct pour le flux actuel, mais devra etre re-verifie si le transport ajoute un signal de controle applicatif.

## Probleme produit

Ces limites ne sont pas des bugs bloquants, mais elles degradent l'experience conversationnelle:
- l'utilisateur ne sait pas si Frida a fini de repondre ou si la connexion a coupe;
- une erreur mid-stream produit un message d'erreur generique au lieu d'un statut clair de la reponse;
- le feedback minimal pendant le buffering donne l'impression que Frida ne repond pas ou qu'elle reste bloquee;
- un texte partiel sauvegarde en DB fausse l'historique de conversation et la memoire.

## Contraintes / hors-scope

### Contraintes
- Le transport actuel est `text/plain` sur `POST /api/chat` avec `fetch + ReadableStream`. C'est fonctionnel et teste.
- EventSource ne fait pas POST nativement — passer a SSE standard exigerait de mettre le message utilisateur en query string (exposition URL) ou de garder fetch avec un parse SSE manuel.
- Le buffering est dicte par `assistant_output_contract`. Modifier ce comportement peut changer la presentation des reponses.
- Depuis les lots Whisper du 2026-04-15, `app/web/app.js` porte aussi `input_mode`, `chatRequestInFlight` et `syncDictationUi()`. Tout lot streaming qui touche `sendToServer()` ou le submit handler devra preserver ce contrat frontend.

### Hors-scope de ce chantier (a moins que specifie ulterieurement)
- Refonte complete du transport vers SSE/WebSocket.
- Lots memoire, admin, plateforme en parallele.
- Refactoring structurel de `chat_llm_flow.py` au-dela de ce que les lots demandent.

## Cadrage produit

### Decision deja prise

Le chantier vise a completer l'existant plutot qu'a remplacer le transport actuel.

Ce cadrage implique:
- conserver `POST /api/chat + fetch + ReadableStream` comme base de travail pour ce lot;
- traiter le sujet comme un lot produit de fiabilisation, pas comme une refonte protocolaire;
- viser une distinction explicite entre le contenu affiche a l'utilisateur et les signaux de controle du flux, meme si les deux transitent encore sur la meme reponse HTTP;
- ordonner le travail en petits lots testables et reversibles.

### Ce document ne tranche pas encore

Ce TODO ne fixe pas a lui seul:
- le format exact du signal applicatif de fin normale et d'erreur;
- la representation concrete d'un plan de controle distinct du contenu (lignes reservees, enveloppe NDJSON, SSE parse via `fetch`, ou variante equivalente);
- la forme du transport de metadonnees post-stream;
- la regle precise de persistance en cas d'interruption;
- le niveau de feedback UX minimal pendant le buffering.

### Option technique legere a evaluer

Une piste simple consiste a conserver le flux `text/plain` actuel tout en introduisant un plan de controle logiquement distinct du texte rendu.

Les marqueurs inline de type `::FRIDA::DONE` / `::FRIDA::ERROR:...` font partie des options possibles, mais ils ne doivent pas etre traites ici comme protocole deja tranche. Le lot code devra confirmer si cette option peut etre rendue suffisamment sure, lisible et reversible, ou s'il faut lui preferer une enveloppe equivalente. Dans tous les cas, le texte affiche a l'utilisateur ne devra pas transporter visiblement la regie du flux.

## Lots proposes

### Lot 0 — Preuves de comportement actuel
- Objectif: valider chaque scenario (stream normal, buffering, erreur) en runtime reel.
- Fichiers runtime: aucun. Doc eventuelle: ce TODO pour figer la matrice observee.
- Done: matrice documentee comportement x mode.
Checklist:
- [x] Verifier le comportement du stream non-bufferise en runtime reel.
- [x] Verifier le comportement du buffering plain text en runtime reel.
- [x] Verifier le comportement observable en cas d'erreur upstream pendant le stream.
- [x] Consigner une matrice simple comportement x mode x issue.

Validation runtime 2026-04-15:

| Scenario | Comportement reseau observable | Comportement UI observable | Persistance | Logging / observabilite | Limites connues |
| --- | --- | --- | --- | --- | --- |
| Stream progressif non-bufferise | `POST /api/chat` repond `200 text/plain`; premier chunk utile observe vers `6.7s`, puis emission progressive sur des centaines de chunks jusqu'a la fin; pas de header `X-Conversation-Updated-At` pendant le flux. | La bulle assistant `…` est creee tout de suite, puis le texte visible s'allonge au fil des chunks. | La reponse complete est sauvegardee; `updated_at` est recupere ensuite par fetch / rehydratation secondaire, pas par le flux. | `llm_call`, `persist_response` et `turn_end` sont `ok`; pas de signal terminal applicatif distinct. | Le frontend ne peut toujours pas distinguer fin normale et simple fermeture reseau. |
| Buffering plain text | `POST /api/chat` repond `200 text/plain`; aucun texte utile avant le bloc final; un seul chunk utile observe vers `18.1s`, puis fin immediate; pas de header `X-Conversation-Updated-At`. | La bulle assistant reste a `…` pendant toute la generation, puis le texte complet apparait d'un coup. | La reponse complete est sauvegardee normalement. | `llm_call`, `persist_response` et `turn_end` sont `ok`; aucune metadonnee terminale supplementaire dans le flux. | L'UI ne distingue pas `preparation`, `buffering sans contenu visible` et `reponse terminee`. |
| Erreur upstream pendant le stream | Preuve provoquee via un upstream de test temporaire et reversible: `POST /api/chat` repond quand meme `200 text/plain`, mais ne livre qu'un texte partiel (`Segment 1. Segment 2.`) sans signal d'erreur applicatif; pas de header `X-Conversation-Updated-At`. | L'utilisateur voit seulement l'attente puis un texte partiel, sans statut clair indiquant que le flux a echoue. | Le fragment partiel est persiste comme message assistant complet. | Une entree `error` avec `llm_stream_error` / `upstream_error` apparait dans la timeline et dans les logs serveur, mais `llm_call` et `turn_end` restent `ok`: le turn logger ne porte donc pas l'echec terminal. | La preuve d'erreur repose sur un upstream temporaire remis en etat apres test; le contrat utilisateur reste muet sur l'interruption. |

### Lot 1 — Signal applicatif de fin et d'erreur
- Objectif: le frontend puisse distinguer fin normale d'erreur mid-stream, avec une frontiere nette entre contenu et controle.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: le flux possede un plan de controle minimal et documente. Le frontend recoit un signal explicite de fin normale et un signal explicite d'erreur sans ambiguite avec la prose affichee.
Checklist:
- [ ] Definir les invariants minimaux du flux: zero ou plusieurs segments de contenu, au plus un signal terminal, aucun contenu apres le terminal.
- [ ] Choisir un format minimal de signal applicatif compatible avec le transport actuel.
- [ ] Emettre un signal explicite en fin normale de stream.
- [ ] Emettre un signal explicite en cas d'erreur mid-stream.
- [ ] Garantir que le texte affiche a l'utilisateur ne contient jamais le signal de controle brut.
- [ ] Parser correctement ce signal cote frontend.
- [ ] Verifier explicitement la robustesse aux chunk boundaries pour le contenu et les signaux de controle.
- [ ] Verifier que le format retenu reste simple a tester et a faire evoluer.

### Lot 2 — Feedback UX pendant l'attente
- Objectif: l'utilisateur dispose d'un etat visible de la reponse en cours, sans modifier dans ce lot le contrat du flux ni la politique de normalisation.
- Fichiers: `app/web/app.js`.
- Done: l'UI distingue au minimum `preparation`, `aucun contenu visible`, `contenu en cours`, `terminee` et `interrompue`, a partir de faits observables cote frontend.
Checklist:
- [ ] Definir une petite machine d'etats UI fondee sur les evenements deja observables (`requete envoyee`, `premier byte`, `premier contenu visible`, `terminal`, `erreur reseau`).
- [ ] Afficher un indicateur de preparation des l'envoi de la requete.
- [ ] Rendre visible l'etat `aucun contenu visible` tant qu'aucun texte n'est affichable pendant le buffering.
- [ ] Basculer explicitement vers l'etat `contenu en cours` des qu'un contenu visible arrive.
- [ ] Retirer proprement l'etat d'attente a la fin normale du stream.
- [ ] Retirer proprement l'etat d'attente en cas d'erreur mid-stream ou de coupure reseau.
- [ ] Verifier que le feedback ne pretend pas a une activite backend que le frontend ne peut pas observer.
- [ ] Garder hors de ce lot toute evolution plus intrusive du flux ou de la normalisation.

### Lot 3 — Metadonnees post-stream
- Objectif: rendre `updated_at` et le statut terminal disponibles au frontend sans dependre uniquement de la rehydratation/fetch secondaire post-stream.
- Fichiers: `app/core/chat_llm_flow.py`, `app/core/chat_session_flow.py`, `app/web/app.js`.
- Done: le frontend recoit, a la fin du stream, un paquet terminal minimal contenant au moins le statut final et `updated_at` ou leur equivalent retenu.
Checklist:
- [ ] Choisir le canal de propagation post-stream des metadonnees terminales.
- [ ] Preciser si la rehydratation/fetch secondaire actuelle reste un simple fallback UI ou une dependance du contrat cible.
- [ ] Rendre `updated_at` disponible a la fin d'un stream complet.
- [ ] Definir la place du statut terminal dans ce meme canal de fin.
- [ ] Reinjecter correctement cette valeur dans le thread cote frontend.
- [ ] Verifier l'absence de divergence entre l'affichage frontend et l'etat persiste.

### Lot 4 — Gestion d'erreurs mid-stream
- Objectif: erreur LLM visible et distinguable cote frontend, sans confondre les differents types d'interruption.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: le frontend affiche un statut d'erreur intelligible, distinct d'une simple coupure reseau, et le thread n'est pas presente comme complet quand la reponse a echoue.
Checklist:
- [ ] Definir une taxonomie minimale des echecs observables (`erreur upstream`, `coupure reseau`, `interruption locale`, ou variante equivalente selon le lot).
- [ ] Faire remonter un statut d'erreur applicatif exploitable jusqu'au frontend.
- [ ] Distinguer cote UI une erreur mid-stream d'une simple coupure reseau.
- [ ] Eviter de presenter la reponse comme terminee quand le stream a echoue.
- [ ] Faire converger le statut utilisateur, le statut de persistance et le statut de logging sur une meme lecture de l'echec.
- [ ] Verifier la coherence entre message utilisateur, etat du thread et observabilite.

### Lot 5 — Persistance robuste en cas d'echec
- Objectif: eviter qu'une reponse interrompue soit persistee comme message assistant complet, et donner un statut explicite au fragment s'il est conserve.
- Fichiers: `app/core/chat_llm_flow.py`.
- Done: la regle produit de persistance en cas d'echec est explicite, implementee et testee. Une reponse interrompue n'est plus confondue avec une reponse breve mais complete.
Checklist:
- [ ] Formaliser un statut terminal canonique du tour assistant (`complete`, `interrupted`, `failed_before_output`, ou equivalent retenu par le lot).
- [ ] Formaliser la regle produit de persistance en cas de stream interrompu.
- [ ] Choisir explicitement entre non-persistance, persistance partielle qualifiee, ou variante equivalente.
- [ ] Decider ou porte ce statut terminal: message, metadonnee laterale, ou structure equivalente.
- [ ] Implementer la garde retenue sans presenter un fragment comme reponse complete.
- [ ] Verifier qu'un echec court ne cree pas de message assistant fantome.
- [ ] Verifier qu'un fragment interrompu ne pollue ni la memoire ni l'historique comme s'il etait canonique.
- [ ] Documenter le choix retenu s'il depend d'une heuristique ou d'un statut d'interruption.

### Lot 6 — Adaptation des tests
- Objectif: adapter les tests existants au signal applicatif retenu et ajouter les tests des nouveaux comportements.
- Fichiers: `app/tests/test_server_phase14.py`, `app/tests/test_server_logs_phase3.py`, `app/tests/unit/chat/test_chat_llm_flow.py`.
- Done: suite complete et verte.
Checklist:
- [ ] Adapter les tests serveur au comportement de stream retenu.
- [ ] Ajouter un cas de fin normale avec signal applicatif.
- [ ] Ajouter un cas d'erreur mid-stream avec comportement frontend attendu.
- [ ] Ajouter ou ajuster les preuves d'observabilite associees.
- [ ] Revalider une suite complete verte apres adaptation.

### Lot 7 — Documentation du protocole
- Objectif: spec du protocole de streaming dans `app/docs/states/specs/`, pensee comme une grammaire d'evenements et non comme un simple format de bytes.
- Fichiers: `app/docs/states/specs/streaming-protocol.md` (nouveau).
- Done: un developpeur peut comprendre le protocole sans lire le code.
Checklist:
- [ ] Decrire le format de stream retenu et son contrat minimal.
- [ ] Decrire les types d'evenements ou signaux logiques du flux (`content`, `terminal success`, `terminal error`, `network interruption inferee`, ou equivalent retenu).
- [ ] Documenter les invariants du protocole (terminal unique, absence de contenu apres terminal, absence de controle dans la prose rendue).
- [ ] Documenter les cas de fin normale, d'erreur et de coupure reseau.
- [ ] Documenter la propagation des metadonnees utiles post-stream.
- [ ] Documenter la regle de persistance applicable en cas d'interruption.
- [ ] Relire la spec pour qu'elle reste comprensible sans retour au chat ni au code.

## Risques

- **Signal applicatif inline**: si le lot code retient des marqueurs dans le flux texte, il faudra verifier le risque de collision avec le contenu genere et definir une strategie simple de mitigation.
- **Chunk boundary**: si le signal applicatif est parse en flux, le frontend devra rester correct meme quand le delimiteur arrive a cheval sur plusieurs chunks TCP.
- **Regret protocolaire**: un format "texte + signal de controle" peut etre suffisant pour l'app actuelle sans constituer une cible long terme pour d'eventuelles surfaces tierces.
- **Confusion prose / regie**: si le plan de controle n'est pas suffisamment distinct, le frontend, les logs et la persistance peuvent traiter un artefact de transport comme du texte Frida.
- **Sur-interpretation UX**: une UI trop ambitieuse peut pretendre voir une activite backend qu'elle ne mesure pas reellement.
- **Tests existants**: les assertions qui supposent un flux texte nu devront etre adaptees si le transport ajoute un signal applicatif. Breaking change mineur mais reel.
- **Persistance conditionnelle (Lot 5)**: changer la logique du `finally` modifie un comportement existant. Le lot devra prouver qu'il n'ecarte pas de reponses valides et qu'il ne degrade pas la memoire conversationnelle.
- **Pollution memoire**: tant qu'un fragment interrompu peut etre traite comme reponse canonique, retrieval et memoire risquent de recycler un artefact d'echec comme un contenu valide.

## Preuves / validations attendues

Pour chaque lot:
- curl ou test unitaire prouvant le comportement attendu.
- `git diff --check` et `git status --short` propres apres chaque patch.
- Tests existants adaptes et verts.

Specifiquement:
- Lot 1: une preuve runtime montre un signal explicite de fin normale et un signal explicite d'erreur, avec le format retenu.
- Lot 2: le frontend affiche l'indicateur pendant l'attente, puis le retire a la terminaison du stream.
- Lot 3: `X-Conversation-Updated-At` ou son equivalent retenu est connu et utilise par le frontend post-stream.
- Lot 4: une erreur mid-stream produit un message intelligible cote utilisateur.
- Lot 5: un stream avorte avec peu ou pas de texte ne cree pas de message assistant presente comme complet en DB; si un fragment est conserve, son statut est explicite.
- Lot 6: tous les tests passent.
- Lot 7: le document spec est lisible et couvre format, erreurs, headers, persistance.

## Definition of done

Le streaming des reponses Frida est considere produit-pret quand:
- [ ] Le frontend distingue explicitement fin normale, erreur mid-stream, et coupure reseau.
- [ ] Le protocole distingue explicitement contenu et signaux de controle, meme si le transport physique reste unique.
- [ ] L'utilisateur a un feedback visuel pendant toute la generation (y compris buffering).
- [ ] Les etats UX affiches correspondent a des faits observables et non a une inference opaque sur l'activite backend.
- [ ] Les metadonnees de conversation sont completes post-stream.
- [ ] Aucun message assistant tronque ou fantome n'est persiste en DB.
- [ ] Aucun fragment interrompu n'est traite par defaut comme une reponse canonique pour l'historique ou la memoire.
- [ ] Tous les tests existants sont adaptes et passent.
- [ ] Le protocole est documente dans `app/docs/states/specs/`.
- [ ] L'observabilite du turn logger couvre les erreurs stream.
