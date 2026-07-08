param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Continue"

Write-Host "Campus demo doctor" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
if (-not $env:CAMPUS_HOME) {
  $env:CAMPUS_HOME = Join-Path $ProjectRoot ".campus-demo"
}
Write-Host "Campus home: $env:CAMPUS_HOME"

$localApp = [Environment]::GetFolderPath("LocalApplicationData")
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } elseif ($localApp) { Join-Path $localApp "hermes" } else { Join-Path $HOME ".hermes" }
$repoSkills = Join-Path $ProjectRoot "skills"
$vendorSkills = Join-Path $repoSkills "vendor"

Write-Host ""
Write-Host "Skills" -ForegroundColor Cyan
Write-Host "Hermes home: $hermesHome"
if (Test-Path (Join-Path $hermesHome "skills")) {
  Get-ChildItem (Join-Path $hermesHome "skills") -Directory | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | Select-Object -ExpandProperty Name
} else {
  Write-Host "No installed Hermes skills directory found."
}
Write-Host "Repo skills: $repoSkills"
if (Test-Path $vendorSkills) {
  Write-Host "Vendored skills:"
  Get-ChildItem $vendorSkills -Directory | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | Select-Object -ExpandProperty Name
}

Write-Host ""
Write-Host "LLM config" -ForegroundColor Cyan
$envFiles = @((Join-Path $hermesHome ".env"), (Join-Path $HOME ".hermes\.env")) | Where-Object { Test-Path $_ } | Select-Object -Unique
if ($envFiles.Count -eq 0) {
  Write-Host "No Hermes .env found. real mode will fail until a provider key is configured."
} else {
  foreach ($file in $envFiles) {
    Write-Host "Env file: $file"
    Select-String -Path $file -Pattern "^(OPENAI_API_KEY|GLM_API_KEY|ZAI_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY)=" | ForEach-Object {
      ($_.Matches.Value -split "=")[0]
    }
  }
}

Write-Host ""
Write-Host "Commands" -ForegroundColor Cyan
foreach ($cmd in @("hermes", "py", "python", "npm.cmd")) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($found) { Write-Host "$cmd -> $($found.Source)" } else { Write-Host "$cmd -> missing" }
}

Write-Host ""
Write-Host "Frontend check" -ForegroundColor Cyan
Push-Location (Join-Path $ProjectRoot "frontend")
try {
  npm.cmd run typecheck
} finally {
  Pop-Location
}
