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


def test_repository_docs_cross_references_are_fresh() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    missing = find_missing_references(repo_root)
    assert not missing
