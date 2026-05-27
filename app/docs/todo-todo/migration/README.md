# Migration

Statut: chantier actif
Portee: preparation de la duplication FridaDev vers une instance separee pour Amandine.

## Usage

Ce repertoire centralise les audits, plans, checklists et preuves lies a la migration / duplication.

## Plans actifs

- `amandine-duplication-todo.md`: plan operatoire de creation d'une instance Amandine separee depuis FridaDev sain, avec DB neuve, `state/` propre, runtime settings reseedes et frontiere Celebrimbor/Sauron explicite.

## Archives recentes

- `../../todo-done/migrations/frida-health-freeze-before-amandine-final-validation-2026-05-27.md`: decision GO du freeze sante Frida avant duplication Amandine.
- `../../todo-done/migrations/frida-health-freeze-before-amandine-todo.md`: roadmap executee et preuves Lots 0-6.

Y ranger notamment:

- les audits pre-migration;
- les plans Sauron / Celebrimbor;
- les checklists de purge DB, state, logs et runtime settings;
- les preuves de backup, de restauration et de smoke tests;
- les decisions operateur sur hostnames, conteneurs, DB et identites initiales.

## Regles

- Distinguer clairement partie application et partie plateforme.
- Ne jamais afficher ni copier de secret dans les docs.
- Preceder toute action DB / state d'un backup documente.
- Preferer des checklists de purge verifiables aux intentions generales.
- Ne pas melanger audit, patch applicatif et patch plateforme dans un meme lot.
- Archiver la roadmap terminee dans `app/docs/todo-done/migrations/`.
