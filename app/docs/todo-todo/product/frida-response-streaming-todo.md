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

### Ce qui reste fragile ou incomplet
- **Pas de signal de fin applicatif**: le frontend ne distingue pas fin normale de coupure reseau — il ne voit que la fermeture TCP.
- **Pas de signal d'erreur mid-stream**: une `RequestException` dans `chat_llm_flow.py:213` est loggee mais ne produit aucun signal visible cote frontend. Le texte partiel accumule est envoye sans indication d'erreur.
- **UX du buffering**: en mode plain text (cas le plus frequent), rien n'est affiche pendant toute la generation LLM. Le frontend attend en silence puis recoit tout d'un coup.
- **Pas de `X-Conversation-Updated-At` dans le stream**: les headers initiaux du stream omettent cette metadonnee (`chat_session_flow.py:61-65`). Le frontend ne connait jamais la date de mise a jour finale.
- **Persistance inconditionnelle en cas d'erreur**: si le stream avorte avec 3 caracteres de texte, ces 3 caracteres sont sauvegardes comme message assistant complet en DB.
- **Observabilite asymetrique**: les erreurs `RequestException` dans le generateur ne remontent pas au turn logger. Le turn se termine avec `status='ok'` meme si une erreur LLM s'est produite.
- **Comptage chars dans le wrapper**: le comptage `stream_response_chars` (`server.py:554-556`) est correct pour le flux actuel, mais devra etre re-verifie si le transport ajoute un signal de controle applicatif.

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
- Refonte complete du transport vers SSE/WebSocket.
- Lots memoire, admin, plateforme en parallele.
- Refactoring structurel de `chat_llm_flow.py` au-dela de ce que les lots demandent.

## Cadrage produit

### Decision deja prise

Le chantier vise a completer l'existant plutot qu'a remplacer le transport actuel.

Ce cadrage implique:
- conserver `POST /api/chat + fetch + ReadableStream` comme base de travail pour ce lot;
- traiter le sujet comme un lot produit de fiabilisation, pas comme une refonte protocolaire;
- ordonner le travail en petits lots testables et reversibles.

### Ce document ne tranche pas encore

Ce TODO ne fixe pas a lui seul:
- le format exact du signal applicatif de fin normale et d'erreur;
- la forme du transport de metadonnees post-stream;
- la regle precise de persistance en cas d'interruption;
- le niveau de feedback UX minimal pendant le buffering.

### Option technique legere a evaluer

Une piste simple consiste a conserver le flux `text/plain` actuel et a y ajouter un signal applicatif parseable cote frontend.

Les marqueurs inline de type `::FRIDA::DONE` / `::FRIDA::ERROR:...` font partie des options possibles, mais ils ne doivent pas etre traites ici comme protocole deja tranche. Le lot code devra confirmer si cette option est la plus lisible, la plus sure et la plus reversible, ou s'il faut lui preferer une variante equivalente.

## Lots proposes

### Lot 0 — Preuves de comportement actuel
- Objectif: valider chaque scenario (stream normal, buffering, erreur) en runtime reel.
- Fichiers: aucun (preuves curl uniquement).
- Done: matrice documentee comportement x mode.
Checklist:
- [ ] Verifier le comportement du stream non-bufferise en runtime reel.
- [ ] Verifier le comportement du buffering plain text en runtime reel.
- [ ] Verifier le comportement observable en cas d'erreur upstream pendant le stream.
- [ ] Consigner une matrice simple comportement x mode x issue.

### Lot 1 — Signal applicatif de fin et d'erreur
- Objectif: le frontend puisse distinguer fin normale d'erreur mid-stream.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: un signal explicite de fin normale et un signal explicite d'erreur sont recues et interpretes cote frontend, avec un format documente dans le lot.
Checklist:
- [ ] Choisir un format minimal de signal applicatif compatible avec le transport actuel.
- [ ] Emettre un signal explicite en fin normale de stream.
- [ ] Emettre un signal explicite en cas d'erreur mid-stream.
- [ ] Parser correctement ce signal cote frontend.
- [ ] Verifier que le format retenu reste simple a tester et a faire evoluer.

### Lot 2 — Feedback UX pendant l'attente
- Objectif: l'utilisateur a un indicateur visuel pendant le buffering.
- Fichiers: `app/web/app.js` (priorite), optionnellement `app/core/chat_llm_flow.py` pour une normalisation incrementale (phase 2).
- Done: un indicateur d'attente est visible des l'envoi et disparait quand le stream se termine normalement ou en erreur.
Checklist:
- [ ] Afficher un indicateur d'attente des l'envoi de la requete.
- [ ] Conserver cet indicateur tant qu'aucun contenu n'est visible pendant le buffering.
- [ ] Retirer proprement l'indicateur a la fin normale du stream.
- [ ] Retirer proprement l'indicateur en cas d'erreur mid-stream.
- [ ] Verifier que le feedback ne se confond pas avec un etat de chargement bloque.

### Lot 3 — Metadonnees post-stream
- Objectif: `X-Conversation-Updated-At` propage au frontend post-stream.
- Fichiers: `app/core/chat_llm_flow.py`, `app/web/app.js`.
- Done: les metadonnees du thread incluent updated_at correct apres un stream complet.
Checklist:
- [ ] Choisir le canal de propagation post-stream de `updated_at`.
- [ ] Rendre cette metadonnee disponible a la fin d'un stream complet.
- [ ] Reinjecter correctement cette valeur dans le thread cote frontend.
- [ ] Verifier l'absence de divergence entre l'affichage frontend et l'etat persiste.

### Lot 4 — Gestion d'erreurs mid-stream
- Objectif: erreur LLM visible et distinguable cote frontend.
- Fichiers: `app/core/chat_llm_flow.py`, `app/server.py`, `app/web/app.js`.
- Done: le frontend affiche un statut d'erreur intelligible, distinct d'une simple coupure reseau, et le thread n'est pas presente comme complet quand la reponse a echoue.
Checklist:
- [ ] Faire remonter un statut d'erreur applicatif exploitable jusqu'au frontend.
- [ ] Distinguer cote UI une erreur mid-stream d'une simple coupure reseau.
- [ ] Eviter de presenter la reponse comme terminee quand le stream a echoue.
- [ ] Verifier la coherence entre message utilisateur, etat du thread et observabilite.

### Lot 5 — Persistance robuste en cas d'echec
- Objectif: eviter qu'une reponse interrompue soit persistee comme message assistant complet.
- Fichiers: `app/core/chat_llm_flow.py`.
- Done: la regle produit de persistance en cas d'echec est explicite, implementee et testee. Si une heuristique de longueur, un statut d'interruption ou une autre garde est retenue, elle est documentee comme choix du lot code et non comme hypothese implicite.
Checklist:
- [ ] Formaliser la regle produit de persistance en cas de stream interrompu.
- [ ] Choisir explicitement entre non-persistance, persistance partielle qualifiee, ou variante equivalente.
- [ ] Implementer la garde retenue sans presenter un fragment comme reponse complete.
- [ ] Verifier qu'un echec court ne cree pas de message assistant fantome.
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
- Objectif: spec du protocole de streaming dans `app/docs/states/specs/`.
- Fichiers: `app/docs/states/specs/streaming-protocol.md` (nouveau).
- Done: un developpeur peut comprendre le protocole sans lire le code.
Checklist:
- [ ] Decrire le format de stream retenu et son contrat minimal.
- [ ] Documenter les cas de fin normale, d'erreur et de coupure reseau.
- [ ] Documenter la propagation des metadonnees utiles post-stream.
- [ ] Documenter la regle de persistance applicable en cas d'interruption.
- [ ] Relire la spec pour qu'elle reste comprensible sans retour au chat ni au code.

## Risques

- **Signal applicatif inline**: si le lot code retient des marqueurs dans le flux texte, il faudra verifier le risque de collision avec le contenu genere et definir une strategie simple de mitigation.
- **Chunk boundary**: si le signal applicatif est parse en flux, le frontend devra rester correct meme quand le delimiteur arrive a cheval sur plusieurs chunks TCP.
- **Regret protocolaire**: un format "texte + signal de controle" peut etre suffisant pour l'app actuelle sans constituer une cible long terme pour d'eventuelles surfaces tierces.
- **Tests existants**: les assertions qui supposent un flux texte nu devront etre adaptees si le transport ajoute un signal applicatif. Breaking change mineur mais reel.
- **Persistance conditionnelle (Lot 5)**: changer la logique du `finally` modifie un comportement existant. Le lot devra prouver qu'il n'ecarte pas de reponses valides et qu'il ne degrade pas la memoire conversationnelle.

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
- [ ] L'utilisateur a un feedback visuel pendant toute la generation (y compris buffering).
- [ ] Les metadonnees de conversation sont completes post-stream.
- [ ] Aucun message assistant tronque ou fantome n'est persiste en DB.
- [ ] Tous les tests existants sont adaptes et passent.
- [ ] Le protocole est documente dans `app/docs/states/specs/`.
- [ ] L'observabilite du turn logger couvre les erreurs stream.
