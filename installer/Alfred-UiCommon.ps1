#Requires -Version 5.1
# Shared helpers for installer GUI modules.

function Get-AlfredInstallerRoot {
    if ($PSScriptRoot) { return $PSScriptRoot }
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath)) {
        $parent = Split-Path -Parent $cmdPath
        if ($parent) { return $parent }
    }
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe)) {
            $parent = Split-Path -Parent $exe
            if ($parent) { return $parent }
        }
    } catch { }
    return (Get-Location).Path
}

function Get-AlfredBrandIcon([string]$Root) {
    if ([string]::IsNullOrWhiteSpace($Root)) { return $null }
    foreach ($rel in @('assets\alfred.ico', 'assets\alfred-source.png', 'assets\alfred.png')) {
        $path = Join-Path $Root $rel
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Get-AlfredExePath {
    $cmdPath = $MyInvocation.MyCommand.Path
    if (-not [string]::IsNullOrWhiteSpace($cmdPath) -and $cmdPath -like '*.exe' -and (Test-Path $cmdPath)) {
        return $cmdPath
    }
    try {
        $exe = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if (-not [string]::IsNullOrWhiteSpace($exe) -and (Test-Path $exe)) { return $exe }
    } catch { }
    return $null
}

function Get-AlfredBrandImage([string]$Root) {
    $path = Get-AlfredBrandIcon $Root
    if ($path) {
        if ($path -like '*.ico') {
            return [System.Drawing.Icon]::ExtractAssociatedIcon($path).ToBitmap()
        }
        return [System.Drawing.Image]::FromFile($path)
    }
    $exePath = Get-AlfredExePath
    if ($exePath) {
        try { return [System.Drawing.Icon]::ExtractAssociatedIcon($exePath).ToBitmap() } catch { }
    }
    return $null
}

function Set-AlfredFormIcon([System.Windows.Forms.Form]$Form, [string]$Root) {
    $iconPath = Get-AlfredBrandIcon $Root
    if ($iconPath) {
        try { $Form.Icon = New-Object System.Drawing.Icon($iconPath); return } catch { }
    }
    $exePath = Get-AlfredExePath
    if ($exePath) {
        try { $Form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($exePath); return } catch { }
    }
}
