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

function Set-AlfredNodeCaCert {
    <#
    .SYNOPSIS
        Make Node.js trust the Windows certificate store so npx/npm/MCP servers
        work behind a corporate TLS-intercepting proxy (Zscaler, Netskope, etc.).
    .DESCRIPTION
        Node ships its own CA bundle and ignores the Windows cert store. On
        machines where a corporate proxy re-signs HTTPS, the handshake fails with
        UNABLE_TO_GET_ISSUER_CERT_LOCALLY and mcp-remote / startup-handshake MCP
        servers die the moment they launch (seen with parallel-search on a
        Zscaler'd Maersk laptop). This exports every currently-valid trusted root
        from the Windows store into a combined PEM and points NODE_EXTRA_CA_CERTS
        at it (User + Process scope). Vendor-agnostic: it trusts exactly what
        Windows already trusts. Idempotent -- refreshes the PEM in place each run.
        Returns $true if the bundle was written.
    #>
    param(
        [string]$CertDir = (Join-Path $env:USERPROFILE ".local\certs"),
        [scriptblock]$OnStep = { param($Msg) Write-Host "  $Msg" -ForegroundColor Cyan }
    )

    try {
        $pemPath = Join-Path $CertDir "windows-roots.pem"
        New-Item -ItemType Directory -Force $CertDir -ErrorAction SilentlyContinue | Out-Null

        $roots = @()
        foreach ($store in @("Cert:\CurrentUser\Root", "Cert:\LocalMachine\Root")) {
            $roots += Get-ChildItem $store -ErrorAction SilentlyContinue
        }
        $now = Get-Date
        $roots = $roots |
            Where-Object { $_.RawData -and $_.NotAfter -gt $now -and $_.NotBefore -le $now } |
            Sort-Object Thumbprint -Unique

        if (-not $roots -or @($roots).Count -eq 0) {
            & $OnStep "No root certificates found to export -- skipping Node CA setup."
            return $false
        }

        $lines = New-Object System.Collections.Generic.List[string]
        foreach ($c in $roots) {
            $lines.Add("# " + $c.Subject)
            $lines.Add("-----BEGIN CERTIFICATE-----")
            $lines.Add([Convert]::ToBase64String($c.RawData, 'InsertLineBreaks'))
            $lines.Add("-----END CERTIFICATE-----")
        }
        Set-Content -Path $pemPath -Value $lines -Encoding ascii

        [System.Environment]::SetEnvironmentVariable("NODE_EXTRA_CA_CERTS", $pemPath, "User")
        $env:NODE_EXTRA_CA_CERTS = $pemPath

        # Name known TLS-interception vendors so the log line is informative.
        $vendorPattern = "Zscaler|Netskope|Palo Alto|Cisco Umbrella|Forcepoint|Blue Coat|Broadcom|Fortinet|McAfee|Skyhigh|Menlo|Cloudflare Gateway"
        $mitm = $roots |
            Where-Object { $_.Subject -match $vendorPattern } |
            ForEach-Object { ([regex]::Match($_.Subject, $vendorPattern)).Value } |
            Select-Object -Unique
        if ($mitm) {
            & $OnStep ("Corporate TLS proxy detected (" + ($mitm -join ', ') + ") -- Node will now trust it.")
        }
        & $OnStep ("Node CA bundle written ($(@($roots).Count) roots) -> NODE_EXTRA_CA_CERTS")
        return $true
    } catch {
        & $OnStep ("Node CA setup skipped: " + $_.Exception.Message)
        return $false
    }
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
