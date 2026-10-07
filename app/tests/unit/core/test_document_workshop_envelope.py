from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import json
import unittest

from core.document_workshop_contract import DocumentWorkshopError
from tests.unit.core.test_document_workshop_canonical_paths import canonical


SOURCE_ID = "00000000-0000-4000-8000-000000000001"


def envelope(*, status="prepared", text="Document préparé.", document=None, **proposal_changes):
    proposal = {
        "operation": "create", "format": "markdown", "relative_path": "Documents/texte.md",
        "source_file_ids": [], "limitations": [],
        "canonical": canonical() if document is None else document,
        **proposal_changes,
    } if status == "prepared" else None
    return {"schema_version": 1, "status": status, "surface_text": text, "proposal": proposal}


class DocumentEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.document_workshop_envelope"), "M4 envelope interface absent")
        self.module = importlib.import_module("core.document_workshop_envelope")

    def read(self, data):
        return self.module.read_document_envelope(json.dumps(data, ensure_ascii=False))

    def reject(self, data, code="document_envelope_invalid"):
        before = copy.deepcopy(data)
        with self.assertRaises(DocumentWorkshopError) as raised:
            self.read(data)
        self.assertEqual(raised.exception.reason_code, code)
        self.assertEqual(data, before)

    def test_prepared_content_and_proposal_are_frozen_without_rewriting(self):
        data = envelope(text="  Prêt : e\u0301 😀.  ", relative_path="Documents/Études/e\u0301.md", source_file_ids=[SOURCE_ID])
        result = self.read(data)
        data["proposal"]["canonical"]["blocks"].clear()
        self.assertEqual(result.status, "prepared")
        self.assertEqual(result.surface_text, "  Prêt : e\u0301 😀.  ")
        self.assertEqual(result.relative_path, "Documents/Études/e\u0301.md")
        self.assertEqual(result.operation, "create")
        self.assertEqual(result.format, "markdown")
        self.assertEqual(result.source_file_ids, (SOURCE_ID,))
        self.assertEqual(result.limitations, ())
        self.assertEqual(result.canonical.as_dict(), canonical())
        projection = result.as_dict()
        projection["proposal"]["canonical"]["blocks"].clear()
        self.assertEqual(result.canonical.as_dict(), canonical())
        with self.assertRaises(FrozenInstanceError):
            result.surface_text = "changed"
        self.assertNotIn("Prêt", repr(result))
        self.assertNotIn("Études", repr(result))

    def test_clarify_and_refuse_preserve_real_surface_without_action(self):
        for status in ("clarify", "refuse"):
            with self.subTest(status=status):
                data = envelope(status=status, text="Précision nécessaire." if status == "clarify" else "Demande hors périmètre.")
                result = self.read(data)
                self.assertEqual(result.as_dict(), data)
                self.assertEqual(result.status, status)
                self.assertIsNone(result.canonical)
                self.assertIsNone(result.operation)
                self.assertIsNone(result.relative_path)
                self.assertIsNone(result.format)
                self.assertEqual(result.source_file_ids, ())
                self.assertEqual(result.limitations, ())

    def test_root_and_proposal_are_closed_with_strict_types(self):
        malformed = []
        for field in ("schema_version", "status", "surface_text", "proposal"):
            data = envelope()
            del data[field]
            malformed.append(data)
        for status in (True, 1, [], {}, "complete", "Prepared", None):
            malformed.append({**envelope(), "status": status})
        malformed.extend([{**envelope(), "schema_version": True}, {**envelope(), "schema_version": 2},
                          {**envelope(), "canonical": canonical()}, {**envelope(), "proposal": None}])
        for field in ("operation", "format", "relative_path", "source_file_ids", "limitations", "canonical"):
            data = envelope()
            del data["proposal"][field]
            malformed.append(data)
        malformed.append(envelope(target_file_id=SOURCE_ID))
        for data in malformed:
            with self.subTest(index=malformed.index(data)):
                self.reject(data)

    def test_clarify_refuse_cannot_smuggle_a_proposal(self):
        for status in ("clarify", "refuse"):
            for proposal in ({}, envelope()["proposal"], []):
                self.reject({**envelope(status=status), "proposal": proposal})

    def test_surface_codepoints_blank_controls_and_type_bounds(self):
        self.assertEqual(self.read(envelope(text="😀" * 2000)).surface_text, "😀" * 2000)
        for text in ("😀" * 2001, "", " \n\t", None, [], 7, "x\x00", "x\ud800"):
            with self.subTest(kind=type(text).__name__, size=len(text) if isinstance(text, str) else 0):
                # JSON ensure_ascii escapes lone surrogates for the validator.
                raw = json.dumps(envelope(text=text), ensure_ascii=True)
                with self.assertRaises(DocumentWorkshopError) as raised:
                    self.module.read_document_envelope(raw)
                self.assertEqual(raised.exception.reason_code, "document_envelope_invalid")

    def test_protocol_json_cannot_be_published_as_a_surface(self):
        canonical_json = json.dumps(canonical("synthetic source canary"))
        envelope_json = json.dumps(envelope(status="clarify", text="Précision nécessaire."))
        for status in ("prepared", "clarify", "refuse"):
            for text in (canonical_json, envelope_json, "```json\n" + canonical_json + "\n```",
                         "```\n" + canonical_json + "\n```", "```JSON\n" + envelope_json + "\n```",
                         json.dumps({"preview": canonical()}), json.dumps([envelope(status="refuse")]),
                         "Document : " + canonical_json, canonical_json + "\nDocument préparé.",
                         "Précision : " + envelope_json + " (voir ci-dessus)",
                         "Voici `" + canonical_json + "`."):
                with self.subTest(status=status, fenced=text.startswith("```")):
                    self.reject(envelope(status=status, text=text))

    def test_ordinary_surface_text_and_non_protocol_json_are_not_rewritten(self):
        for text in ('  {"explanation":"Précision nécessaire.","schema_version":1}  ',
                     "Le mot canonical désigne la révision préparée.", "```json\n{\"explanation\":\"Précision\"}\n```",
                     "synthetic source canary"):
            self.assertEqual(self.read(envelope(status="clarify", text=text)).surface_text, text)
        # A plaintext source echo cannot be classified structurally without
        # rejecting legitimate speech; the prompt carries that semantic rule.

    def test_only_create_copy_markdown_can_be_prepared(self):
        self.assertEqual(self.read(envelope(operation="copy", source_file_ids=[SOURCE_ID])).operation, "copy")
        # M7 parses update; selected-target/version authority is server-owned
        # and must still be established before a durable confirmable action.
        self.assertEqual(self.read(envelope(operation="update")).operation, "update")
        for operation in ("delete", None, [], 1):
            self.reject(envelope(operation=operation))
        for format in ("docx", "pdf", "txt", [], None):
            self.reject(envelope(format=format))
        self.reject(envelope(operation="copy"))

    def test_target_uses_m0_documents_path_authority(self):
        for path in ("Documents/../x.md", "Elsewhere/x.md", "Documents/x.docx", "/Documents/x.md"):
            self.reject(envelope(relative_path=path), "document_path_invalid")
        self.reject(envelope(relative_path="Documents/" + "a/" * 9 + "x.md"), "document_path_depth_limit")

    def test_source_ids_are_uuid_unique_even_with_equivalent_spellings(self):
        upper = "ABCDEF00-0000-4000-8000-000000000001"
        result = self.read(envelope(source_file_ids=[upper]))
        self.assertEqual(result.source_file_ids, (upper.lower(),))
        for values in (None, "uuid", {}, [1], ["invalid"], [SOURCE_ID, SOURCE_ID], [upper, upper.lower()]):
            self.reject(envelope(source_file_ids=values))

    def test_limitations_are_typed_unique_known_codes(self):
        codes = ["markdown_pagination_reader_dependent", "markdown_style_reader_dependent",
                 "write_confirmation_unavailable", "docx_pdf_unavailable", "update_unavailable"]
        self.assertEqual(self.read(envelope(limitations=codes)).limitations, tuple(codes))
        for values in (None, "code", {}, [1], [[]], ["unknown"], [codes[0], codes[0]]):
            self.reject(envelope(limitations=values))

    def test_canonical_validation_and_volume_limits_are_reused(self):
        self.reject(envelope(document={}), "document_canonical_invalid")
        self.reject(envelope(document=canonical("x" * 75001)), "document_character_limit")
        self.reject(envelope(document=canonical("mot " * 10001)), "document_word_limit")
        document = canonical()
        document["blocks"] += [{"type": "page_break"}] * 50000
        self.reject(envelope(document=document), "document_json_envelope_limit")

    def test_duplicate_keys_nonfinite_truncated_json_and_old_root_are_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}', '{',
                    json.dumps(canonical()), "", "```json\n{}\n```", None, {}):
            with self.subTest(kind=type(raw).__name__):
                with self.assertRaises(DocumentWorkshopError) as raised:
                    self.module.read_document_envelope(raw)
                self.assertEqual(raised.exception.reason_code, "document_envelope_invalid")

    def test_duplicate_fields_inside_canonical_are_not_repaired(self):
        raw = json.dumps(envelope()).replace('"profile": "frida_document_v1"',
                                            '"profile": "frida_document_v1", "profile": "frida_document_v1"')
        with self.assertRaises(DocumentWorkshopError) as raised:
            self.module.read_document_envelope(raw)
        self.assertEqual(raised.exception.reason_code, "document_envelope_invalid")

    def test_technical_envelope_bound_is_separate_and_never_truncates(self):
        raw = json.dumps(envelope())
        maximum = 1048576 + 65536
        exact = raw + " " * (maximum - len(raw.encode("utf-8")))
        self.assertEqual(self.module.read_document_envelope(exact).canonical.as_dict(), canonical())
        with self.assertRaises(DocumentWorkshopError) as raised:
            self.module.read_document_envelope(exact + " ")
        self.assertEqual(raised.exception.reason_code, "document_json_envelope_limit")


if __name__ == "__main__":
    unittest.main()
