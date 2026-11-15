"""Check that every generated internal fragment points to an HTML element."""

from __future__ import annotations

import posixpath
from difflib import get_close_matches
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1] / "public"


class Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        props = dict(attrs)
        if props.get("id"):
            self.ids.add(props["id"] or "")
        if tag == "a" and "internal" in (props.get("class") or "").split():
            if props.get("href"):
                self.links.append(props["href"] or "")


def main() -> None:
    pages: dict[str, Reader] = {}
    for file in ROOT.rglob("*.html"):
        relative = file.relative_to(ROOT).as_posix()
        reader = Reader()
        reader.feed(file.read_text(encoding="utf-8"))
        pages[relative] = reader

    missing: list[str] = []
    checked = 0
    for source, reader in pages.items():
        for href in reader.links:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.fragment:
                continue
            checked += 1
            target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))
            if parsed.path:
                if parsed.path.endswith("/"):
                    target += "index.html"
                elif not Path(target).suffix:
                    target += ".html"
            else:
                target = source
            anchor = unquote(parsed.fragment)
            if target not in pages or anchor not in pages[target].ids:
                suggestions = get_close_matches(anchor, pages[target].ids, n=3, cutoff=0.25) if target in pages else []
                missing.append(f"{source}: {href} -> {target}#{anchor}; nearest: {suggestions}")

    print(f"Checked {checked} fragment links in {len(pages)} HTML pages; {len(missing)} missing targets")
    for item in missing[:30]:
        print(item)
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
