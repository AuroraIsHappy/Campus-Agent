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

$settings = Invoke-RestMethod "$BaseUrl/settings/status"
if (-not $settings.ok) { throw "settings failed" }
Write-Host "OK /settings/status home=$($settings.campus_home)"

$agent = Post-Json "/agent/run" @{
  message = "我想学 Linux，帮我安排 3 天计划"
  mode = "offline"
  context = @{ days = 3 }
}
if (-not $agent.ok) { throw "agent run failed: $($agent.error)" }
Write-Host "OK /agent/run -> $($agent.run_id)"

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

$cards = Post-Json "/learning/flashcards" @{ topic = "Linux"; count = 3 }
if (-not $cards.ok -or $cards.flashcards.Count -lt 3) { throw "learning flashcards failed" }
Write-Host "OK Learning flashcards"

$health = Post-Json "/life/health" @{ mood = "ok"; sleep_hours = 7; exercise = "walk" }
if (-not $health.ok) { throw "life health failed" }
$travel = Post-Json "/life/travel_plan" @{ destination = "上海"; days = 2; budget = 800 }
if (-not $travel.ok) { throw "life travel failed" }
Write-Host "OK Life health/travel"

$email = Post-Json "/club/email_draft" @{ purpose = "邀请老师指导活动"; recipient = "老师" }
if (-not $email.ok) { throw "club email failed" }
Write-Host "OK Club email draft"

$career = Post-Json "/career/interview_plan" @{ role = "AI 产品实习生"; days = 7 }
if (-not $career.ok) { throw "career interview failed" }
Write-Host "OK Career interview plan"

Write-Host "Campus demo smoke passed." -ForegroundColor Green
