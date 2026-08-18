from __future__ import annotations

import importlib
import unittest

from biblio import librarian_tools


def _registry_module():
    try:
        return importlib.import_module("biblio.librarian_tool_registry")
    except ModuleNotFoundError as exc:
        raise AssertionError("the Lot 9G.1 registry boundary is missing") from exc


def _handlers(registry_module, handler=None):
    selected = handler or (lambda params: params)
    return {name: selected for name in registry_module.LOT3_TOOL_NAMES}


def _construct(registry_module, **kwargs):
    try:
        return registry_module.BiblioLibrarianToolRegistry(**kwargs)
    except TypeError as exc:
        raise AssertionError("the registry boundary still requires an external namespace") from exc


class BiblioLibrarianToolRegistryBoundaryTests(unittest.TestCase):
    def test_registry_requires_an_exact_ordered_handler_set(self) -> None:
        registry_module = _registry_module()
        exact = _handlers(registry_module)

        registry = _construct(
            registry_module,
            handlers=exact,
        )

        self.assertEqual(registry.tool_names, registry_module.LOT3_TOOL_NAMES)
        for mutated in (
            dict(tuple(exact.items())[:-1]),
            {**exact, "synthetic_extra": lambda params: params},
            dict(reversed(tuple(exact.items()))),
        ):
            with self.subTest(handler_names=tuple(mutated)):
                with self.assertRaises(ValueError):
                    _construct(
                        registry_module,
                        handlers=mutated,
                    )

    def test_registry_rejects_before_dispatch_and_copies_allowed_params(self) -> None:
        registry_module = _registry_module()
        dispatched: list[dict[str, object]] = []

        def read_handler(params):
            dispatched.append(params)
            params["handler_mutation"] = True
            return "allowed-result"

        handlers = _handlers(registry_module)
        handlers[registry_module.TOOL_CATALOG_LIST] = read_handler
        registry = _construct(
            registry_module,
            handlers=handlers,
        )
        original = {"limit": 3}

        self.assertEqual(
            registry.run(f" {registry_module.TOOL_CATALOG_LIST} ", original),
            "allowed-result",
        )
        self.assertEqual(original, {"limit": 3})
        self.assertEqual(dispatched, [{"limit": 3, "handler_mutation": True}])

        error_type = getattr(registry_module, "BiblioLibrarianToolError", None)
        self.assertIsNotNone(error_type)
        for name, reason in (("export/chunk", "forbidden_tool"), ("missing", "unknown_tool")):
            with self.subTest(tool_name=name):
                with self.assertRaises(error_type) as raised:
                    registry.run(name, {"raw": "synthetic"})
                self.assertEqual(raised.exception.tool_name, name)
                self.assertEqual(raised.exception.reason_code, reason)
        self.assertEqual(len(dispatched), 1)

    def test_librarian_tools_keeps_the_compatibility_surface(self) -> None:
        registry_module = _registry_module()
        client = object()
        registry = librarian_tools.build_librarian_tool_registry(client)

        self.assertIs(
            librarian_tools.BiblioLibrarianToolRegistry,
            registry_module.BiblioLibrarianToolRegistry,
        )
        self.assertIsInstance(registry, registry_module.BiblioLibrarianToolRegistry)
        self.assertEqual(registry.tool_names, librarian_tools.LOT3_TOOL_NAMES)
        self.assertIs(getattr(registry, "_client", None), client)
        error_type = getattr(registry_module, "BiblioLibrarianToolError", None)
        self.assertIsNotNone(error_type)
        self.assertIs(
            librarian_tools.BiblioLibrarianToolError,
            error_type,
        )


if __name__ == "__main__":
    unittest.main()
