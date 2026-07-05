#Requires -Version 5.1
# Shared repo tool installs - npm manifest, optional CLIs (used by Alfred-Install.ps1).

function Get-AlfredNpmToolList {
    param([string]$RepoRoot)

    $file = Join-Path $RepoRoot 'requirements\npm-tools.txt'
    $list = @()
    if (-not (Test-Path $file)) { return $list }

    Get-Content $file | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } | ForEach-Object {
        $parts = $_ -split ':', 3
        if ($parts.Count -ge 2) {
            $list += [PSCustomObject]@{
                Package     = $parts[0].Trim()
                Command     = $parts[1].Trim()
                Description = if ($parts.Count -ge 3) { $parts[2].Trim() } else { $parts[0].Trim() }
            }
        }
    }
    return $list
}

function Install-AlfredNpmTools {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $npmExe = Find-Command 'npm'
    if (-not $npmExe) {
        Write-Warn 'npm not available - skipping npm CLI tools from requirements/npm-tools.txt.'
        return @{}
    }

    $npmGlobal = & $npmExe prefix -g 2>$null | Select-Object -First 1
    if ($npmGlobal) { Add-PathEntry $npmGlobal.Trim() }

    $status = @{}
    $tools = Get-AlfredNpmToolList -RepoRoot $RepoRoot
    if ($tools.Count -eq 0) {
        Write-Warn 'requirements/npm-tools.txt missing or empty - no npm tools installed.'
        return $status
    }

    foreach ($tool in $tools) {
        $toolExe = Find-Command $tool.Command
        if ($toolExe) {
            $ver = & $toolExe --version 2>&1 | Select-Object -First 1
            Write-OK ($tool.Description + ' - ' + $ver)
            $status[$tool.Command] = $true
            continue
        }

        if (Test-AlfredGuiInstall) {
            $script:InstallProgress.SetDetail('Installing ' + $tool.Description + '...')
        } else {
            Write-Host ('  Installing ' + $tool.Description + ' via npm install -g ' + $tool.Package + '...') -ForegroundColor Cyan
        }

        if (Test-AlfredGuiInstall -and $script:AlfredInstallLogPath) {
            $exit = Invoke-InstallExternal -FilePath $npmExe -ArgumentList @('install', '-g', $tool.Package) `
                -StatusMessage ('Installing ' + $tool.Description + '...')
        } else {
            & $npmExe install -g $tool.Package
            $exit = $LASTEXITCODE
        }

        Refresh-Path
        if ($exit -eq 0 -and (Find-Command $tool.Command)) {
            Write-Done ($tool.Description + ' installed.')
            $status[$tool.Command] = $true
        } else {
            Write-Warn ($tool.Description + ' install failed or not on PATH - run: npm install -g ' + $tool.Package)
            $status[$tool.Command] = $false
        }
    }

    return $status
}

function Install-AlfredVenvPostSetup {
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPath
    )

    $venvScripts = Join-Path $VenvPath 'Scripts'
    if (Test-Path $venvScripts) {
        Add-PathEntry $venvScripts | Out-Null
        Write-OK ('Alfred venv Scripts on user PATH - ' + $venvScripts)
    }

    $xlwingsExe = Join-Path $venvScripts 'xlwings.exe'
    if (Test-Path $xlwingsExe) {
        try {
            if (Test-AlfredGuiInstall -and $script:AlfredInstallLogPath) {
                $xlExit = Invoke-InstallExternal -FilePath $xlwingsExe -ArgumentList @('addin', 'install') `
                    -StatusMessage 'Registering xlwings Excel add-in...'
            } else {
                & $xlwingsExe addin install 2>&1 | Out-Null
                $xlExit = $LASTEXITCODE
            }
            if ($xlExit -eq 0) {
                Write-Done 'xlwings Excel add-in registered.'
            } else {
                Write-Warn 'xlwings add-in registration skipped (non-fatal).'
            }
        } catch {
            Write-Warn ('xlwings add-in registration skipped: ' + $_.Exception.Message)
        }
    }
}

function Install-AlfredOptionalCliTools {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallPath,
        [string]$VenvPath
    )

    $binDir = Join-Path $InstallPath 'bin'
    if (-not (Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir -Force | Out-Null }
    Add-PathEntry $binDir | Out-Null

    if (Find-Command 'jq') {
        Write-OK ('jq - ' + (& jq --version 2>&1 | Select-Object -First 1))
    } elseif (Find-Command 'winget') {
        if (Test-AlfredGuiInstall) { $script:InstallProgress.SetDetail('Installing jq...') }
        winget install jqlang.jq --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Refresh-Path
        if (Find-Command 'jq') { Write-Done 'jq installed.' }
        else { Write-Warn 'jq install skipped - run: winget install jqlang.jq' }
    }

    if (Find-Command 'pandoc') {
        Write-OK ('pandoc - ' + (& pandoc --version 2>&1 | Select-Object -First 1))
    } elseif (Find-Command 'winget') {
        if (Test-AlfredGuiInstall) { $script:InstallProgress.SetDetail('Installing pandoc...') }
        winget install JohnMacFarlane.Pandoc --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Refresh-Path
        if (Find-Command 'pandoc') { Write-Done 'pandoc installed.' }
        else { Write-Warn 'pandoc install skipped - run: winget install JohnMacFarlane.Pandoc' }
    }

    $ghExe = Join-Path $binDir 'gh.exe'
    if ((Find-Command 'gh') -or (Test-Path $ghExe)) {
        $ghBin = if (Test-Path $ghExe) { $ghExe } else { 'gh' }
        Write-OK ('gh - ' + (& $ghBin --version 2>&1 | Select-Object -First 1))
    } else {
        if (Test-AlfredGuiInstall) { $script:InstallProgress.SetDetail('Installing GitHub CLI (portable)...') }
        try {
            $release = Invoke-RestMethod 'https://api.github.com/repos/cli/cli/releases/latest' -UseBasicParsing -ErrorAction Stop
            $ghVersion = $release.tag_name -replace '^v', ''
            $ghUrl = 'https://github.com/cli/cli/releases/download/v' + $ghVersion + '/gh_' + $ghVersion + '_windows_amd64.zip'
            $zipPath = Join-Path $env:TEMP 'gh_portable.zip'
            $extractDir = Join-Path $env:TEMP 'gh_portable_extract'
            Invoke-WebRequest -Uri $ghUrl -OutFile $zipPath -UseBasicParsing -ErrorAction Stop
            if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
            Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
            $src = Get-ChildItem -Path $extractDir -Filter 'gh.exe' -Recurse | Select-Object -First 1
            if ($src) {
                Copy-Item $src.FullName $ghExe -Force
                Write-Done ('gh CLI ' + $ghVersion + ' installed to Alfred\bin\')
            } else {
                Write-Warn 'gh.exe not found in downloaded archive.'
            }
            Remove-Item $zipPath, $extractDir -Recurse -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Warn ('gh portable install failed: ' + $_)
        }
    }

    $excelMcpDir = Join-Path $binDir 'excel-mcp'
    $excelMcpExe = Join-Path $excelMcpDir 'mcp-excel.exe'
    if (Test-Path $excelMcpExe) {
        Write-OK 'excel-mcp - present in Alfred/bin/excel-mcp/'
    } else {
        if (Test-AlfredGuiInstall) { $script:InstallProgress.SetDetail('Installing ExcelMcp server (portable)...') }
        try {
            $emRelease = Invoke-RestMethod 'https://api.github.com/repos/sbroenne/mcp-server-excel/releases/latest' -UseBasicParsing -ErrorAction Stop
            $emAsset = $emRelease.assets | Where-Object { $_.name -match '^ExcelMcp-MCP-Server-.*-windows\.zip$' } | Select-Object -First 1
            if (-not $emAsset) { throw 'ExcelMcp windows zip asset not found.' }
            $emZip = Join-Path $env:TEMP 'excelmcp_server.zip'
            $emExtractDir = Join-Path $env:TEMP 'excelmcp_server_extract'
            Invoke-WebRequest -Uri $emAsset.browser_download_url -OutFile $emZip -UseBasicParsing -ErrorAction Stop
            if (Test-Path $emExtractDir) { Remove-Item $emExtractDir -Recurse -Force }
            Expand-Archive -Path $emZip -DestinationPath $emExtractDir -Force
            $emSrc = Get-ChildItem -Path $emExtractDir -Filter 'mcp-excel.exe' -Recurse | Select-Object -First 1
            if ($emSrc) {
                if (-not (Test-Path $excelMcpDir)) { New-Item -ItemType Directory -Path $excelMcpDir -Force | Out-Null }
                Copy-Item $emSrc.FullName $excelMcpExe -Force
                Write-Done ('ExcelMcp ' + $emRelease.tag_name + ' installed to Alfred/bin/excel-mcp/')
            } else {
                Write-Warn 'mcp-excel.exe not found in downloaded archive.'
            }
            Remove-Item $emZip, $emExtractDir -Recurse -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Warn ('ExcelMcp portable install failed: ' + $_)
        }
    }

    $azVenv = @(
        (Join-Path $VenvPath 'Scripts\az.cmd'),
        (Join-Path $VenvPath 'Scripts\az.bat'),
        (Join-Path $VenvPath 'Scripts\az')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ((Find-Command 'az') -or $azVenv) {
        $azBin = if (Find-Command 'az') { 'az' } else { $azVenv }
        Write-OK ('az - ' + (& $azBin version 2>&1 | Select-Object -First 1))
    } elseif (Find-Command 'winget') {
        if (Test-AlfredGuiInstall) { $script:InstallProgress.SetDetail('Installing Azure CLI...') }
        winget install Microsoft.AzureCLI --scope user --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        Refresh-Path
        if (Find-Command 'az') { Write-Done 'Azure CLI installed.' }
        else { Write-Warn 'Azure CLI skipped - Alfred works without it.' }
    }
}
