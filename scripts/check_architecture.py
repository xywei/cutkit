#!/usr/bin/env python3
"""Enforce architecture dependency direction for core CUTKIT layers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

CORE_LAYER_ORDER = {
    "geometry": 0,
    "topology": 1,
    "clipping": 2,
    "quadrature": 3,
}
UTILITY_LAYERS = {"diagnostics", "io"}
KNOWN_LAYERS = set(CORE_LAYER_ORDER) | UTILITY_LAYERS

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "cutkit"
SRC_ROOT = REPO_ROOT / "src"


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    message: str


def module_name_for_path(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def layer_for_module(module_name: str) -> str | None:
    parts = module_name.split(".")
    if len(parts) >= 2 and parts[0] == "cutkit" and parts[1] in KNOWN_LAYERS:
        return parts[1]
    return None


def imported_modules(current_module: str, node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    if isinstance(node, ast.ImportFrom):
        if node.level == 0:
            return [node.module] if node.module is not None else []

        current_parts = current_module.split(".")
        if node.level > len(current_parts):
            return []

        base_parts = current_parts[: -node.level]
        if node.module is not None:
            return [".".join(base_parts + node.module.split("."))]

        modules: list[str] = []
        for alias in node.names:
            modules.append(".".join(base_parts + [alias.name]))
        return modules

    return []


def is_dependency_allowed(source_layer: str, target_layer: str) -> bool:
    if source_layer not in CORE_LAYER_ORDER:
        return True
    if target_layer not in CORE_LAYER_ORDER:
        return False
    return CORE_LAYER_ORDER[target_layer] <= CORE_LAYER_ORDER[source_layer]


def required_layer_dirs_missing() -> list[str]:
    missing: list[str] = []
    for layer in sorted(KNOWN_LAYERS):
        if not (PACKAGE_ROOT / layer).is_dir():
            missing.append(layer)
    return missing


def collect_violations() -> list[Violation]:
    violations: list[Violation] = []

    missing_layers = required_layer_dirs_missing()
    for layer in missing_layers:
        violations.append(
            Violation(
                path=PACKAGE_ROOT,
                lineno=1,
                message=f"Missing required architecture layer directory: cutkit/{layer}",
            )
        )

    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        module_name = module_name_for_path(path)
        source_layer = layer_for_module(module_name)
        if source_layer is None:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            for imported in imported_modules(module_name, node):
                if imported is None:
                    continue
                imported = imported.strip()
                if not imported.startswith("cutkit."):
                    continue

                target_layer = layer_for_module(imported)
                if target_layer is None:
                    continue

                if source_layer == target_layer:
                    continue

                if is_dependency_allowed(source_layer, target_layer):
                    continue

                violations.append(
                    Violation(
                        path=path,
                        lineno=getattr(node, "lineno", 1),
                        message=(
                            f"Forbidden dependency: {source_layer} cannot depend on {target_layer} "
                            f"({module_name} imports {imported})."
                        ),
                    )
                )

    return violations


def main() -> int:
    violations = collect_violations()
    if not violations:
        print("Architecture check passed.")
        return 0

    print("Architecture check failed:")
    for violation in violations:
        rel = violation.path.relative_to(REPO_ROOT)
        print(f"- {rel}:{violation.lineno}: {violation.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
