"""Report local vault edits and pending changes to the public reading site.

This watcher only reads the Obsidian vault. It never copies notes or publishes them.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from sync_vault import DEFAULT_VAULT, file_list, key


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "sync-report.json"


def snapshot(vault: Path) -> dict[str, tuple[int, int]]:
    result = {}
    for relative in file_list(vault):
        stat = (vault / relative).stat()
        result[relative.as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return result


def pending(vault: Path) -> None:
    process = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_vault.py"),
         "--vault", str(vault), "--dry-run", "--report", str(REPORT)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
    )
    if process.returncode:
        print(f"发布范围检查失败：{process.stderr.strip() or process.stdout.strip()}", flush=True)
        return
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    changes = report["changes"]
    print(
        f"待发布：新增 {len(changes['new'])}、修改 {len(changes['modified'])}、"
        f"移出 {len(changes['removed'])}；无法解析的链接 {report['unresolved_count']}。",
        flush=True,
    )
    for label, field in (("新增", "new"), ("修改", "modified"), ("移出", "removed")):
        for name in changes[field]:
            print(f"  {label}：{name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--interval", type=float, default=2.0, help="检查间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只检查当前待发布变化")
    args = parser.parse_args()
    vault = args.vault.resolve()
    if not vault.is_dir():
        parser.error(f"Obsidian 库不存在：{vault}")
    if args.interval <= 0:
        parser.error("检查间隔必须大于 0")

    before = snapshot(vault)
    print(f"正在监测 {vault}（{len(before)} 个文件）。", flush=True)
    pending(vault)
    if args.once:
        return
    print("保存笔记后会显示变化；按 Ctrl+C 停止。不会自动上传。", flush=True)
    try:
        while True:
            time.sleep(args.interval)
            after = snapshot(vault)
            if after == before:
                continue
            # Obsidian and OneDrive may write a file more than once per save.
            time.sleep(0.7)
            after = snapshot(vault)
            old_names, new_names = set(before), set(after)
            added = sorted(new_names - old_names, key=key)
            modified = sorted((p for p in old_names & new_names if before[p] != after[p]), key=key)
            removed = sorted(old_names - new_names, key=key)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 本地文件变化：", flush=True)
            for label, names in (("新增", added), ("修改", modified), ("删除", removed)):
                for name in names:
                    print(f"  {label}：{name}", flush=True)
            before = after
            pending(vault)
    except KeyboardInterrupt:
        print("\n已停止监测。", flush=True)


if __name__ == "__main__":
    main()
