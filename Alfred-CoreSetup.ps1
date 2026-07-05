#Requires -Version 5.1
<#
.SYNOPSIS
    Shared Python venv + pip install used by setup.ps1 and Alfred-Install.ps1.
#>

function Install-AlfredPythonEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        $PythonInfo,
        [scriptblock]$OnStep = { param($Msg) Write-Host "  $Msg" -ForegroundColor Cyan }
    )

    $VenvPath = Join-Path $RepoRoot '.venv'
    $PipExe = Join-Path $VenvPath 'Scripts\pip.exe'
    $ReqFile = Join-Path $RepoRoot 'requirements\python-requirements.txt'

    if (-not (Test-Path $VenvPath)) {
        & $OnStep 'Creating virtual environment...'
        & $PythonInfo.Exe @($PythonInfo.VenvArgs + @($VenvPath))
        if ($LASTEXITCODE -ne 0) {
            return [PSCustomObject]@{ Ok = $false; VenvPath = $VenvPath; PipExe = $PipExe; Message = 'Could not create .venv.' }
        }
    }

    if (-not (Test-Path $PipExe)) {
        return [PSCustomObject]@{ Ok = $false; VenvPath = $VenvPath; PipExe = $PipExe; Message = 'pip not found in .venv.' }
    }

    & $OnStep 'Installing Python packages...'
    $failed = @()
    if (Test-Path $ReqFile) {
        Get-Content $ReqFile | ForEach-Object {
            $pkg = $_.Trim()
            if ($pkg -and -not $pkg.StartsWith('#')) {
                & $PipExe install --quiet --disable-pip-version-check $pkg
                if ($LASTEXITCODE -ne 0) { $failed += $pkg }
            }
        }
    } else {
        & $PipExe install --quiet --disable-pip-version-check openai rich python-dotenv typer
    }

    return [PSCustomObject]@{
        Ok       = $true
        VenvPath = $VenvPath
        PipExe   = $PipExe
        Failed   = $failed
    }
}
