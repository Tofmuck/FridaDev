# Frida V1 - Mail bonus borne - TODO

Statut: spec-only Frida 1.0, runtime reporte post-V1
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Decision Lot 6 final audit: 2026-06-24

## Objectif court

Explorer un Mail V1 borne si la cloture Frida 1.0 laisse de la marge.

Decision actuelle: Frida 1.0 ne livre aucun runtime Mail. Le lot final audit
Lot 6 cloture seulement le cadrage audit/spec-only et reporte tout acces Mail
reel post-V1.

## Decision Frida 1.0

- `mail_runtime_v1`: `not_delivered`.
- `mail_scope_for_frida_1_0`: `spec_only`.
- `send_allowed`: `false`.
- `human_confirmation_required`: `true` pour tout futur runtime.
- Cloture Frida 1.0: audit final archive en Lot Z; Mail runtime reste post-V1
  sauf GO operateur separe.

## Inventaire Lot 6

- Aucun fichier runtime Mail dedie n'existe sous `app/`.
- `find app -type f \( -iname "*mail*" -o -iname "*email*" \)` ne trouve que
  cette TODO.
- Les occurrences `mail` / `email` hors docs sont des fixtures Agenda
  `mailto:` ou des termes de redaction/observabilite, pas un agent Mail.
- Les occurrences `draft` / `confirmation` du grep large relevent d'Agenda
  pending drafts et confirmations calendaires, pas de brouillons Mail.
- Aucun IMAP, SMTP, Nextcloud Mail live, envoi, lecture de boite ou endpoint UI
  Mail n'est livre.

## Scope

- Audit Nextcloud Mail / IMAP / SMTP / API controlee.
- Lecture.
- Resume.
- Tri ou classement.
- Brouillons.
- Envoi seulement avec confirmation humaine.
- Archivage ou rattachement eventuel a des dossiers Frida.

## Spec-only minimale

Tout futur chantier Mail devra repartir de ces invariants:

- lecture reelle interdite avant GO operateur separe;
- aucun IMAP/SMTP/Nextcloud Mail live sans lot runtime dedie;
- fakes/no-op obligatoires avant tout live;
- brouillons seulement avant confirmation humaine;
- aucun envoi automatique;
- confirmation humaine obligatoire avant tout envoi;
- aucun secret, token, app-password, header, URL IMAP/SMTP/DAV ou payload brut
  dans logs, artefacts, docs ou reponses;
- aucun corps de mail brut dans preuves content-free;
- rattachement eventuel a dossiers Frida seulement post-V1;
- feature flag, rollback et kill switch requis si un runtime futur existe.

## Hors-scope

- Bloquer la cloture Frida 1.0.
- Automatisation d'envoi autonome.
- Migration complete de boite mail.
- Classement automatique non supervise.
- Runtime Mail Frida 1.0.
- Endpoint, UI, provider live, IMAP live, SMTP live ou Nextcloud Mail live.

## Preuves attendues

- Audit no-op d'abord.
- Tests/fakes avant tout live.
- Smokes content-free si active.
- Confirmation humaine prouvee avant envoi.

Pour Frida 1.0, la preuve de cloture est documentaire: inventaire repo,
absence de runtime Mail dedie, decision spec-only et report runtime post-V1.

## A detailler dans un lot separe

Choix du protocole, garde-fous, surfaces utilisateur, stockage, rattachement a
dossiers Frida et rollback.
