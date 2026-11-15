param(
    [string]$Vault = 'C:\Users\TCMzh\OneDrive\文档\obsidian中医经典',
    [switch]$PreviewOnly
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repo

python scripts/sync_vault.py --vault $Vault
if ($LASTEXITCODE -ne 0) { throw '笔记筛选失败。' }

node quartz/bootstrap-cli.mjs build
if ($LASTEXITCODE -ne 0) { throw '网页构建失败。' }
python scripts/fix_tag_links.py
if ($LASTEXITCODE -ne 0) { throw '标签链接修复失败。' }
python scripts/repair_fragments.py
if ($LASTEXITCODE -ne 0) { throw '段落链接修复失败。' }
python scripts/audit_anchors.py
if ($LASTEXITCODE -ne 0) { throw '有段落链接未能定位，请检查输出。' }

if ($PreviewOnly) {
    Write-Host '本地网页已生成在 public 目录。运行 python scripts/preview.py 预览。'
    exit 0
}

if (-not (git remote get-url origin 2>$null)) {
    throw '尚未设置 GitHub 仓库 origin。请先完成首次发布配置。'
}

git add content scripts/published-files.json
if (git diff --cached --quiet) {
    Write-Host '网页内容与上次发布相同。'
    exit 0
}

git commit -m "更新金匮要略笔记"
if ($LASTEXITCODE -ne 0) { throw 'Git 提交失败。' }
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'GitHub 推送失败。请检查登录状态和网络。' }
Write-Host '更新已推送；GitHub Pages 将自动重新构建。'
