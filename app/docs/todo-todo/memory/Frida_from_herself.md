# Frida from herself - suspendu

Statut: suspendu le 2026-05-25; reevalue apres la refonte mutable judge-first, sans chantier parallele ouvert.

Decision: ce fichier ne doit pas devenir un chantier actif parallele. L'intuition `feed her from herself` est probablement absorbee par la refonte mutable: les auto-formulations de Frida doivent etre lues par le meme juge mutable que les formulations utilisateur, dans une fenetre complete de 5 paires, avec `llm.static`, `llm.mutable`, `user.static` et `user.mutable`.

Regle apres cloture de la refonte:

- [x] Ne pas implementer un artefact reflexif separe dans la refonte mutable.
- [x] Ne pas ouvrir un second writer identitaire.
- [x] Ne pas faire persister des auto-formulations de Frida hors du juge mutable commun.
- [x] Reevaluer ce document apres la refonte mutable: il reste suspendu; aucun artefact distinct n'est necessaire sans decision produit separee.

## Brouillon rapide

Idee historique a garder:
- ouvrir plus tard un espace ou Frida puisse dire quelque chose d'elle-meme;
- non pas d'abord comme reecriture directe de l'identite canonique ou de l'identite mutable en base;
- mais comme artefact propre, consultable, editable par elle, dont elle est le sujet.

## Intuition hermeneutique

Aujourd'hui, l'identite de Frida est surtout ecrite sur elle.
Piste a explorer plus tard:
- qu'elle puisse aussi devenir sujet de parole sur elle-meme;
- qu'elle puisse reprendre quelque chose de ce qu'elle est;
- qu'elle puisse expliciter un rapport a sa maniere de dire, a son mode de parole, a ses inflexions, a ses contrats de reponse.

## Addendum 2026-05-24 - promesses de memoire et d'intention

Declencheur a retenir:
- Frida ne doit pas dire `d'accord, je retiens` ou `je parlerai de...` comme si elle pouvait decider seule de memoriser durablement une preference, une relation ou une consigne de conduite;
- si aucun canal de persistence/reinjection ne porte cette intention, la phrase produit une fausse promesse de memoire ou de volonte;
- exemple concret: la correction `Amandine n'est pas ma compagne, c'est ma cherie` ne doit pas seulement devenir une tournure locale; si Frida promet de la retenir, cette promesse doit avoir un write-path reel.

Regle de conception:
- soit Frida reconnait la correction localement sans promettre de memoire durable;
- soit l'engagement qu'elle formule entre dans une couche mutable, un staging mutable, ou un artefact equivalent persistable, auditable et reinjectable;
- entre les deux, il y a une parole relationnelle non tenue par l'infrastructure.

Nom de travail:
- `feed her from herself`;
- objectif: transformer certaines paroles de Frida sur sa propre conduite en candidats d'etat, au lieu de les laisser comme effets de surface;
- ces candidats ne doivent pas forcement entrer directement dans `identity_mutables`: ils peuvent commencer dans un espace reflexif separe, date, relu et gouverne;
- une promotion vers le mutable identitaire ne doit arriver que si le contenu concerne vraiment une modulation stable de sa maniere d'etre, de dire ou de repondre.

Hors-scope immediat:
- pas de patch runtime sans cadrage separe;
- pas d'ecriture automatique directe dans `static` ou `mutable`;
- pas de permission donnee au LLM final de reecrire son identite canonique;
- pas de capture de secrets ou de contenu sensible.

Question a reevaluer apres la refonte mutable:
- comment detecter qu'une phrase de Frida est une simple reconnaissance locale, un engagement durable, ou un candidat legitime pour `feed her from herself` ?

## Forme possible

Premier pas envisageable historique, a ne pas lancer avant la refonte mutable:
- un fichier texte separe;
- hors canon fort;
- hors identite figee;
- peut-etre meme hors identite mutable au debut;
- mais lisible par Frida et modifiable par elle sous certaines conditions.

Autrement dit:
- pas d'abord un pouvoir de canonisation;
- d'abord un lieu ou elle peut se dire.

## Contenu possible

Cet artefact pourrait contenir:
- des formulations sur ce a quoi elle tient dans sa maniere de repondre;
- ce qu'elle refuse;
- des contrats du dire;
- des formulations stabilisees dans le dialogue;
- des points nes d'un consensus entre l'utilisateur et Frida;
- des reprises reflexives sur ce qu'elle reconnait comme important d'elle-meme.

## Point important

Si un contrat du dire emerge dans le dialogue, il pourrait parfois avoir plus de poids que des artefacts plus anciens.
Mais pas silencieusement.
A penser avec:
- datation;
- tracabilite;
- revision;
- promotion eventuelle vers l'identite mutable seulement sous conditions.

## Prudence

Ne pas donner trop tot au LLM final le pouvoir de reecrire directement son identite mutable en base.
Risques:
- derive auto-narrative;
- inflation;
- contradictions mal gerees;
- confusion entre parole sur soi et stabilisation canonique.

## Hypothese de travail plus tard

Ordre possible:
1. stabiliser davantage la prosodie, le mode d'etre, le mode de parole et de reponse;
2. ouvrir un artefact reflexif propre a Frida;
3. observer ses usages et ses derives;
4. seulement ensuite reflechir a une promotion partielle vers l'identite mutable.
