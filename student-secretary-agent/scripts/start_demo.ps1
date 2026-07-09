param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 5173
)

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$env:CAMPUS_HOME = Join-Path $ProjectRoot ".campus-demo"

function Test-Python($cmd) {
  if (-not $cmd) { return $false }
  try {
    & $cmd --version *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

$candidates = @()
if ($env:CAMPUS_PYTHON) { $candidates += $env:CAMPUS_PYTHON }
if (Test-Path $VenvPython) { $candidates += $VenvPython }
$cmdPython = Get-Command python -ErrorAction SilentlyContinue
if ($cmdPython) { $candidates += $cmdPython.Source }
$cmdPython3 = Get-Command python3 -ErrorAction SilentlyContinue
if ($cmdPython3) { $candidates += $cmdPython3.Source }

$PythonCmd = $candidates | Where-Object { Test-Python $_ } | Select-Object -First 1
if (-not $PythonCmd) {
  throw "No runnable Python found. Set CAMPUS_PYTHON to a Python executable with FastAPI/uvicorn available."
}

$sitePackages = Join-Path $ProjectRoot ".venv\Lib\site-packages"
if ($PythonCmd -ne $VenvPython -and (Test-Path $sitePackages)) {
  $env:PYTHONPATH = "$sitePackages;$env:PYTHONPATH"
}
$PythonArgs = @("-m", "uvicorn", "campus.api.server:app", "--host", "127.0.0.1", "--port", "$ApiPort")

Write-Host "Starting Campus API on http://127.0.0.1:$ApiPort"
Start-Process -FilePath $PythonCmd -ArgumentList $PythonArgs -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Write-Host "Starting frontend on http://127.0.0.1:$WebPort"
Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$WebPort") -WorkingDirectory $FrontendRoot -WindowStyle Hidden

Write-Host "Demo URLs:"
Write-Host "  API:      http://127.0.0.1:$ApiPort/health"
Write-Host "  Frontend: http://127.0.0.1:$WebPort"
