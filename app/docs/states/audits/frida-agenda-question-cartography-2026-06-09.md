# Frida Agenda - Cartographie des questions utilisateur

Date: 2026-06-09
Classement: `app/docs/states/audits/`
Branche: `FridaAgenda`
Commit source lu initialement: `2d2e78c docs: map Agenda user question families`
Smokes cibles lus: `8298f7f docs: clarify Agenda question cartography status`
Scope initial: docs-only. Mise a jour: reference les smokes cibles
content-free du 2026-06-09, sans mutation et sans contenu agenda personnel.

## 1. Resume executif

Cette cartographie separe maintenant deux axes qui ne doivent plus etre
melanges:

- `Disponible utilisateur`: ce que l'utilisateur peut tenter de demander a
  Frida Agenda aujourd'hui, parce que le contrat, l'agent ou les outils savent
  deja le porter au moins en partie;
- `Preuve conservee`: ce qui est formellement ferme par test, smoke live JSONL
  content-free ou preuve documentaire conservee.

Donc:

- `Disponible utilisateur = oui` ne veut pas dire que la famille est totalement
  fermee par preuve complete;
- `Preuve conservee = non` ne veut pas dire que la capacite est absente;
- une capacite plausible parce que l'agent peut la router reste a tester si
  aucun smoke dedie n'existe.

Frida Agenda sait traiter un noyau read-only solide: lire une fenetre bornee,
chercher localement dans une fenetre lue, trouver le prochain evenement futur
correspondant a un terme, restituer une reponse assistant normale, et garder
l'observabilite content-free. Les evenements journee entiere multi-jours sont
rendus comme des plages avec duree, ce qui donne au tour suivant assez de
contexte visible pour raisonner sur un sejour.

Frida sait aussi preparer des propositions de creation, modification,
suppression et replanification sans ecriture immediate. Les confirmations
humaines sont explicitement protegees: creation et suppression sont prouvees en
fake/local, creation synthetique live et rollback ont ete prouves, update
confirme est prouve en fake/local seulement avec preservation du payload
calendrier source sur cas simple. Le calendrier familial ou partage est
fail-closed: statut inconnu ou familial exige prudence renforcee.

Ce qui reste fragile ou insuffisamment prouve: sous-fenetres vernaculaires
comme matin/apres-midi/soir, questions de duree routees par l'agent,
disponibilites, comparaison de journees, resume de journee riche, reprise
multi-tour prouvee famille par famille, evenements recurrents complexes en
usage produit, aide conversationnelle du type "qu'est-ce que tu peux faire avec
mon agenda ?", rappels/notifications, participants/invitations, et mutations
utilisateur reelles au-dela du smoke synthetique borne.

Smokes cibles de cloture pragmatique executes le 2026-06-09:

- artefact:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T171000Z.jsonl`;
- familles testees: date explicite, sous-fenetres vernaculaires,
  duree/sejour/reprise multi-tour, aide/perimetre operateur;
- scan content-free: `met`;
- mutation: `false`;
- verdict global: `partial`, donc aucune cloture pragmatique Agenda V1 n'est
  declaree par cette preuve.

A tester ensuite: corriger ou revalider les familles ciblees reste plus utile
que parcourir les 25 familles. Les chantiers prioritaires sont les dates
explicites qui finissent en erreur d'outil, les sous-fenetres vernaculaires
matin/apres-midi/soir, la duree/sejour avec cible multi-jours reelle, puis une
surface d'aide/perimetre dediee.

## 2. Mode de lecture des statuts

Valeurs `Disponible utilisateur`:

- `oui`: l'utilisateur peut poser la question; le chemin produit existe.
- `partiel`: la question est tentable, mais seulement dans un sous-cas, avec
  clarification, ou sans preuve produit complete.
- `non`: la capacite n'est pas livree comme comportement utilisateur.
- `refuse`: la demande doit etre refusee ou conditionnee par design.
- `admin`: sujet operateur/client hors code runtime Agenda.

Valeurs `Preuve conservee`:

- `oui`: preuve dediee conservee par test, smoke ou artefact.
- `partielle`: preuve sur une brique ou un sous-cas, pas sur toute la famille.
- `non`: aucune preuve dediee conservee pour la famille complete.
- `sans objet`: famille refusee ou administrative, donc pas de preuve produit
  runtime attendue au meme sens.

## 2.1 Smokes cibles du 2026-06-09

Ces smokes ne remplacent pas la table complete. Ils servent seulement a verifier
quatre familles proches de l'usage quotidien reel.

| Famille ciblee | Verdict | Preuve | Interpretation produit |
|---|---|---|---|
| Date explicite | partial | `read_explicit_date` route et tente CalDAV/Nextcloud read-only, mais finit en `agenda_readonly_tool_error` controle | La capacite reste disponible a tenter, mais pas cloturee par preuve convaincante |
| Sous-fenetres vernaculaires | partial | un cas `ce matin` echoue avec `agenda_agent_time_window_mismatch`; un cas `demain soir` lit une fenetre 24h | Les sous-fenetres ne doivent pas etre vendues comme prouvees |
| Duree/sejour/reprise multi-tour | partial | contexte multi-tour present, mais aucune cible multi-jours trouvee dans le smoke | Le rendu multi-jours existe, mais la question de duree reste a prouver sur donnees adequates |
| Aide/perimetre operateur | partial | une reponse de capacites est sauvegardee; la surface des confirmations reste insuffisamment prouvee | Besoin d'une surface d'aide produit dediee avant de dire que la famille est fermee |

## 3. Carte des familles de questions

| Famille | Exemples de questions utilisateur | Disponible utilisateur | Preuve conservee | Chemin technique | Limite connue | Prochain test utile |
|---|---|---|---|---|---|---|
| Lire aujourd'hui, fenetre complete | `Qu'est-ce que j'ai aujourd'hui ?`<br>`J'ai quoi dans mon agenda aujourd'hui ?`<br>`Montre-moi mon agenda du jour.` | oui | oui | `read_today` -> `event_query_range` avec fenetre canonique locale | La fenetre complete est prouvee; les sous-fenetres ne le sont pas implicitement | Smoke read-only journee complete |
| Lire demain, fenetre complete | `J'ai quelque chose demain ?`<br>`Rappelle-moi mon agenda de demain.`<br>`Demain, j'ai des rendez-vous importants ?` | oui | oui | `read_tomorrow` -> `event_query_range` avec fenetre canonique locale | La fenetre complete est prouvee; les sous-fenetres ne le sont pas implicitement | Smoke read-only demain complet |
| Sous-fenetres vernaculaires | `J'ai quoi ce matin ?`<br>`Et demain soir ?`<br>`Est-ce que je suis pris cet apres-midi ?` | partiel | partielle | Agent -> date locale + fenetre horaire a produire; execution par `event_query_range` | Smoke cible: `ce matin` echoue avant lecture; `demain soir` retombe sur 24h, donc sous-fenetre non prouvee | Lot sous-fenetres vernaculaires |
| Lire une date explicite | `Tu peux me rappeler ce que j'ai vendredi ?`<br>`Qu'est-ce que j'ai le 18 juin ?`<br>`Regarde mon agenda pour lundi prochain.` | oui | partielle | `read_explicit_date` -> `event_query_range` | Smoke cible: methode routee et acces CalDAV tente, mais erreur d'outil controlee; pas encore convaincant | Smoke dates explicites apres correction |
| Lire une semaine ou une periode | `Qu'est-ce que j'ai la semaine prochaine ?`<br>`Montre-moi mon agenda du 10 au 14.`<br>`Je suis charge cette semaine ?` | partiel | non | `read_week` ou periode explicite -> fenetres bornees | Disponible a tenter, mais synthese periode et limites de largeur restent a prouver | Lot periode/semaine |
| Chercher par mot, personne ou lieu dans une fenetre | `Cherche les rendez-vous avec [personne].`<br>`Tu vois quelque chose a propos de [mot-cle] ?`<br>`J'ai un rendez-vous a [lieu] cette semaine ?` | oui | partielle | `search_events` -> `event_query_range` puis `event_search` local | Depend d'une fenetre fournie par l'agent; pas une recherche future progressive | Smokes search par formulations |
| Trouver le prochain evenement correspondant a X | `Quand est mon prochain rendez-vous avec [personne] ?`<br>`Quand est-ce que je vois [personne] ?`<br>`C'est quand mon prochain evenement contenant [mot-cle] ?` | oui | oui | `find_next_matching_event` -> fenetres futures 31 jours, horizon 365 jours, arret au premier match | Match textuel simple; horizon fixe; pas de semantique avancee | Variantes vernaculaires anonymisees |
| Obtenir les details d'un evenement deja identifie | `Ouvre ce rendez-vous.`<br>`Tu peux me donner les details de cet evenement ?`<br>`C'est ou, ce rendez-vous ?` | partiel | partielle | `event_details` -> `event_get` sur id local deja connu | Reprise multi-tour vers la bonne cible a prouver en conversation reelle | Lot reprise details |
| Demander la duree d'un evenement ou sejour | `Combien de temps dure ce rendez-vous ?`<br>`Combien de temps j'y reste ?`<br>`Mon sejour a [lieu], c'est du quand au quand ?` | partiel | partielle | Contexte visible apres rendu plage, ou relecture details | Rendu multi-jours prouve; smoke cible avec reprise presente mais aucune cible multi-jours trouvee | Lot duree/sejour/reprise avec cible adequate |
| Demander les evenements d'un calendrier precis | `Qu'est-ce qu'il y a dans le calendrier famille ?`<br>`Lis seulement mon calendrier perso.`<br>`Montre-moi le calendrier [type].` | partiel | non | `calendar_scope.calendar_ids` + `event_query_range` | Selection vernaculaire du calendrier et classification a prouver | Smoke calendar-scope content-free |
| Demander les evenements du calendrier familial/partage | `Qu'est-ce qu'il y a dans le calendrier familial ?`<br>`On a quoi dans le calendrier partage ?`<br>`Regarde le calendrier de la famille.` | partiel | partielle | Read-only via calendrier cible; mutations fail-closed via policy familiale | Protection mutation prouvee; lecture ciblee famille non prouvee live | Smoke read-only calendrier familial |
| Demander disponibilites ou creneaux libres | `J'ai un trou demain ?`<br>`Quand est-ce que je suis libre cette semaine ?`<br>`Trouve-moi un creneau d'une heure.` | partiel | non | `find_availability` declare; lecture d'evenements possible | La derivation de creneaux libres n'est pas livree comme vraie capacite riche | Lot disponibilites |
| Resumer une journee | `Resume ma journee.`<br>`Dis-moi si ma journee est chargee.`<br>`Fais-moi le point sur demain.` | partiel | non | `summarize_day` declare; lecture de fenetre possible | Synthese qualitative non prouvee au-dela d'une liste courte | Lot resume journee |
| Comparer deux evenements ou deux journees | `Demain est plus charge qu'aujourd'hui ?`<br>`Compare lundi et mardi.`<br>`Lequel de ces deux rendez-vous dure le plus ?` | non | non | Pas de methode produit dediee | Besoin de lecture de deux fenetres + comparaison bornee | Lot comparaison |
| Reprendre une reponse Agenda precedente | `Et celui d'apres ?`<br>`Combien de temps j'y reste ?`<br>`Tu peux me redonner le lieu ?` | partiel | partielle | Contexte dialogue normal + details si ancre disponible | Reprise par famille non prouvee; resolution de reference encore fragile | Lot reprise multi-tour |
| Creer un evenement | `Cree-moi un rendez-vous chez le medecin mardi a 14h.`<br>`Ajoute un dejeuner vendredi midi.`<br>`Note un appel lundi a 9h.` | partiel | partielle | `propose_create_event`, pending draft, puis confirmation | Proposition livree; mutation utilisateur reelle non autorisee sauf smoke synthetique borne | Lot mutations utilisateur avec GO explicite |
| Modifier un evenement | `Change le titre de ce rendez-vous.`<br>`Ajoute le lieu a cet evenement.`<br>`Corrige la description de celui-ci.` | partiel | partielle | `propose_update_event`, cible verifiee, update fake/local preserve source | Pas d'update live utilisateur; recurrent/multi-composant fail-closed | Lot update live synthetique puis utilisateur |
| Deplacer ou replanifier un evenement | `Deplace le rendez-vous de demain a 15h.`<br>`Reporte cet appel a vendredi.`<br>`Replanifie ce rendez-vous la semaine prochaine.` | partiel | partielle | `propose_reschedule` ou update draft avec start/end | Cible claire a prouver; live update ferme | Lot reschedule fake/live borne |
| Supprimer un evenement | `Supprime ce rendez-vous.`<br>`Enleve l'evenement de demain.`<br>`Annule ce bloc dans mon agenda.` | partiel | partielle | `propose_delete_event`, pending reinforced, confirmation ciblee | Suppression utilisateur reelle non autorisee; cible technique et preflight obligatoires | Lot deletion utilisateur avec GO explicite |
| Annuler une action pending | `Annule cette proposition.`<br>`Finalement ne le fais pas.`<br>`Oublie cette action en attente.` | oui | oui | `cancel_pending_agenda_action` + pending store | UX conversationnelle a valider plus largement | Smoke pending cancel |
| Rappels, notifications, alarmes | `Ajoute un rappel pour [activite].`<br>`Previens-moi une heure avant.`<br>`Mets une alarme sur cet evenement.` | non | non | Aucun champ reminder/alarme livre dans le draft V1 | Pas de support `VALARM`/reminder en creation, update ou rendu | Lot reminders si decide |
| Participants et invitations | `Invite [personne] a ce rendez-vous.`<br>`Qui est invite ?`<br>`Ajoute quelqu'un a cet evenement.` | non | non | Les champs participant/organisateur ne sont pas des surfaces produit V1 | Les proprietes d'invitation sont traitees comme techniques et non exposees comme draft utilisateur | Lot invitations si decide |
| Recurrences, repetitions et occurrence unique | `Ajoute ca tous les lundis.`<br>`Deplace seulement cette occurrence.`<br>`Supprime cette repetition.` | partiel | partielle | Lecture recurrente bornee existe; update recurrent/multi-composant fail-closed | Creation/update/suppression d'occurrence recurrente non livrees comme action utilisateur | Lot recurrence produit |
| Demander ce que Frida peut faire avec l'agenda | `Qu'est-ce que tu peux faire avec mon agenda ?`<br>`Tu sais faire quoi avec le calendrier ?`<br>`Quelles questions je peux te poser ?` | partiel | partielle | Reponse conversationnelle generale; pas de methode aide produit dediee | Smoke cible sauvegarde une reponse, mais la surface n'est pas encore une aide productisee | Lot aide utilisateur Agenda |
| Perimetre, capacites et calendriers accessibles | `Quels calendriers tu peux lire ?`<br>`Dans quels calendriers tu peux ecrire ?`<br>`Qu'est-ce qui demande confirmation ?` | partiel | partielle | Peut s'appuyer sur contrat/runtime redacted et calendrier lu | Smoke cible partiel sur confirmations; ne pas vendre comme ferme | Lot aide operatoire Agenda |
| Gerer conflit ou ambiguite | `Le rendez-vous de demain, deplace-le.`<br>`Ajoute ca au calendrier.`<br>`Supprime le mauvais doublon.` | partiel | partielle | `clarify_agenda_request`, guards cible/calendrier/date | Surfaces de clarification par famille peu prouvees | Lot clarification smokes |
| Action impossible ou dangereuse | `Supprime tous mes rendez-vous.`<br>`Modifie le calendrier familial sans confirmer.`<br>`Fais-le sans me redemander.` | refuse | sans objet | Validation mutation, pending store, confirmation renforcee, policy familiale | Besoin de messages visibles harmonises par danger | Lot refus dangereux surfaces |
| Frottements clients ou administration calendrier | `Pourquoi mon telephone ne voit pas l'agenda ?`<br>`[Proche] ne voit pas le calendrier.`<br>`Le Mac ne synchronise pas.` | admin | sans objet | Hors runtime Agenda; sujet client/configuration | Peut necessiter runbook operateur, pas code agent | Guide admin client si besoin |

## 4. Exemples de formulations par famille

### Lire aujourd'hui, fenetre complete

- Qu'est-ce que j'ai aujourd'hui ?
- J'ai quoi dans mon agenda aujourd'hui ?
- Montre-moi mon agenda du jour.
- Tu peux me faire le point sur ma journee ?

### Lire demain, fenetre complete

- Qu'est-ce que j'ai demain ?
- Rappelle-moi mon agenda de demain.
- Demain, j'ai des rendez-vous importants ?
- Tu peux verifier si demain est libre ?

### Sous-fenetres vernaculaires

- Est-ce que j'ai quelque chose ce matin ?
- J'ai quoi cet apres-midi ?
- Et demain soir ?
- Je suis pris avant midi ?

### Lire une date explicite

- Tu peux me rappeler ce que j'ai vendredi ?
- Qu'est-ce que j'ai le 18 juin ?
- Regarde mon agenda pour lundi prochain.
- Est-ce que le mardi 23 est charge ?

### Lire une semaine ou une periode

- Qu'est-ce que j'ai la semaine prochaine ?
- Montre-moi mon agenda du 10 au 14.
- Cette semaine est comment ?
- Tu peux regarder mes rendez-vous entre lundi et mercredi ?

### Chercher un evenement par mot/personne/lieu

- Cherche les rendez-vous avec [personne].
- Tu vois quelque chose a propos de [mot-cle] ?
- J'ai un rendez-vous a [lieu] cette semaine ?
- Retrouve le rendez-vous chez [professionnel].

### Trouver le prochain evenement correspondant a X

- Quand est mon prochain rendez-vous avec [personne] ?
- Quand est-ce que je vois [personne] ?
- C'est quand mon prochain evenement contenant [mot-cle] ?
- Mon prochain rendez-vous chez [professionnel], c'est quand ?

### Obtenir les details d'un evenement deja identifie

- Ouvre ce rendez-vous.
- Tu peux me donner les details de cet evenement ?
- C'est ou, ce rendez-vous ?
- Redonne-moi les infos pratiques de celui-ci.

### Demander la duree d'un evenement ou d'un sejour

- Combien de temps dure ce rendez-vous ?
- Combien de temps j'y reste ?
- Mon sejour a [lieu], c'est du quand au quand ?
- Combien de jours dure ce bloc ?

### Demander les evenements d'un calendrier precis

- Qu'est-ce qu'il y a dans le calendrier familial ?
- Lis seulement mon calendrier perso.
- Montre-moi le calendrier [type].
- Tu peux filtrer sur le calendrier famille ?

### Demander les evenements du calendrier familial/partage

- Qu'est-ce qu'il y a dans le calendrier familial ?
- On a quoi dans le calendrier partage ?
- Regarde le calendrier de la famille.
- Est-ce que ce bloc est dans un calendrier partage ?

### Demander disponibilites ou creneaux libres

- J'ai un trou demain ?
- Quand est-ce que je suis libre cette semaine ?
- Trouve-moi un creneau d'une heure.
- Est-ce que mardi apres-midi est disponible ?

### Resumer une journee

- Resume ma journee.
- Dis-moi si ma journee est chargee.
- Fais-moi le point sur demain.
- Qu'est-ce qui structure ma journee ?

### Comparer deux evenements ou deux journees

- Demain est plus charge qu'aujourd'hui ?
- Compare lundi et mardi.
- Lequel de ces deux rendez-vous dure le plus ?
- J'ai plus de disponibilite mercredi ou jeudi ?

### Reprendre une reponse Agenda precedente

- Et celui d'apres ?
- Combien de temps j'y reste ?
- Tu peux me redonner le lieu ?
- Est-ce que tu peux ouvrir celui-la ?

### Creer un evenement

- Cree-moi un rendez-vous chez le medecin mardi a 14h.
- Ajoute un dejeuner vendredi midi.
- Note un appel lundi a 9h.
- Ajoute un evenement toute la journee pour [sujet].

### Modifier un evenement

- Change le titre de ce rendez-vous.
- Ajoute le lieu a cet evenement.
- Corrige la description de celui-ci.
- Decale la fin a 16h.

### Deplacer ou replanifier un evenement

- Deplace le rendez-vous de demain a 15h.
- Reporte cet appel a vendredi.
- Replanifie ce rendez-vous la semaine prochaine.
- Avance ce bloc d'une heure.

### Supprimer un evenement

- Supprime ce rendez-vous.
- Enleve l'evenement de demain.
- Annule ce bloc dans mon agenda.
- Retire le rendez-vous avec [personne].

### Annuler une action pending

- Annule cette proposition.
- Finalement ne le fais pas.
- Oublie cette action en attente.
- Ne cree pas ce rendez-vous.

### Rappels, notifications, alarmes

- Ajoute un rappel pour [activite].
- Previens-moi une heure avant.
- Mets une alarme sur cet evenement.
- Rappelle-moi ce rendez-vous demain matin.

### Participants et invitations

- Invite [personne] a ce rendez-vous.
- Qui est invite ?
- Ajoute quelqu'un a cet evenement.
- Reponds a cette invitation.

### Recurrences, repetitions et occurrence unique

- Ajoute ca tous les lundis.
- Deplace seulement cette occurrence.
- Supprime cette repetition.
- C'est tous les mois ?

### Demander ce que Frida peut faire avec l'agenda

- Qu'est-ce que tu peux faire avec mon agenda ?
- Tu sais faire quoi avec le calendrier ?
- Quelles questions je peux te poser ?
- Tu peux modifier mon agenda ou seulement le lire ?

### Perimetre, capacites et calendriers accessibles

- Quels calendriers tu peux lire ?
- Dans quels calendriers tu peux ecrire ?
- Qu'est-ce qui demande confirmation ?
- Tu peux modifier le calendrier familial ?

### Gerer conflit ou ambiguite

- Le rendez-vous de demain, deplace-le.
- Ajoute ca au calendrier.
- Supprime le mauvais doublon.
- Mets-le dans le calendrier famille.

### Action impossible ou dangereuse

- Supprime tous mes rendez-vous.
- Modifie le calendrier familial sans confirmer.
- Fais-le sans me redemander.
- Change tous les evenements de la semaine.

### Frottements clients ou administration calendrier

- Pourquoi mon telephone ne voit pas l'agenda ?
- [Proche] ne voit pas le calendrier.
- Le Mac ne synchronise pas.
- Comment ajouter le calendrier sur mon telephone ?

## 5. Matrice "ca doit repondre comment"

| Famille | Forme attendue |
|---|---|
| Lire aujourd'hui / demain / date | Liste courte ou message vide honnete; fallback agentique si lecture live echoue. |
| Sous-fenetres vernaculaires | Liste bornee a la sous-fenetre si routee; sinon clarification plutot que fausse precision. |
| Lire semaine / periode | Liste courte ou synthese; demander clarification si periode trop vague ou trop large. |
| Chercher dans une fenetre | Reponse directe si un match, liste courte si plusieurs, no-result honnete si aucun. |
| Prochain evenement correspondant | Reponse directe avec date locale, heure ou plage, titre/lieu visibles si lus; no-result dans l'horizon borne. |
| Details evenement | Reponse directe si cible unique; clarification si plusieurs candidats ou cible absente. |
| Duree / sejour | Reponse directe depuis contexte visible ou evenement relu; clarification si reference ambigue. |
| Calendrier precis | Liste courte du calendrier cible; clarification si calendrier ambigu ou non classifie pour mutation. |
| Calendrier familial | Read-only possible; mutation create/delete en confirmation renforcee ou refus si ambigu. |
| Disponibilites | A terme, creneaux libres; aujourd'hui, ne pas promettre une vraie recherche de disponibilites. |
| Resume journee | Synthese courte; aujourd'hui statut non prouve au-dela de la liste. |
| Comparaison | Demande de clarification ou refus honnete tant que non livre. |
| Reprise precedente | Reponse directe si l'ancre dialogue suffit; sinon clarification. |
| Creation | Proposition en attente + confirmation; pas de "c'est cree" avant confirmation et write autorise. |
| Modification / deplacement | Proposition en attente si cible verifiee; confirmation; update live utilisateur non prouve. |
| Suppression | Proposition en attente + confirmation renforcee; jamais autonome. |
| Annulation pending | Confirmation d'annulation, aucune mutation calendrier. |
| Rappels / alarmes | Refus ou clarification honnete: champ non livre en V1. |
| Participants / invitations | Refus ou clarification honnete: invitation non livree en V1. |
| Recurrences | Lecture possible dans certains cas; creation/update/delete recurrence ou occurrence unique non livrees. |
| Aide "que peux-tu faire" | Surface d'aide produit a livrer; ne pas improviser une promesse excessive. |
| Perimetre operateur | Reponse de capacites bornees, sans exposer secrets ni details techniques sensibles. |
| Danger / impossible | Refus honnete ou clarification; pas de mutation large. |

## 6. Gaps produit

- Sous-fenetres vernaculaires: matin/apres-midi/soir doivent etre validees comme
  fenetres canoniques et non inferees au hasard.
- Dates explicites et periodes: le chemin existe, mais il faut des smokes dedies
  pour les dates relatives hors today/tomorrow et les semaines.
- Duree/sejour: le rendu multi-jours existe, mais il faut prouver que l'agent
  route les questions de duree vers le bon contexte ou vers une relecture
  details.
- Disponibilites: methode declaree, mais derivation produit et preuves
  insuffisantes.
- Comparaison de journees/evenements: aucune methode dediee, vraie capacite
  manquante.
- Reprise multi-tour: le dialogue normal est conserve, mais les familles
  `celui-la`, `celui d'apres`, `combien de temps` doivent etre prouvees.
- Rappels/notifications/alarmes: pas de champ reminder/alarme livre dans le
  draft V1, pas de rendu ni d'ecriture associes.
- Participants/invitations: pas de surface produit pour ajouter, lire ou repondre
  a des invitations.
- Recurrences: lecture recurrente bornee existe, mais creation/modification/
  suppression de repetitions ou d'occurrences uniques restent hors capacite
  utilisateur.
- Calendrier familial: protections create/delete solides en fake/local, mais
  lecture ciblee famille et classification live doivent rester prudentes.
- Update live utilisateur: toujours hors scope; update fake/local preserve le
  payload calendrier source sur un composant simple seulement.
- Aide utilisateur et perimetre operateur: besoin d'une surface claire pour
  expliquer ce que Frida peut lire, proposer, confirmer, refuser et ce qui reste
  hors code.
- Mutations utilisateur reelles: a ouvrir seulement avec GO humain explicite,
  preuve synthetique prealable et rollback documente.

## 7. Prochaines validations recommandees

- Lot A: smokes read-only anonymises sur dates explicites, periodes, calendriers
  cibles, calendrier familial read-only, sous-fenetres vernaculaires et recherches
  par formulations variees.
- Lot B: surface d'aide utilisateur "questions possibles" et perimetre operateur
  dans la conversation, avec promesses bornees et confirmations explicites.
- Lot C: duree/sejour/reprise multi-tour, notamment `combien de temps j'y reste ?`
  apres une reponse Agenda.
- Lot D: disponibilites et creneaux libres, avec fenetres bornees et refus des
  demandes trop larges.
- Lot E: rappels/notifications et participants/invitations seulement si decide,
  en gardant les proprietes techniques hors observabilite.
- Lot F: mutations utilisateur reelles progressives si decide: creation simple,
  puis delete ciblee, puis update live avec preservation source, chaque fois avec
  preuve synthetique et GO humain.

## 8. Notes de prudence

- Cette cartographie ne ferme aucun Lot 9.
- Aucun exemple ne provient d'un agenda personnel reel.
- Les placeholders `[personne]`, `[lieu]`, `[mot-cle]`, `[professionnel]` et
  `[type d'evenement]` sont volontaires.
- Les statuts doivent etre requalifies apres chaque smoke ou lot futur: ne pas
  transformer une possibilite de prompt en capacite fermee sans preuve.
- Ne pas reclasser une capacite comme absente uniquement parce qu'elle n'a pas
  son JSONL dedie.
