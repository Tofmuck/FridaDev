# Frida V1 - Mail bonus borne - TODO

Statut: bonus, non bloquant Frida 1.0
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Explorer un Mail V1 borne si la cloture Frida 1.0 laisse de la marge.

## Scope

- Audit Nextcloud Mail / IMAP / SMTP / API controlee.
- Lecture.
- Resume.
- Tri ou classement.
- Brouillons.
- Envoi seulement avec confirmation humaine.
- Archivage ou rattachement eventuel a des dossiers Frida.

## Hors-scope

- Bloquer la cloture Frida 1.0.
- Automatisation d'envoi autonome.
- Migration complete de boite mail.
- Classement automatique non supervise.

## Preuves attendues

- Audit no-op d'abord.
- Tests/fakes avant tout live.
- Smokes content-free si active.
- Confirmation humaine prouvee avant envoi.

## A detailler dans un lot separe

Choix du protocole, garde-fous, surfaces utilisateur, stockage et rollback.
