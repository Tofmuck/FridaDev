from __future__ import annotations

import copy
import unittest

from tests.support import memory_admin_golden


class Lot9MemoryAdminGoldenMatrixTests(unittest.TestCase):
    def test_memory_summary_lane_and_arbiter_provenance_form_one_stable_matrix(self) -> None:
        observed = memory_admin_golden.exercise_memory_arbiter_matrix()

        self.assertEqual(observed, memory_admin_golden.EXPECTED_MEMORY_ARBITER_MATRIX)
        memory_admin_golden.assert_content_free(observed)

        lane_mutation = copy.deepcopy(observed)
        lane_mutation["internal_sources"] = tuple(reversed(lane_mutation["internal_sources"]))
        with self.assertRaises(AssertionError):
            self.assertEqual(lane_mutation, memory_admin_golden.EXPECTED_MEMORY_ARBITER_MATRIX)

        provenance_mutation = copy.deepcopy(observed)
        provenance_mutation["decisions"] = (
            (*provenance_mutation["decisions"][0][:-2], "fallback", "synthetic-memory-arbiter"),
            *provenance_mutation["decisions"][1:],
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(provenance_mutation, memory_admin_golden.EXPECTED_MEMORY_ARBITER_MATRIX)

    def test_identity_read_model_keeps_canonical_surfaces_and_minimizes_legacy_layers(self) -> None:
        observed = memory_admin_golden.exercise_identity_read_model_matrix()

        self.assertEqual(observed, memory_admin_golden.EXPECTED_IDENTITY_MATRIX)
        memory_admin_golden.assert_content_free(observed)

        authority_mutation = copy.deepcopy(observed)
        authority_mutation["legacy_runtime_authority"] = ("active", "historical_only")
        with self.assertRaises(AssertionError):
            self.assertEqual(authority_mutation, memory_admin_golden.EXPECTED_IDENTITY_MATRIX)

        leaked = copy.deepcopy(observed)
        leaked["raw_legacy"] = memory_admin_golden.RAW_LEGACY_IDENTITY
        with self.assertRaises(AssertionError):
            memory_admin_golden.assert_content_free(leaked)

    def test_runtime_settings_read_validate_patch_matrix_redacts_secrets(self) -> None:
        observed = memory_admin_golden.exercise_runtime_settings_matrix()

        self.assertEqual(observed, memory_admin_golden.EXPECTED_SETTINGS_MATRIX)
        memory_admin_golden.assert_content_free(observed)

        validity_mutation = copy.deepcopy(observed)
        validity_mutation["validation"] = {**validity_mutation["validation"], "valid": False}
        with self.assertRaises(AssertionError):
            self.assertEqual(validity_mutation, memory_admin_golden.EXPECTED_SETTINGS_MATRIX)

        leaked = copy.deepcopy(observed)
        leaked["secret"] = memory_admin_golden.RAW_SETTINGS_SECRET
        with self.assertRaises(AssertionError):
            memory_admin_golden.assert_content_free(leaked)


if __name__ == "__main__":
    unittest.main()
