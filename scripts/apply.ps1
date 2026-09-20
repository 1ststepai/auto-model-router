# Apply auto-model-router: install user skills, copy demo, open savings dashboard.
# Running this script is how the dashboard auto-starts. Dropping SKILL.md alone does not.
[CmdletBinding()]
param(
  [switch]$NoOpen,
  [switch]$Open,
  [switch]$EnableWeeklyReview,
  [switch]$DisableWeeklyReview,
  [switch]$EnableAudit,
  [switch]$DisableAudit,
  [switch]$ApplyRecommendations,
  [switch]$InstallSchedule,
  [switch]$UninstallSchedule,
  [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
  Write-Host @"
Usage: .\scripts\apply.ps1 [options]

Dashboard:
  (default)               Open dashboard unless preference says no
  -NoOpen                 Do not open browser; set openDashboardOnApply=false
  -Open                   Open browser; set openDashboardOnApply=true

Savings Desk audit (opt-in; local usage log only — not vendor billing):
  -EnableAudit            Set auditOptIn=true (required before agents append usage.jsonl)
  -DisableAudit           Set auditOptIn=false
  -ApplyRecommendations   After audit: yes, write local maps + boundaryGatedConfirms=true

Weekly review (opt-in; local usage log only — not vendor billing):
  -EnableWeeklyReview     Set weeklyReview=true
  -DisableWeeklyReview    Set weeklyReview=false
  -InstallSchedule        Install a user Task Scheduler weekly job (explicit opt-in)
  -UninstallSchedule      Remove the weekly task installed by this script

Preference file: `$env:USERPROFILE\.auto-model-router\config.json
  { "openDashboardOnApply": true, "weeklyReview": false, "auditOptIn": false,
    "hosts": ["cursor", "claude-code", "codex"], "usageLogPath": "",
    "boundaryGatedConfirms": false }

Try Savings Desk (detect → audit → ask → yes):
  .\scripts\apply.ps1 -EnableAudit -NoOpen
  python `$env:USERPROFILE\.auto-model-router\detect_active.py
  python `$env:USERPROFILE\.auto-model-router\audit_usage.py
  python `$env:USERPROFILE\.auto-model-router\apply_recommendations.py --yes
"@
  exit 0
}

if ($NoOpen -and $Open) {
  Write-Error "Specify only one of -Open or -NoOpen"
}
if ($EnableWeeklyReview -and $DisableWeeklyReview) {
  Write-Error "Specify only one of -EnableWeeklyReview or -DisableWeeklyReview"
}
if ($EnableAudit -and $DisableAudit) {
  Write-Error "Specify only one of -EnableAudit or -DisableAudit"
}

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SkillSrc = Join-Path $Root "skills\auto-model-router\SKILL.md"
$DemoSrc = Join-Path $Root "demo"
$WeeklySrc = Join-Path $Root "scripts\weekly_review.py"
$AmrUsageSrc = Join-Path $Root "scripts\amr_usage.py"
$AuditSrc = Join-Path $Root "scripts\audit_usage.py"
$ApplyRecSrc = Join-Path $Root "scripts\apply_recommendations.py"
$DetectSrc = Join-Path $Root "scripts\detect_active.py"

if (-not (Test-Path -LiteralPath $SkillSrc)) {
  Write-Error "Missing skill at $SkillSrc"
}

$HomeDir = $env:USERPROFILE
if ([string]::IsNullOrWhiteSpace($HomeDir)) {
  Write-Error "USERPROFILE is not set"
}

$AmrHome = Join-Path $HomeDir ".auto-model-router"
$DemoDest = Join-Path $AmrHome "demo"
$LogsDest = Join-Path $AmrHome "logs"
$ConfigFile = Join-Path $AmrHome "config.json"
$WeeklyDest = Join-Path $AmrHome "weekly_review.py"
$AmrUsageDest = Join-Path $AmrHome "amr_usage.py"
$AuditDest = Join-Path $AmrHome "audit_usage.py"
$ApplyRecDest = Join-Path $AmrHome "apply_recommendations.py"
$DetectDest = Join-Path $AmrHome "detect_active.py"
$TaskName = "AutoModelRouterWeeklyReview"

function Read-Config {
  $cfg = [ordered]@{
    openDashboardOnApply = $true
    weeklyReview = $false
    auditOptIn = $false
    hosts = @("cursor", "claude-code", "codex")
    usageLogPath = ""
    boundaryGatedConfirms = $false
    currentHost = ""
    currentTier = ""
    currentModel = ""
  }
  if (Test-Path -LiteralPath $ConfigFile) {
    try {
      $raw = Get-Content -LiteralPath $ConfigFile -Raw -ErrorAction Stop
      $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
      if ($null -ne $parsed.openDashboardOnApply) {
        $cfg.openDashboardOnApply = [bool]$parsed.openDashboardOnApply
      }
      if ($null -ne $parsed.weeklyReview) {
        $cfg.weeklyReview = [bool]$parsed.weeklyReview
      }
      if ($null -ne $parsed.auditOptIn) {
        $cfg.auditOptIn = [bool]$parsed.auditOptIn
      }
      if ($null -ne $parsed.boundaryGatedConfirms) {
        $cfg.boundaryGatedConfirms = [bool]$parsed.boundaryGatedConfirms
      }
      if ($null -ne $parsed.usageLogPath) {
        $cfg.usageLogPath = [string]$parsed.usageLogPath
      }
      if ($null -ne $parsed.hosts) {
        $cfg.hosts = @($parsed.hosts)
      }
      if ($null -ne $parsed.currentHost) { $cfg.currentHost = [string]$parsed.currentHost }
      if ($null -ne $parsed.currentTier) { $cfg.currentTier = [string]$parsed.currentTier }
      if ($null -ne $parsed.currentModel) { $cfg.currentModel = [string]$parsed.currentModel }
    } catch {
      # keep defaults
    }
  }
  return $cfg
}

function Write-Config {
  param($Cfg)
  New-Item -ItemType Directory -Force -Path $AmrHome | Out-Null
  $obj = [ordered]@{
    openDashboardOnApply = [bool]$Cfg.openDashboardOnApply
    weeklyReview = [bool]$Cfg.weeklyReview
    auditOptIn = [bool]$Cfg.auditOptIn
    hosts = @($Cfg.hosts)
    usageLogPath = [string]$Cfg.usageLogPath
    boundaryGatedConfirms = [bool]$Cfg.boundaryGatedConfirms
    currentHost = [string]$Cfg.currentHost
    currentTier = [string]$Cfg.currentTier
    currentModel = [string]$Cfg.currentModel
  }
  $json = ($obj | ConvertTo-Json -Depth 4) + [Environment]::NewLine
  [System.IO.File]::WriteAllText($ConfigFile, $json)
}

function Set-ConfigBool {
  param([string]$Key, [bool]$Value)
  $cfg = Read-Config
  $cfg[$Key] = $Value
  Write-Config -Cfg $cfg
  $literal = if ($Value) { "true" } else { "false" }
  Write-Host "  preference → $ConfigFile ($Key=$literal)"
}

function Install-Skill {
  param([string]$DestDir)
  New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
  Copy-Item -LiteralPath $SkillSrc -Destination (Join-Path $DestDir "SKILL.md") -Force
  Write-Host "  installed skill → $(Join-Path $DestDir 'SKILL.md')"
}

function Install-WeeklySchedule {
  if (-not (Test-Path -LiteralPath $WeeklyDest)) {
    Write-Error "Missing $WeeklyDest (apply install first)"
  }
  $python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
  }
  if (-not $python) {
    Write-Error "python/python3 not found; cannot install schedule"
  }
  $tr = "`"$($python.Source)`" `"$WeeklyDest`" --force"
  # Remove existing task if present, then create weekly Monday 09:00.
  schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
  $create = schtasks /Create /TN $TaskName /SC WEEKLY /D MON /ST 09:00 /TR $tr /F
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create scheduled task $TaskName"
  }
  Write-Host "  installed weekly task → $TaskName (Mondays 09:00)"
  Write-Host "  remove with: .\scripts\apply.ps1 -UninstallSchedule"
}

function Uninstall-WeeklySchedule {
  $existing = schtasks /Query /TN $TaskName 2>$null
  if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "  removed scheduled task → $TaskName"
  } else {
    Write-Host "  no scheduled task named $TaskName found"
  }
}

Write-Host "Applying auto-model-router..."

Install-Skill (Join-Path $HomeDir ".cursor\skills\auto-model-router")
Install-Skill (Join-Path $HomeDir ".claude\skills\auto-model-router")
Install-Skill (Join-Path $HomeDir ".codex\skills\auto-model-router")

New-Item -ItemType Directory -Force -Path $DemoDest | Out-Null
New-Item -ItemType Directory -Force -Path $LogsDest | Out-Null
Copy-Item -LiteralPath (Join-Path $DemoSrc "dashboard.html") -Destination (Join-Path $DemoDest "dashboard.html") -Force
Copy-Item -LiteralPath (Join-Path $DemoSrc "savings_estimator.py") -Destination (Join-Path $DemoDest "savings_estimator.py") -Force
Copy-Item -LiteralPath (Join-Path $DemoSrc "sample_usage_log.json") -Destination (Join-Path $DemoDest "sample_usage_log.json") -Force
Write-Host "  demo → $DemoDest"

if (Test-Path -LiteralPath $WeeklySrc) {
  Copy-Item -LiteralPath $WeeklySrc -Destination $WeeklyDest -Force
  Write-Host "  weekly review → $WeeklyDest"
}
if (Test-Path -LiteralPath $AmrUsageSrc) {
  Copy-Item -LiteralPath $AmrUsageSrc -Destination $AmrUsageDest -Force
  Write-Host "  usage helpers → $AmrUsageDest"
}
if (Test-Path -LiteralPath $AuditSrc) {
  Copy-Item -LiteralPath $AuditSrc -Destination $AuditDest -Force
  Write-Host "  audit → $AuditDest"
}
if (Test-Path -LiteralPath $ApplyRecSrc) {
  Copy-Item -LiteralPath $ApplyRecSrc -Destination $ApplyRecDest -Force
  Write-Host "  apply recommendations → $ApplyRecDest"
}
if (Test-Path -LiteralPath $DetectSrc) {
  Copy-Item -LiteralPath $DetectSrc -Destination $DetectDest -Force
  Write-Host "  detect active → $DetectDest"
}
$ExamplesDest = Join-Path $AmrHome "examples"
New-Item -ItemType Directory -Force -Path $ExamplesDest | Out-Null
foreach ($map in @(
  "cursor-tier-map.example.json",
  "claude-tier-map.example.json",
  "codex-tier-map.example.json",
  "gemini-tier-map.example.json",
  "config.example.json"
)) {
  $src = Join-Path $Root "integrations\$map"
  if (Test-Path -LiteralPath $src) {
    Copy-Item -LiteralPath $src -Destination (Join-Path $ExamplesDest $map) -Force
  }
}

if (-not (Test-Path -LiteralPath $ConfigFile)) {
  Write-Config -Cfg ([ordered]@{
    openDashboardOnApply = $true
    weeklyReview = $false
    auditOptIn = $false
    hosts = @("cursor", "claude-code", "codex")
    usageLogPath = ""
    boundaryGatedConfirms = $false
    currentHost = ""
    currentTier = ""
    currentModel = ""
  })
  Write-Host "  created config → $ConfigFile"
}

$UsageLog = Join-Path $LogsDest "usage.jsonl"
if (-not (Test-Path -LiteralPath $UsageLog)) {
  New-Item -ItemType File -Force -Path $UsageLog | Out-Null
  Write-Host "  created empty log → $UsageLog"
} else {
  Write-Host "  kept existing log → $UsageLog"
}

if ($NoOpen) {
  Set-ConfigBool -Key "openDashboardOnApply" -Value $false
} elseif ($Open) {
  Set-ConfigBool -Key "openDashboardOnApply" -Value $true
}

if ($EnableWeeklyReview) {
  Set-ConfigBool -Key "weeklyReview" -Value $true
} elseif ($DisableWeeklyReview) {
  Set-ConfigBool -Key "weeklyReview" -Value $false
}

if ($EnableAudit) {
  Set-ConfigBool -Key "auditOptIn" -Value $true
} elseif ($DisableAudit) {
  Set-ConfigBool -Key "auditOptIn" -Value $false
}

if ($UninstallSchedule) {
  Uninstall-WeeklySchedule
}
if ($InstallSchedule) {
  Set-ConfigBool -Key "weeklyReview" -Value $true
  Install-WeeklySchedule
}

$cfg = Read-Config
$ShouldOpen = [bool]$cfg.openDashboardOnApply
if ($NoOpen) { $ShouldOpen = $false }
elseif ($Open) { $ShouldOpen = $true }

$Dashboard = Join-Path $DemoDest "dashboard.html"
$opened = $false
if ($ShouldOpen) {
  try {
    Start-Process $Dashboard
    $opened = $true
  } catch {
    try {
      Invoke-Item -LiteralPath $Dashboard
      $opened = $true
    } catch {
      $opened = $false
    }
  }
}

Write-Host ""
Write-Host "Success: auto-model-router applied."
Write-Host "  Skills: %USERPROFILE%\.cursor, .claude, .codex (under skills\auto-model-router\)"
Write-Host "  Dashboard: $Dashboard"
Write-Host "  Config: $ConfigFile"
if (-not $ShouldOpen) {
  Write-Host "  Skipped opening the browser (-NoOpen or openDashboardOnApply=false)."
  Write-Host "  Open the dashboard path above manually when you want it,"
  Write-Host "  or re-run with -Open to enable auto-open again."
} elseif ($opened) {
  Write-Host "  Opened the savings dashboard in your default browser."
} else {
  Write-Host "  Could not auto-open a browser. Open the dashboard path above manually,"
  Write-Host "  then click `"Load sample log`"."
}
if ($ApplyRecommendations) {
  $cfg = Read-Config
  if (-not $cfg.auditOptIn) {
    Write-Host "  -ApplyRecommendations skipped: enable audit first (-EnableAudit)."
  } elseif (Test-Path -LiteralPath $ApplyRecDest) {
    Write-Host ""
    Write-Host "Applying Savings Desk recommendations (local maps + boundary-gate flag)..."
    & python $ApplyRecDest --yes --dest $AmrHome
  } else {
    Write-Host "  apply_recommendations.py not installed; skip -ApplyRecommendations"
  }
}

if ($cfg.weeklyReview) {
  Write-Host "  Weekly review: enabled (local usage log only — not vendor billing)."
  Write-Host "  Run: python $WeeklyDest --force"
} else {
  Write-Host "  Weekly review: disabled (opt-in). Enable: .\scripts\apply.ps1 -EnableWeeklyReview"
}
if ($cfg.auditOptIn) {
  Write-Host "  Savings Desk audit: enabled (local log only — not vendor billing)."
  Write-Host "  Collected: tier, host, confirmed/overridden, task_kind, gate, timestamp."
  Write-Host "  Never: prompts, code, secrets, vendor credentials, billing APIs."
  Write-Host "  Run: python $AuditDest --force"
  Write-Host "  Automate: python $ApplyRecDest"
} else {
  Write-Host "  Savings Desk audit: disabled (opt-in). Enable: .\scripts\apply.ps1 -EnableAudit"
}
Write-Host ""
Write-Host "Note: Cursor/Claude loading SKILL.md alone cannot open a GUI."
Write-Host "      `"Apply`" means running this script so the dashboard auto-starts."
