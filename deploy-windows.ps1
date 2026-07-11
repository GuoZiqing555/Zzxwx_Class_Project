param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9.-]+$')]
    [string]$Domain
)

$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated Administrator PowerShell.'
}

foreach ($command in @('python', 'caddy', 'nssm')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "$command was not found. Install the prerequisites from README and reopen Administrator PowerShell."
    }
}

if (-not (Test-Path (Join-Path $projectDir '.env'))) {
    throw '.env was not found. Copy .env.example to .env and set the API key first.'
}

$venvDir = Join-Path $projectDir '.venv'
$pythonExe = Join-Path $venvDir 'Scripts\python.exe'
$logsDir = Join-Path $projectDir 'logs'
$dataDir = Join-Path $projectDir 'data'
$caddyConfig = Join-Path $projectDir 'Caddyfile.windows'

if (-not (Test-Path $pythonExe)) {
    & python -m venv $venvDir
}
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $projectDir 'requirements.txt')
New-Item -ItemType Directory -Force -Path $logsDir, $dataDir | Out-Null

$appArgs = '-m streamlit run app.py --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false'
if (-not (Get-Service -Name 'ZzxwxApp' -ErrorAction SilentlyContinue)) {
    & nssm install ZzxwxApp $pythonExe $appArgs
}
& nssm set ZzxwxApp Application $pythonExe
& nssm set ZzxwxApp AppParameters $appArgs
& nssm set ZzxwxApp AppDirectory $projectDir
& nssm set ZzxwxApp AppStdout (Join-Path $logsDir 'app.log')
& nssm set ZzxwxApp AppStderr (Join-Path $logsDir 'app-error.log')
& nssm set ZzxwxApp AppRotateFiles 1
& nssm set ZzxwxApp Start SERVICE_AUTO_START

$caddyExe = (Get-Command caddy).Source
$caddyArgs = "run --config `"$caddyConfig`" --adapter caddyfile"
if (-not (Get-Service -Name 'ZzxwxCaddy' -ErrorAction SilentlyContinue)) {
    & nssm install ZzxwxCaddy $caddyExe $caddyArgs
}
& nssm set ZzxwxCaddy Application $caddyExe
& nssm set ZzxwxCaddy AppParameters $caddyArgs
& nssm set ZzxwxCaddy AppDirectory $projectDir
& nssm set ZzxwxCaddy AppEnvironmentExtra "DOMAIN=$Domain"
& nssm set ZzxwxCaddy AppStdout (Join-Path $logsDir 'caddy.log')
& nssm set ZzxwxCaddy AppStderr (Join-Path $logsDir 'caddy-error.log')
& nssm set ZzxwxCaddy AppRotateFiles 1
& nssm set ZzxwxCaddy DependOnService ZzxwxApp
& nssm set ZzxwxCaddy Start SERVICE_AUTO_START

foreach ($port in @(80, 443)) {
    $ruleName = "Zzxwx Website TCP $port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
    }
}

if ((Get-Service ZzxwxApp).Status -eq 'Running') {
    Restart-Service ZzxwxApp
} else {
    Start-Service ZzxwxApp
}
Start-Sleep -Seconds 3
if ((Get-Service ZzxwxCaddy).Status -eq 'Running') {
    Restart-Service ZzxwxCaddy
} else {
    Start-Service ZzxwxCaddy
}

Write-Host "Deployment complete. Open https://$Domain"
Write-Host "Logs: $logsDir"
