param (
    [string]$Time = "08:30",
    [switch]$Uninstall,
    [switch]$RunNow
)

# ==============================================================================
# TechPulse Daily - Windows 计划任务配置脚本 (PowerShell 7)
# ==============================================================================
$ErrorActionPreference = "Stop"
$TaskName = "TechPulse_Daily_Digest"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RunnerScript = Join-Path $ProjectRoot "scripts\run_digest.ps1"

if ($Uninstall) {
    Write-Host "正在卸载 Windows 计划任务 [$TaskName]..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "计划任务 [$TaskName] 已成功移除！" -ForegroundColor Green
    exit 0
}

if ($RunNow) {
    Write-Host "立即触发计划任务 [$TaskName] 测试执行..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "已触发执行！" -ForegroundColor Green
    exit 0
}

# 寻找 pwsh 路径
$PwshPath = (Get-Command "pwsh" -ErrorAction SilentlyContinue).Source
if (-not $PwshPath) {
    Write-Error "系统未找到 PowerShell 7 (pwsh)，请先安装 pwsh。"
    exit 1
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "配置 TechPulse 每日定时计划任务 (Windows Task Scheduler)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "触发时间: 每日 $Time"
Write-Host "执行程序: $PwshPath"
Write-Host "执行脚本: $RunnerScript"

# 创建任务操作与触发器
$Action = New-ScheduledTaskAction -Execute $PwshPath -Argument "-NoLogo -NoProfile -WindowStyle Hidden -File `"$RunnerScript`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 注册任务（覆盖旧任务）
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "TechPulse Daily GitHub Trending & Hacker News Digest" -Force | Out-Null

Write-Host ""
Write-Host "计划任务 [$TaskName] 注册成功！" -ForegroundColor Green
Write-Host "提示：每天北京时间 $Time，系统将在后台自动静默执行抓取并更新 RSS 与推送通知。" -ForegroundColor Gray
Write-Host "如需手动测试运行: pwsh scripts\setup_task_windows.ps1 -RunNow" -ForegroundColor Gray
Write-Host "如需移除计划任务: pwsh scripts\setup_task_windows.ps1 -Uninstall" -ForegroundColor Gray
