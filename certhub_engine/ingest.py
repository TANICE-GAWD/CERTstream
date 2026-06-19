"""Parse a Technical Documentation bundle into structured sections.

Accepts a single markdown/txt file or a directory of them. Sections are split
on markdown headings (``
installed; otherwise PDFs are skipped with a warning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_HEADING_RE = re.compile(r"^(


@dataclass
class Section:
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


def _split_markdown(raw: str, fallback_title: str) -> list[Section]:
    sections: list[Section] = []
    cur_title = fallback_title
    cur_body: list[str] = []

    def flush():
        body = "\n".join(cur_body).strip()
        if cur_title.strip() or body:
            sections.append(Section(title=cur_title.strip(), body=body))

    for line in raw.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            flush()
            cur_title = m.group(2)
            cur_body = []
        else:
            cur_body.append(line)
    flush()
    
    return [s for s in sections if s.body or s.title]


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  
            print(f"[ingest] skipping {path.name}: cannot read PDF ({exc})")
            return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_techdoc(path: str | Path) -> list[Section]:
    """Return the list of sections for a file or a directory of files."""
    p = Path(path)
    files: list[Path]
    if p.is_dir():
        files = sorted(
            f for f in p.iterdir()
            if f.suffix.lower() in (".md", ".txt", ".pdf")
        )
    else:
        files = [p]

    sections: list[Section] = []
    for f in files:
        raw = _read_file(f)
        if raw.strip():
            sections.extend(_split_markdown(raw, fallback_title=f.stem))
    return sections
