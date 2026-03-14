"""Tests for scripts.evals quality gate checks."""

from __future__ import annotations

from pathlib import Path

from scripts.evals import check_docstrings, check_no_todos


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_check_docstrings_reports_public_symbols_without_docstrings(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "app" / "src"
    _write_file(
        source_root / "module.py",
        "def public_function():\n"
        "    return 1\n\n"
        "def _private_function():\n"
        "    return 2\n",
    )

    violations = check_docstrings(source_root)

    assert len(violations) == 1
    assert "public_function" in violations[0].message


def test_check_docstrings_ignores_empty_init(tmp_path: Path) -> None:
    source_root = tmp_path / "app" / "src"
    _write_file(source_root / "__init__.py", "")

    violations = check_docstrings(source_root)

    assert violations == []


def test_check_no_todos_detects_text_and_placeholder_patterns(tmp_path: Path) -> None:
    source_root = tmp_path / "app" / "src"
    _write_file(
        source_root / "module.py",
        "# TODO remove\n"
        "def incomplete():\n"
        "    pass\n\n"
        "def incomplete_ellipsis():\n"
        "    ...\n\n"
        "def allowed_skeleton():\n"
        '    """Documented skeleton."""\n'
        "    pass\n",
    )

    violations = check_no_todos(source_root)
    messages = [violation.message for violation in violations]

    assert any("TODO" in message for message in messages)
    assert any("incomplete" in message for message in messages)
    assert any("incomplete_ellipsis" in message for message in messages)
    assert all("allowed_skeleton" not in message for message in messages)


def test_check_no_todos_skips_placeholder_bodies_in_init_files(
    tmp_path: Path,
) -> None:
    """Placeholder function bodies in __init__.py files are not flagged."""
    source_root = tmp_path / "app" / "src"
    _write_file(
        source_root / "__init__.py",
        "def placeholder_in_init():\n    pass\n",
    )
    _write_file(
        source_root / "module.py",
        "def placeholder_in_module():\n    pass\n",
    )

    violations = check_no_todos(source_root)
    messages = [violation.message for violation in violations]

    assert any("placeholder_in_module" in message for message in messages)
    assert all("placeholder_in_init" not in message for message in messages)
