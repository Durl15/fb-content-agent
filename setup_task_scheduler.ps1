# setup_task_scheduler.ps1
# Creates a Windows Task Scheduler task that starts the FB Content Agent
# automatically at login and on system startup (AC power only).
# Run once as Administrator.

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$script  = Join-Path $root "Start-Agent.ps1"
$taskName = "FBContentAgent"

Write-Host "  Setting up Windows Task Scheduler..." -ForegroundColor Cyan
Write-Host "  Task    : $taskName"
Write-Host "  Script  : $script"
Write-Host ""

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Build the action
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`"" `
    -WorkingDirectory $root

# Trigger 1: at log on
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Trigger 2: at system startup (5-minute delay so network is up)
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerBoot.Delay = "PT5M"

# Settings: run whether logged on or not, restart on failure
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Principal: run as current user with highest privileges
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

$task = New-ScheduledTask `
    -Action $action `
    -Trigger @($triggerLogon, $triggerBoot) `
    -Settings $settings `
    -Principal $principal `
    -Description "Starts FB Content Agent API, automation scheduler, and dashboard on login/startup."

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null

Write-Host "  Task registered." -ForegroundColor Green
Write-Host ""
Write-Host "  To run now:     Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host "  To remove:      Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
Write-Host "  To view in UI:  taskschd.msc" -ForegroundColor White
Write-Host ""
Write-Host "  Agent will now start automatically at every login." -ForegroundColor Cyan
