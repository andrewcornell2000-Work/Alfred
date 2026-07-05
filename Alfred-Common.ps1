#Requires -Version 5.1
<#
.SYNOPSIS
    Shared PowerShell helpers for Alfred setup and installer scripts.
.DESCRIPTION
    Dot-sourced by setup.ps1 and Alfred-Install.ps1. Inlined into Alfred-Install.exe
    by build-installer.ps1 at the # ALFRED_COMMON_INLINE marker.
#>

function Find-Command([string]$Name) {
    foreach ($candidate in @("$Name.cmd", "$Name.exe", "$Name.bat", $Name)) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandType -ne "Alias" } |
            Select-Object -First 1
        if ($null -ne $cmd) { return $cmd.Source }
    }
    return $null
}

function Get-PythonExe {
    $candidatePaths = @()
    foreach ($candidate in @("py.exe", "python.exe", "python3.exe", "py", "python", "python3")) {
        $cmd = Find-Command $candidate
        if ($cmd) { $candidatePaths += $cmd }
    }
    foreach ($root in @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles",
        "${env:ProgramFiles(x86)}"
    )) {
        if ($root -and (Test-Path $root)) {
            $candidatePaths += @(
                Get-ChildItem -Path $root -Directory -Filter "Python3*" -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending |
                    ForEach-Object {
                        $exe = Join-Path $_.FullName "python.exe"
                        if (Test-Path $exe) { $exe }
                    }
            )
        }
    }
    foreach ($regRoot in @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )) {
        if (Test-Path $regRoot) {
            $candidatePaths += @(
                Get-ChildItem $regRoot -ErrorAction SilentlyContinue |
                    Sort-Object PSChildName -Descending |
                    ForEach-Object {
                        $install = Get-ItemProperty "$($_.PSPath)\InstallPath" -ErrorAction SilentlyContinue
                        $exes = @()
                        if ($install.ExecutablePath) { $exes += $install.ExecutablePath }
                        if ($install.'(default)') { $exes += (Join-Path $install.'(default)' "python.exe") }
                        foreach ($exe in $exes) {
                            if ($exe -and (Test-Path $exe)) { $exe }
                        }
                    }
            )
        }
    }

    $orderedCandidates = @($candidatePaths | Where-Object { $_ -notlike "*\Microsoft\WindowsApps\*" } | Select-Object -Unique)
    $orderedCandidates += @($candidatePaths | Where-Object { $_ -like "*\Microsoft\WindowsApps\*" } | Select-Object -Unique)
    foreach ($cmd in $orderedCandidates) {
        if (-not $cmd) { continue }
        $isLauncher = [IO.Path]::GetFileNameWithoutExtension($cmd) -eq "py"
        $args = if ($isLauncher) { @("-3", "--version") } else { @("--version") }
        $output = & $cmd @args 2>&1 | Select-Object -First 1
        if ("$output" -match "^Python\s+3\.(1[0-9])\.") {
            return [PSCustomObject]@{
                Exe      = $cmd
                VenvArgs = if ($isLauncher) { @("-3", "-m", "venv") } else { @("-m", "venv") }
                Version  = "$output"
            }
        }
    }
    return $null
}

function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

function Add-ProcessPathEntry([string]$PathEntry) {
    if ([string]::IsNullOrWhiteSpace($PathEntry) -or -not (Test-Path $PathEntry)) {
        return $false
    }

    $currentParts = @($env:PATH -split ';' | Where-Object { $_ })
    if (-not ($currentParts | Where-Object { $_.TrimEnd('\') -ieq $PathEntry.TrimEnd('\') })) {
        $env:PATH = "$PathEntry;$env:PATH"
    }

    return $true
}

function Add-PathEntry([string]$PathEntry) {
    if ([string]::IsNullOrWhiteSpace($PathEntry) -or -not (Test-Path $PathEntry)) {
        return $false
    }

    $currentParts = @($env:PATH -split ';' | Where-Object { $_ })
    if (-not ($currentParts | Where-Object { $_.TrimEnd('\') -ieq $PathEntry.TrimEnd('\') })) {
        $env:PATH = "$PathEntry;$env:PATH"
    }

    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    $userParts = @($userPath -split ';' | Where-Object { $_ })
    if (-not ($userParts | Where-Object { $_.TrimEnd('\') -ieq $PathEntry.TrimEnd('\') })) {
        $updatedUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
            $PathEntry
        } else {
            "$userPath;$PathEntry"
        }
        [System.Environment]::SetEnvironmentVariable("PATH", $updatedUserPath, "User")
    }

    return $true
}
