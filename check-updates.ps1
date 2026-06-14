#Requires -Version 5.1
<#
.SYNOPSIS
    Checks whether the local Alfred repo is behind origin/main and offers to pull.
.DESCRIPTION
    Runs git fetch, compares HEAD with origin/main, and prompts the user if updates
    exist. Never auto-pulls — user approval is always required.
    Safe to run offline; fetch failure is a silent no-op.
.OUTPUTS
    Exit 0  -- no updates available, user declined, or check could not complete.
    Exit 10 -- updates were pulled; caller should re-run setup.ps1 to apply them.
#>

$Root = $PSScriptRoot

if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    exit 0
}

Write-Host ""
Write-Host "Checking for Alfred updates..." -ForegroundColor Cyan

# Fetch quietly; if offline or remote unreachable, skip the check
$fetchOut = git -C $Root fetch origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  (Could not reach GitHub -- skipping update check)" -ForegroundColor DarkGray
    exit 0
}

$localHead  = (git -C $Root rev-parse HEAD           2>&1).Trim()
$remoteHead = (git -C $Root rev-parse origin/main    2>&1).Trim()

if ($localHead -eq $remoteHead) {
    Write-Host "  Alfred is up to date." -ForegroundColor Green
    exit 0
}

$behind    = (git -C $Root rev-list --count "HEAD..origin/main" 2>&1).Trim()
$commitLog =  git -C $Root log --oneline "HEAD..origin/main"   2>&1

Write-Host ""
Write-Host "  Updates available: $behind new commit(s) on origin/main." -ForegroundColor Yellow
Write-Host ""
Write-Host "  What's new:" -ForegroundColor White
$commitLog | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkYellow }
Write-Host ""

$response = Read-Host "  Pull updates now? [Y/N]"
if ($response -notmatch "^[Yy]") {
    Write-Host "  Skipping update." -ForegroundColor DarkGray
    exit 0
}

Write-Host "  Pulling updates..." -ForegroundColor Cyan
git -C $Root pull origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Updates applied. Setup will re-run to apply any new requirements." -ForegroundColor Green
    exit 10
} else {
    Write-Host "  Pull failed. Resolve any issues above and try again." -ForegroundColor Red
    exit 0
}
