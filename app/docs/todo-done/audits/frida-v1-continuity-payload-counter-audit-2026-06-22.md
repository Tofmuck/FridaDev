# Frida V1 - Continuity Payload Counter-Audit - 2026-06-22

Archive documentaire: `app/docs/todo-done/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`, deplacee lors de la cloture Lot Z globale du 2026-08-19.

## Statut

Statut: contre-audit historique superseded par la cloture Lot Z Continuity
Payload.

Source de cloture courante:
`app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`

Artefact Lot Z:
`app/docs/states/baselines/continuity-payload-smokes/frida-v1-continuity-payload-lotz-closure-20260623T100649Z.jsonl`

Contrat courant:
`app/docs/states/specs/frida-v1-continuity-payload-contract.md`

Les findings P1/P2/P3 ci-dessous sont conserves comme constats historiques
produits avant Lot Z. Ils ne constituent plus un registre actif apres la
cloture Continuity Payload, sauf si une TODO active les rouvre explicitement.
Ne pas lire ce fichier comme une demande de correction produit courante.

Contre-audit read-only produit depuis la session lead, en parallele de l'audit principal demande a Celebrimbor.

Ce document ne modifie pas le runtime. Il synthetise quatre axes de relecture independants du payload modele et de la continuite conversationnelle:

- Axe A: construction du payload chat principal et ordre d'injection.
- Axe B: identity, mutable identity, memory RAG et summaries.
- Axe C: lanes agentiques et outils injectables.
- Axe D: tests, observabilite et preuves content-free disponibles.

Le fichier d'audit principal `app/docs/todo-done/audits/frida-v1-continuity-payload-audit-2026-06-22.md` est laisse intact pour Celebrimbor.

## Verdict court

Frida dispose deja de beaucoup de briques de continuite: system prompt hermeneutique, identity statique et mutable, active summary, memory RAG, traces, lanes Documents/Notes/Biblio/Agenda/Web, et observabilite agentique recente.

Le probleme n'est donc pas l'absence de memoire au sens simple. Le probleme est que la continuite personnelle et tonale n'est pas encore un objet produit explicite. Elle emerge de plusieurs voies heterogenes, avec des fenetres, priorites et preuves differentes.

Avant d'ecrire une `Continuity Capsule`, il faut d'abord rendre le payload final prouvable de maniere content-free. Sinon on risque d'ajouter une nouvelle couche sans savoir verifier clairement ce que le modele recoit vraiment.

## Findings

### P1 - Le payload final exact n'est pas prouvable content-free aujourd'hui

Le payload reel envoye au provider contient bien `messages` dans `app/core/llm_client.py:422`, mais l'observabilite actuelle expose surtout des compteurs et flags. L'evenement `prompt_prepared` dans `app/server.py:567` ne donne pas de manifeste final stable: pas de sequence finale des roles, pas d'origine de chaque bloc, pas de fingerprint court par message, pas de hash global du payload apres toutes les injections tardives.

Impact: on peut raisonner sur le code, mais on ne peut pas fermer proprement un audit de continuite en prouvant, sans contenu brut, que le modele a recu tel assemblage final dans tel ordre.

Correction cible: ajouter un `main_payload_manifest_v1` content-free avant toute capsule de continuite durable.

### P2 - Pas d'objet trans-conversationnel dedie a la continuite de presence

Les nouvelles conversations passent par `app/core/chat_session_flow.py`, puis recuperent identity, summary et memoire selon les chemins existants. L'active summary est attachee a la conversation courante, tandis que la memoire cross-conversation depend fortement de la requete courante.

Impact: une nouvelle conversation vague peut retrouver des faits, mais elle ne porte pas forcement la tonalite, la posture relationnelle, les motifs de travail et les continuites souples construites dans une longue conversation precedente.

Correction cible: specifier une `Continuity Capsule` distincte de l'identity canonique et du summary de conversation. Elle doit rester courte, contestable, non souveraine et explicite sur ses limites.

### P2 - Les fenetres de continuite divergent selon les sous-systemes

Les chemins relus montrent plusieurs fenetres actives:

- Memory RAG et signaux memoire s'appuient sur une fenetre recente propre.
- Le noeud hermeneutique utilise une fenetre recente reconstruite separement.
- Biblio et Agenda reconstruisent leur propre dialogue recent dans `app/core/chat_service.py`.
- Le prompt final est assemble ensuite par `app/core/conversations_prompt_window.py`.

Impact: plusieurs composants peuvent croire disposer du contexte recent pertinent, mais ne pas parler exactement du meme contexte. Cela peut produire une continuite instable, surtout sur les reprises longues ou les changements de conversation.

Correction cible: definir une source de verite content-free pour les fenetres de continuite, ou au minimum journaliser leurs empreintes et tailles respectives dans un manifeste commun.

### P2 - La mutable identity staging est conversation-scoped avant canonisation

La mutable identity est ecrite apres plusieurs paires de dialogue et passe par un staging rattache a la conversation. Avant canonisation dans la projection active, les signaux recents d'une conversation longue ne sont pas automatiquement disponibles dans une nouvelle conversation.

Impact: ce qui fait la presence fine des derniers tours peut etre perdu au demarrage d'une nouvelle conversation, meme si l'identite durable reste disponible.

Correction cible: ne pas transformer automatiquement le staging en identity globale, mais prevoir une capsule de reprise bornee qui peut etre derivee des derniers etats valides sans ecrire de contenu brut.

### P2 - Les lanes injectent du contexte comme messages `user`, ce qui brouille la provenance

Documents, Notes, Biblio et Adobe peuvent injecter des blocs de contexte dans le flux visible au provider sous forme de messages `user`. C'est fonctionnel, mais le provider ne voit pas toujours une distinction forte entre parole humaine et contexte recupere.

Impact: la continuite peut etre influencee par des blocs outilles qui ressemblent formellement a de la parole utilisateur.

Correction cible: dans le manifeste content-free, tracer l'origine de chaque bloc (`human_user`, `system_context`, `tool_lane_context`, `retrieved_document_context`, etc.). Cote prompt, envisager une convention plus explicite de delimitation des lanes.

### P2 - Conflit potentiel Agenda/Biblio final-lock avec priorite implicite Agenda

Dans `app/core/chat_service.py`, Biblio et Agenda peuvent produire des overrides finaux. La ligne `app/core/chat_service.py:1144` passe `agenda_final_response_override or biblio_final_response_override`, ce qui donne implicitement la priorite a Agenda si les deux surfaces verrouillent une reponse finale.

Impact: en cas de double activation, la continuite conversationnelle peut etre tranchee par une priorite implicite plutot que par une decision produit documentee.

Correction cible: declarer une politique de conflit final-lock et la tester. Cela peut rester simple, mais il faut que ce soit visible et volontaire.

### P2 - Notes V1 est branche cote backend mais pas expose dans le payload frontend chat

Le backend lit `workspace_note_id` / `workspace_note_ids` dans `app/core/workspace_folder_notes_prompt_lane.py:282`, mais le payload frontend courant de chat ne les envoie pas dans `app/web/app.js` autour du bloc de creation de requete.

Impact: une capacite de continuite par note existe, mais elle n'est pas naturellement activable dans la conversation utilisateur courante. On peut croire que la lane Notes contribue a la continuite alors qu'elle reste hors chemin UI normal.

Correction cible: soit documenter que Notes n'est pas une voie UI de continuite aujourd'hui, soit livrer un branchement explicite avec tests DOM et contrat serveur.

### P2 - L'observabilite writer-side accepte encore des champs payload arbitraires

`app/observability/chat_turn_logger.py:80` persiste `payload_json` apres une sanitation qui depend surtout des noms de champs connus. Les projections admin ont ete durcies, mais le writer reste une surface ou un futur appel pourrait introduire `messages`, `prompt`, `content` ou `payload` sous un champ non prevu.

Impact: le read-model admin peut rester content-free tout en laissant entrer du contenu brut dans le store historique si un futur writer se trompe.

Correction cible: ajouter un guard writer-side pour les cles dangereuses, sauf schema explicite et teste. Ce guard doit etre traite comme prerequisite de toute instrumentation de payload plus riche.

### P3 - Le soft limit prompt est observe, pas impose

`app/core/conversations_prompt_window.py:333` calcule `prompt_soft_limit_exceeded`, mais `dialogue_messages_truncated=False` reste pose plus loin. Le systeme observe le depassement sans prouver une politique d'exclusion ou de degradation.

Impact: sur conversation longue, le comportement depend encore de la tolerance du provider et de la taille finale, pas d'une strategie produit prouvee.

Correction cible: pour ce chantier, ne pas corriger tout de suite; ajouter d'abord un test de longue conversation qui prouve la composition finale et l'absence de fuite brute.

### P3 - Les no-op Documents/Notes ne sont pas toujours observables

`app/observability/active_documents_observability.py:224` retourne sans evenement quand rien n'est selectionne hors erreur. Les Notes suivent une logique comparable quand aucune note n'est demandee.

Impact: pour l'audit de continuite, il est difficile de distinguer proprement `non selectionne` de `lane non instrumentee`.

Correction cible: introduire des no-op content-free seulement si cela reste lisible et non bruyant. Ce n'est pas le premier patch a faire.

### P3 - Certaines docs historiques peuvent brouiller l'audit Identity

Les archives Identity gardent des traces de plans anciens, tandis que la spec active `mutable-identity-judge-contract.md` decrit le fonctionnement courant.

Impact: l'auditeur peut confondre doctrine cible, archive operatoire et runtime actuel.

Correction cible: dans l'audit principal, citer explicitement les trois statuts documentaires: spec active, plan doctrinal, archive de chantier.

## Ordre simplifie du payload principal

Carte reconstruite sans contenu brut:

1. `server.api_chat()` recoit la requete.
2. `chat_service.chat_response()` resout session, settings, toggles et dependances.
3. Le message utilisateur courant est ajoute a la conversation avant les phases memoire/summary.
4. Le summary peut etre mis a jour.
5. Le system prompt augmente assemble prompt principal, hermeneutique, temps canonique et identity.
6. Memory RAG, traces, hints et arbitrage preparent leur contexte.
7. Stimmung, web, documents actifs, notes, Biblio, Agenda et autres lanes peuvent preparer des blocs ou decisions.
8. Le noeud hermeneutique produit jugement et guards injectes dans le system.
9. `conversations_prompt_window.build_prompt_messages()` assemble system, active summary, hints, memory et dialogue recent.
10. Les injections tardives mutent ou inserent certains messages avant l'appel LLM.
11. `chat_llm_flow.run_llm_exchange()` appelle le provider, sauf override final Biblio/Agenda.

Point critique: l'etape 10 rend insuffisante une preuve limitee au prompt window intermediaire. Il faut prouver le payload apres injections tardives.

## Proposition de lots pour le chantier Continuity Payload

### Lot 0 - Audit principal read-only

Celebrimbor produit l'audit principal dans `frida-v1-continuity-payload-audit-2026-06-22.md`.

Ce contre-audit recommande que l'audit principal ne ferme pas le sujet sans:

- carte du payload final;
- carte des sources de continuite;
- liste des surfaces non prouvables;
- decision explicite sur la future capsule ou sur son report.

### Lot 1 - Payload manifest content-free

Ajouter un manifeste d'observabilite, pas le contenu:

- `payload_schema_version=main_payload_manifest_v1`;
- `message_count`;
- `role_sequence`;
- `lane_origin_sequence`;
- tailles par message;
- hash court par bloc apres redaction canonique;
- hash global court du payload final;
- flags `raw_prompt_included=false`, `raw_message_included=false`, `raw_lane_content_included=false`.

No-go: ne jamais logger les messages, prompts, documents, notes, passages, payload provider ou secrets.

### Lot 2 - Spec Continuity Capsule docs-only

Definir une capsule courte et non souveraine:

- posture relationnelle;
- style de travail;
- motifs recurrents;
- preferences de reprise;
- limites et incertitudes;
- dernier etat de travail utilisable;
- TTL ou conditions de renouvellement;
- contestabilite humaine.

No-go: pas de capsule qui fige une personnalite comme verdict psychologique; pas de resume intime expansif; pas d'ecriture depuis un seul tour faible.

### Lot 3 - Runtime borne de capsule

Seulement apres Lot 1 et Lot 2:

- injection au demarrage d'une nouvelle conversation ou apres long gap;
- pas d'ecriture brute;
- provenance et hash content-free;
- tests nouvelle conversation vague vs conversation existante;
- rollback simple via flag.

### Lot 4 - Lanes et conflits

Traiter les interactions qui perturbent la continuite:

- politique Agenda/Biblio final-lock;
- statut reel Notes UI;
- no-op observables Documents/Notes si utile;
- origine explicite des blocs outilles dans le manifeste.

## No-go immediats

- Ne pas ecrire une capsule avant d'avoir un manifeste final du payload.
- Ne pas persister de prompt brut, message brut, contenu document, note Markdown, passage Biblio, payload provider ou secret.
- Ne pas corriger la continuite par une simple rallonge de system prompt.
- Ne pas confondre identity durable, active summary, memory RAG et continuity capsule.
- Ne pas backfiller l'historique sans decision explicite.

## Checks effectues pour ce contre-audit

Commandes et lectures realisees en SSH sur OVH, sans mutation runtime:

- lecture de `AGENTS.md` distant;
- verification branche/status;
- relecture ciblee de `app/server.py`, `app/core/chat_service.py`, `app/core/conversations_prompt_window.py`, `app/core/llm_client.py`, `app/observability/chat_turn_logger.py`, `app/core/workspace_folder_notes_prompt_lane.py`, `app/web/app.js`;
- synthese de quatre sous-audits independants;
- aucune lecture ou conservation de prompt brut, message brut, secret ou payload provider.

## Conclusion

La direction saine n'est pas une usine a gaz memoire. C'est un objet tres borne en deux temps:

1. rendre le payload final prouvable sans contenu;
2. seulement ensuite definir une capsule de continuite courte, contestable et non souveraine.

Cette approche preserve ce qui fait deja la force de Frida: une presence construite dans le dialogue, sans transformer la relation en simple scoring operationnel.
