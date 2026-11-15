# 邓珍本金匮要略全释阅读站

本项目使用 [Quartz 5](https://quartz.jzhao.xyz/) 把本地 Obsidian 笔记生成只读网页。

## 内容范围

- 以 `注解金匱要略/邓珍本金匮要略全释` 下第 1–9 章为入口。
- `scripts/sync_vault.py` 逐层追踪这些章节的 Obsidian 双链和 Markdown 链接，仅复制能到达的笔记、附件，不修改原始 Obsidian 库。
- 当前选择结果见 `scripts/published-files.json`；运行脚本后，`sync-report.json` 记录所选文件和无法解析的链接。报告含本机绝对路径，不提交到 GitHub。
- 首页以第 1–9 章为入口；左侧目录把已选中的关联笔记分为医案、金匮注解与原文、经典引文。目录不会引入筛选范围外的文件。
- Obsidian 的标题链接、块引用链接会定位到对应小节或段落并加框；右侧反向链接会带到原文引用位置，可切换多处引用并返回上一页。

**发布前请检查所选文件**，因为沿链接追踪可能把新增加的私有笔记纳入公开网站。公开的 GitHub 仓库和 Pages 站点没有访问密码。

## 本地预览

需要 Node.js 22+、npm 10.9.2+ 和 Python 3。首次运行：

```powershell
npm ci
node quartz/bootstrap-cli.mjs plugin install --from-config
./scripts/发布更新.ps1 -PreviewOnly
python scripts/preview.py
```

打开 `http://127.0.0.1:8080/jingui-notes/`。

## GitHub Pages

仓库地址：[TCMzhoutong/jingui-notes](https://github.com/TCMzhoutong/jingui-notes)。部署地址：[网页阅读站](https://TCMzhoutong.github.io/jingui-notes/)。

在仓库的 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。每次推送 `main` 分支，`.github/workflows/deploy.yml` 会重新构建并部署网页。

GitHub Actions 会生成并部署网页。访客只能阅读和使用链接、搜索、悬停预览，无法在网页修改源笔记。

## 日常更新

在 Obsidian 中正常修改本地笔记后运行：

```powershell
./scripts/发布更新.ps1
```

脚本会重新追踪链接、复制本次所需内容、构建验证、提交并推送。每次运行前应查看 `sync-report.json` 与 `scripts/published-files.json`，确认新增的公开内容。推送后 GitHub Pages 会自动更新。若只想本地预览，加 `-PreviewOnly`。

构建还会执行 `scripts/repair_fragments.py` 和 `scripts/audit_anchors.py`。后者会检查所有指向小节或段落的内部链接，发现无法定位的链接即中止发布，避免默默跳到文件开头。
