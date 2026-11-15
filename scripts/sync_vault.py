"""Publish the outgoing-link closure of chapters 1–9 from the local Obsidian vault.

The source vault is read-only. Only files selected by the link graph are copied into
Quartz's content directory. Run this again after editing notes in Obsidian.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import unicodedata
from collections import Counter, deque
from pathlib import Path
from urllib.parse import unquote


DEFAULT_VAULT = Path(r"C:\Users\TCMzh\OneDrive\文档\obsidian中医经典")
MAIN_DIR = Path("注解金匱要略/邓珍本金匮要略全释")
WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)")


def key(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\\", "/")).casefold()


def file_list(vault: Path) -> list[Path]:
    return sorted(
        (p.relative_to(vault) for p in vault.rglob("*")
         if p.is_file() and ".obsidian" not in p.relative_to(vault).parts),
        key=lambda p: key(p.as_posix()),
    )


def references(text: str):
    for match in WIKILINK.finditer(text):
        yield match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
    for match in MARKDOWN_LINK.finditer(text):
        raw = match.group(1).strip().strip("<>").split(None, 1)[0]
        yield unquote(raw.split("#", 1)[0])


class Resolver:
    def __init__(self, paths: list[Path]):
        self.paths = paths
        self.by_path = {key(p.as_posix()): p for p in paths}
        self.by_name: dict[str, list[Path]] = {}
        for path in paths:
            self.by_name.setdefault(key(path.name), []).append(path)

    def resolve(self, raw: str, source: Path) -> tuple[Path | None, str | None]:
        raw = unquote(raw.strip().replace("\\", "/"))
        if not raw or re.match(r"^[a-z][a-z\d+.-]*:", raw, re.I) or raw.startswith("//"):
            return None, None
        raw = raw.lstrip("/")
        name = Path(raw).name
        variants = [raw] if Path(raw).suffix else [raw + ".md", raw]
        for variant in variants:
            for candidate in (source.parent / variant, Path(variant)):
                normalized = key(candidate.as_posix())
                if normalized in self.by_path:
                    return self.by_path[normalized], None

        candidates: list[Path] = []
        for variant in variants:
            candidates.extend(self.by_name.get(key(Path(variant).name), []))
        if "/" in raw:
            candidates = [p for p in candidates if any(
                key(p.as_posix()).endswith("/" + key(v)) for v in variants
            )]
        candidates = list(dict.fromkeys(candidates))
        if len(candidates) == 1:
            return candidates[0], None
        if not candidates:
            return None, "missing"

        def distance(p: Path) -> tuple[int, int]:
            a, b = source.parent.parts, p.parent.parts
            common = 0
            for x, y in zip(a, b):
                if key(x) != key(y):
                    break
                common += 1
            return (-common, len(a) + len(b) - 2 * common)

        ranked = sorted(candidates, key=distance)
        if len(ranked) == 1 or distance(ranked[0]) < distance(ranked[1]):
            return ranked[0], None
        return None, "ambiguous"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "content")
    parser.add_argument("--report", type=Path, default=Path(__file__).resolve().parents[1] / "sync-report.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    vault = args.vault.resolve()
    if not vault.is_dir():
        parser.error(f"Vault does not exist: {vault}")

    paths = file_list(vault)
    resolver = Resolver(paths)
    seeds = []
    for number in range(1, 10):
        matches = [p for p in paths if p.parent == MAIN_DIR and re.match(rf"^{number} ", p.name)]
        if len(matches) != 1:
            parser.error(f"Expected exactly one chapter {number} in {MAIN_DIR}, found {len(matches)}")
        seeds.extend(matches)

    queue = deque(seeds)
    selected: set[Path] = set()
    unresolved: list[dict[str, str]] = []
    while queue:
        path = queue.popleft()
        if path in selected:
            continue
        selected.add(path)
        if path.suffix.lower() != ".md":
            continue
        for ref in references((vault / path).read_text(encoding="utf-8-sig")):
            target, problem = resolver.resolve(ref, path)
            if target and target not in selected:
                queue.append(target)
            elif problem:
                unresolved.append({"source": path.as_posix(), "link": ref, "reason": problem})

    selected_sorted = sorted(selected, key=lambda p: key(p.as_posix()))
    report = {
        "source_vault": str(vault),
        "seed_chapters": [p.as_posix() for p in seeds],
        "selected_count": len(selected_sorted),
        "selected_by_extension": dict(Counter(p.suffix.lower() for p in selected_sorted)),
        "selected_files": [p.as_posix() for p in selected_sorted],
        "unresolved_count": len(unresolved),
        "unresolved_links": unresolved,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selected {len(selected_sorted)} files from {len(paths)} vault files; {len(unresolved)} unresolved links")
    if args.dry_run:
        return

    out = args.out.resolve()
    if out == vault or vault in out.parents:
        parser.error("Output must not be inside the source vault")
    previous_manifest = Path(__file__).resolve().parent / "published-files.json"
    if previous_manifest.exists():
        for relative in json.loads(previous_manifest.read_text(encoding="utf-8")):
            old = out / relative
            if old.is_file():
                old.unlink()
    for path in selected_sorted:
        destination = out / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vault / path, destination)

    title = "邓珍本金匮要略全释"
    index = ["---", f"title: {title}", "---", "", '<div class="reading-home">',
             '<p class="reading-home-kicker">金匮要略 · 前九篇</p>',
             '<p class="reading-home-lead">以邓珍本为主线，循原文、注解与医案逐层阅读。</p>',
             '<p class="reading-home-help">选择篇章开始。左侧目录还可浏览这些篇章涉及的医案、金匮注解与经典引文。</p>',
             '<div class="chapter-grid">']
    for number, path in enumerate(seeds, 1):
        url = html.escape(path.with_suffix('').as_posix(), quote=True)
        label = html.escape(path.stem[2:])
        index.append(f'<a class="chapter-card" href="{url}"><span class="chapter-number">{number:02}</span><span class="chapter-name">{label}</span><span class="chapter-arrow">↗</span></a>')
    index.extend(['</div>', '</div>', ''])
    (out / "index.md").write_text("\n".join(index), encoding="utf-8")
    previous_manifest.write_text(json.dumps([p.as_posix() for p in selected_sorted], ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
