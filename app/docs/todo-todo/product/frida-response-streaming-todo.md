# Frida Response Streaming TODO

Statut: ouvert
Classement: `app/docs/todo-todo/product/`
Nature: TODO canonique produit — fiabilisation du streaming des reponses Frida
Portee: `/api/chat`, transport de reponse, UX frontend, persistance, observabilite

## Contexte

Le streaming des reponses de Frida existe **deja de bout en bout**.

Ce n'est pas un chantier "ajouter le streaming", mais un chantier "fiabiliser, durcir et completer l'existant".

Le systeme actuel fonctionne dans la configuration suivante:
- le frontend envoie toujours `stream: true` a `POST /api/chat` (`app/web/app.js:624`);
- le backend parse la SSE OpenRouter dans `app/core/chat_llm_flow.py:191-196`;
- le texte extrait est envoye au navigateur en flux brut `text/plain; charset=utf-8` (`app/server.py:609`);
- le frontend lit le corps via `ReadableStream + TextDecoder` (`app/web/app.js:677-689`);
- la persistance conversation se fait dans le `finally` du generateur (`app/core/chat_llm_flow.py:240-276`).

## Etat actuel

### Ce qui fonctionne
- Le flux texte arrive bien du LLM au navigateur incrementalement (en mode non-bufferise).
- Les tests couvrent le stream normal, le stream normalise plain text, et le stream structure (`app/tests/test_server_phase14.py:175-390`).
- Le turn logger suit correctement le cycle de vie stream (`app/server.py:545-605`).
- La politique de buffering (`assistant_output_contract`) est fonctionnelle: plain text = bufferise en un bloc final, structure/code = stream progressif.

### Ce qui est fragile ou incomplet
- **Pas de signal de fin applicatif**: le frontend ne distingue pas fin normale de coupure reseau — il ne voit que la fermeture TCP.
- **Pas de signal d'erreur mid-stream**: une `RequestException` dans `chat_llm_flow.py:213` est loggee mais ne produit aucun signal visible cote frontend. Le texte partiel accumule est envoye sans indication d'erreur.
- **UX du buffering**: en mode plain text (cas le plus frequent), RIEN n'est affiche pendant toute la generation LLM. Le frontend attend en silence puis recoit tout d'un coup.
- **Pas de `X-Conversation-Updated-At` dans le stream**: les headers initiaux du stream omettent cette metadonnee (`chat_session_flow.py:61-65`). Le frontend ne connait jamais la date de mise a jour finale.
- **Persistance inconditionnelle en cas d'erreur**: si le stream avorte avec 3 caracteres de texte, ces 3 caracteres sont sauvegardes comme message assistant complet en DB.
- **Observabilité asymetrique**: les erreurs `RequestException` dans le generateur ne remontent pas au turn logger. Le turn se termine avec `status='ok'` meme si une erreur LLM s'est produite.
- **Comptage chars dans le wrapper**: le comptage `stream_response_chars` (`server.py:554-556`) est correct mais si des marqueurs de controle futuraux sont ajoutes au flux, ils seront comptes dans le total.

## Probleme produit

Ces limites ne sont pas des bugs bloquants, mais elles degradent l'experience conversationnelle:
- l'utilisateur ne sait pas si Frida a fini de repondre ou si la connexion a coupe;
- une erreur mid-stream produit un message d'erreur generique au lieu d'un statut clair de la reponse;
- le silence pendant le buffering donne l'impression que Frida ne repond pas;
- un texte partiel sauvegarde en DB fausse l'historique de conversation et la memoire.

## Contraintes / hors-scope

### Contraintes
- Le transport actuel est `text/plain` sur `POST /api/chat` avec `fetch + ReadableStream`. C'est fonctionnel et teste.
- EventSource ne fait pas POST nativement — passer a SSE standard exigerait de mettre le message utilisateur en query string (exposition URL) ou de garder fetch avec un parse SSE manuel.
- Le buffering est dicte par `assistant_output_contract`. Modifier ce comportement peut changer la presentation des reponses.

### Hors-scope de ce chantier (a moins que specifie ulterieurement)
- Refonte completa du transport vers SSE/WebSocket.
- Lots memoire, admin, platforme en parallele.
- Refactoring structurel de `chat_llm_flow.py` au-dela de ce que les lots demandent.

## Decision cible

**Le plan retenu est de completer l'existant plutot que de le remplacer.**

Arguments:
1. Le stream existe et est teste de bout en bout.
2. Les faiblesses sont incrementales (marqueurs fin/erreur, buffering UX, metadonnees, persistance conditionnelle).
3. Aucun avantage fonctionnel ne justifie une refonte vers SSE/WebSocket pour un contenu qui est du texte continu.
4. Le contrat `POST /api/chat + fetch + ReadableStream` est extensible (ajout de marqueurs de controle dans le flux texte).
5. La transition serait reversible: un marqueur de ligne est trivial a parser, et le format peut evoluer sans breaking change.

Le protocole cible:
- **Protocole**: texte brut + marqueurs de controle de ligne (ex: `::FRIDA::DONE`, `::FRIDA::ERROR:msg`).
- **Content-Type**: reste `text/plain; charset=utf-8`.
- **Frontend**: lit le flux comme aujourd'hui, detecte les marqueurs de controle.
- **Extensibilite**: les marqueurs utilisent un prefixe artificiel non linguistique qui n'a aucune chance d'etre genere par le LLM.

## Lots proposes

### Lot 0 — Preuves de comportement actuel
- Objectif: valider chaque scenario (stream normal, buffering, erreur) en runtime reel.
- Fichiers: aucun (preuves curl uniquement).
- Done: matrice documentee comportement x mode.

### Lot 1 — Marqueurs de fin et d'erreur
- Objectif: le frontend puisse distinguer fin normale d'erreur mid-stream.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: `::FRIDA::DONE` recu en fin normale; `::FRIDA::ERROR:msg` recu en cas d'erreur.

### Lot 2 — Feedback UX pendant l'attente
- Objectif: l'utilisateur a un indicateur visuel pendant le buffering.
- Fichiers: `app/web/app.js` (priorite), optionnellement `app/core/chat_llm_flow.py` pour une normalisation incrementale (phase 2).
- Done: indicateur "Frida reflechit..." visible des l'envoi, retire au DONE/ERROR.

### Lot 3 — Metadonnees post-stream
- Objectif: `X-Conversation-Updated-At` propage au frontend post-stream.
- Fichiers: `app/core/chat_llm_flow.py` (marqueur DONE avec updated_at), `app/web/app.js` (parse et setThreadMeta).
- Done: les metadonnees du thread incluent updated_at correct apres un stream complet.

### Lot 4 — Gestion d'erreurs mid-stream
- Objectif: erreur LLM visible et distinguable cote frontend.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: le frontend affiche le message d'erreur au lieu de "Erreur de connexion."; le thread n'est pas hydrate avec un texte tronque.

### Lot 5 — Persistance robuste en cas d'echec
- Objectif: pas de message assistant fantosome ou tronquee en DB apres un stream avorte.
- Fichiers: `app/core/chat_llm_flow.py` (gard de longueur minimale ou marqueur d'interruption).
- Done: stream erreur avec <seuil chars → pas de message DB; stream erreur avec texte suffisant → message avec indication d'interruption.

### Lot 6 — Adaptation des tests
- Objectif: adapter les tests existants aux nouveaux marqueurs et ajouter les tests des nouveaux comportements.
- Fichiers: `app/tests/test_server_phase14.py`, `app/tests/test_server_logs_phase3.py`, `app/tests/unit/chat/test_chat_llm_flow.py`.
- Done: suite complete et verte.

### Lot 7 — Documentation du protocole
- Objectif: spec du protocole de streaming dans `app/docs/states/specs/`.
- Fichiers: `app/docs/states/specs/streaming-protocol.md` (nouveau).
- Done: un developpeur peut comprendre le protocole sans lire le code.

## Risques

- **Marqueur dans le contenu genere**: `::FRIDA::DONE` est artificiel et improbabile, mais non impossible. Utiliser un prefixe avec caracteres de controle (`\x02`) eliminera ce risque au prix d'une lisibilite reduite dans les logs curl.
- **Chunk boundary**: un marqueur coupe entre deux chunks TCP peut etre rate. Le frontend doit accumuler un buffer de fin de chunk (20 chars) pour la verification.
- **Regret protocole**: le format "texte + marqueurs de ligne" est fonctionnel mais pas standard. Si l'app evolue vers des surfaces tierces (API publique, mobile), un wrapping JSON/SSE propre sera necessaire.
- **Tests existants**: les tests qui verifient `response.get_data(as_text=True) == 'text'` doivent etre adaptes pour filtrer les marqueurs. Breaking change mineur mais reel.
- **Persistance conditionnelle (Lot 5)**: changer la logique du finally modifie un comportement existant — il faut valider qu'aucun scenario ne perd de reponses valides.

## Preuves / validations attendues

Pour chaque lot:
- curl ou test unitaire prouvant le comportement attendu.
- `git diff --check` et `git status --short` propres apres chaque patch.
- Tests existants adaptes et verts.

Specifiquement:
- Lot 1: `curl -sN` montre `::FRIDA::DONE` en fin de flux; une erreur montre `::FRIDA::ERROR`.
- Lot 2: le frontend affiche l'indicateur pendant l'attente, le retire au DONE.
- Lot 3: `X-Conversation-Updated-At` est connu et utilise par le frontend post-stream.
- Lot 4: une erreur mid-stream produit un message intelligible cote utilisateur.
- Lot 5: un stream avorte avec peu de texte ne cree pas de message fantome en DB.
- Lot 6: tous les tests passent.
- Lot 7: le document spec est lisible et couvre format, erreurs, headers, persistance.

## Definition of done

Le streaming des reponses Frida est considere produit-pret quand:
- [ ] Le frontend distingue explicitement fin normale, erreur mid-stream, et coupure reseau.
- [ ] L'utilisateur a un feedback visuel pendant toute la generation (y compris buffering).
- [ ] Les metadonnees de conversation sont completes post-stream.
- [ ] Aucun message assistant tronque ou fantome n'est persiste en DB.
- [ ] Tous les tests existants sont adaptes et passent.
- [ ] Le protocole est documente dans `app/docs/states/specs/`.
- [ ] L'observabilité du turn logger couvre les erreurs stream.
