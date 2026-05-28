# Migration

Statut: aucun chantier actif
Portee: index des plans de migration. La duplication Amandine preparee le
2026-05-27 est annulee par decision produit le 2026-05-28.

## Usage

Ce repertoire centralise les audits, plans, checklists et preuves lies a la migration / duplication.

## Plans actifs

Aucun.

La duplication Amandine n'est pas reportee implicitement. Amandine ne souhaite
pas de Frida separee; aucune DB, aucun conteneur, aucun secret/token, aucun
hostname et aucun `state/` Amandine ne doivent etre crees dans l'etat produit
courant.

## Archives recentes

- `../../todo-done/migrations/amandine-duplication-annulee-2026-05-28.md`: archive du plan de duplication Amandine prepare puis annule par decision produit, sans execution runtime.
- `../../todo-done/migrations/frida-health-freeze-before-amandine-final-validation-2026-05-27.md`: freeze sante Frida valide. Il reste utile comme baseline Frida et preuve de sante, sans declencher de duplication Amandine.
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
