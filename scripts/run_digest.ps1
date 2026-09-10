# ==============================================================================
# TechPulse Daily - 运行早报聚合脚本 (PowerShell 7)
# ==============================================================================
$ErrorActionPreference = "Stop"

# 获取脚本所在根目录
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

# 寻找可用的 Python 解释器
$PythonPath = $null
if (Test-Path "$ProjectRoot\.venv\Scripts\python.exe") {
    $PythonPath = "$ProjectRoot\.venv\Scripts\python.exe"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonPath = (Get-Command "python").Source
    if ($PythonPath -like "*WindowsApps*") {
        # 规避 WindowsApps 替身
        if (Test-Path "$env:USERPROFILE\miniforge3\python.exe") {
            $PythonPath = "$env:USERPROFILE\miniforge3\python.exe"
        }
    }
} elseif (Test-Path "$env:USERPROFILE\miniforge3\python.exe") {
    $PythonPath = "$env:USERPROFILE\miniforge3\python.exe"
}

if (-not $PythonPath) {
    Write-Error "未找到有效的 Python 环境，请确认已安装 Python 并配置环境变量。"
    exit 1
}

Write-Host "使用 Python: $PythonPath" -ForegroundColor Cyan
Write-Host "工作目录:   $ProjectRoot" -ForegroundColor Cyan

# 执行聚合流程
& $PythonPath main.py --run

if ($LASTEXITCODE -eq 0) {
    Write-Host "每日技术早报生成完成！" -ForegroundColor Green
} else {
    Write-Host "任务执行失败，退出代码: $LASTEXITCODE" -ForegroundColor Red
}
