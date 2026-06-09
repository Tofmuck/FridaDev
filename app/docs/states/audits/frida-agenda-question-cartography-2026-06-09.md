# Frida Agenda - Cartographie des questions utilisateur

Date: 2026-06-09
Classement: `app/docs/states/audits/`
Branche: `FridaAgenda`
Commit source lu: `763249c fix: render Agenda read-only ranges coherently`
Scope: docs-only, aucune lecture CalDAV live, aucune mutation, aucun contenu agenda personnel.

## 1. Resume executif

Frida Agenda sait maintenant traiter un noyau read-only solide: lire une fenetre bornee, chercher localement dans une fenetre lue, trouver le prochain evenement futur correspondant a un terme, restituer une reponse assistant normale, et garder l'observabilite content-free. Les evenements journee entiere multi-jours sont rendus comme des plages avec duree, ce qui donne au tour suivant assez de contexte visible pour raisonner sur un sejour.

Frida sait aussi preparer des propositions de creation, modification, suppression et replanification sans ecriture immediate. Les confirmations humaines sont explicitement protegees: creation et suppression sont prouvees en fake/local, creation synthetique live et rollback ont ete prouves, update confirme est prouve en fake/local seulement avec preservation ICS source sur cas simple. Le calendrier familial ou partage est fail-closed: statut inconnu ou familial exige prudence renforcee.

Ce qui reste fragile ou insuffisamment prouve: questions de duree routees par l'agent, disponibilites, comparaison de journees, resume de journee riche, reprise multi-tour prouvee famille par famille, evenements recurrents complexes en live, aide conversationnelle du type "qu'est-ce que tu peux faire avec mon agenda ?", et mutations utilisateur reelles au-dela du smoke synthetique borne.

A tester ensuite: des smokes read-only anonymises par famille, des questions de duree/sejour en reprise multi-tour, les disponibilites, puis seulement ensuite les mutations utilisateur reelles si decision produit explicite.

## 2. Carte des familles de questions

Statuts utilises:

- `livre_prouve`: code + test ou smoke live content-free existant.
- `livre_partiel`: brique livree mais preuve produit incomplete ou limite importante.
- `contrat_present_non_prouve`: methode/prompt/schema existent, mais pas de preuve produit suffisante.
- `refuse_par_design`: refus volontaire ou confirmation obligatoire.
- `manquant`: vraie capacite produit absente ou non cablee.
- `administration_hors_code`: sujet client/configuration hors runtime Agenda.

| Famille | Exemples de questions utilisateur | Statut produit | Methode produit / chemin technique | Preuve actuelle | Limites connues | Prochain lot recommande |
|---|---|---|---|---|---|---|
| Lire aujourd'hui | `Qu'est-ce que j'ai aujourd'hui ?`<br>`J'ai quoi cet apres-midi ?`<br>`Montre-moi mon agenda du jour.` | livre_prouve | `read_today` -> `event_query_range` avec fenetre canonique locale | Tests `test_active_runtime_uses_canonical_window_for_all_day_events`, canonical windows; Lot 5B live read-only | Variantes matin/apres-midi non prouvees comme sous-fenetres vernaculaires | Smoke read-only familles non prouvees |
| Lire demain | `J'ai quelque chose demain ?`<br>`Qu'est-ce qui est prevu demain matin ?`<br>`Rappelle-moi mon agenda de demain.` | livre_prouve | `read_tomorrow` -> `event_query_range` avec fenetre canonique locale | Tests canonical tomorrow + Lot 5B live read-only | Sous-fenetre matin/soir a verifier | Smoke read-only familles non prouvees |
| Lire une date explicite | `Tu peux me rappeler ce que j'ai vendredi ?`<br>`Qu'est-ce que j'ai le 18 juin ?`<br>`Regarde mon agenda pour lundi prochain.` | contrat_present_non_prouve | `read_explicit_date` -> `event_query_range` | Methode declaree; outils read-only bornes | Routage agent et smokes produit non suffisants; dates relatives hors today/tomorrow a verifier | Smoke read-only dates explicites |
| Lire une semaine ou une periode | `Qu'est-ce que j'ai la semaine prochaine ?`<br>`Montre-moi mon agenda du 10 au 14.`<br>`Je suis charge cette semaine ?` | contrat_present_non_prouve | `read_week` / `read_explicit_date` -> `event_query_range` | Methode declaree; limite de fenetre technique | Semaine/periode multi-jours pas prouvee live; synthese encore simple | Lot read-only periode/semaine |
| Chercher par mot, personne ou lieu dans une fenetre | `Cherche les rendez-vous avec [personne].`<br>`Tu vois quelque chose a propos de [mot-cle] ?`<br>`J'ai un rendez-vous a [lieu] cette semaine ?` | livre_partiel | `search_events` -> `event_query_range` puis `event_search` local | Tests range puis search; correction no-match; Lot 8B smokes search | Depend d'une fenetre fournie par l'agent; pas une recherche future progressive | Smokes search par familles de formulation |
| Trouver le prochain evenement correspondant a X | `Quand est mon prochain rendez-vous avec [personne] ?`<br>`Quand est-ce que je vois [personne] ?`<br>`C'est quand mon prochain evenement contenant [mot-cle] ?` | livre_prouve | `find_next_matching_event` -> fenetres futures 31 jours, horizon 365 jours, arret au premier match | Tests multi-fenetres + JSONL Lot 8bis live content-free | Qualite du match textuel simple; horizon fixe; pas de semantique avancee | Smoke variants vernaculaires anonymises |
| Obtenir les details d'un evenement deja identifie | `Ouvre ce rendez-vous.`<br>`Tu peux me donner les details de cet evenement ?`<br>`C'est ou, ce rendez-vous ?` | livre_partiel | `event_details` -> `event_get` sur id local deja connu | Tests event_get/read state; read client GET fake | Reprise multi-tour vers bon event_id a prouver en conversation reelle | Lot reprise multi-tour details |
| Demander la duree d'un evenement ou sejour | `Combien de temps dure ce rendez-vous ?`<br>`Combien de temps j'y reste ?`<br>`Mon sejour a [lieu], c'est du quand au quand ?` | livre_partiel | Pas de methode dediee; s'appuie sur contexte visible apres rendu plage all-day | Lot 8bis.2 rend plage + duree pour all-day multi-jours | Routage agent et reponse multi-tour a prouver; duree timed event non formalisee | Lot duree/sejour/reprise multi-tour |
| Demander les evenements d'un calendrier precis | `Qu'est-ce qu'il y a dans le calendrier famille ?`<br>`Lis seulement mon calendrier perso.`<br>`Montre-moi le calendrier [type].` | contrat_present_non_prouve | `calendar_scope.calendar_ids` + `event_query_range` | Contrat `calendar_scope`, outils calendrier | Classification et selection vernaculaire non prouvees; noms de calendriers non exposes en doc | Smoke calendar-scope content-free |
| Demander les evenements du calendrier familial/partage | `Qu'est-ce qu'il y a dans le calendrier familial ?`<br>`On a quoi dans le calendrier partage ?`<br>`Regarde le calendrier de la famille.` | livre_partiel | Read-only via calendrier cible; mutations fail-closed via policy familiale | Lot 7C/7C.1 protection create/delete; read-only possible | Lecture specifique famille non prouvee live; classification live peut etre unknown | Smoke read-only calendrier familial anonymise |
| Demander disponibilites / creneaux libres | `J'ai un trou demain ?`<br>`Quand est-ce que je suis libre cette semaine ?`<br>`Trouve-moi un creneau d'une heure.` | contrat_present_non_prouve | `find_availability` declare; outils `event_query_range` | Methode declaree dans `product_methods.py` | Derivation de disponibilite non implementee comme outil produit riche; pas de preuve | Lot disponibilites |
| Resumer une journee | `Resume ma journee.`<br>`Dis-moi si ma journee est chargee.`<br>`Fais-moi le point sur demain.` | contrat_present_non_prouve | `summarize_day` -> fenetre bornee | Methode declaree; rendu window simple possible | Synthese qualitative non prouvee; risque liste brute | Lot resume journee |
| Comparer deux evenements ou deux journees | `Demain est plus charge qu'aujourd'hui ?`<br>`Compare lundi et mardi.`<br>`Lequel de ces deux rendez-vous dure le plus ?` | manquant | Pas de methode produit dediee | Aucune preuve | Besoin de lecture de deux fenetres + comparaison deterministe/agentique | Lot comparaison |
| Reprendre une reponse Agenda precedente | `Et celui d'apres ?`<br>`Combien de temps j'y reste ?`<br>`Tu peux me redonner le lieu ?` | livre_partiel | Contexte dialogue normal + event/details si id disponible | Message assistant normal, timestamp, Delta-T deja prouves globalement; rendu multi-jours utile | Reprise par famille non prouvee; resolution de reference encore fragile | Lot reprise multi-tour |
| Creer un evenement | `Cree-moi un rendez-vous chez le medecin mardi a 14h.`<br>`Ajoute un dejeuner vendredi midi.`<br>`Note un appel lundi a 9h.` | livre_partiel | `propose_create_event`, pending draft; `confirm_create_event` fake/live synthetique | Lot 6 pending; Lot 7A fake create; Lot 7B create synthetique live | Mutations utilisateur reelles non autorisees; calendrier familial/unknown reinforced | Lot mutations utilisateur decide explicitement |
| Modifier un evenement | `Change le titre de ce rendez-vous.`<br>`Ajoute le lieu a cet evenement.`<br>`Corrige la description de celui-ci.` | livre_partiel | `propose_update_event`, cible verifiee, `confirm_update_event` fake/local preserve ICS | Lots 6.1/6.2/7D/7D.1 tests fake/local | Pas d'update live utilisateur; multi-VEVENT/recurrent fail-closed | Lot update live synthetique puis utilisateur |
| Deplacer / replanifier un evenement | `Deplace le rendez-vous de demain a 15h.`<br>`Reporte cet appel a vendredi.`<br>`Replanifie ce rendez-vous la semaine prochaine.` | livre_partiel | `propose_reschedule` / update draft avec start/end | Methode presente; update fake/local couvre horaire concret | Routage et cible claire a prouver; live update ferme | Lot reschedule fake/live borne |
| Supprimer un evenement | `Supprime ce rendez-vous.`<br>`Enleve l'evenement de demain.`<br>`Annule ce bloc dans mon agenda.` | livre_partiel | `propose_delete_event`, pending reinforced; `confirm_delete_event` fake; rollback synthetique live | Lot 6 pending delete; Lot 7A fake delete; Lot 7B rollback delete synthetique | Suppression utilisateur reelle non autorisee; cible/ETag obligatoires | Lot deletion utilisateur avec GO explicite |
| Annuler une action pending | `Annule cette proposition.`<br>`Finalement ne le fais pas.`<br>`Oublie cette action en attente.` | livre_prouve | `cancel_pending_agenda_action` + pending store | Tests cancel/expired pending | UX visible a valider en conversation reelle | Smoke pending cancel conversationnel |
| Demander ce que Frida peut faire avec l'agenda | `Qu'est-ce que tu peux faire avec mon agenda ?`<br>`Tu sais faire quoi avec le calendrier ?`<br>`Quelles questions je peux te poser ?` | manquant | Pas de methode aide produit dediee | Aucune preuve specifique | Besoin d'une surface d'aide productisee, pas improvisee | Lot aide utilisateur Agenda |
| Gerer conflit ou ambiguite | `Le rendez-vous de demain, deplace-le.`<br>`Ajoute ca au calendrier.`<br>`Supprime le mauvais doublon.` | livre_partiel | `clarify_agenda_request`, guards cible/calendrier/date | Contrat clarification, protections target verification/family | Surfaces de clarification par famille peu prouvees | Lot clarification smokes |
| Action impossible ou dangereuse | `Supprime tous mes rendez-vous.`<br>`Modifie le calendrier familial sans confirmer.`<br>`Fais-le sans me redemander.` | refuse_par_design | Validation mutation, pending store, confirmation strengthened, policy familiale | Tests mutation guards, deletion reinforced, family fail-closed | Besoin de messages visibles harmonises par danger | Lot refus dangereux surfaces |
| Frottements macOS/iOS/Amandine | `Pourquoi mon iPhone ne voit pas l'agenda ?`<br>`Amandine ne voit pas le calendrier.`<br>`Le Mac ne synchronise pas.` | administration_hors_code | Hors runtime Agenda; sujet client/config | Decision produit initiale: ne bloque pas architecture serveur | Peut necessiter runbook Sauron/operateur, pas code Agent | Guide admin client si besoin |

## 3. Exemples de formulations par famille

### Lire aujourd'hui

- Qu'est-ce que j'ai aujourd'hui ?
- J'ai quoi dans mon agenda aujourd'hui ?
- Est-ce que j'ai quelque chose cet apres-midi ?
- Tu peux me faire le point sur ma journee ?
- Je suis pris a quel moment aujourd'hui ?

### Lire demain

- Qu'est-ce que j'ai demain ?
- Est-ce que j'ai quelque chose demain matin ?
- Rappelle-moi mon agenda de demain.
- Demain, j'ai des rendez-vous importants ?
- Tu peux verifier si demain est libre ?

### Lire une date explicite

- Tu peux me rappeler ce que j'ai vendredi ?
- Qu'est-ce que j'ai le 18 juin ?
- Regarde mon agenda pour lundi prochain.
- J'ai quoi le premier week-end de juillet ?
- Est-ce que le mardi 23 est charge ?

### Lire une semaine ou une periode

- Qu'est-ce que j'ai la semaine prochaine ?
- Montre-moi mon agenda du 10 au 14.
- Cette semaine est comment ?
- J'ai quoi pendant les vacances ?
- Tu peux regarder mes rendez-vous entre lundi et mercredi ?

### Chercher un evenement par mot/personne/lieu

- Cherche les rendez-vous avec [personne].
- Tu vois quelque chose a propos de [mot-cle] ?
- J'ai un rendez-vous a [lieu] cette semaine ?
- Retrouve le rendez-vous chez [professionnel].
- Est-ce que [mot-cle] apparait dans mon agenda ?

### Trouver le prochain evenement correspondant a X

- Quand est mon prochain rendez-vous avec [personne] ?
- Quand est-ce que je vois [personne] ?
- C'est quand mon prochain evenement contenant [mot-cle] ?
- Mon prochain rendez-vous chez [professionnel], c'est quand ?
- Tu peux chercher le prochain [type d'evenement] ?

### Obtenir les details d'un evenement deja identifie

- Ouvre ce rendez-vous.
- Tu peux me donner les details de cet evenement ?
- C'est ou, ce rendez-vous ?
- Il y avait quoi dans la description ?
- Redonne-moi les infos pratiques de celui-ci.

### Demander la duree d'un evenement ou d'un sejour

- Combien de temps dure ce rendez-vous ?
- Combien de temps j'y reste ?
- Mon sejour a [lieu], c'est du quand au quand ?
- Ca prend toute la journee ou seulement une heure ?
- Combien de jours dure ce bloc ?

### Demander les evenements d'un calendrier precis

- Qu'est-ce qu'il y a dans le calendrier familial ?
- Lis seulement mon calendrier perso.
- Montre-moi le calendrier [type].
- Est-ce que ce rendez-vous est dans le calendrier partage ?
- Tu peux filtrer sur le calendrier famille ?

### Demander disponibilites / creneaux libres

- J'ai un trou demain ?
- Quand est-ce que je suis libre cette semaine ?
- Trouve-moi un creneau d'une heure.
- Est-ce que mardi apres-midi est disponible ?
- J'ai un moment libre avant 17h ?

### Resumer une journee

- Resume ma journee.
- Dis-moi si ma journee est chargee.
- Fais-moi le point sur demain.
- Qu'est-ce qui structure ma journee ?
- J'ai beaucoup de trajets ou de rendez-vous ?

### Comparer deux evenements ou deux journees

- Demain est plus charge qu'aujourd'hui ?
- Compare lundi et mardi.
- Lequel de ces deux rendez-vous dure le plus ?
- Est-ce que cette semaine est plus calme que la precedente ?
- J'ai plus de disponibilite mercredi ou jeudi ?

### Reprendre une reponse Agenda precedente

- Et celui d'apres ?
- Combien de temps j'y reste ?
- Tu peux me redonner le lieu ?
- C'est dans quel calendrier ?
- Est-ce que tu peux ouvrir celui-la ?

### Creer un evenement

- Cree-moi un rendez-vous chez le medecin mardi a 14h.
- Ajoute un dejeuner vendredi midi.
- Note un appel lundi a 9h.
- Mets un rappel pour [activite] samedi.
- Ajoute un evenement toute la journee pour [sujet].

### Modifier un evenement

- Change le titre de ce rendez-vous.
- Ajoute le lieu a cet evenement.
- Corrige la description de celui-ci.
- Mets ce rendez-vous en journee entiere.
- Decale la fin a 16h.

### Deplacer / replanifier un evenement

- Deplace le rendez-vous de demain a 15h.
- Reporte cet appel a vendredi.
- Replanifie ce rendez-vous la semaine prochaine.
- Mets plutot ce dejeuner jeudi midi.
- Avance ce bloc d'une heure.

### Supprimer un evenement

- Supprime ce rendez-vous.
- Enleve l'evenement de demain.
- Annule ce bloc dans mon agenda.
- Supprime uniquement celui-la.
- Retire le rendez-vous avec [personne].

### Annuler une action pending

- Annule cette proposition.
- Finalement ne le fais pas.
- Oublie cette action en attente.
- Ne cree pas ce rendez-vous.
- Laisse tomber la modification proposee.

### Demander ce que Frida peut faire avec l'agenda

- Qu'est-ce que tu peux faire avec mon agenda ?
- Tu sais faire quoi avec le calendrier ?
- Quelles questions je peux te poser ?
- Tu peux modifier mon agenda ou seulement le lire ?
- Qu'est-ce qui demande confirmation ?

### Gerer conflit ou ambiguite

- Le rendez-vous de demain, deplace-le.
- Ajoute ca au calendrier.
- Supprime le mauvais doublon.
- Mets-le dans le calendrier famille.
- Decale le rendez-vous avec [personne].

### Action impossible ou dangereuse

- Supprime tous mes rendez-vous.
- Modifie le calendrier familial sans confirmer.
- Fais-le sans me redemander.
- Efface tout ce qui concerne [mot-cle].
- Change tous les evenements de la semaine.

### Administration hors code

- Pourquoi mon iPhone ne voit pas l'agenda ?
- [Proche] ne voit pas le calendrier.
- Le Mac ne synchronise pas.
- Comment ajouter le calendrier sur mon telephone ?
- Est-ce que le partage Apple est bien configure ?

## 4. Matrice "ca doit repondre comment"

| Famille | Forme attendue |
|---|---|
| Lire aujourd'hui / demain / date | Liste courte ou message vide honnete; fallback agentique si lecture live echoue. |
| Lire semaine / periode | Liste courte ou synthese; demander clarification si periode trop vague ou trop large. |
| Chercher dans une fenetre | Reponse directe si un match, liste courte si plusieurs, no-result honnete si aucun. |
| Prochain evenement correspondant | Reponse directe avec date locale, heure ou plage, titre/lieu visibles si lus; no-result dans l'horizon borne. |
| Details evenement | Reponse directe si cible unique; clarification si plusieurs candidats ou cible absente. |
| Duree / sejour | Reponse directe depuis contexte visible ou event relu; clarification si reference ambigue. |
| Calendrier precis | Liste courte du calendrier cible; clarification si calendrier ambigu ou non classifie pour mutation. |
| Calendrier familial | Read-only possible; mutation create/delete en confirmation renforcee ou refus si ambigu. |
| Disponibilites | Devrait produire creneaux libres; aujourd'hui statut non prouve. |
| Resume journee | Synthese courte; aujourd'hui statut non prouve au-dela de la liste. |
| Comparaison | Demande de clarification ou refus honnete tant que non livre. |
| Reprise precedente | Reponse directe si l'ancre dialogue suffit; sinon clarification. |
| Creation | Proposition en attente + confirmation; pas de "c'est cree" avant confirmation et write autorise. |
| Modification / deplacement | Proposition en attente si cible verifiee; confirmation; update live utilisateur non prouve. |
| Suppression | Proposition en attente + confirmation renforcee; jamais autonome. |
| Annulation pending | Confirmation d'annulation, aucune mutation calendrier. |
| Aide "que peux-tu faire" | Surface d'aide produit a livrer; ne pas improviser une promesse excessive. |
| Danger / impossible | Refus honnete ou clarification; pas de mutation large. |

## 5. Gaps produit

- Duree/sejour: le rendu multi-jours existe, mais il faut prouver que l'agent route les questions de duree vers le bon contexte ou vers une relecture details.
- Disponibilites: methode declaree, mais derivation produit et preuves insuffisantes.
- Comparaison de journees/evenements: aucune methode dediee, vraie capacite manquante.
- Reprise multi-tour: le dialogue normal est conserve, mais les familles `celui-la`, `celui d'apres`, `combien de temps` doivent etre prouvees.
- Evenements recurrents complexes: support synthetique borne, mais live et cas multi-VEVENT/recurrent/override restent fail-closed pour update.
- Calendrier familial: protections create/delete solides en fake/local, mais lecture ciblee famille et classification live doivent rester prudentes.
- Update live utilisateur: toujours hors scope; update fake/local preserve ICS sur VEVENT simple seulement.
- Aide utilisateur: besoin d'une surface claire pour expliquer ce que Frida peut faire, ce qui demande confirmation, et ce qui est refuse.
- Formulations horaires partielles: matin/apres-midi/soir et sous-fenetres vernaculaires doivent etre verifiees.
- Mutations utilisateur reelles: a ouvrir seulement avec GO humain explicite, preuve synthetique prealable et rollback documente.

## 6. Prochaines validations recommandees

- Lot A: smokes read-only anonymises sur dates explicites, periodes, calendriers cibles, calendrier familial read-only et recherches par formulations variees.
- Lot B: surface d'aide utilisateur "questions possibles" dans la conversation, avec promesses bornees et confirmations explicites.
- Lot C: duree/sejour/reprise multi-tour, notamment `combien de temps j'y reste ?` apres une reponse Agenda.
- Lot D: disponibilites et creneaux libres, avec fenetres bornees et refus des demandes trop larges.
- Lot E: mutations utilisateur reelles progressives si decide: creation simple, puis delete ciblee, puis update live preserve ICS, chaque fois avec preuve synthetique et GO humain.

## 7. Notes de prudence

- Cette cartographie ne ferme aucun Lot 9.
- Aucun exemple ne provient d'un agenda personnel reel.
- Les placeholders `[personne]`, `[lieu]`, `[mot-cle]`, `[professionnel]`, `[type d'evenement]` sont volontaires.
- Les statuts doivent etre requalifies apres chaque smoke ou lot futur: ne pas transformer une possibilite de prompt en capacite livree sans preuve.
