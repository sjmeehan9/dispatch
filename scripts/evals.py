"""Project quality gate checks for Dispatch source files."""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SOURCE_ROOT = Path("app/src")
PYTHON_EXTENSION = ".py"
TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("TODO comment", re.compile(r"\bTODO\b")),
    ("FIXME comment", re.compile(r"\bFIXME\b")),
    ("NotImplementedError usage", re.compile(r"\bNotImplementedError\b")),
)


@dataclass(frozen=True)
class Violation:
    """Represents a quality check violation."""

    file_path: Path
    line: int
    message: str


def _iter_python_files(path: Path) -> list[Path]:
    """Return sorted Python files under a source root."""

    return sorted(file_path for file_path in path.rglob(f"*{PYTHON_EXTENSION}"))


def _read_file(file_path: Path) -> str:
    """Read a UTF-8 text file."""

    return file_path.read_text(encoding="utf-8")


def _parse_ast(file_path: Path, source: str) -> ast.AST:
    """Parse Python source into an AST."""

    return ast.parse(source, filename=str(file_path))


def _is_public(name: str) -> bool:
    """Return whether a symbol name should be treated as public."""

    return not name.startswith("_")


def _display_path(file_path: Path) -> str:
    """Return a repository-relative path for reporting."""

    return file_path.as_posix()


def check_docstrings(path: Path) -> list[Violation]:
    """Check public classes and functions for docstrings.

    Args:
        path: Source root to inspect.

    Returns:
        A list of detected violations.
    """

    violations: list[Violation] = []
    for file_path in _iter_python_files(path):
        source = _read_file(file_path)
        if file_path.name == "__init__.py" and not source.strip():
            continue

        tree = _parse_ast(file_path, source)
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            if not _is_public(node.name):
                continue
            if ast.get_docstring(node, clean=False) is None:
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        message=f"Missing docstring for public symbol '{node.name}'",
                    )
                )
    return violations


def _is_placeholder_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function body is only a placeholder statement."""

    if len(node.body) != 1:
        return False

    statement = node.body[0]
    if isinstance(statement, ast.Pass):
        return ast.get_docstring(node, clean=False) is None

    if isinstance(statement, ast.Expr):
        value = statement.value
        if isinstance(value, ast.Constant) and value.value is Ellipsis:
            return ast.get_docstring(node, clean=False) is None

    return False


def check_no_todos(path: Path) -> list[Violation]:
    """Check source files for TODO/FIXME and placeholder implementations.

    Args:
        path: Source root to inspect.

    Returns:
        A list of detected violations.
    """

    violations: list[Violation] = []
    for file_path in _iter_python_files(path):
        source = _read_file(file_path)
        lines = source.splitlines()
        for line_number, line in enumerate(lines, start=1):
            for label, pattern in TEXT_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=line_number,
                            message=f"{label} found",
                        )
                    )

        tree = _parse_ast(file_path, source)
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and _is_placeholder_body(node):
                violations.append(
                    Violation(
                        file_path=file_path,
                        line=node.lineno,
                        message=f"Placeholder function body in '{node.name}'",
                    )
                )
    return violations


def _print_section(title: str, violations: list[Violation]) -> None:
    """Print a formatted report section."""

    print(f"\n{title}")
    if not violations:
        print("  PASS")
        return

    for violation in sorted(
        violations, key=lambda item: (item.file_path.as_posix(), item.line)
    ):
        print(
            f"  { _display_path(violation.file_path) }:{violation.line}: {violation.message}"
        )


def main() -> int:
    """Run all quality checks and return an exit code."""

    if not SOURCE_ROOT.exists():
        print(f"Source root not found: {SOURCE_ROOT}")
        return 1

    docstring_violations = check_docstrings(SOURCE_ROOT)
    todo_violations = check_no_todos(SOURCE_ROOT)
    all_violations = docstring_violations + todo_violations

    _print_section("Docstring checks", docstring_violations)
    _print_section("Placeholder and TODO checks", todo_violations)
    print(f"\nSummary: {len(all_violations)} violation(s)")

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
