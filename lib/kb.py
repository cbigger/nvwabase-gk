#!/usr/bin/env python3
"""Knowledge base: a domain reference shelf for the agent swarm.

Distinct from the fact graph. The GRAPH is live per-run working memory (facts a
run produces). The KB is static reference the workers *look things up in* —
checklists, methods, playbooks. The engine here is domain-agnostic; its
*contents* are the domain part. The base ships the KB empty; you add your own.

Storage: one JSON file per entry under ``<kb>/entries/<id>.json``:
    {"id": "...", "title": "...", "tags": ["..."], "body": "..."}

Search is dependency-free keyword overlap (title and tags weighted over body),
good enough to surface the few entries a worker should read before improvising.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


class KBError(Exception):
    pass


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _slug(text: str) -> str:
    s = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return s or "entry"


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


class KB:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.entries_dir = self.root / "entries"

    # -- persistence ---------------------------------------------------------
    def _path(self, entry_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", entry_id or ""):
            raise KBError(f"invalid entry id '{entry_id}'")
        return self.entries_dir / f"{entry_id}.json"

    def list(self) -> list[dict]:
        if not self.entries_dir.exists():
            return []
        out = []
        for p in sorted(self.entries_dir.glob("*.json")):
            try:
                out.append(self._load(p))
            except KBError:
                continue  # a damaged entry must not break the whole shelf
        return out

    def _load(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise KBError(f"cannot read KB entry {path.name}: {exc}")
        if not isinstance(data, dict) or not isinstance(data.get("title"), str):
            raise KBError(f"invalid KB entry {path.name}: needs a string 'title'")
        data.setdefault("id", path.stem)
        data.setdefault("tags", [])
        data.setdefault("body", "")
        if not isinstance(data["tags"], list):
            raise KBError(f"invalid KB entry {path.name}: 'tags' must be a list")
        return data

    def get(self, entry_id: str) -> dict:
        p = self._path(entry_id)
        if not p.exists():
            raise KBError(f"no KB entry '{entry_id}'")
        return self._load(p)

    def add(self, title: str, body: str = "", tags: list[str] | None = None,
            entry_id: str | None = None, overwrite: bool = False) -> dict:
        if not isinstance(title, str) or not title.strip():
            raise KBError("entry title cannot be empty")
        tags = tags or []
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise KBError("tags must be a list of strings")
        entry_id = entry_id or _slug(title)
        p = self._path(entry_id)
        if p.exists() and not overwrite:
            raise KBError(f"KB entry '{entry_id}' already exists (use overwrite)")
        entry = {"id": entry_id, "title": title.strip(),
                 "tags": [t.strip() for t in tags if t.strip()], "body": body}
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
        return entry

    # -- search --------------------------------------------------------------
    def search(self, query: str, limit: int = 5) -> list[dict]:
        q = _tokens(query)
        if not q:
            return []
        scored = []
        for entry in self.list():
            title_t = _tokens(entry["title"])
            tag_t = _tokens(" ".join(entry.get("tags", [])))
            body_t = _tokens(entry.get("body", ""))
            score = 3 * len(q & title_t) + 2 * len(q & tag_t) + len(q & body_t)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda s: (-s[0], s[1]["id"]))
        return [{"score": sc, **e} for sc, e in scored[:max(1, limit)]]


def resolve_kb_root(explicit: str | None = None) -> Path:
    """Pick the KB root: --kb/arg, else FG_KB env, else the repo's kb/."""
    if explicit:
        return Path(explicit)
    env = os.environ.get("FG_KB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "kb"
