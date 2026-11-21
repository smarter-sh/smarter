"""Test that the smarter.lib.logging package doesn't import itself while it initializes."""

import ast
import pathlib

from smarter.lib.unittest.base_classes import SmarterTestBase

PACKAGE = pathlib.Path(__file__).resolve().parent.parent
"""The smarter/lib/logging folder."""

SELF_IMPORTS = ("smarter.lib.logging",)
"""Imports of the package itself, which are circular in a module the package imports while initializing."""


def initialization_modules() -> list[pathlib.Path]:
    """Return the package's modules that its __init__.py imports, e.g. waffle_switched_logger.py."""
    tree = ast.parse((PACKAGE / "__init__.py").read_text())
    modules = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            modules.append(PACKAGE / f"{node.module}.py")
    return modules


def self_imports(path: pathlib.Path) -> list[str]:
    """Return the top-level statements of a module that import the smarter.lib.logging package."""
    tree = ast.parse(path.read_text())
    found = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "smarter.lib":
            for alias in node.names:
                if alias.name == "logging":
                    found.append(ast.unparse(node))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(SELF_IMPORTS):
            found.append(ast.unparse(node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(SELF_IMPORTS):
                    found.append(ast.unparse(node))
    return found


class TestPackageImports(SmarterTestBase):
    """The modules that __init__.py imports must not import smarter.lib.logging: it is still initializing."""

    def test_initialization_modules_are_found(self):
        names = [path.name for path in initialization_modules()]
        self.assertIn("waffle_switched_logger.py", names)
        self.assertIn("utils.py", names)

    def test_no_initialization_module_imports_the_package(self):
        for path in initialization_modules():
            with self.subTest(module=path.name):
                self.assertEqual(self_imports(path), [], "import the standard library's logging, or a sibling with '.'")
