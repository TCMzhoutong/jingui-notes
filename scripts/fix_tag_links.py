"""Normalize Quartz 5.1 tag links in nested pages after a site build.

The current Obsidian plugin sometimes adds an extra ../ to tag URLs. This
small output-only repair keeps links valid on GitHub Pages subpaths too.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1] / "public"
HREF = re.compile(r'href="([^"]+)"')


def fix(page: Path) -> int:
    source = page.read_text(encoding="utf-8")
    depth = len(page.relative_to(ROOT).parts) - 1
    prefix = "../" * depth if depth else "./"
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        href = match.group(1)
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or "tags/" not in parsed.path:
            return match.group(0)
        tail = parsed.path.split("tags/", 1)[1]
        correct = f"{prefix}tags/{tail}"
        if parsed.query:
            correct += "?" + parsed.query
        if parsed.fragment:
            correct += "#" + parsed.fragment
        if correct != href:
            count += 1
        return f'href="{correct}"'

    result = HREF.sub(replace, source)
    if count:
        page.write_text(result, encoding="utf-8")
    return count


if __name__ == "__main__":
    total = sum(fix(page) for page in ROOT.rglob("*.html"))
    print(f"Normalized {total} tag links")
