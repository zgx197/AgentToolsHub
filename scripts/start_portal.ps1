param(
    [int]$Port = 8765,
    [string]$Python = "python",
    [switch]$NoBrowser
)

function Test-PortOpen {
    param([int]$TestPort)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect("127.0.0.1", $TestPort, $null, $null)
        $connected = $iar.AsyncWaitHandle.WaitOne(250)
        if (-not $connected) {
            return $false
        }

        $client.EndConnect($iar) | Out-Null
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$hubRoot = Split-Path -Parent $scriptDir
$portalUrl = "http://127.0.0.1:$Port/apps/portal/"
$serverProcess = $null

$serverAlreadyRunning = Test-PortOpen -TestPort $Port
if (-not $serverAlreadyRunning) {
    $serveCommand = ('Set-Location -LiteralPath "{0}"; {1} -m http.server {2}' -f $hubRoot, $Python, $Port)
    $serverProcess = Start-Process -FilePath "powershell" -PassThru -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $serveCommand
    )

    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        if (Test-PortOpen -TestPort $Port) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        Write-Error ("Local static server failed to start on port {0}." -f $Port)
        exit 1
    }
}

Write-Host ("HubRoot: {0}" -f $hubRoot)
Write-Host ("Portal: {0}" -f $portalUrl)

if ($serverAlreadyRunning) {
    Write-Host ("Reusing existing server on port {0}." -f $Port)
}
else {
    Write-Host "Started local static server."
    if ($serverProcess) {
        Write-Host ("ServerPid: {0}" -f $serverProcess.Id)
    }
}

if (-not $NoBrowser) {
    Start-Process $portalUrl | Out-Null
}
