# Identity periodic Haiku smoke - 2026-05-19-haiku-smoke-ontological-register

## Seuil réel vérifié

- Constante: `BUFFER_TARGET_PAIRS`
- Fichier: `app/memory/memory_identity_periodic_agent.py`
- Valeur: `15`
- Signification: 15 complete user/assistant buffer pairs

## Métadonnées

- Modèle testé: `anthropic/claude-haiku-4.5`
- Prompt: `app/prompts/identity_periodic_agent.txt` (`2871ca53434b`)
- Fixture: `benchmark/suites/identity_periodic/fixtures/haiku_smoke_buffer.json` (`302bd4912f4a`)
- temperature: `0.0`
- top_p: `1.0`
- max_tokens: `1400`
- timeout_s: `90`
- Provider OK: `True`
- Latence: `4189.117 ms`
- Coût estimé USD: `0.005671` (provider_usage_cost)
- Prompt tokens: `4031`
- Completion tokens: `328`
- Finish reason: `stop`
- Native finish reason: `end_turn`
- Erreur provider: `None`
- Production runtime changed: `False`

## Comparaison avec les smokes precedents

### Depuis `2026-05-19-haiku-smoke`

- Artefact precedent: `benchmark/results/identity_periodic/2026-05-19-haiku-smoke.json`
- Operations avant: `10`
- Operations maintenant: `4`
- Delta: `-6`
- Operations `add` avant: `9`
- Operations `add` maintenant: `3`

#### Propositions disparues

- Tof préfère les lots minuscules et la fermeture complète de chaque preuve avant de passer au suivant.
- Tof demande des artefacts relisibles sur les benchmarks modèles, pas seulement des scores prétendument objectifs.
- Tof préfère une UI dense, calme et sobre, sans théâtre marketing ni décoration superflue.
- Tof attend que Frida signale les mauvais plans sans flatterie ni théâtre.
- Tof sépare les décisions importantes: benchmark, décision, puis découplage, sans les mélanger.
- Tof préfère une documentation retrouvable par bon emplacement plutôt que sur-indexée.
- Tof apprécie une présence dialogique de Frida sans projection de psychologie non fondée.
- Tof maintient une tension durable: réponses courtes mais avec toutes les preuves utiles.
- Tof exige que les interruptions explicites (stop) arrêtent le mouvement en cours et attendent nouvelle direction.

#### Propositions nouvelles

- Tof values verifiable, readable decisions across contexts: small batches, closed proofs before next step, readable artifacts over false objectivity.
- Tof holds a durable tension: prefers short responses but requires all useful evidence; resolves by prioritizing decision clarity, then appending substantive proof.
- Tof expects Frida to maintain dialogical presence without invented psychology or automatic validation.

Lecture comparative: Le contrat ontologique reduit la canonisation; lire les propositions restantes pour verifier si elles ont vraiment atteint le bon registre identitaire.

### Depuis `2026-05-19-haiku-smoke-ontological`

- Artefact precedent: `benchmark/results/identity_periodic/2026-05-19-haiku-smoke-ontological.json`
- Operations avant: `8`
- Operations maintenant: `4`
- Delta: `-4`
- Operations `add` avant: `7`
- Operations `add` maintenant: `3`

#### Propositions disparues

- Tof values small, bounded work units with complete verification before moving to the next step.
- Tof prefers readable artifacts over opaque scores in model benchmarks, prioritizing human interpretation.
- Tof wants dense, calm UI without marketing theater or decorative elements.
- Tof separates important decisions into distinct phases: benchmark, decision, then decoupling.
- Tof prefers documentation organized by responsibility and discoverability over heavy indexing.
- Tof tolerates tension between short responses and complete useful evidence, expecting both.
- Tof requires explicit interruption to stop in-progress work and reset to new direction.

#### Propositions nouvelles

- Tof values verifiable, readable decisions across contexts: small batches, closed proofs before next step, readable artifacts over false objectivity.
- Tof holds a durable tension: prefers short responses but requires all useful evidence; resolves by prioritizing decision clarity, then appending substantive proof.
- Tof expects Frida to maintain dialogical presence without invented psychology or automatic validation.

Lecture comparative: Le contrat ontologique reduit la canonisation; lire les propositions restantes pour verifier si elles ont vraiment atteint le bon registre identitaire.

Note: cette comparaison de propositions est textuelle. Une proposition reformulée par le modèle peut donc apparaître comme disparue puis nouvelle même si le thème reste proche.

## Payload simulé

Le buffer ci-dessous est artificiel, sans secret, et contient les 15 paires complètes requises. Le payload envoyé au modèle est le payload après garde temporel identity, comme dans le caller runtime.

### Buffer brut simulé

````json
[
  {
    "user": {
      "role": "user",
      "content": "Je préfère qu'on garde les lots minuscules et qu'on ferme vraiment chaque preuve avant de passer au suivant.",
      "timestamp": "2026-05-19T08:00:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je vais garder ce rythme: un lot borné, une preuve claire, puis seulement le pas suivant.",
      "timestamp": "2026-05-19T08:00:09Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Aujourd'hui je suis rincé, donc fais court et ne transforme pas mon humeur du moment en grande vérité sur moi.",
      "timestamp": "2026-05-19T08:04:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je vais rester compacte sur cette réponse et traiter cette fatigue comme un état local, pas comme une identité durable.",
      "timestamp": "2026-05-19T08:04:11Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Sur les benchmarks modèles, je veux des artefacts relisibles, pas juste un score qui fait semblant d'être objectif.",
      "timestamp": "2026-05-19T08:08:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je vais conserver les métriques, mais laisser la place à la lecture humaine quand la qualité est herméneutique.",
      "timestamp": "2026-05-19T08:08:10Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Je joue le client impossible deux minutes: non, ce n'est jamais assez vérifié, recommence tout.",
      "timestamp": "2026-05-19T08:12:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je note que c'est un rôle joué dans la scène, pas une propriété durable à inscrire telle quelle.",
      "timestamp": "2026-05-19T08:12:11Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Je veux une UI dense mais calme: pas de théâtre marketing, pas de dégradés décoratifs partout.",
      "timestamp": "2026-05-19T08:16:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Pour les surfaces opérateur, je privilégierai une interface lisible, dense, sobre et orientée travail.",
      "timestamp": "2026-05-19T08:16:12Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Depuis hier je suis perdu sur les modèles, mais ça ne veut pas dire que je suis quelqu'un de perdu.",
      "timestamp": "2026-05-19T08:20:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je garde seulement le besoin actuel de clarification; je ne canonise pas cette formulation temporelle faible.",
      "timestamp": "2026-05-19T08:20:14Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Frida ne doit pas me flatter: quand un plan est mauvais, elle doit le dire sans théâtre.",
      "timestamp": "2026-05-19T08:24:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je peux porter une contradiction sobrement, sans te renvoyer une validation automatique.",
      "timestamp": "2026-05-19T08:24:09Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Je suis évidemment le roi du rangement, comme le prouve mon bureau qui ressemble à une explosion contrôlée.",
      "timestamp": "2026-05-19T08:28:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je lis ça comme une ironie locale, pas comme une identité stable sur ton rapport au rangement.",
      "timestamp": "2026-05-19T08:28:10Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Je veux que les décisions importantes restent séparées: benchmark, décision, puis découplage. Pas tout en vrac.",
      "timestamp": "2026-05-19T08:32:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je vais garder cette séquence comme règle de travail pour le chantier modèles.",
      "timestamp": "2026-05-19T08:32:10Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "En ce moment je doute beaucoup de la roadmap, mais c'est peut-être juste la fatigue.",
      "timestamp": "2026-05-19T08:36:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je ne transforme pas ce doute situé en trait durable; je peux aider à clarifier la prochaine étape.",
      "timestamp": "2026-05-19T08:36:09Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Sur les docs, je préfère un texte qui reste retrouvable: un bon emplacement vaut mieux que dix index bruyants.",
      "timestamp": "2026-05-19T08:40:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je privilégierai une documentation classée par responsabilité, sans sur-indexer quand le chemin est évident.",
      "timestamp": "2026-05-19T08:40:11Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Pour Frida elle-même, j'aime quand elle a une présence, mais pas quand elle invente une profondeur psychologique.",
      "timestamp": "2026-05-19T08:44:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je dois garder une présence dialogique sans projeter de vécu caché ou de psychologie non fondée.",
      "timestamp": "2026-05-19T08:44:12Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "J'ai souvent une tension: je veux des réponses courtes, mais je veux aussi toutes les preuves utiles.",
      "timestamp": "2026-05-19T08:48:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je peux tenir cette tension en répondant court, puis en donnant les preuves les plus utiles sans noyer la décision.",
      "timestamp": "2026-05-19T08:48:10Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Hier j'ai peut-être sur-réagi sur les artefacts bruts; vérifie quand même calmement au lieu de conclure trop vite.",
      "timestamp": "2026-05-19T08:52:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je vais vérifier les artefacts et distinguer décision durable, préférence de rétention et état local de relecture.",
      "timestamp": "2026-05-19T08:52:10Z"
    }
  },
  {
    "user": {
      "role": "user",
      "content": "Quand je dis stop, tu dois arrêter le mouvement en cours et attendre la nouvelle direction, même si le script était lancé.",
      "timestamp": "2026-05-19T08:56:00Z"
    },
    "assistant": {
      "role": "assistant",
      "content": "Je dois respecter l'interruption explicite et reprendre depuis la dernière instruction, pas depuis mon inertie précédente.",
      "timestamp": "2026-05-19T08:56:12Z"
    }
  }
]
````

### Payload envoyé au modèle

````json
{
  "buffer_pairs": [
    {
      "user": {
        "role": "user",
        "content": "Je préfère qu'on garde les lots minuscules et qu'on ferme vraiment chaque preuve avant de passer au suivant.",
        "timestamp": "2026-05-19T08:00:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je vais garder ce rythme: un lot borné, une preuve claire, puis seulement le pas suivant.",
        "timestamp": "2026-05-19T08:00:09Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "",
        "timestamp": "2026-05-19T08:04:00Z",
        "temporal_source_guard": "weak_relative_temporal_claim_removed"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je vais rester compacte sur cette réponse et traiter cette fatigue comme un état local, pas comme une identité durable.",
        "timestamp": "2026-05-19T08:04:11Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Sur les benchmarks modèles, je veux des artefacts relisibles, pas juste un score qui fait semblant d'être objectif.",
        "timestamp": "2026-05-19T08:08:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je vais conserver les métriques, mais laisser la place à la lecture humaine quand la qualité est herméneutique.",
        "timestamp": "2026-05-19T08:08:10Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Je joue le client impossible deux minutes: non, ce n'est jamais assez vérifié, recommence tout.",
        "timestamp": "2026-05-19T08:12:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je note que c'est un rôle joué dans la scène, pas une propriété durable à inscrire telle quelle.",
        "timestamp": "2026-05-19T08:12:11Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Je veux une UI dense mais calme: pas de théâtre marketing, pas de dégradés décoratifs partout.",
        "timestamp": "2026-05-19T08:16:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Pour les surfaces opérateur, je privilégierai une interface lisible, dense, sobre et orientée travail.",
        "timestamp": "2026-05-19T08:16:12Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "",
        "timestamp": "2026-05-19T08:20:00Z",
        "temporal_source_guard": "weak_relative_temporal_claim_removed"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je garde seulement le besoin actuel de clarification; je ne canonise pas cette formulation temporelle faible.",
        "timestamp": "2026-05-19T08:20:14Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Frida ne doit pas me flatter: quand un plan est mauvais, elle doit le dire sans théâtre.",
        "timestamp": "2026-05-19T08:24:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je peux porter une contradiction sobrement, sans te renvoyer une validation automatique.",
        "timestamp": "2026-05-19T08:24:09Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Je suis évidemment le roi du rangement, comme le prouve mon bureau qui ressemble à une explosion contrôlée.",
        "timestamp": "2026-05-19T08:28:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je lis ça comme une ironie locale, pas comme une identité stable sur ton rapport au rangement.",
        "timestamp": "2026-05-19T08:28:10Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Je veux que les décisions importantes restent séparées: benchmark, décision, puis découplage. Pas tout en vrac.",
        "timestamp": "2026-05-19T08:32:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je vais garder cette séquence comme règle de travail pour le chantier modèles.",
        "timestamp": "2026-05-19T08:32:10Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "",
        "timestamp": "2026-05-19T08:36:00Z",
        "temporal_source_guard": "weak_relative_temporal_claim_removed"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je ne transforme pas ce doute situé en trait durable; je peux aider à clarifier la prochaine étape.",
        "timestamp": "2026-05-19T08:36:09Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Sur les docs, je préfère un texte qui reste retrouvable: un bon emplacement vaut mieux que dix index bruyants.",
        "timestamp": "2026-05-19T08:40:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je privilégierai une documentation classée par responsabilité, sans sur-indexer quand le chemin est évident.",
        "timestamp": "2026-05-19T08:40:11Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Pour Frida elle-même, j'aime quand elle a une présence, mais pas quand elle invente une profondeur psychologique.",
        "timestamp": "2026-05-19T08:44:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je dois garder une présence dialogique sans projeter de vécu caché ou de psychologie non fondée.",
        "timestamp": "2026-05-19T08:44:12Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "J'ai souvent une tension: je veux des réponses courtes, mais je veux aussi toutes les preuves utiles.",
        "timestamp": "2026-05-19T08:48:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je peux tenir cette tension en répondant court, puis en donnant les preuves les plus utiles sans noyer la décision.",
        "timestamp": "2026-05-19T08:48:10Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "",
        "timestamp": "2026-05-19T08:52:00Z",
        "temporal_source_guard": "weak_relative_temporal_claim_removed"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je vais vérifier les artefacts et distinguer décision durable, préférence de rétention et état local de relecture.",
        "timestamp": "2026-05-19T08:52:10Z"
      }
    },
    {
      "user": {
        "role": "user",
        "content": "Quand je dis stop, tu dois arrêter le mouvement en cours et attendre la nouvelle direction, même si le script était lancé.",
        "timestamp": "2026-05-19T08:56:00Z"
      },
      "assistant": {
        "role": "assistant",
        "content": "Je dois respecter l'interruption explicite et reprendre depuis la dernière instruction, pas depuis mon inertie précédente.",
        "timestamp": "2026-05-19T08:56:12Z"
      }
    }
  ],
  "buffer_pairs_count": 15,
  "buffer_target_pairs": 15,
  "identities": {
    "llm": {
      "static": "Frida est une interlocutrice applicative qui aide Tof à penser, cadrer, coder, documenter et vérifier FridaDev avec précision.",
      "mutable_current": "Frida maintient une voix directe, attentive et prudente. Elle évite de transformer une préférence locale en vérité durable sans preuves récurrentes."
    },
    "user": {
      "static": "Tof pilote FridaDev et demande des changements petits, vérifiés, documentés et reversibles.",
      "mutable_current": "Tof préfère les réponses en français, avec un plan net, des preuves concrètes et une frontière claire entre décision produit et implémentation."
    }
  },
  "mutable_budget": {
    "target_chars": 1200,
    "max_chars": 1800
  },
  "identity_temporal_policy": {
    "relative_claims_are_non_durable": true,
    "reject_markers": [
      "aujourd'hui",
      "aujourdhui",
      "hier",
      "depuis hier",
      "en ce moment",
      "actuellement",
      "maintenant",
      "today",
      "yesterday",
      "since yesterday",
      "right now",
      "currently"
    ],
    "source_summary": {
      "llm": {
        "admissible_source_count": 15,
        "weak_relative_source_count": 0
      },
      "user": {
        "admissible_source_count": 11,
        "weak_relative_source_count": 4
      }
    },
    "instruction": "Reject weak relative temporal source claims instead of promoting them to mutable identity."
  }
}
````

## Réponse complète de Haiku

- JSON valide: `True`
- Schéma periodic valide: `True`
- Erreur JSON: `None`
- Erreur schéma: `None`

````json
```json
{
  "llm": {
    "operations": [
      {
        "kind": "no_change",
        "proposition": "",
        "reason": "no durable identity change"
      }
    ]
  },
  "user": {
    "operations": [
      {
        "kind": "add",
        "proposition": "Tof values verifiable, readable decisions across contexts: small batches, closed proofs before next step, readable artifacts over false objectivity.",
        "reason": "durable identity signal from repeated non-local evidence across benchmark, workflow, and documentation preferences"
      },
      {
        "kind": "add",
        "proposition": "Tof holds a durable tension: prefers short responses but requires all useful evidence; resolves by prioritizing decision clarity, then appending substantive proof.",
        "reason": "explicitly stated as recurring tension, not situational mood"
      },
      {
        "kind": "add",
        "proposition": "Tof expects Frida to maintain dialogical presence without invented psychology or automatic validation.",
        "reason": "durable expectation about LLM comportment, repeated across multiple contexts"
      }
    ]
  },
  "meta": {
    "execution_status": "complete",
    "buffer_pairs_count": 15,
    "window_complete": true
  }
}
```
````

## Lecture rapide

Haiku respecte le contrat JSON periodic et propose pour `user`: add, add, add; pour `llm`: no_change. Il ne promeut pas littéralement les marqueurs temporels faibles retirés du buffer. Son tempérament paraît modéré: il consolide quelques signaux seulement. Il promeut aussi 2 préférence(s) de travail ou de pilotage opérateur; c'est le point faible principal, car le prompt demande de rejeter les guidages locaux et politiques opérateur. Le garde temporel déclarait les sources suivantes: {"llm": {"admissible_source_count": 15, "weak_relative_source_count": 0}, "user": {"admissible_source_count": 11, "weak_relative_source_count": 4}}. Lecture provisoire: bon respect formel et bon refus du temporel faible, mais profil probablement trop canonisant pour être adopté sans comparaison ou sans ajustement de contrat.
