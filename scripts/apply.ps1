# Apply auto-model-router: install user skills, copy demo, open savings dashboard.
# Running this script is how the dashboard auto-starts. Dropping SKILL.md alone does not.
[CmdletBinding()]
param(
  [switch]$NoOpen,
  [switch]$Open,
  [switch]$EnableWeeklyReview,
  [switch]$DisableWeeklyReview,
  [switch]$InstallSchedule,
  [switch]$UninstallSchedule,
  [switch]$ShareAdoption,
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

Weekly review (opt-in; local usage log only — not vendor billing):
  -EnableWeeklyReview     Set weeklyReview=true
  -DisableWeeklyReview    Set weeklyReview=false
  -InstallSchedule        Install a user Task Scheduler weekly job (explicit opt-in)
  -UninstallSchedule      Remove the weekly task installed by this script

Adoption evidence (explicit opt-in):
  -ShareAdoption          Open a public GitHub adoption form after applying.
                          Nothing is submitted until you review and submit it.

Preference file: `$env:USERPROFILE\.auto-model-router\config.json
  { "openDashboardOnApply": true, "weeklyReview": false }

Run a review anytime:
  python `$env:USERPROFILE\.auto-model-router\weekly_review.py --force
"@
  exit 0
}

if ($NoOpen -and $Open) {
  Write-Error "Specify only one of -Open or -NoOpen"
}
if ($EnableWeeklyReview -and $DisableWeeklyReview) {
  Write-Error "Specify only one of -EnableWeeklyReview or -DisableWeeklyReview"
}

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SkillSrc = Join-Path $Root "skills\auto-model-router\SKILL.md"
$DemoSrc = Join-Path $Root "demo"
$WeeklySrc = Join-Path $Root "scripts\weekly_review.py"

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
$ReceiptFile = Join-Path $AmrHome "install-receipt.json"
$TaskName = "AutoModelRouterWeeklyReview"
$AdoptionUrl = "https://github.com/1ststepai/auto-model-router/issues/new?template=adoption.yml"

function Read-Config {
  $cfg = [ordered]@{
    openDashboardOnApply = $true
    weeklyReview = $false
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
  }
  $json = ($obj | ConvertTo-Json -Compress) + [Environment]::NewLine
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
  $destFile = Join-Path $DestDir "SKILL.md"
  if ((Test-Path -LiteralPath $destFile) -and
      ((Get-FileHash -Algorithm SHA256 -LiteralPath $SkillSrc).Hash -eq
       (Get-FileHash -Algorithm SHA256 -LiteralPath $destFile).Hash)) {
    Write-Host "  skill already current → $destFile"
    return
  }
  Copy-Item -LiteralPath $SkillSrc -Destination $destFile -Force
  Write-Host "  installed skill → $destFile"
}

function Update-InstallReceipt {
  $nowValue = [DateTimeOffset]::UtcNow
  $now = $nowValue.ToString("yyyy-MM-ddTHH:mm:ssZ")
  $firstAppliedAt = $now
  $applyCount = 0
  if (Test-Path -LiteralPath $ReceiptFile) {
    try {
      $existing = Get-Content -LiteralPath $ReceiptFile -Raw | ConvertFrom-Json
      if (-not [string]::IsNullOrWhiteSpace([string]$existing.firstAppliedAt)) {
        try {
          $parsedFirst = ([DateTimeOffset]$existing.firstAppliedAt).ToUniversalTime()
          $firstAppliedAt = if ($parsedFirst -le $nowValue) {
            $parsedFirst.ToString("yyyy-MM-ddTHH:mm:ssZ")
          } else {
            $now
          }
        } catch {
          $firstAppliedAt = $now
        }
      }
      if ($null -ne $existing.applyCount) {
        $applyCount = [int]$existing.applyCount
      }
    } catch {
      # Replace malformed local metadata; no remote data exists.
    }
  }
  $receipt = [ordered]@{
    schemaVersion = 1
    firstAppliedAt = $firstAppliedAt
    lastAppliedAt = $now
    applyCount = $applyCount + 1
    installedHosts = @("cursor", "claude", "codex", "agents", "gemini")
    installerTransmitted = $false
  }
  [System.IO.File]::WriteAllText(
    $ReceiptFile,
    (($receipt | ConvertTo-Json -Depth 3) + [Environment]::NewLine)
  )
  Write-Host "  local install receipt → $ReceiptFile (not transmitted)"
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
Install-Skill (Join-Path $HomeDir ".agents\skills\auto-model-router")
Install-Skill (Join-Path $HomeDir ".gemini\skills\auto-model-router")

New-Item -ItemType Directory -Force -Path $DemoDest | Out-Null
New-Item -ItemType Directory -Force -Path $LogsDest | Out-Null
Copy-Item -LiteralPath (Join-Path $DemoSrc "dashboard.html") -Destination (Join-Path $DemoDest "dashboard.html") -Force
Copy-Item -LiteralPath (Join-Path $DemoSrc "savings_estimator.py") -Destination (Join-Path $DemoDest "savings_estimator.py") -Force
Copy-Item -LiteralPath (Join-Path $DemoSrc "sample_usage_log.json") -Destination (Join-Path $DemoDest "sample_usage_log.json") -Force
Copy-Item -LiteralPath (Join-Path $DemoSrc "classify.py") -Destination (Join-Path $DemoDest "classify.py") -Force
foreach ($name in @("sample_measured_usage.jsonl", "prices.example.json")) {
  $src = Join-Path $DemoSrc $name
  if (Test-Path -LiteralPath $src) {
    Copy-Item -LiteralPath $src -Destination (Join-Path $DemoDest $name) -Force
  }
}
$routerSrc = Join-Path $Root "auto_model_router.py"
if (Test-Path -LiteralPath $routerSrc) {
  Copy-Item -LiteralPath $routerSrc -Destination (Join-Path $AmrHome "auto_model_router.py") -Force
}
foreach ($scriptName in @("confirm_gate.py", "detect_active.py")) {
  $src = Join-Path $Root "scripts\$scriptName"
  if (Test-Path -LiteralPath $src) {
    Copy-Item -LiteralPath $src -Destination (Join-Path $AmrHome $scriptName) -Force
  }
}
Write-Host "  demo → $DemoDest"

if (Test-Path -LiteralPath $WeeklySrc) {
  Copy-Item -LiteralPath $WeeklySrc -Destination $WeeklyDest -Force
  Write-Host "  weekly review → $WeeklyDest"
}

if (-not (Test-Path -LiteralPath $ConfigFile)) {
  Write-Config -Cfg ([ordered]@{ openDashboardOnApply = $true; weeklyReview = $false })
  Write-Host "  created config → $ConfigFile"
}

$UsageLog = Join-Path $LogsDest "usage.jsonl"
if (-not (Test-Path -LiteralPath $UsageLog)) {
  New-Item -ItemType File -Force -Path $UsageLog | Out-Null
  Write-Host "  created empty log → $UsageLog"
} else {
  Write-Host "  kept existing log → $UsageLog"
}

Update-InstallReceipt

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
Write-Host "  Skills: %USERPROFILE%\.cursor, .claude, .codex, .agents, .gemini (under skills\auto-model-router\)"
Write-Host "  Dashboard: $Dashboard"
Write-Host "  Config: $ConfigFile"
Write-Host "  Adoption: local receipt only; no telemetry was sent."
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
if ($cfg.weeklyReview) {
  Write-Host "  Weekly review: enabled (local usage log only — not vendor billing)."
  Write-Host "  Run: python $WeeklyDest --force"
} else {
  Write-Host "  Weekly review: disabled (opt-in). Enable: .\scripts\apply.ps1 -EnableWeeklyReview"
}
Write-Host ""
Write-Host "Note: Cursor/Claude/Gemini loading SKILL.md alone cannot open a GUI."
Write-Host "      `"Apply`" means running this script so the dashboard auto-starts."
if ($ShareAdoption) {
  try {
    Start-Process $AdoptionUrl
    Write-Host "  Opened the optional public adoption form. Review it, then submit it yourself."
  } catch {
    Write-Host "  Could not open the optional adoption form: $AdoptionUrl"
  }
} else {
  Write-Host "  Optional: re-run with -ShareAdoption to open the public adoption form."
}
