from __future__ import annotations

from pathlib import Path

from cutkit.docs_freshness import find_missing_references


def test_docs_freshness_detects_missing_reference(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See `docs/missing.md` and [root](../README.md).\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# temp\n", encoding="utf-8")

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "docs/missing.md"


def test_docs_freshness_detects_missing_reference_in_fenced_block(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        """
```bash
uv run python scripts/missing_check.py
```
""".strip()
        + "\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "scripts/missing_check.py"


def test_docs_freshness_scans_openspec_markdown_by_default(tmp_path: Path) -> None:
    openspec_dir = tmp_path / "openspec"
    openspec_dir.mkdir(parents=True, exist_ok=True)

    source = openspec_dir / "README.md"
    source.write_text(
        "Run `scripts/missing_from_openspec.py`.\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path)
    assert len(missing) == 1
    assert missing[0].source == source
    assert missing[0].reference == "scripts/missing_from_openspec.py"


def test_docs_freshness_scans_skill_docs_by_default(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".codex" / "skills" / "example"
    skill_dir.mkdir(parents=True, exist_ok=True)

    source = skill_dir / "SKILL.md"
    source.write_text(
        "Refer to `scripts/missing_from_skill.py`.\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path)
    assert len(missing) == 1
    assert missing[0].source == source
    assert missing[0].reference == "scripts/missing_from_skill.py"


def test_docs_freshness_excludes_node_modules_markdown(tmp_path: Path) -> None:
    vendor_dir = tmp_path / ".opencode" / "node_modules" / "pkg"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    source = vendor_dir / "README.md"
    source.write_text("See `scripts/missing_from_vendor.py`.\n", encoding="utf-8")

    missing = find_missing_references(tmp_path)
    assert not missing


def test_docs_freshness_detects_missing_single_segment_directory_reference(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs" / "exec-plans"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "plan.md"
    source.write_text("See `active/`.\n", encoding="utf-8")

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "active/"


def test_docs_freshness_ignores_conceptual_single_segment_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "ARCHITECTURE.md"
    source.write_text(
        "Layer names: `geometry/`, `topology/`, `clipping/`.\n", encoding="utf-8"
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_detects_missing_in_file_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "# Intro\n\nSee [details](#missing-section).\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "#missing-section"
    assert missing[0].resolved == source
    assert missing[0].missing_anchor == "missing-section"


def test_docs_freshness_allows_existing_in_file_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "# Intro\n\nSee [details](#intro).\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_detects_missing_cross_file_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [details](guide.md#missing-anchor).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text("# Guide\n", encoding="utf-8")

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#missing-anchor"
    assert missing[0].resolved == docs_dir / "guide.md"
    assert missing[0].missing_anchor == "missing-anchor"


def test_docs_freshness_allows_existing_cross_file_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [details](guide.md#guide-details).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text("# Guide Details\n", encoding="utf-8")

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_duplicate_heading_anchor_suffixes(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [second](guide.md#overview-1).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "# Overview\n\n## Overview\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_setext_heading_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [setext](guide.md#setext-title).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "Setext Title\n------------\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_ignores_indented_setext_like_code(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [bad anchor](guide.md#not-a-heading).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "    not a heading\n---\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#not-a-heading"


def test_docs_freshness_ignores_tab_indented_setext_like_code(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [bad anchor](guide.md#not-a-heading).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "\tnot a heading\n---\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#not-a-heading"


def test_docs_freshness_allows_explicit_html_anchor_id(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [anchor](guide.md#custom-target).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        '<a id="custom-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_explicit_html_anchor_name(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [anchor](guide.md#legacy-anchor).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        '<a name="legacy-anchor"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_treats_explicit_html_anchor_as_literal(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#foo-bar).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text('<a id="Foo Bar"></a>\n', encoding="utf-8")

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#foo-bar"


def test_docs_freshness_allows_multiline_explicit_html_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '<a\n  id="custom-target"\n></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_multiline_anchor_with_indented_attr(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '<a\n    id="custom-target"\n></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_list_indented_html_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#list-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '- Item\n    <a id="list-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_ignores_list_item_code_block_anchor_sample(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#list-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '- Item\n        <a id="list-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#list-target"


def test_docs_freshness_ignores_inline_html_anchor_samples(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        'Use `<a id="custom-target"></a>` as an example.\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_ignores_data_id_anchor_like_attributes(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '<a data-id="custom-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_ignores_indented_html_anchor_code_samples(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '    <a id="custom-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_recognizes_id_and_name_on_same_anchor(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [new](guide.md#new) and [legacy](guide.md#legacy).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        '<a id="new" name="legacy"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_unquoted_explicit_anchor_attributes(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text(
        "See [id](guide.md#custom-target) and [name](guide.md#legacy).\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "<a id=custom-target name=legacy></a>\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_ignores_tilde_fenced_html_anchor_samples(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '~~~html\n<a id="custom-target"></a>\n~~~\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_ignores_mismatched_fence_delimiter_inside_code(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#fake).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "```\ncode\n~~~\n# fake\n```\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#fake"


def test_docs_freshness_ignores_anchor_after_malformed_fence_closer(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '```html\ncode\n``` not-close\n<a id="custom-target"></a>\n```\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_ignores_setext_heading_inside_html_comment(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#not-a-heading).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "<!--\nnot a heading\n---\n-->\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#not-a-heading"


def test_docs_freshness_ignores_name_substring_inside_other_attribute_value(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#custom-target).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        '<a title="x name=custom-target"></a>\n',
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#custom-target"


def test_docs_freshness_ignores_ordered_list_setext_like_sequence(
    tmp_path: Path,
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#1-not-a-heading).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "1. not a heading\n---\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert len(missing) == 1
    assert missing[0].reference == "guide.md#1-not-a-heading"


def test_docs_freshness_allows_heading_after_thematic_break(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#real-heading).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "---\n# Real Heading\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_allows_frontmatter_closed_with_ellipsis(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#real-heading).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "---\ntitle: Sample\n...\n# Real Heading\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_docs_freshness_ignores_thematic_break_as_frontmatter(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    source = docs_dir / "index.md"
    source.write_text("See [anchor](guide.md#real-heading).\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "---\n# Real Heading\n---\n",
        encoding="utf-8",
    )

    missing = find_missing_references(tmp_path, markdown_files=(source,))
    assert not missing


def test_repository_docs_cross_references_are_fresh() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    missing = find_missing_references(repo_root)
    assert not missing
