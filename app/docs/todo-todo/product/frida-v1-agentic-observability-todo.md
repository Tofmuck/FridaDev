# Frida V1 - Observabilite globale / logs agentiques - TODO

Statut: TODO a detailler
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Objectif court

Rendre l'observabilite Frida 1.0 lisible en mode agentique sans exposer de
contenu brut.

## Scope

- Audit des traces actuelles.
- Degradation en mode agentique.
- Harmonisation statuts, reason codes, traces d'outils, smokes et dashboard.
- Separation observabilite technique, produit, preuves live et surface
  utilisateur.
- Contrat content-free transversal.

## Hors-scope

- Refonte complete du dashboard.
- Nouveau systeme de logs plateforme.
- Exposition de contenu utilisateur.
- Grand audit final.

## Preuves attendues

- Inventaire des champs actuels.
- Tests anti-fuite.
- Smokes content-free representatifs.
- Documentation des reason codes majeurs.

## References livrees

- `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md` section
  "Observabilite content-free": precedent local Lot 6 pour read-model
  allowliste, reason codes dossiers, hash courts, compteurs et scan anti-fuite
  sans contenu utilisateur.

## A detailler dans un lot separe

Schema cible, migration douce, dashboard minimal et scan anti-fuite.
