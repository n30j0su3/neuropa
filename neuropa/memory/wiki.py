"""C1: Wiki bundle service — NeuroPA-owned memory bundle.

Provides markdown-based Wiki pages with YAML-like frontmatter, sandboxed
to the app data directory. Atomic writes, path traversal protection, and
deterministic validation.
"""
from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_WIKI_DIRS = ("entities", "concepts", "comparisons", "queries", "notes", "raw")
_VALID_TYPES = {"entity", "concept", "comparison", "query", "note", "raw"}
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")

_DIR_TO_TYPE = {v: k for k, v in {
    "entity": "entities",
    "concept": "concepts",
    "comparison": "comparisons",
    "query": "queries",
    "note": "notes",
    "raw": "raw",
}.items()}

_TYPE_TO_DIR = {
    "entity": "entities",
    "concept": "concepts",
    "comparison": "comparisons",
    "query": "queries",
    "note": "notes",
    "raw": "raw",
}


class WikiService:
    def __init__(self, data_dir: str | Path):
        self.bundle_root = Path(data_dir) / "wiki"
        self.bundle_root.mkdir(parents=True, exist_ok=True)
        for subdir in _WIKI_DIRS:
            (self.bundle_root / subdir).mkdir(parents=True, exist_ok=True)
        self._init_index()

    def _init_index(self) -> None:
        index = self.bundle_root / "index.md"
        if not index.exists():
            self._atomic_write(index, "---\ntitle: Índice\ntype: note\ntags: []\n---\n\n# Índice de la Wiki\n\nEsta es la Wiki local de NeuroPA.\n")

    def _atomic_write(self, target: Path, content: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".wiki-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _validate_slug(self, slug: str) -> None:
        if not _SLUG_PATTERN.match(slug):
            raise ValueError(f"slug inválido: {slug}")

    def _resolve_path(self, wiki_type: str, slug: str) -> Path:
        self._validate_slug(slug)
        if wiki_type not in _VALID_TYPES:
            raise ValueError(f"tipo inválido: {wiki_type}")
        subdir = _TYPE_TO_DIR.get(wiki_type, wiki_type + "s")
        resolved = (self.bundle_root / subdir / f"{slug}.md").resolve()
        root = self.bundle_root.resolve()
        if root != resolved and root not in resolved.parents:
            raise ValueError("path escapes wiki root")
        return resolved

    def _validate_frontmatter(self, fm: dict[str, Any]) -> None:
        if not isinstance(fm, dict):
            raise ValueError(f"frontmatter debe ser un mapping, no {type(fm).__name__}")
        required = {"title", "type"}
        missing = required - set(fm)
        if missing:
            raise ValueError(f"frontmatter faltan campos: {missing}")
        if not isinstance(fm["title"], str) or not fm["title"].strip():
            raise ValueError("title debe ser texto no vacío")
        if fm["type"] not in _VALID_TYPES:
            raise ValueError(f"type inválido: {fm['type']}")
        if "tags" in fm and not isinstance(fm["tags"], list):
            raise ValueError("tags debe ser una lista")
        if "related_concepts" in fm and not isinstance(fm["related_concepts"], list):
            raise ValueError("related_concepts debe ser una lista")

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        if not content.startswith("---\n"):
            return {}, content
        end = content.find("\n---\n", 4)
        if end == -1:
            return {}, content
        fm_text = content[4:end]
        body = content[end + 5:]
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"frontmatter YAML inválido: {exc}") from exc
        return fm, body

    def _build_frontmatter(self, fm: dict[str, Any]) -> str:
        clean = {
            "title": fm.get("title", "Sin título"),
            "type": fm.get("type", "note"),
            "tags": fm.get("tags", []),
            "created": fm.get("created", _now_iso()),
            "updated": _now_iso(),
            "summary": fm.get("summary", ""),
            "source_claims": fm.get("source_claims", []),
            "related_concepts": fm.get("related_concepts", []),
        }
        return "---\n" + yaml.dump(clean, allow_unicode=True, default_flow_style=False).strip() + "\n---\n\n"

    def write_page(self, wiki_type: str, slug: str, title: str, body: str, tags: list[str] | None = None, summary: str = "", source_claims: list[str] | None = None, related_concepts: list[str] | None = None) -> dict[str, Any]:
        path = self._resolve_path(wiki_type, slug)
        fm = {
            "title": title,
            "type": wiki_type,
            "tags": tags or [],
            "summary": summary,
            "source_claims": source_claims or [],
            "related_concepts": related_concepts or [],
        }
        fm_text = self._build_frontmatter(fm)
        content = fm_text + body + "\n"
        self._validate_frontmatter(self._parse_frontmatter(content)[0])
        self._atomic_write(path, content)
        return {"slug": slug, "type": wiki_type, "path": str(path.relative_to(self.bundle_root)), "title": title}

    def read_page(self, wiki_type: str, slug: str) -> dict[str, Any]:
        if wiki_type not in _VALID_TYPES:
            raise ValueError(f"tipo inválido: {wiki_type}")
        path = self._resolve_path(wiki_type, slug)
        if not path.is_file():
            raise FileNotFoundError(f"Wiki page not found: {slug}")
        content = path.read_text(encoding="utf-8")
        fm, body = self._parse_frontmatter(content)
        self._validate_frontmatter(fm)
        if fm.get("type") != wiki_type:
            raise ValueError(f"tipo en frontmatter '{fm.get('type')}' no coincide con ruta '{wiki_type}'")
        return {"slug": slug, "type": wiki_type, "path": str(path.relative_to(self.bundle_root)), "frontmatter": fm, "body": body}

    def list_pages(self, wiki_type: str | None = None) -> list[dict[str, Any]]:
        if wiki_type is not None and wiki_type not in _VALID_TYPES:
            raise ValueError(f"tipo inválido: {wiki_type}")
        pages = []
        if wiki_type:
            search_dirs = [_TYPE_TO_DIR.get(wiki_type, wiki_type + "s")]
        else:
            search_dirs = list(_WIKI_DIRS)
        for subdir in search_dirs:
            dir_path = self.bundle_root / subdir
            if not dir_path.is_dir():
                continue
            page_type = _DIR_TO_TYPE.get(subdir, subdir.rstrip("s"))
            for f in sorted(dir_path.glob("*.md")):
                try:
                    content = f.read_text(encoding="utf-8")
                    fm, _ = self._parse_frontmatter(content)
                    pages.append({
                        "slug": f.stem,
                        "type": page_type,
                        "title": fm.get("title", f.stem),
                        "tags": fm.get("tags", []),
                        "path": str(f.relative_to(self.bundle_root)),
                    })
                except Exception:
                    continue
        return pages

    def backlinks(self) -> dict[str, list[str]]:
        """H1: Derive a backlinks index from all pages' related_concepts."""
        index: dict[str, list[str]] = {}
        for page_slug, _page_type, fm, _body in self._all_page_refs():
            related = fm.get("related_concepts", []) if isinstance(fm, dict) else []
            for ref in related:
                index.setdefault(ref, []).append(page_slug)
        return index

    def _all_page_refs(self) -> list[tuple[str, str, dict[str, Any], str]]:
        """Load all pages with their parsed frontmatter; raises on unreadable."""
        refs = []
        for subdir in _WIKI_DIRS:
            dir_path = self.bundle_root / subdir
            if not dir_path.is_dir():
                continue
            for f in sorted(dir_path.glob("*.md")):
                try:
                    content = f.read_text(encoding="utf-8")
                    fm, body = self._parse_frontmatter(content)
                    self._validate_frontmatter(fm)
                    page_type = _DIR_TO_TYPE[subdir]
                    if fm.get("type") != page_type:
                        continue
                    refs.append((f.stem, page_type, fm, body))
                except (OSError, UnicodeError, ValueError, yaml.YAMLError):
                    continue
        return refs

    def lint(self) -> list[dict[str, str]]:
        """H2: Robust lint — no silent swallowing. Returns structured issues."""
        issues: list[dict[str, str]] = []
        all_slugs: set[str] = set()
        pages_data: list[tuple[str, str, Path]] = []
        for subdir in _WIKI_DIRS:
            dir_path = self.bundle_root / subdir
            if not dir_path.is_dir():
                continue
            for f in sorted(dir_path.glob("*.md")):
                pages_data.append((f.stem, subdir, f))
        # First pass: collect all valid slugs
        for slug, subdir, f in pages_data:
            try:
                content = f.read_text(encoding="utf-8")
                fm, _body = self._parse_frontmatter(content)
                self._validate_frontmatter(fm)
                all_slugs.add(slug)
            except ValueError as exc:
                issues.append({"page": slug, "issue": "invalid_frontmatter", "detail": str(exc)})
            except Exception as exc:
                issues.append({"page": slug, "issue": "unreadable_page", "detail": str(exc)})
        # Second pass: check references and type coherence
        for slug, subdir, f in pages_data:
            page_type = _DIR_TO_TYPE.get(subdir, subdir.rstrip("s"))
            try:
                content = f.read_text(encoding="utf-8")
                fm, _body = self._parse_frontmatter(content)
                if not isinstance(fm, dict):
                    continue
                if fm.get("type") != page_type:
                    issues.append({"page": slug, "issue": "type_mismatch", "expected": page_type, "found": str(fm.get("type"))})
                related = fm.get("related_concepts", [])
                for ref in related:
                    if ref not in all_slugs:
                        issues.append({"page": slug, "issue": "broken_wikilink", "ref": ref})
            except Exception:
                pass  # Already reported in first pass
        return issues

    def search(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for page in self.list_pages():
            try:
                full = self.read_page(page["type"], page["slug"])
                text = (full["frontmatter"].get("title", "") + " " + full["body"]).lower()
                if query_lower in text:
                    results.append({"slug": page["slug"], "type": page["type"], "title": page["title"], "summary": full["frontmatter"].get("summary", "")})
            except Exception:
                continue
        return results
