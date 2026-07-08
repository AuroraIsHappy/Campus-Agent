param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"
$env:CAMPUS_HOME = Join-Path $ProjectRoot ".campus-demo"

function Post-Json($path, $body) {
  Invoke-RestMethod -Method Post -Uri "$BaseUrl$path" -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 12)
}

Write-Host "Smoke testing Campus demo at $BaseUrl" -ForegroundColor Cyan

$health = Invoke-RestMethod "$BaseUrl/health"
if (-not $health.ok) { throw "health failed" }
Write-Host "OK /health"

$status = Invoke-RestMethod "$BaseUrl/demo/status"
if (-not $status.ok) { throw "demo status failed" }
Write-Host "OK /demo/status llm=$($status.llm.readiness) skills=$($status.vendor.Count + $status.campus.Count)"

$demoA = Post-Json "/demo_a/run" @{
  topic = "校园低碳实践"
  region = "北京高校社区"
  window = "2026 暑期"
  mode = "offline"
}
if (-not $demoA.ok) { throw "demo A failed: $($demoA.error)" }
Write-Host "OK Demo A -> $($demoA.run_dir)"

$demoC = Post-Json "/demo_c/run" @{
  goal = "7 天入门线性代数"
  days = 3
  minutes = 20
  quiz_n = 2
  mode = "offline"
}
if (-not $demoC.ok) { throw "demo C failed: $($demoC.error)" }
Write-Host "OK Demo C -> $($demoC.run_dir)"

$topic = Post-Json "/research/topics" @{
  title = "LLM agents for students"
  query = "student secretary agent papers"
}
if (-not $topic.ok) { throw "research topic failed: $($topic.error)" }
$digest = Post-Json "/research/topics/$($topic.topic.id)/refresh" @{ mode = "auto" }
if (-not $digest.ok) { throw "research refresh failed: $($digest.error)" }
if (-not $digest.note_path) { throw "research note_path missing" }
Write-Host "OK Research -> $($digest.note_path)"

$sync = Post-Json "/notes/notion/sync" @{ digest = $digest; mode = "local" }
if (-not $sync.ok) { throw "note sync failed: $($sync.error)" }
Write-Host "OK Notes -> $($sync.local_path)"

Write-Host "Campus demo smoke passed." -ForegroundColor Green
