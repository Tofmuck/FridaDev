from __future__ import annotations

import copy
import unittest
from types import SimpleNamespace

from admin import runtime_settings_validation


class RuntimeSettingsValidationBoundaryTests(unittest.TestCase):
    def test_facade_preserves_real_model_and_platform_validation_outcomes(self) -> None:
        model_validation = getattr(
            runtime_settings_validation,
            "runtime_settings_model_validation",
            None,
        )
        platform_validation = getattr(
            runtime_settings_validation,
            "runtime_settings_platform_validation",
            None,
        )
        self.assertIsNotNone(model_validation)
        self.assertIsNotNone(platform_validation)

        views = {
            "arbiter_model": SimpleNamespace(
                payload={
                    "model": {"value": "synthetic/legacy-arbiter"},
                    "timeout_s": {"value": 3},
                    "temperature": {"value": 0.0},
                    "top_p": {"value": 1.0},
                },
                source="candidate",
                source_reason="validate_payload",
            ),
            "agenda_agent": SimpleNamespace(
                payload={
                    "mode": {"value": "off"},
                    "caldav_account": {"value": "tof"},
                    "caldav_app_password": {"is_secret": True, "is_set": False},
                },
                source="candidate",
                source_reason="validate_payload",
            ),
        }

        def candidate_runtime_section(section, **_kwargs):
            return views[section]

        def fail_secret_resolution(*_args, **_kwargs):
            raise AssertionError("these two validators must not resolve a secret")

        common_kwargs = {
            "candidate_runtime_section": candidate_runtime_section,
            "resolve_runtime_secret_from_view": fail_secret_resolution,
            "secret_required_error_cls": RuntimeError,
            "secret_resolution_error_cls": ValueError,
            "config_module": SimpleNamespace(),
        }
        model_result = runtime_settings_validation.validate_runtime_section(
            "arbiter_model",
            **common_kwargs,
        )
        platform_result = runtime_settings_validation.validate_runtime_section(
            "agenda_agent",
            **common_kwargs,
        )

        projection = {
            "model": (
                model_result["section"],
                model_result["source"],
                model_result["source_reason"],
                model_result["valid"],
                tuple(
                    (check["name"], check["ok"], check["detail"])
                    for check in model_result["checks"]
                ),
            ),
            "platform": (
                platform_result["section"],
                platform_result["source"],
                platform_result["source_reason"],
                platform_result["valid"],
                tuple(
                    (check["name"], check["ok"], check["detail"])
                    for check in platform_result["checks"]
                ),
            ),
        }
        expected = {
            "model": (
                "arbiter_model",
                "candidate",
                "validate_payload",
                True,
                (
                    ("model", True, "model=synthetic/legacy-arbiter"),
                    ("timeout_s", True, "timeout_s=3"),
                    ("temperature", True, "temperature=0.0"),
                    ("top_p", True, "top_p=1.0"),
                ),
            ),
            "platform": (
                "agenda_agent",
                "candidate",
                "validate_payload",
                True,
                (
                    ("mode", True, "mode=off; allowed=off,active"),
                    (
                        "caldav_identity",
                        True,
                        "caldav_account=tof; expected=tof; service_account=false",
                    ),
                    (
                        "caldav_app_password_presence",
                        True,
                        "configured=False; required_for_mode=False; value=redacted",
                    ),
                    (
                        "caldav_runtime_access",
                        True,
                        "lot2 configuration only; caldav_access=false; nextcloud_access=false",
                    ),
                ),
            ),
        }
        self.assertEqual(projection, expected)

        wrong_router = copy.deepcopy(projection)
        wrong_router["model"] = projection["platform"]
        with self.assertRaises(AssertionError):
            self.assertEqual(wrong_router, expected)


if __name__ == "__main__":
    unittest.main()
