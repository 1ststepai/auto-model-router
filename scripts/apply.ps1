# Apply auto-model-router: install user skills, copy demo, open savings dashboard.
# Running this script is how the dashboard auto-starts. Dropping SKILL.md alone does not.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SkillSrc = Join-Path $Root "skills\auto-model-router\SKILL.md"
$DemoSrc = Join-Path $Root "demo"

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

function Install-Skill {
  param([string]$DestDir)
  New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
  Copy-Item -LiteralPath $SkillSrc -Destination (Join-Path $DestDir "SKILL.md") -Force
  Write-Host "  installed skill → $(Join-Path $DestDir 'SKILL.md')"
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

$UsageLog = Join-Path $LogsDest "usage.jsonl"
if (-not (Test-Path -LiteralPath $UsageLog)) {
  New-Item -ItemType File -Force -Path $UsageLog | Out-Null
  Write-Host "  created empty log → $UsageLog"
} else {
  Write-Host "  kept existing log → $UsageLog"
}

$Dashboard = Join-Path $DemoDest "dashboard.html"
$opened = $false
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

Write-Host ""
Write-Host "Success: auto-model-router applied."
Write-Host "  Skills: %USERPROFILE%\.cursor, .claude, .codex (under skills\auto-model-router\)"
Write-Host "  Dashboard: $Dashboard"
if ($opened) {
  Write-Host "  Opened the savings dashboard in your default browser."
} else {
  Write-Host "  Could not auto-open a browser. Open the dashboard path above manually,"
  Write-Host "  then click `"Load sample log`"."
}
Write-Host ""
Write-Host "Note: Cursor/Claude loading SKILL.md alone cannot open a GUI."
Write-Host "      `"Apply`" means running this script so the dashboard auto-starts."
