from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

# =============================================================================
# Module Overview
# =============================================================================
# The import rule as a test. A tool imports `shared` and nothing else in the
# repo; only `chat/` and `analysis/` call more than one tool. The second test
# guards the flat layout: a dependency that installed its own top-level
# `shared`, `tools`, `chat` or `api` would shadow ours silently.

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FORBIDDEN_FOR_TOOLS = ("chat", "api", "analysis", "tests", "scripts")


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def test_a_tool_imports_shared_and_nothing_else_in_the_repo() -> None:
    offenders: list[str] = []
    for tool_dir in sorted(p for p in TOOLS.iterdir() if p.is_dir()):
        for py in tool_dir.rglob("*.py"):
            for name in _imported_roots(py):
                head = name.split(".")[0]
                other_tool = name.startswith("tools.") and not name.startswith(f"tools.{tool_dir.name}")
                if other_tool or head in FORBIDDEN_FOR_TOOLS:
                    offenders.append(f"{py.relative_to(ROOT)} imports {name}")
    assert not offenders, "tools talk through shared.types, not imports:\n" + "\n".join(offenders)


def test_the_four_packages_resolve_to_this_repo() -> None:
    for name in ("shared", "tools", "chat", "api"):
        spec = importlib.util.find_spec(name)
        assert spec is not None and spec.origin, f"{name} does not import"
        assert Path(spec.origin).resolve().is_relative_to(ROOT), f"{name} resolves outside the repo: {spec.origin}"
