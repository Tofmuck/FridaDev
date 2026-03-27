# FridaDev Conventions (Minimal)

Objectif: réduire la friction de lecture/maintenance sans refacto cosmétique global.

## 1) Logging
- Namespace canonique: `frida.*`.
- Déclaration standard: `logger = logging.getLogger("frida.<scope>")`.
- Pas de wrapper/custom logger framework dans ce repo.
- Changement de namespace limité au préfixe; ne pas renommer massivement les suffixes sans besoin métier.

## 2) Typage (règle minimale)
- Pas de passe globale de style.
- Sur un fichier touché, rester cohérent localement et préférer un typage explicite utile au comportement modifié.

## 3) Discipline de patch
- Tranches petites, fermées, testées.
- Pas de commit de formatage global.
- Toute convention nouvelle doit être accompagnée d'un garde-fou léger exécutable.
