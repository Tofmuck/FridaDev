# M9-A — contrat de sortie OpenRouter et discriminants d'enveloppe

11 octobre 2026, Celebrimbor. Lot sur code uniquement, base propre alignée
`902c3d2d69ecbcb2a9ad34f7238ec0a896bdf97d`, branche M9-A. Aucun déploiement
ni appel modèle. La cause exacte du canari historique reste inconnue.

## Plan borné et état de travail

1. Revalider les prescriptions et le catalogue publics ; arrêter les paramètres
   documentaires compatibles sans modifier le chat partagé.
2. Baseline ciblée, puis rouge causal du vrai assemblage jusqu'au HTTP loopback.
3. Schéma unique avant gel/mesure, provenance honnête du manifeste ; discriminant
   fermé de première garde, dans le canal durable existant et sans contenu.
4. Corpus de schéma avec validateur existant, preuves HTTP/SSE/PostgreSQL isolées,
   voisins utiles et contrôles négatifs ; aucun assouplissement du canonical.
5. Réconcilier contrats/roadmap, auto-audit, commit/push et arrêt pour Codex.

La baseline de six modules envelope/canonical_paths/admission/provider_progress/
http_transport/final_usage est verte : 115 IDs, 10,098 s, exit 0, aucun skip.
L'image de preuve existante est montée en lecture seule, réseau none ; les
services et données opérateur ne sont pas accessibles aux runners.

Le runtime relu reste running/healthy, image
`sha256:5d28d36f50006d37710a51022e6166e24a179973ec451af3808df958aaa52d06`.
Sa provenance reste `8088571296a81f5182ce60448ed366ee49450524` selon le diagnostic
précédent et le contre-audit Codex transmis par Tof. Aucun changement runtime.

## Choix officiels et portée

Pages actuelles consultées le **11 octobre 2026**, GET publics sans clé ni compte.
Le catalogue a répondu HTTP 200 à **16:40:37Z**. La contre-lecture Codex de
`902c3d2d…`, son alignement et l'absence de schéma sont attribués à Codex selon
Tof ; les 115 tests antérieurs restent ceux de Celebrimbor, non rejoués par Codex.
Le [diagnostic historique](frida-v1-document-workshop-envelope-diagnostic-20261011.md)
est conservé : réponse exacte absente, règle rejetée inconnue, aucun second stop
observé revendiqué. Le présent lot corrige l'écart prouvé, sans causalité rétroactive.

| Prescription / URL / section (11/10/2026) | Chemin effectivement corrigé | Conclusion et limite |
| --- | --- | --- |
| [OpenRouter Structured Outputs — Using, Best Practices, Streaming](https://openrouter.ai/docs/guides/features/structured-outputs#using-structured-outputs) : `response_format.type=json_schema`, `json_schema.strict=true` ; support par endpoint | [Schéma unique, l.19](../../../core/document_workshop_output_schema.py#L19), [admission, l.95](../../../core/document_workshop_admission.py#L95) | Schéma explicite avant gel, streaming conservé. Garantie demandée pour la forme ; métier local. La réserve Best Practices sur l'application variable selon provider prévaut sur la promesse générale. |
| [Provider Selection — Requiring Providers to Support All Parameters](https://openrouter.ai/docs/guides/routing/provider-selection#requiring-providers-to-support-all-parameters) | Admission : `require_parameters=true`, `allow_fallbacks=false` | Filtrage des paramètres demandé ; aucun provider `only/order`, changement global, retry ni fallback. Une préférence souple ne suffirait pas. |
| [Catalogue GPT-5.1 endpoints](https://openrouter.ai/api/v1/models/openai/gpt-5.1/endpoints) | Admission : omission de temperature/top_p/stop ; max_tokens conservé | Cinq endpoints annoncent reasoning, response_format, structured_outputs. OpenAI flex/standard/fast annonce max_tokens ; Azure standard/swedencentral annonce max_completion_tokens. Aucun n'annonce les trois options omises. Compatibilité déclarée des candidats OpenAI ; pas une capture historique ni une preuve d'ignorance passée. |
| [Parameters — Response Format, Stop, Reasoning](https://openrouter.ai/docs/api_reference/parameters#response-format) | Builder partagé inchangé ; adaptation dans la seule admission documentaire | Consigne seule ≠ JSON garanti ; json_object ≠ schéma. Le guide spécialisé définit la forme json_schema utilisée. Aucun champ `structured_outputs` supplémentaire nécessaire dans cet exemple contractuel. Suppression des arrêts textuels hérités : le terminal stop/DONE contrôlé par le lecteur reste requis. |
| [OpenAI — Supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas), [Azure — JSON Schema support and limitations](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs#json-schema-support-and-limitations) | Schéma fermé, propriétés toutes requises, anyOf imbriqué, `$defs`/`$ref`, nullable aux seuls emplacements existants | Sous-ensemble commun choisi, aucune clé métier ajoutée à null. Restrictions applicables aux fournisseurs annoncés ; aucun événement/paramètre Responses transposé à OpenRouter Chat Completions. |

Le schéma contient **28 propriétés d'objet, 30 valeurs d'enum**, 2 648 octets UTF-8
pour le response_format compact. Racine objet, jamais anyOf racine. Les alternatives
de blocs gardent leurs clés propres. Proposal est objet/null ; link string/null.
Pas de if/then/else, allOf, pattern, format, min/maxLength, min/maxItems ou uniqueItems.
Les contraintes métier volontairement locales sont précisées ci-dessous.

Les sources divergent : OpenAI publie 5 000 propriétés, 10 niveaux, 120 000
caractères de noms/valeurs et 1 000 enums ; Azure publie 100 propriétés et 5 niveaux,
avec davantage de mots-clés exclus. Leur formulation « nesting » ne définit pas
formellement le traitement des tableaux et références. Nous ne lui inventons pas
de convention : le calcul conservateur, références développées, racine à 1 et
**tous les conteneurs** comptés, donne **9** (10 avec la feuille scalaire). Le
trajet contient cinq objets. Il tient la limite publiée OpenAI même avec ce calcul
strict ; nous ne certifions pas les cinq niveaux Azure. Le payload avec max_tokens
a des candidats annoncés OpenAI ; les endpoints Azure n'annoncent pas ce nom de
paramètre. Aucun alias/routage Azure effectif n'est déduit : normalisation éventuelle
par OpenRouter et acceptation endpoint restent à qualifier live. Le filtrage porte
sur les paramètres, pas sur une profondeur de schéma analysée par notre routeur.

Omettre sampling délègue ces choix aux valeurs par défaut supportées de l'endpoint ;
aucune équivalence numérique ou historique avec 0.7/1.0 n'est revendiquée. Garder
les options non annoncées avec require_parameters aurait laissé zéro route
documentaire déclarée compatible. `max_tokens=24000`, contexte 400 000, modèle
`openai/gpt-5.1`, effort courant et `exclude=true` sont conservés. Stream/options
usage, attribution metadata/trace et headers restent ceux du transport OpenRouter,
distincts des options LLM de sampling listées au catalogue. Aucun appel au catalogue
pendant un tour, aucun SDK/dépendance installé.

## Delta et gardes préservées

Le builder réellement traversé reste `server._LlmChatLogProxy` → `llm_client.build_payload`.
L'[admission](../../../core/document_workshop_admission.py#L95) retire seulement les
trois options locales, refuse un response_format concurrent différent, ajoute le
schéma possédé puis sérialise. La même copie gelée fournit le corps HTTP et la
représentation d'estimation hors messages, passée au compteur partagé existant.
Mutation des entrées mesurées → refus ; mutation tardive d'un objet du builder →
aucune modification des bytes déjà admis. Aucun ajout après mesure.

Le [callback de manifeste](../../../core/document_workshop_turn.py#L246) décrit les
messages HTTP, sans la ligne auxiliaire. L'estimation totale inclut toujours le
schéma ; `document_output_contract` l'annonce avec son SHA-256/12, une ligne
d'estimation uniquement, strict/routage/fallback. L'empreinte concerne le schéma
statique public, jamais les messages. Temperature/top_p sont correctement absents
dans runtime_settings. Le compteur préliminaire `prompt_prepared` du proxy reste
une estimation des seuls messages avant adaptation ; il ne devient pas l'admission
complète. Aucune seconde mesure d'admission ni modification du manifeste du chat.

Le [parseur strict partagé](../../../core/document_canonical.py#L19) garde sa classe
de base DocumentWorkshopError et sa raison `document_canonical_invalid`, avec une
sous-classe portant seulement syntaxe/doublon/non-fini. Le lecteur d'enveloppe
traduit ce site en diagnostic, sans second parseur. Les autres appels conservent
leurs codes. Chaque première [garde d'enveloppe](../../../core/document_workshop_envelope.py#L130)
porte un des 25 codes fermés du [contrat](../../../core/document_workshop_contract.py#L22).
Les familles sont parsing, forme/types/enums, surface, sources, limitations ; aucune
clé reçue, valeur, position, chemin, exception brute ou réponse n'est transmise.
`json_syntax` couvre aussi l'échec de décodage par limite de récursion du parseur.

Le [tour](../../../core/document_workshop_turn.py#L148) émet `envelope_rejection`
dans document_preparation existant, corrélé turn/action/context. Le guard refuse
toute valeur extérieure à l'énumération. Raison publique **document_envelope_invalid**,
état failed, finalisation/claim et absence de révision inchangés. Une exception
d'émission est absorbée seulement pour ce diagnostic optionnel ; le refus métier
reste acquis. Si le sink échoue, le discriminant peut manquer, sans succès inventé.

Restent locaux : parsing strict/doublons/Unicode, surface bornée sans protocole,
status/proposal cohérents, texte non blanc, spans/listes non vides sauf cellules,
rectangularité, chemins, UUID et unicité, copie avec source, limitations uniques,
liens passifs, volumes, capacité, ownership, fraîcheur, confirmation et pagination
Writer. JSON Schema `integer` peut accepter 1.0, Python `type(...) is int` le
refuse : exemple testé, garde conservée. Canonical/chemin/volumes gardent leurs
codes propres. Aucune réparation/coercition/suppression/troncature. Stop/DONE
prouvent la terminaison du protocole ; JSON, schéma et métier sont des contrôles
distincts. Length/refus/coupure/erreur de schéma ou de route restent possibles.

## Preuves et incidents

| Passage | IDs distincts dans ce passage / résultat |
| --- | --- |
| Baseline avant patch, six modules historiques | 115/115, 10,098 s, exit 0 |
| Rouge causal assemblage réel + HTTP/SSE/SQL | 3 échecs attendus, 3,523 s : response_format absent ; diagnostic absent, y compris scénario sink défaillant |
| Rouge corpus de schéma / diagnostic | 4 erreurs (module schéma absent) ; diagnostic sans champ/site et guard non raccordé |
| Unitaires ciblés finaux | 132/132, 12,433 s, exit 0 |
| SQL/HTTP et provenance finaux | 19/19, 16,825 s, exit 0 |
| Schéma, validateur jsonschema 4.19.2 existant | 4/4, 0,163 s, exit 0 dans runner isolé |
| Voisins chat/reasoning/manifeste/guard | 12/12, 0,008 s, exit 0 |
| Contrôles négatifs, chacun sur overlay jetable | 4 × exit 1 attendu : schéma retiré, require_parameters désactivé, schéma non mesuré, diagnostic non émis |
| Compléments après assertions de fermeture du sink/manifeste | mêmes 3 SQL et 4 diagnostic, 3,743 s / 0,004 s, verts ; aucun ID ajouté au total |

**167 IDs finaux distincts**, aucun skip : les 115 baseline ne sont pas additionnés
à nouveau. 16 nouveaux IDs, 151 existants. Les contrôles négatifs et répétitions
justifiées ne gonflent pas ce total. Empreinte de la liste triée, sans LF final :
`06ba127d0ef4661d3736938432fecdf00e8dc182aac928487d32ac0db001cb0b`.
Inventaire normalisé au format exact unittest puis chargé par TestLoader :
167 IDs résolus, zéro erreur de chargement ; aucun rejeu compté à cette étape.

Le cas causal principal monte le vrai `/api/chat`, les claims/snapshots PostgreSQL,
le proxy/builder réels, l'admission, le lecteur SSE et le socket HTTP loopback.
Seuls réglages/facultés/données/endpoint sont synthétiques, pas le builder. Il
prouve un envoi unique, les bytes mesurés/transmis, le manifeste, puis la révision
Markdown exacte du harnais existant. Le corpus hors ligne couvre aussi DOCX,
create/copy/update, prepared/clarify/refuse, chaque bloc et contenu riche. Il
prouve l'admissibilité synthétique, jamais une génération réelle sous schéma.
Les refus durables ont zéro révision/fichier ; dans le harnais M4, journal et
reçus d'exécution sont absents (to_regclass), et seraient vérifiés vides s'ils
existaient. Aucun consommateur Writer/DAV ni confirmation n'est activé.

Incidents conservés : le lecteur Web a échoué sur le catalogue ; GET urllib public
200 utilisé. Lectures longues tronquées, sections utiles relues. Le runner Python
3.11 existant n'a pas jsonschema ; aucune installation : validation initiale pure
sous Python hôte 3.13.5, env vidé, puis preuve finale en conteneur sans réseau avec
`/usr` hôte monté en lecture seule (bibliothèques existantes uniquement). Premier
test nouveau de chemin attendait à tort `document_path_outside_root` : corrigé vers
le code réel `document_path_invalid`, sans toucher au produit. Premier passage SQL
après patch : trois erreurs de test UndefinedTable sur journal/receipt absents du
harnais M4 ; assertions adaptées à cette absence, sans migration. Les warnings du
harnais sur tables summary absentes et log admin en filesystem ro sont conservés
dans les sorties temporaires, sans échec final. Le premier rouge affichait le
payload **synthétique** dans son assertion : remplacée par un message fixe ; aucun
contenu personnel/opérateur ni sortie brute conservé dans le relevé.
Nettoyage : le premier rmtree a rencontré les permissions du socket créé par
PostgreSQL ; suppression achevée par un conteneur éphémère sans réseau, UID 0,
avec seulement le répertoire temporaire du lot monté en écriture, puis absence
du répertoire/socket/conteneur vérifiée. Aucun droit opérateur modifié.

Tof a explicitement autorisé l'actualisation des seules attentes historiques
obsolètes (schéma, estimation, provider et provenance), avec IDs et toutes les
vérifications conservés. Aucun test supprimé, aucune fixture commune modifiée.
Les variantes d'injection de schéma utilisent désormais le même propriétaire ;
un autre schéma est explicitement testé comme refusé. Les six JSON historiques
M9-A restent à empreinte inchangée.

## Commandes reproductibles

Le checkout doit être ce commit, aucune donnée/clé opérateur. Images existantes,
`--pull=never`. Image Python `486a8afeb2f6…`, PostgreSQL `87e04d274d18…`.
Les commandes ci-dessous factorisent exactement les options exécutées. Répertoire
temporaire utilisé ici : `/tmp/frida-m9a-output-20261011-nkig328_` ; aucun volume
persistant, port publié ou réseau applicatif. L'instance PG est propre au lot.

```bash
M9A_PROOF_DIR=$(mktemp -d /tmp/frida-m9a-output-XXXXXXXX)
mkdir "$M9A_PROOF_DIR/pg-socket"
chmod 777 "$M9A_PROOF_DIR/pg-socket"
docker run -d --name frida-m9a-output-proof-pg --pull=never --network none \
  --read-only --tmpfs /tmp:rw,nosuid,nodev --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev \
  -v "$M9A_PROOF_DIR/pg-socket:/var/run/postgresql" \
  -e POSTGRES_USER=m1proof -e POSTGRES_DB=m1proof -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgres:16-alpine -c listen_addresses=
docker exec frida-m9a-output-proof-pg pg_isready -U m1proof -d m1proof

m9a_unit() {
  docker run --rm --pull=never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev \
    -v /opt/platform/fridadev:/workspace:ro -w /workspace/app \
    --entrypoint /usr/bin/env fridadev-audit-py:latest -i PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/app:/workspace \
    EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid \
    python -m unittest -v "$@"
}
m9a_unit tests.unit.core.test_document_workshop_envelope \
  tests.unit.core.test_document_workshop_canonical_paths tests.unit.core.test_document_workshop_admission \
  tests.unit.core.test_document_workshop_provider_progress tests.unit.core.test_document_workshop_http_transport \
  tests.unit.core.test_document_workshop_final_usage tests.unit.core.test_document_workshop_envelope_rejections \
  tests.unit.core.test_document_workshop_output_admission tests.unit.core.test_document_workshop_provenance \
  tests.unit.core.test_document_workshop_m4_observability tests.unit.core.test_document_workshop_turn_ownership
# Baseline : même commande, six premiers modules seulement, sur 902c3d2d.
# Voisins : m9a_unit suivi des 12 IDs du groupe neighbors de l'inventaire ci-dessous.

docker run --rm --pull=never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev \
  -v /opt/platform/fridadev:/workspace:ro -v "$M9A_PROOF_DIR/pg-socket:/proof/sock:ro" \
  -w /workspace/app --entrypoint /usr/bin/env fridadev-audit-py:latest -i \
  PATH=/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/app:/workspace \
  EMBED_BASE_URL=https://embed.invalid CRAWL4AI_URL=https://crawl.invalid SEARXNG_URL=https://search.invalid \
  M1_PROOF_PG_SOCKET=/proof/sock M2_PROOF_PG_SOCKET=/proof/sock M3_PROOF_PG_SOCKET=/proof/sock M4_PROOF_PG_SOCKET=/proof/sock \
  python -m unittest -v tests.integration.document_workshop.test_output_contract_postgresql \
  tests.integration.document_workshop.test_preparation_http_postgresql \
  tests.integration.document_workshop.test_preparation_provenance_postgresql

docker run --rm --pull=never --network none --read-only --tmpfs /tmp:rw,nosuid,nodev \
  -v /usr:/usr:ro -v /opt/platform/fridadev:/workspace:ro -w /workspace/app \
  --entrypoint /usr/bin/env fridadev-audit-py:latest -i PATH=/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/app:/workspace \
  python3 -m unittest -v tests.unit.core.test_document_workshop_output_schema
```

Négatifs : dans une copie temporaire d'admission, retirer seulement l'affectation
`payload["response_format"] = output_format`, ou mettre require_parameters à false,
ou retirer les deux lignes ajoutant response_format à estimation_messages. Monter
chaque copie ro à `/workspace/app/core/document_workshop_admission.py` avec `-v`
supplémentaire dans le runner SQL ; exécuter uniquement
`OutputContractPostgresqlTests.test_real_assembly_schema_routing_measurement_and_exact_revision`.
Échecs observés : schéma absent ; routing différent ; aucune mesure correspondant
aux messages plus schéma. Quatrième copie : remplacer `if diagnostic:` par
`if False:` dans turn.py, overlay ro du même fichier ; exécuter uniquement
`OutputContractPostgresqlTests.test_envelope_rejection_is_durable_and_content_free`.
Zéro diagnostic observé au lieu d'un, exit 1. Aucun fichier produit de travail
modifié pendant ces contrôles. Préfixe complet des deux IDs dans l'inventaire.

## Limites, livraison et auto-audit

Compatibilité documentaire et validation hors ligne établies ; acceptation native
du schéma, endpoint choisi et qualité de génération restent **non éprouvés live**.
Seule suite justifiée : contre-audit Codex ; ensuite éventuelle décision distincte
de remise runtime et qualification contrôlée. Pas de préparation live dans ce lot.
Le discriminant futur ne retrouvera pas la règle du canari historique absent.
OBS-M9A-PREP-01 et M9-A restent ouverts ; M9-B/M10 hors périmètre.

Auto-audit : aucun réglage global ni texte d'instruction modifié ; aucune garde
d'acceptation affaiblie, donnée brute opérateur exportée, preuve inventée, nouvel
appel, retry, fallback, réparation, migration ou surface UI. Corpus et contrôles
négatifs couvrent dérive schéma/validateur, omission dans la mesure, provenance,
fuite de contenu, chat/overrides, terminaux SSE, autorité et fermeture. Sept fichiers
existants embarqués relus par empreinte : identiques à `80885712…`, image inchangée.

Fichiers runtime exacts pour une **éventuelle** remise ultérieure (aucune envoyée) :

```text
app/core/document_canonical.py
app/core/document_workshop_admission.py
app/core/document_workshop_contract.py
app/core/document_workshop_envelope.py
app/core/document_workshop_output_schema.py
app/core/document_workshop_turn.py
app/observability/observability_payload_guard.py
app/observability/observability_payload_guard_context_schema.py
```

Inventaire exact des IDs ci-dessous ; le hash du commit et l'état distant sont
donnés dans la livraison Git finale, sans référence circulaire du commit à lui-même.
Nettoyage effectué et vérifié : conteneur PG du lot, socket, overlays et logs
temporaires supprimés ; aucun réseau ni volume Docker créé. Runtime applicatif
toujours running/healthy sur l'image attendue. Liens locaux contrôlés et six JSON
historiques comparés à la base sans écart. L'inventaire AST des IDs et appels
d'assertion des quatre fichiers historiques modifiés est identique avant/après.

<details>
<summary>Inventaire des 167 IDs distincts (classe + méthode)</summary>

**unit — 132 IDs**

`tests.unit.core.test_document_workshop_admission.DocumentAdmissionTests` :

```text
test_adversarial_unicode_spaces_and_punctuation_follow_shared_estimate
test_complete_messages_counted_with_real_shared_callable
test_counter_error_invalid_unavailable_and_mutation_fail_closed
test_exact_estimated_threshold_and_output_reservation
test_hidden_extra_payload_or_multimodal_input_is_refused
test_model_outside_contract_is_not_replaced_and_secrets_not_resolved
test_new_sources_and_metadata_change_estimate_and_can_refuse
test_normal_builder_preserves_default_and_legitimate_override
test_one_complete_envelope_schema_is_counted_before_send
test_textual_response_schema_outside_messages_has_explicit_estimate_adapter
```

`tests.unit.core.test_document_workshop_canonical_paths.CanonicalContractTests` :

```text
test_codepoint_limit_independent_of_words
test_combining_and_non_bmp_codepoints_are_not_utf16_or_graphemes
test_exact_word_limit_and_refusal_do_not_rewrite_input
test_json_duplicate_fields_and_nonfinite_values_rejected
test_layout_and_final_writer_page_evidence
test_passive_links_and_style_preserved_active_references_refused
test_schema_is_closed_and_content_complete
test_titles_cells_and_links_cannot_hide_volume
test_unhashable_fields_are_protocol_refusals_and_envelope_is_bounded
test_unicode_count_and_split_spans_include_all_blocks
```

`tests.unit.core.test_document_workshop_canonical_paths.DocumentPathContractTests` :

```text
test_eight_directories_are_allowed_ninth_is_refused
test_formats_closed_and_extension_preserved
test_french_name_frozen_and_dav_segments_use_same_representation
test_full_relative_path_includes_documents_prefix
test_segment_codepoints_and_filename_extension_included
test_segment_utf8_limit_independent_of_codepoints
test_traversals_encoded_disguised_and_ambiguous_paths_rejected
test_unicode_reverse_separators_and_line_paragraph_ambiguities_refused
```

`tests.unit.core.test_document_workshop_envelope.DocumentEnvelopeTests` :

```text
test_canonical_validation_and_volume_limits_are_reused
test_clarify_and_refuse_preserve_real_surface_without_action
test_clarify_refuse_cannot_smuggle_a_proposal
test_duplicate_fields_inside_canonical_are_not_repaired
test_duplicate_keys_nonfinite_truncated_json_and_old_root_are_rejected
test_limitations_are_typed_unique_known_codes
test_only_create_copy_markdown_can_be_prepared
test_ordinary_surface_text_and_non_protocol_json_are_not_rewritten
test_prepared_content_and_proposal_are_frozen_without_rewriting
test_protocol_json_cannot_be_published_as_a_surface
test_root_and_proposal_are_closed_with_strict_types
test_source_ids_are_uuid_unique_even_with_equivalent_spellings
test_surface_codepoints_blank_controls_and_type_bounds
test_target_uses_m0_documents_path_authority
test_technical_envelope_bound_is_separate_and_never_truncates
```

`tests.unit.core.test_document_workshop_envelope_rejections.EnvelopeRejectionTests` :

```text
test_closed_sink_rejects_untrusted_values_extra_keys_and_other_stage
test_other_contract_codes_never_become_envelope_rejections
test_parsing_strict_unicode_input_and_first_guard
test_structure_surface_sources_and_limitations
```

`tests.unit.core.test_document_workshop_final_usage.FinalUsageHTTPTests` :

```text
test_accounting_exception_keeps_nearby_rejections_and_diagnostics
test_accounting_frame_merges_valid_partial_usage_after_content_bearing_stop
test_cancellation_and_inactivity_after_accounting_still_abort_real_socket
test_documented_final_usage_repeating_stop_keeps_exact_canonical_and_usage
test_final_usage_still_requires_done_and_cannot_repeat_twice
```

`tests.unit.core.test_document_workshop_http_transport.DocumentHTTPTransportTests` :

```text
test_body_protocol_rejects_invalid_json_and_utf8_content_free
test_chunked_json_response_is_consumed
test_close_interrupts_initial_headers_and_peer_observes_eof
test_close_interrupts_json_body_and_peer_observes_eof
test_close_interrupts_real_pending_tls_handshake_without_connection_leak
test_close_interrupts_sse_body_and_peer_observes_eof
test_diagnostic_construction_failure_preserves_rejection_and_physical_close
test_early_sse_rejection_does_not_drain_or_count_cleanup_as_http_end
test_eof_framed_json_response_is_consumed
test_eof_network_bound_is_enforced_without_waiting_for_peer_close
test_frozen_admitted_bytes_and_headers_reach_real_socket_verbatim_once
test_invalid_chunk_size_and_terminator_are_rejected
test_json_incomplete_and_other_sse_errors_do_not_gain_rejection_diagnostic
test_large_provider_envelope_has_network_space_beyond_canonical_limit
test_m0_cancellation_aborts_blocked_body_and_leaves_no_exchange_task
test_m0_inactivity_aborts_blocked_json_and_sse_read_without_late_success
test_m0_inactivity_aborts_initial_headers_socket_without_provider_event
test_network_bound_counts_chunked_decoded_bytes
test_network_bound_includes_chunk_framing_not_only_decoded_body
test_network_bound_rejects_announced_oversize_before_body_read
test_oversize_headers_are_bounded_before_end_marker
test_premature_eof_is_refused_for_content_length_and_chunked
test_real_chunked_sse_utf8_split_across_chunks_is_consumed
test_real_m0_consumes_sse_terminal_and_closes_one_exchange
test_real_m0_success_closes_peer_after_one_json_exchange
test_request_framing_injection_is_refused_before_any_socket
test_response_protocol_rejects_ambiguous_framing_encoding_and_headers
test_sse_eof_classifies_only_http_ends_consumed_by_real_transport
test_sse_incomplete_preserves_closed_site_and_observed_terminals
test_sse_lines_accept_cr_lf_and_crlf_across_response_chunks
test_sse_rejects_invalid_utf8_without_replacement
test_tls_verifies_certificate_on_real_loopback_connection
test_trailer_framing_cannot_replace_response_authority
```

`tests.unit.core.test_document_workshop_m4_observability.M4ProgressAndObservabilityTests` :

```text
test_closed_documentary_event_schema_accepts_only_technical_values
test_repeated_steps_or_sources_cannot_forge_progress
test_sse_diagnostic_guard_rejects_free_values_and_extra_content
test_upstream_steps_renew_effective_progress_without_total_deadline
```

`tests.unit.core.test_document_workshop_output_admission.OutputAdmissionTests` :

```text
test_competing_schema_is_refused_before_measure_or_transport_resolution
test_late_builder_and_schema_mutation_cannot_change_measured_body
test_normal_options_and_overrides_survive_documentary_local_omission
test_schema_cost_can_make_complete_input_exceed_unchanged_budget
test_schema_estimation_mutation_refused_before_transport_resolution
```

`tests.unit.core.test_document_workshop_provenance.DocumentProvenanceBoundaryTests` :

```text
test_indexed_source_survives_json_clones_and_identical_neighbor
test_response_format_estimation_adapter_does_not_change_sent_source_index
```

`tests.unit.core.test_document_workshop_provider_progress.DocumentProviderProgressTests` :

```text
test_actual_shared_admission_builder_and_simulated_send
test_blocked_open_is_also_covered
test_caller_task_cancellation_closes_transport
test_cancellation_is_prompt_and_no_late_result_can_succeed
test_clarify_and_refuse_are_complete_single_exchanges_without_canonical
test_complete_json_with_length_refused_without_repair
test_content_tool_calls_and_hidden_reasoning_never_become_envelope
test_continuous_keepalives_empty_or_reasoning_chunks_do_not_reset
test_counter_exception_never_sends_and_is_content_free
test_done_control_or_reasoning_only_cannot_prove_document
test_first_wait_blocked_read_exact_threshold_and_close
test_inactivity_late_result_is_neutralized
test_initial_cancel_and_failed_transport_release_do_not_succeed
test_invalid_envelope_or_old_canonical_root_has_one_call_and_no_repair
test_model_change_or_model_absence_refused
test_nonstream_empty_missing_terminal_invalid_json_or_canonical_refused
test_oversized_envelope_json_and_stream_fail_without_partial_document
test_oversized_sse_frame_is_rejected_before_json_decode
test_provider_context_error_refusal_http_and_exception_have_no_fallthrough
test_refused_estimate_never_sends
test_reported_completion_over_budget_refused
test_reported_context_overflow_without_total_is_refused
test_reported_usage_reuses_existing_extractor_and_absence_not_invented
test_same_preparation_does_not_send_twice
test_source_canary_in_protocol_surface_is_rejected_before_publication
test_steps_cannot_be_repeated_to_manufacture_progress
test_stream_is_consumed_and_terminal_usage_preserved
test_stream_length_no_done_and_error_frames_refused
test_stream_valid_json_without_finish_and_malformed_usage_refused
test_streamed_usage_components_merge_before_context_check
test_synchronous_preparation_cannot_hide_elapsed_inactivity
test_useful_stream_progress_allows_total_duration_over_120
test_valid_dense_content_can_have_a_larger_escaped_sse_frame
test_valid_multiline_sse_and_post_terminal_content_refused
```

`tests.unit.core.test_document_workshop_turn_ownership.DocumentaryLoopOwnershipTests` :

```text
test_cancel_returns_before_dns_releases_and_never_connects_late
test_inactivity_at_120_returns_before_dns_releases_and_never_connects_late
```

**sql — 19 IDs**

`tests.integration.document_workshop.test_output_contract_postgresql.OutputContractPostgresqlTests` :

```text
test_diagnostic_sink_failure_preserves_rejection_and_close
test_envelope_rejection_is_durable_and_content_free
test_real_assembly_schema_routing_measurement_and_exact_revision
```

`tests.integration.document_workshop.test_preparation_http_postgresql.HTTPPreparationPostgresqlTests` :

```text
test_diagnostic_emission_failure_keeps_public_error_failed_action_and_close
test_exact_admitted_http_bytes_consume_sse_and_commit_before_close
test_final_accounting_stop_commits_exact_revision_without_execution
test_keepalive_only_does_not_renew_inactivity_and_closes_real_socket
test_other_request_cancels_consumed_socket_and_prevents_late_commit
test_request_transaction_probe_rejects_transaction_held_during_real_http_wait
test_sse_rejection_reaches_existing_durable_channel_with_turn_and_action
```

`tests.integration.document_workshop.test_preparation_provenance_postgresql.PreparationProvenancePostgresqlTests` :

```text
test_equal_content_neighbor_does_not_inherit_document_provenance
test_estimation_mutation_refuses_transport
test_long_history_capsule_disabled_keeps_index_after_json_copies
test_long_history_capsule_enabled_keeps_index_after_json_copies
test_no_sources_with_capsule_has_no_document_attribution
test_original_messages_mutated_after_freeze_do_not_change_body_or_provenance
test_response_format_estimation_only_preserves_transmitted_source_position
test_selected_source_provenance_matches_received_loopback_bytes
test_three_sources_share_one_attributed_data_message
```

**schema — 4 IDs**

`tests.unit.core.test_document_workshop_output_schema.DocumentOutputSchemaTests` :

```text
test_all_statuses_operations_formats_blocks_and_rich_shapes
test_closed_required_variants_enums_types_and_references
test_schema_conformance_does_not_replace_local_business_guards
test_schema_uses_only_documented_subset_and_fresh_owned_objects
```

**neighbors — 12 IDs**

`tests.test_llm_client.LlmClientRuntimeSettingsTests` :

```text
test_build_payload_keeps_env_fallback_when_db_row_is_missing
test_build_payload_omits_reasoning_for_non_gpt51_main_model
test_build_payload_uses_runtime_main_model_from_db_when_present
```

`tests.unit.chat.test_main_llm_reasoning.MainLlmReasoningTests` :

```text
test_non_gpt51_model_does_not_send_reasoning
test_resolves_supported_gpt51_payload_with_hidden_reasoning
test_supported_reasoning_efforts_are_gpt51_specific
```

`tests.unit.logs.test_main_payload_manifest.MainPayloadManifestTests` :

```text
test_admin_projection_preserves_manifest_shape_content_free
test_hash_policy_rejects_stable_short_hash_leakage
test_simple_conversation_manifest_has_order_and_no_raw_content
```

`tests.unit.logs.test_observability_payload_guard.ObservabilityPayloadGuardTests` :

```text
test_content_free_payload_passes
test_dangerous_keys_and_nested_values_are_rejected_content_free
test_general_payload_rejects_unknown_mapping_and_list_keys
```

</details>
