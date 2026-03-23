"""Docs cross-reference freshness checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

_URI_PREFIXES = ("http://", "https://", "mailto:")
_ROOT_FILES = {
    "AGENTS.md",
    "ARCHITECTURE.md",
    "README.md",
    "Makefile",
    "pyproject.toml",
    ".pre-commit-config.yaml",
}
_ROOT_PREFIXES = (
    "docs/",
    "src/",
    "tests/",
    "scripts/",
    "openspec/",
    ".github/",
)
_KNOWN_SUFFIXES = (
    ".md",
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".sh",
)


@dataclass(frozen=True)
class MissingReference:
    source: Path
    reference: str
    resolved: Path


def markdown_files_for_freshness(root: Path) -> tuple[Path, ...]:
    """Return markdown files that participate in docs freshness checks."""

    files: list[Path] = []
    docs_root = root / "docs"
    if docs_root.is_dir():
        files.extend(path for path in docs_root.rglob("*.md") if path.is_file())

    for name in sorted(_ROOT_FILES):
        path = root / name
        if path.is_file() and path.suffix == ".md":
            files.append(path)

    return tuple(sorted(set(files), key=lambda path: str(path.relative_to(root))))


def _iter_reference_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    tokens.extend(match.group(1) for match in _MARKDOWN_LINK_RE.finditer(text))
    tokens.extend(match.group(1) for match in _INLINE_CODE_RE.finditer(text))
    return tuple(tokens)


def _normalize_reference(raw_reference: str) -> str | None:
    reference = raw_reference.strip()
    if not reference:
        return None
    if reference.startswith(_URI_PREFIXES):
        return None
    if reference.startswith("#"):
        return None
    if reference.startswith("<") and reference.endswith(">"):
        reference = reference[1:-1].strip()
    if not reference:
        return None

    if "#" in reference:
        reference = reference.split("#", 1)[0]
    if "?" in reference:
        reference = reference.split("?", 1)[0]
    if not reference:
        return None

    if any(char in reference for char in ("*", "{", "}", "<", ">", "|")):
        return None
    if any(char.isspace() for char in reference):
        return None

    if reference in _ROOT_FILES:
        return reference
    if reference.startswith(_ROOT_PREFIXES):
        return reference

    has_nested_path = "/" in reference.rstrip("/")
    if has_nested_path and (
        reference.endswith(_KNOWN_SUFFIXES) or reference.endswith("/")
    ):
        return reference
    if not has_nested_path and reference.endswith(".md"):
        return reference

    return None


def _resolve_reference(*, root: Path, source: Path, reference: str) -> Path:
    if reference.startswith("/"):
        return root / reference.lstrip("/")
    if reference in _ROOT_FILES or reference.startswith(_ROOT_PREFIXES):
        return root / reference
    return source.parent / reference


def find_missing_references(
    root: Path,
    *,
    markdown_files: tuple[Path, ...] | None = None,
) -> tuple[MissingReference, ...]:
    """Find stale local docs cross-references under *root*."""

    if markdown_files is None:
        markdown_files = markdown_files_for_freshness(root)

    missing: list[MissingReference] = []
    seen: set[tuple[str, str, str]] = set()

    for source in markdown_files:
        if not source.is_file():
            continue

        text = source.read_text(encoding="utf-8")
        for raw_reference in _iter_reference_tokens(text):
            normalized = _normalize_reference(raw_reference)
            if normalized is None:
                continue

            resolved = _resolve_reference(
                root=root, source=source, reference=normalized
            )
            if resolved.exists():
                continue

            key = (str(source), normalized, str(resolved))
            if key in seen:
                continue
            seen.add(key)
            missing.append(
                MissingReference(
                    source=source,
                    reference=normalized,
                    resolved=resolved,
                )
            )

    return tuple(
        sorted(
            missing,
            key=lambda item: (
                str(item.source.relative_to(root)),
                item.reference,
                str(item.resolved),
            ),
        )
    )
