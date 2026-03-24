"""Docs cross-reference freshness checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import unquote

_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_FENCED_CODE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_FENCED_TOKEN_RE = re.compile(r"[A-Za-z0-9._/-]+")
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_SETEXT_HEADING_UNDERLINE_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
_FENCE_DELIMITER_RE = re.compile(r"^\s*```")
_MARKDOWN_LINK_LABEL_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_TRAILING_HEADING_HASHES_RE = re.compile(r"\s+#+\s*$")
_ANCHOR_INVALID_CHARS_RE = re.compile(r"[^\w\s-]")
_WHITESPACE_RE = re.compile(r"\s+")
_MULTI_DASH_RE = re.compile(r"-{2,}")
_FRONTMATTER_KEY_VALUE_RE = re.compile(r"^[A-Za-z0-9_.\"' -]+\s*:\s*.*$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_ANCHOR_TAG_RE = re.compile(
    r"<a\b(?P<attrs>[^>]*)>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_ANCHOR_ATTR_RE = re.compile(
    r"(?:^|\s)(?:id|name)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')",
    re.IGNORECASE,
)

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
_EXEC_PLAN_STAGE_DIRS = {
    "active/",
    "completed/",
}
_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".entire",
    "node_modules",
}


def _is_exec_plan_stage_reference(*, reference: str, root: Path, source: Path) -> bool:
    if reference not in _EXEC_PLAN_STAGE_DIRS:
        return False
    exec_plans_root = root / "docs" / "exec-plans"
    try:
        source.relative_to(exec_plans_root)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class MissingReference:
    source: Path
    reference: str
    resolved: Path
    missing_anchor: str | None = None


@dataclass(frozen=True)
class _AnchorCatalog:
    heading_anchors: frozenset[str]
    explicit_anchors: frozenset[str]


def markdown_files_for_freshness(root: Path) -> tuple[Path, ...]:
    """Return markdown files that participate in docs freshness checks."""

    files: set[Path] = set()

    for parent in (
        root / "docs",
        root / "openspec",
        root / ".codex",
        root / ".opencode",
    ):
        if parent.is_dir():
            files.update(path for path in parent.rglob("*.md") if path.is_file())

    files.update(path for path in root.rglob("README.md") if path.is_file())

    for name in sorted(_ROOT_FILES):
        path = root / name
        if path.is_file() and path.suffix == ".md":
            files.add(path)

    filtered = [
        path
        for path in files
        if not any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts[:-1])
    ]
    return tuple(sorted(filtered, key=lambda path: str(path.relative_to(root))))


def _iter_reference_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    tokens.extend(match.group(1) for match in _MARKDOWN_LINK_RE.finditer(text))
    tokens.extend(match.group(1) for match in _INLINE_CODE_RE.finditer(text))
    for block in _FENCED_CODE_RE.findall(text):
        for match in _FENCED_TOKEN_RE.finditer(block):
            token = match.group(0)
            if token in {".", ".."}:
                continue
            tokens.append(token)
    return tuple(tokens)


def _iter_markdown_link_targets(text: str) -> tuple[str, ...]:
    return tuple(match.group(1) for match in _MARKDOWN_LINK_RE.finditer(text))


def _slugify_anchor_text(text: str) -> str:
    normalized = text.strip().lower()
    if not normalized:
        return ""
    normalized = _MARKDOWN_LINK_LABEL_RE.sub(r"\1", normalized)
    normalized = normalized.replace("`", "")
    normalized = _ANCHOR_INVALID_CHARS_RE.sub("", normalized)
    normalized = _WHITESPACE_RE.sub("-", normalized)
    normalized = _MULTI_DASH_RE.sub("-", normalized)
    return normalized.strip("-")


def _decode_anchor_fragment(raw_fragment: str) -> str | None:
    decoded = unquote(raw_fragment).strip()
    if not decoded:
        return None
    return decoded


def _normalize_anchor_fragment(raw_fragment: str) -> str | None:
    decoded = _decode_anchor_fragment(raw_fragment)
    if decoded is None:
        return None
    normalized = _slugify_anchor_text(decoded)
    if not normalized:
        return None
    return normalized


def _extract_explicit_html_anchors(text: str) -> frozenset[str]:
    sanitized = _FENCED_CODE_RE.sub("\n", text)
    sanitized = _INLINE_CODE_RE.sub("", sanitized)
    sanitized = _HTML_COMMENT_RE.sub("", sanitized)

    anchors: set[str] = set()
    for tag_match in _HTML_ANCHOR_TAG_RE.finditer(sanitized):
        attrs = tag_match.group("attrs")
        attr_match = _HTML_ANCHOR_ATTR_RE.search(attrs)
        if attr_match is None:
            continue

        value = (attr_match.group(1) or attr_match.group(2) or "").strip()
        if not value:
            continue
        anchors.add(value)

    return frozenset(anchors)


def _add_heading_anchor(
    heading: str,
    *,
    anchors: set[str],
    counts: dict[str, int],
) -> None:
    base_anchor = _slugify_anchor_text(heading)
    if not base_anchor:
        return

    count = counts.get(base_anchor, 0)
    anchor = base_anchor if count == 0 else f"{base_anchor}-{count}"
    counts[base_anchor] = count + 1
    anchors.add(anchor)


def _frontmatter_end_index(lines: list[str]) -> int | None:
    if not lines:
        return None
    if lines[0].strip() != "---":
        return None

    for index in range(1, len(lines)):
        marker = lines[index].strip()
        if marker in {"---", "..."}:
            metadata_block = lines[1:index]
            has_key_value = any(
                _FRONTMATTER_KEY_VALUE_RE.match(line.strip())
                for line in metadata_block
                if line.strip()
            )
            if not has_key_value:
                return None
            return index
    return None


def _markdown_heading_anchors(text: str) -> _AnchorCatalog:
    heading_anchors: set[str] = set()
    counts: dict[str, int] = {}
    in_fenced_block = False
    lines = text.splitlines()
    frontmatter_end = _frontmatter_end_index(lines)
    explicit_anchors = _extract_explicit_html_anchors(text)

    for index, line in enumerate(lines):
        expanded_line = line.expandtabs(4)
        leading_spaces = len(expanded_line) - len(expanded_line.lstrip(" "))
        stripped = line.strip()

        if frontmatter_end is not None and index <= frontmatter_end:
            continue

        if _FENCE_DELIMITER_RE.match(line):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue

        heading_match = _MARKDOWN_HEADING_RE.match(line)
        if heading_match is not None:
            heading = _TRAILING_HEADING_HASHES_RE.sub(
                "", heading_match.group(1)
            ).strip()
            _add_heading_anchor(heading, anchors=heading_anchors, counts=counts)
            continue

        if index + 1 >= len(lines):
            continue
        if leading_spaces >= 4:
            continue
        if not stripped:
            continue
        if stripped.startswith(("#", ">", "-", "*", "+", "|", "```")):
            continue
        if _SETEXT_HEADING_UNDERLINE_RE.match(lines[index + 1]) is None:
            continue

        _add_heading_anchor(stripped, anchors=heading_anchors, counts=counts)

    return _AnchorCatalog(
        heading_anchors=frozenset(heading_anchors),
        explicit_anchors=explicit_anchors,
    )


def _normalize_anchor_reference(
    raw_reference: str,
) -> tuple[str | None, str, str | None] | None:
    reference = raw_reference.strip()
    if not reference:
        return None
    if reference.startswith(_URI_PREFIXES):
        return None
    if reference.startswith("<") and reference.endswith(">"):
        reference = reference[1:-1].strip()
    if not reference or "#" not in reference:
        return None

    path_part, fragment = reference.split("#", 1)
    if "?" in path_part:
        path_part = path_part.split("?", 1)[0]

    literal_anchor = _decode_anchor_fragment(fragment)
    if literal_anchor is None:
        return None
    normalized_anchor = _slugify_anchor_text(literal_anchor)
    if not path_part:
        return None, literal_anchor, (normalized_anchor or None)
    return path_part, literal_anchor, (normalized_anchor or None)


def _normalize_reference(*, raw_reference: str, root: Path, source: Path) -> str | None:
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
    if "YYYY-MM-DD" in reference:
        return None

    if reference in _ROOT_FILES:
        return reference
    if reference.startswith(_ROOT_PREFIXES):
        return reference
    if _is_exec_plan_stage_reference(reference=reference, root=root, source=source):
        return reference

    is_single_segment_dir = reference.endswith("/") and "/" not in reference.rstrip("/")
    if is_single_segment_dir:
        return None

    has_path_separator = "/" in reference
    if (
        has_path_separator
        and reference != "/"
        and (reference.endswith(_KNOWN_SUFFIXES) or reference.endswith("/"))
    ):
        return reference
    if not has_path_separator and reference.endswith(".md"):
        try:
            source_rel = source.relative_to(root)
        except ValueError:
            return None
        if source_rel.parts and source_rel.parts[0] == "docs":
            return reference

    return None


def _resolve_reference(*, root: Path, source: Path, reference: str) -> Path:
    if reference.startswith("/"):
        return root / reference.lstrip("/")
    if _is_exec_plan_stage_reference(reference=reference, root=root, source=source):
        return root / "docs" / "exec-plans" / reference.rstrip("/")
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
    seen: set[tuple[str, str, str, str | None]] = set()
    markdown_anchor_cache: dict[Path, _AnchorCatalog] = {}

    for source in markdown_files:
        if not source.is_file():
            continue

        text = source.read_text(encoding="utf-8")
        for raw_reference in _iter_reference_tokens(text):
            normalized = _normalize_reference(
                raw_reference=raw_reference,
                root=root,
                source=source,
            )
            if normalized is None:
                continue

            resolved = _resolve_reference(
                root=root, source=source, reference=normalized
            )
            if resolved.exists():
                continue

            path_key = (str(source), normalized, str(resolved), None)
            if path_key in seen:
                continue
            seen.add(path_key)
            missing.append(
                MissingReference(
                    source=source,
                    reference=normalized,
                    resolved=resolved,
                )
            )

        for raw_reference in _iter_markdown_link_targets(text):
            anchor_reference = _normalize_anchor_reference(raw_reference)
            if anchor_reference is None:
                continue

            raw_path, literal_anchor, slug_anchor = anchor_reference
            anchor_display = slug_anchor or literal_anchor
            if raw_path is None:
                normalized_reference = f"#{anchor_display}"
                resolved = source
            else:
                normalized_path = _normalize_reference(
                    raw_reference=raw_path,
                    root=root,
                    source=source,
                )
                if normalized_path is None:
                    continue
                resolved = _resolve_reference(
                    root=root,
                    source=source,
                    reference=normalized_path,
                )
                if not resolved.exists():
                    continue
                normalized_reference = f"{normalized_path}#{anchor_display}"

            if not resolved.is_file() or resolved.suffix != ".md":
                continue

            anchor_catalog = markdown_anchor_cache.get(resolved)
            if anchor_catalog is None:
                anchor_catalog = _markdown_heading_anchors(
                    resolved.read_text(encoding="utf-8")
                )
                markdown_anchor_cache[resolved] = anchor_catalog

            if (
                slug_anchor is not None
                and slug_anchor in anchor_catalog.heading_anchors
            ):
                continue
            if literal_anchor in anchor_catalog.explicit_anchors:
                continue

            anchor_key = (
                str(source),
                normalized_reference,
                str(resolved),
                literal_anchor,
            )
            if anchor_key in seen:
                continue
            seen.add(anchor_key)
            missing.append(
                MissingReference(
                    source=source,
                    reference=normalized_reference,
                    resolved=resolved,
                    missing_anchor=literal_anchor,
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
