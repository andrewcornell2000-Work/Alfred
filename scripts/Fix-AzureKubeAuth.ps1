#Requires -Version 5.1
<#
.SYNOPSIS
    Convert AKS kubeconfig from device-code auth to kubelogin + Azure CLI.
.DESCRIPTION
    Corporate Conditional Access is disabling device-code authentication.
    IT remediation: kubelogin convert-kubeconfig -l azurecli

    This script:
      1. Installs kubelogin via winget if missing
      2. Converts ~/.kube/config when present
      3. Prints hard rules (never az login --use-device-code)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Fix-AzureKubeAuth.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Write-Head([string]$m) { Write-Host ""; Write-Host "== $m" -ForegroundColor Cyan }
function Write-Ok([string]$m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Write-Warn2([string]$m){ Write-Host "  [WARN] $m" -ForegroundColor Yellow }
function Write-Fail([string]$m) { Write-Host "  [FAIL] $m" -ForegroundColor Red }
function Write-Note([string]$m) { Write-Host "         $m" -ForegroundColor DarkGray }

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = (($machine, $user) | Where-Object { $_ }) -join ";"
}

function Test-Cmd([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Head "Azure / AKS auth remediation (no device-code)"

Write-Host ""
Write-Host "  Hard rules:" -ForegroundColor Yellow
Write-Note "Never use:  az login --use-device-code"
Write-Note "Do use:     az login   (browser / company MAZAL SSO)"
Write-Note "CI/CD:      service principal or managed/workload identity — not a user account"
Write-Host ""

# ── kubelogin ────────────────────────────────────────────────────────────────
if (-not (Test-Cmd "kubelogin")) {
    if (Test-Cmd "winget") {
        Write-Host "  Installing kubelogin via winget..." -ForegroundColor Cyan
        winget install --id Microsoft.Azure.Kubelogin --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Refresh-Path
    }
}

if (-not (Test-Cmd "kubelogin")) {
    # Older / alternate winget id
    if (Test-Cmd "winget") {
        winget install --id Azure.kubelogin --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Refresh-Path
    }
}

if (-not (Test-Cmd "kubelogin")) {
    Write-Fail "kubelogin not found on PATH."
    Write-Note "Install manually: https://github.com/Azure/kubelogin/releases"
    Write-Note "Then re-run this script."
    exit 2
}

$klVer = & kubelogin --version 2>&1 | Select-Object -First 1
Write-Ok "kubelogin -- $klVer"

# ── kubeconfig convert ───────────────────────────────────────────────────────
$kubeConfig = Join-Path $env:USERPROFILE ".kube\config"
if (-not (Test-Path $kubeConfig)) {
    Write-Warn2 "No kubeconfig at $kubeConfig"
    Write-Note "If you use AKS, get credentials first:"
    Write-Note "  az login"
    Write-Note "  az aks get-credentials --resource-group <rg> --name <cluster> --overwrite-existing"
    Write-Note "  powershell -ExecutionPolicy Bypass -File scripts\Fix-AzureKubeAuth.ps1"
    Write-Host ""
    Write-Note "Login guidance still applies: never --use-device-code."
    exit 1
}

Write-Host "  Converting kubeconfig (kubelogin -l azurecli)..." -ForegroundColor Cyan
& kubelogin convert-kubeconfig -l azurecli
if ($LASTEXITCODE -ne 0) {
    Write-Fail "kubelogin convert-kubeconfig failed (exit $LASTEXITCODE)."
    exit 3
}

Write-Ok "kubeconfig converted to kubelogin + azurecli login method"
Write-Note "Next: az login (browser/SSO), then kubectl get ns to verify."
Write-Host ""
exit 0
