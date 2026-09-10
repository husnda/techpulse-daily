# ==============================================================================
# TechPulse Daily - 自动化集成测试脚本 (PowerShell 7)
# ==============================================================================
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

# 获取 Python 路径
$Python = if (Test-Path "$env:USERPROFILE\miniforge3\python.exe") { "$env:USERPROFILE\miniforge3\python.exe" } else { "python" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "开始运行 TechPulse 完整集成测试..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 语法编译检查
Write-Host "[1/3] 正在检查 Python 模块语法完整性..." -ForegroundColor Yellow
& $Python -m py_compile main.py core/config.py core/fetcher_github.py core/fetcher_hackernews.py core/data_processor.py core/rss_generator.py core/notifiers.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 模块语法编译失败！"
    exit 1
}
Write-Host "语法检查通过！" -ForegroundColor Green

# 2. 模拟运行管道
Write-Host "[2/3] 正在执行全量抓取与生成测试 (--dry-run)..." -ForegroundColor Yellow
& $Python main.py --dry-run
if ($LASTEXITCODE -ne 0) {
    Write-Error "聚合管道执行失败！"
    exit 1
}
Write-Host "管道执行成功！" -ForegroundColor Green

# 3. 校验产物文件是否存在且大小正常
Write-Host "[3/3] 验证产物文件完整性..." -ForegroundColor Yellow
$RequiredFiles = @(
    "outputs\feed.xml",
    "outputs\rss.xml",
    "outputs\index.html",
    "outputs\latest_digest.md"
)

foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Error "缺少预期生成文件: $file"
        exit 1
    }
    $size = (Get-Item $file).Length
    if ($size -lt 100) {
        Write-Error "生成的文件内容过小 ($size bytes): $file"
        exit 1
    }
    Write-Host "  OK -> $file ($size bytes)" -ForegroundColor Green
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "所有测试全部通过！系统处于就绪状态。" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
