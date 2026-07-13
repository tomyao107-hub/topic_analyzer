param(
    [string]$Python = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $Root $Python
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python environment not found: $PythonPath"
}

& $PythonPath -m PyInstaller --noconfirm --clean --distpath (Join-Path $Root "build\sidecar-dist") --workpath (Join-Path $Root "build\sidecar-work") (Join-Path $Root "topic-analyzer-backend.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller sidecar build failed" }

$Source = Join-Path $Root "build\sidecar-dist\topic-analyzer-backend-x86_64-pc-windows-msvc.exe"
$DestinationDirectory = Join-Path $Root "desktop\src-tauri\binaries"
$Destination = Join-Path $DestinationDirectory "topic-analyzer-backend-x86_64-pc-windows-msvc.exe"
New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
Copy-Item -LiteralPath $Source -Destination $Destination -Force
Write-Host "Sidecar ready: $Destination"
