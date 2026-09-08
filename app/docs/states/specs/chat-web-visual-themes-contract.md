# Contrat visuel du chat Web — clair et sombre

Date d'autorité : 2026-09-08
Statut : livré dans le frontend Web courant

## Portée

Le chat Web possède une structure unique et deux présentations visuelles :
`light` et `dark`. Le bouton de la barre supérieure bascule entre elles et le
choix est conservé localement sous `frida.chat.theme`. Aucun réglage serveur,
cookie métier, route ou schéma n'est ajouté.

Les deux thèmes modifient uniquement des tokens et effets CSS. Ils conservent
exactement la même géométrie du compositeur, le même DOM fonctionnel et les
mêmes contrôles. Le mode sombre ne constitue pas une seconde interface.

## Invariants fonctionnels

Dans les deux thèmes restent présents et opérants :

- nouveau chat, sélection, renommage et déplacement des conversations ;
- création, renommage, déplacement, repli et icône des répertoires ;
- ajout, sélection, OCR et édition des fichiers ;
- création et sélection des notes, Exports et Images ;
- dictée, Web, document actif, génération d'image, Adobe, Biblio, Notes,
  Agenda, niveau de raisonnement et envoi ;
- heure et copie de chaque bulle, ainsi que l'export de conversation.

Le changement de thème ne déclenche aucune requête applicative et ne réordonne
aucun état. La même règle vaut après rechargement de la page.

## Identité visuelle

Le PNG transparent officiel `fridalogo.png` reste l'unique image d'identité.
Le logo de la sidebar et les miniatures précédant les réponses de Frida sont
posés sur un halo radial CSS. Le halo et l'ombre portée sont extérieurs à
l'image, circulaires et non rognés par un conteneur rectangulaire.

Le compositeur est une surface flottante arrondie et translucide. Les bulles,
la sidebar et la barre supérieure utilisent les mêmes rayons, transparences et
hiérarchie dans les deux thèmes ; seules les couleurs changent.

## Limites

Ce contrat couvre le chat Web responsive existant. Il ne prétend pas livrer
une composition mobile dédiée, le dialogue oral semi-duplex, un nouveau STT ou
un nouveau TTS.

## Preuves minimales

```bash
node --test app/tests/unit/frontend_chat/test_chat_theme_module.js
node --test --test-name-pattern="chat theme switch preserves" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
```

La preuve navigateur doit comparer les rectangles du formulaire, du textarea
et de la grille d'outils avant et après bascule, vérifier la persistance après
rechargement et constater que les neuf contrôles du compositeur restent
visibles.
