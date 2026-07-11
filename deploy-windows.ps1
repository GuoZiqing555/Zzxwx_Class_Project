param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectDir = $PSScriptRoot
$runtimeDir = Join-Path $projectDir '.runtime'
$downloadDir = Join-Path $runtimeDir 'downloads'
$pythonDir = Join-Path $runtimeDir 'python'
$caddyDir = Join-Path $runtimeDir 'caddy'
$logsDir = Join-Path $projectDir 'logs'
$dataDir = Join-Path $projectDir 'data'
$envFile = Join-Path $projectDir '.env'
$markerFile = Join-Path $runtimeDir 'zzxwx-runtime.marker'
$appTaskName = 'ZzxwxClassProject-App'
$proxyTaskName = 'ZzxwxClassProject-Caddy'
$pythonVersion = '3.12.10'
$caddyVersion = '2.10.2'

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from an elevated Administrator PowerShell.'
    }
}

function Get-DotEnvValue([string]$Name) {
    $line = Get-Content -LiteralPath $envFile -Encoding UTF8 |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } |
        Select-Object -Last 1
    if (-not $line) { return '' }
    return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'")
}

function Download-File([string]$Uri, [string]$Destination) {
    if (Test-Path -LiteralPath $Destination) { return }
    Write-Host "Downloading $Uri"
    $partial = "$Destination.partial"
    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partial
    Move-Item -LiteralPath $partial -Destination $Destination
}

function Assert-PortFree([int]$Port) {
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listeners) {
        $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ', '
        throw "TCP port $Port is already in use by PID(s): $owners. Nothing was changed on that process."
    }
}

function Stop-OwnTask([string]$TaskName) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

Assert-Administrator

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $projectDir '.env.example') -Destination $envFile
    throw '.env was created. Open it in Notepad, set the API key and domain, then run this script again.'
}

$apiKey = Get-DotEnvValue 'DEEPSEEK_API_KEY'
$domain = Get-DotEnvValue 'DOMAIN'
if (-not $apiKey -or $apiKey -like 'replace_*' -or $apiKey -like '*actual*') {
    throw 'Set DEEPSEEK_API_KEY in .env before deployment.'
}
if (-not $domain -or $domain -eq 'demo.example.com' -or $domain -notmatch '^[A-Za-z0-9.-]+$') {
    throw 'Set DOMAIN in .env to a valid hostname without protocol, path or port.'
}

New-Item -ItemType Directory -Force -Path $runtimeDir, $downloadDir, $pythonDir, $caddyDir, $logsDir, $dataDir | Out-Null

$existingOwnTasks = Get-ScheduledTask -TaskName "$($appTaskName.Split('-')[0])*" -ErrorAction SilentlyContinue |
    Where-Object { $_.TaskName -in @($appTaskName, $proxyTaskName) }
if ($existingOwnTasks -and -not (Test-Path -LiteralPath $markerFile)) {
    throw 'Matching scheduled tasks already exist but were not created by this project. Deployment stopped.'
}

Stop-OwnTask $proxyTaskName
Stop-OwnTask $appTaskName
Assert-PortFree 80
Assert-PortFree 443
Assert-PortFree 8504

$pythonZip = Join-Path $downloadDir "python-$pythonVersion-embed-amd64.zip"
Download-File "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip" $pythonZip
if (-not (Test-Path (Join-Path $pythonDir 'python.exe'))) {
    Expand-Archive -LiteralPath $pythonZip -DestinationPath $pythonDir -Force
    $pthFile = Get-ChildItem -LiteralPath $pythonDir -Filter 'python*._pth' | Select-Object -First 1
    if (-not $pthFile) { throw 'Python runtime configuration was not found.' }
    $pth = Get-Content -LiteralPath $pthFile.FullName
    $pth = $pth | ForEach-Object { if ($_ -eq '#import site') { 'import site' } else { $_ } }
    Set-Content -LiteralPath $pthFile.FullName -Value $pth -Encoding ASCII
}

$pythonExe = Join-Path $pythonDir 'python.exe'
$getPip = Join-Path $downloadDir 'get-pip.py'
Download-File 'https://bootstrap.pypa.io/get-pip.py' $getPip
& $pythonExe $getPip --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'pip bootstrap failed.' }
& $pythonExe -m pip install --disable-pip-version-check --no-warn-script-location -r (Join-Path $projectDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

$caddyZip = Join-Path $downloadDir "caddy-$caddyVersion-windows-amd64.zip"
Download-File "https://github.com/caddyserver/caddy/releases/download/v$caddyVersion/caddy_${caddyVersion}_windows_amd64.zip" $caddyZip
$caddyChecksums = Join-Path $downloadDir "caddy-$caddyVersion-checksums.txt"
Download-File "https://github.com/caddyserver/caddy/releases/download/v$caddyVersion/caddy_${caddyVersion}_checksums.txt" $caddyChecksums
$checksumLine = Get-Content -LiteralPath $caddyChecksums |
    Where-Object { $_ -match "\s+caddy_$([regex]::Escape($caddyVersion))_windows_amd64\.zip$" } |
    Select-Object -First 1
if (-not $checksumLine) { throw 'Caddy checksum was not found in the official checksum file.' }
$expectedChecksum = ($checksumLine -split '\s+', 2)[0].ToUpperInvariant()
$checksumAlgorithm = if ($expectedChecksum.Length -eq 128) { 'SHA512' } elseif ($expectedChecksum.Length -eq 64) { 'SHA256' } else { throw 'Unsupported Caddy checksum format.' }
$actualChecksum = (Get-FileHash -LiteralPath $caddyZip -Algorithm $checksumAlgorithm).Hash
if ($actualChecksum -ne $expectedChecksum) { throw 'Caddy download checksum verification failed.' }
if (-not (Test-Path (Join-Path $caddyDir 'caddy.exe'))) {
    Expand-Archive -LiteralPath $caddyZip -DestinationPath $caddyDir -Force
}
$caddyExe = Join-Path $caddyDir 'caddy.exe'
$pythonSignature = Get-AuthenticodeSignature -LiteralPath $pythonExe
if ($pythonSignature.Status -ne 'Valid') {
    throw "Embedded Python signature is not valid: $($pythonSignature.Status)"
}
$pythonDll = Join-Path $pythonDir 'python312.dll'
$pythonDllSignature = Get-AuthenticodeSignature -LiteralPath $pythonDll
if ($pythonDllSignature.Status -ne 'Valid') {
    throw "Embedded Python DLL signature is not valid: $($pythonDllSignature.Status)"
}

$runtimeCaddyfile = Join-Path $runtimeDir 'Caddyfile'
$caddyDataDir = Join-Path $runtimeDir 'caddy-data'
New-Item -ItemType Directory -Force -Path $caddyDataDir | Out-Null
$caddyDataForConfig = $caddyDataDir.Replace('\', '/')
$caddyText = @"
{
    admin off
    persist_config off
    storage file_system {
        root "$caddyDataForConfig"
    }
}

$domain {
    encode zstd gzip
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        -Server
    }
    reverse_proxy 127.0.0.1:8504
}
"@
Set-Content -LiteralPath $runtimeCaddyfile -Value $caddyText -Encoding ASCII
& $caddyExe validate --config $runtimeCaddyfile --adapter caddyfile
if ($LASTEXITCODE -ne 0) { throw 'Caddy configuration validation failed.' }

$appArgs = '-m streamlit run app.py --server.address 127.0.0.1 --server.port 8504 --server.headless true --browser.gatherUsageStats false'
$appRunner = Join-Path $runtimeDir 'run-app.ps1'
$appLog = Join-Path $logsDir 'app.log'
$appRunnerText = @"
`$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '$($projectDir.Replace("'", "''"))'
& '$($pythonExe.Replace("'", "''"))' $appArgs *>> '$($appLog.Replace("'", "''"))'
exit `$LASTEXITCODE
"@
Set-Content -LiteralPath $appRunner -Value $appRunnerText -Encoding ASCII
$powerShellExe = Join-Path $PSHOME 'powershell.exe'
$appTaskArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$appRunner`""
$appAction = New-ScheduledTaskAction -Execute $powerShellExe -Argument $appTaskArgs -WorkingDirectory $projectDir
$appTrigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $appTaskName -Action $appAction -Trigger $appTrigger -Settings $settings -Principal $principal -Force | Out-Null

$caddyArgs = "run --config `"$runtimeCaddyfile`" --adapter caddyfile"
$caddyRunner = Join-Path $runtimeDir 'run-caddy.ps1'
$caddyLog = Join-Path $logsDir 'caddy.log'
$caddyRunnerText = @"
`$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '$($projectDir.Replace("'", "''"))'
& '$($caddyExe.Replace("'", "''"))' $caddyArgs *>> '$($caddyLog.Replace("'", "''"))'
exit `$LASTEXITCODE
"@
Set-Content -LiteralPath $caddyRunner -Value $caddyRunnerText -Encoding ASCII
$proxyTaskArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$caddyRunner`""
$proxyAction = New-ScheduledTaskAction -Execute $powerShellExe -Argument $proxyTaskArgs -WorkingDirectory $projectDir
$proxyTrigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName $proxyTaskName -Action $proxyAction -Trigger $proxyTrigger -Settings $settings -Principal $principal -Force | Out-Null

Set-Content -LiteralPath $markerFile -Value 'ZzxwxClassProject isolated runtime' -Encoding ASCII
Start-ScheduledTask -TaskName $appTaskName

$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8504/_stcore/health' -TimeoutSec 2
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) {
    Stop-ScheduledTask -TaskName $appTaskName -ErrorAction SilentlyContinue
    throw "Application health check failed. See $appLog"
}

foreach ($port in @(80, 443)) {
    $ruleName = "ZzxwxClassProject-TCP-$port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
    }
}

Start-ScheduledTask -TaskName $proxyTaskName
Write-Host "Deployment complete: https://$domain"
Write-Host "Logs: $logsDir"
Write-Host 'Existing Python installations, port 3008 and unrelated processes were not modified.'
