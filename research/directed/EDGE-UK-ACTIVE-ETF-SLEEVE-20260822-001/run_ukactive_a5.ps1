[CmdletBinding()]
param(
    [ValidateSet("auto", "setup", "signal", "execute", "telemetry", "report")]
    [string]$Mode = "auto",
    [string]$Asof = "latest",
    [switch]$NoCommitPush,
    [switch]$JsonSummary
)

$programmeRoot = $PSScriptRoot
$runnerPath = Join-Path $programmeRoot "code\run_ukactive_a5_shadow.py"
$runnerArgs = @($runnerPath, "--mode", $Mode, "--asof", $Asof)

if (-not $NoCommitPush -and $Mode -ne "setup" -and $Mode -ne "report") {
    $runnerArgs += "--commit-push"
}
if ($JsonSummary) {
    $runnerArgs += "--json-summary"
}

& python @runnerArgs
exit $LASTEXITCODE
