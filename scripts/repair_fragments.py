"""Repair Quartz output for Obsidian block IDs and mismatched heading aliases.

The source vault and copied Markdown stay unchanged. These fixes are applied to
the built HTML so a future Obsidian sync will produce the same working links.
"""

from __future__ import annotations

import html
import posixpath
import re
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
from urllib.parse import unquote, urlsplit

from audit_anchors import ROOT, Reader


LIST_ID = re.compile(r'(<li(?: [^>]*)?>)([^<]*?)\s\^([A-Za-z0-9-]+)\s*(?=<)')
EMBED_ID = re.compile(r'</blockquote>\s+\^([A-Za-z0-9-]+)(?=<)')
HEADING = re.compile(r'<h([1-6]) id="([^"]+)"[^>]*>(.*?)</h\1>', re.DOTALL)
SELF_LINK = re.compile(r'<a role="anchor"[^>]*href="#([^"]+)"')
MALFORMED_FIRST_HEADING = re.compile(
    r'(<p>)(?=(?:(?!</p>).){0,1000}# 麻黃杏仁薏苡甘草湯\s*</p>)', re.DOTALL
)


def keep_block_ids(source: str) -> str:
    # Quartz 5.1 leaves IDs as literal text on list items with nested lists.
    source = LIST_ID.sub(
        lambda m: m.group(0) if ' id=' in m.group(1) else
        f'{m.group(1)[:-1]} id="{m.group(3)}">{m.group(2)}', source
    )
    # A transclusion followed by a block ID also needs a landing point.
    return EMBED_ID.sub(
        lambda m: f'</blockquote><span id="{m.group(1)}" class="anchor-alias"></span>', source
    )


def keep_malformed_first_heading(source: str, path: str) -> str:
    # The published copy of 叶天士用经方 currently begins with two wiki links
    # directly before "# 麻黃杏仁薏苡甘草湯" on the same line. Markdown treats it
    # as a paragraph, so give the linked section a landing point in the HTML.
    if path != "医案/叶天士医案/叶天士用经方.html":
        return source
    anchor = "麻黃杏仁薏苡甘草湯"
    if f'id="{anchor}"' in source:
        return source
    return MALFORMED_FIRST_HEADING.sub(
        f'<span class="anchor-alias" id="{anchor}"></span>\\1', source, count=1
    )


def target_page(source: str, path: str) -> str:
    if not path:
        return source
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(path)))
    if path.endswith("/"):
        target += "index.html"
    elif not Path(target).suffix:
        target += ".html"
    return target


def replacement(anchor: str, candidates: set[str], heading_aliases: dict[str, str]) -> str | None:
    # Obsidian links can contain two heading levels. Quartz currently combines
    # them into a single slug; the last level is the requested destination.
    for suffix in ("一胸痹一", "五咳喘"):
        if anchor.endswith(suffix) and suffix in candidates:
            return suffix
    if anchor == "麻黄加术汤-麻黃加朮湯" and "麻黄加术汤" in candidates:
        return "麻黄加术汤"
    if anchor == "三百合病吵所架致后又经汗" and "三百合病吵架所致后又经汗" in candidates:
        return "三百合病吵架所致后又经汗"
    if anchor in heading_aliases and heading_aliases[anchor] in candidates:
        return heading_aliases[anchor]
    close = get_close_matches(anchor, candidates, n=2, cutoff=0.8)
    if close and SequenceMatcher(None, anchor, close[0]).ratio() >= 0.95:
        return close[0]
    return None


def main() -> None:
    sources = {}
    for file in ROOT.rglob("*.html"):
        path = file.relative_to(ROOT).as_posix()
        source = keep_block_ids(file.read_text(encoding="utf-8"))
        sources[path] = keep_malformed_first_heading(source, path)
    readers: dict[str, Reader] = {}
    self_links: dict[str, dict[str, str]] = {}
    for path, source in sources.items():
        reader = Reader()
        reader.feed(source)
        readers[path] = reader
        self_links[path] = {}
        parents: dict[int, str] = {}
        for heading in HEADING.finditer(source):
            level = int(heading.group(1))
            heading_id = html.unescape(heading.group(2))
            for ancestor in list(parents):
                if ancestor >= level:
                    del parents[ancestor]
            for ancestor in sorted(parents):
                self_links[path].setdefault(parents[ancestor] + heading_id, heading_id)
            parents[level] = heading_id
            link = SELF_LINK.search(heading.group(3))
            if link and link.group(1) != heading.group(2):
                self_links[path][html.unescape(link.group(1))] = html.unescape(heading.group(2))

    inserted = 0
    for path, reader in readers.items():
        for href in reader.links:
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.fragment:
                continue
            target = target_page(path, parsed.path)
            if target not in readers:
                continue
            anchor = unquote(parsed.fragment)
            if anchor in readers[target].ids:
                continue
            correct = replacement(anchor, readers[target].ids, self_links[target])
            if not correct:
                continue
            markup = sources[target]
            marker = f'id="{html.escape(correct, quote=True)}"'
            offset = markup.find(marker)
            if offset < 0:
                continue
            start = markup.rfind("<", 0, offset)
            alias = f'<span class="anchor-alias" id="{html.escape(anchor, quote=True)}"></span>'
            sources[target] = markup[:start] + alias + markup[start:]
            readers[target].ids.add(anchor)
            inserted += 1

    changed = 0
    for path, source in sources.items():
        file = ROOT / path
        if file.read_text(encoding="utf-8") != source:
            file.write_text(source, encoding="utf-8")
            changed += 1
    print(f"Repaired fragment landing points in {changed} pages; added {inserted} heading aliases")


if __name__ == "__main__":
    main()
