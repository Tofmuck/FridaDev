# Chat - copie de bulle et export Markdown

Statut: spec produit legere
Classement: `app/docs/states/specs/`
Portee: comportements visibles du chat pour copier une bulle et exporter une conversation en Markdown
Etat runtime: livre le 2026-05-17

## 1. Copie d'une bulle

- chaque message visible du chat expose une action discrete `Copier cette bulle`;
- l'action copie uniquement le texte de la bulle concernee;
- elle ne copie pas la byline, les statuts de streaming, les identifiants de conversation, les metadonnees techniques, les logs ni les payloads;
- l'action reste locale au navigateur et ne cree aucun evenement d'observabilite.

## 2. Export Markdown

- la conversation courante peut etre exportee en fichier `.md` depuis le chat;
- l'export force une relecture des messages de la conversation avant de produire le fichier, pour viser la conversation complete disponible cote serveur;
- le fichier est lisible par un humain:
  - titre `Conversation avec Frida`;
  - date d'export;
  - sections par message;
  - labels humains `Tof` et `Frida`;
  - texte de message preserve, y compris Markdown saisi dans une bulle.
- l'export exclut les messages systeme et toute metadonnee technique.

## 3. Interdits

L'export ne doit pas contenir:

- `conversation_id`;
- ids internes;
- hashes;
- statuts techniques;
- payloads JSON;
- logs d'observabilite;
- contenu de documents actifs hors messages conversationnels deja visibles.

Cette surface reste distincte de `/log`, du dashboard et des surfaces admin.
