param(
    [string]$RepoPath = (Get-Location).Path,
    [ValidateSet("current-project", "workspace")]
    [string]$Mode = "current-project",
    [ValidateSet("detailed", "brief", "both")]
    [string]$Detail = "both",
    [ValidateSet("markdown", "json")]
    [string]$Format = "markdown",
    [string]$DiscoverRoot = "",
    [string]$Author = "",
    [string]$Since = "",
    [string]$Until = "",
    [string]$Python = "python"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$hubRoot = Split-Path -Parent $scriptDir
$runner = Join-Path $hubRoot "capabilities\workspace-daily-report\core\generate_daily_report.py"

if (-not (Test-Path $runner)) {
    Write-Error "找不到日报脚本: $runner"
    exit 1
}

$resolvedRepoPath = (Resolve-Path $RepoPath).Path
$args = @(
    $runner,
    "--mode", $Mode,
    "--detail", $Detail,
    "--format", $Format,
    "--cwd", $resolvedRepoPath
)

if ($DiscoverRoot) {
    $args += @("--discover-root", (Resolve-Path $DiscoverRoot).Path)
}

if ($Author) {
    $args += @("--author", $Author)
}

if ($Since) {
    $args += @("--since", $Since)
}

if ($Until) {
    $args += @("--until", $Until)
}

Write-Host "RepoPath: $resolvedRepoPath"
Write-Host "Mode: $Mode | Detail: $Detail | Format: $Format"
Write-Host "Runner: $runner"

Push-Location $resolvedRepoPath
try {
    & $Python @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
