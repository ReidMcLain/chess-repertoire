[CmdletBinding()]
param([int]$WaitMinutes = 1440)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$parentDirectory = Split-Path -Parent $projectRoot
$destination = Join-Path $parentDirectory 'TheoryVault'
$logName = 'TheoryVault-rebrand.log'
$python = (Get-Command python -ErrorAction Stop).Source

function Write-Status([string]$Message) {
    Add-Content -LiteralPath (Join-Path $projectRoot $logName) -Value "$(Get-Date -Format s) $Message"
}

try {
    # Keep this helper's working directory outside the folder being renamed.
    Set-Location -LiteralPath $parentDirectory
    if ($projectRoot -ne $destination) {
        if (Test-Path -LiteralPath $destination) {
            throw "Destination already exists; refusing to overwrite: $destination"
        }
        $resolvedSource = (Resolve-Path -LiteralPath $projectRoot).ProviderPath
        if ($resolvedSource -ne $projectRoot -or
            (Split-Path -Parent $destination) -ne (Split-Path -Parent $resolvedSource)) {
            throw 'Unexpected source or destination for folder rename'
        }
        Write-Status 'Waiting for the project folder to be released by open applications.'
        $deadline = (Get-Date).AddMinutes($WaitMinutes)
        while ($true) {
            try {
                Rename-Item -LiteralPath $resolvedSource -NewName 'TheoryVault' -ErrorAction Stop
                break
            }
            catch [System.IO.IOException] {
                # Retry only Windows sharing/lock violations, not other I/O failures.
                $code = $_.Exception.HResult -band 0xFFFF
                if ($code -notin @(32, 33) -or (Get-Date) -ge $deadline) { throw }
                Start-Sleep -Seconds 3
            }
        }
        $projectRoot = $destination
    }
    Write-Status 'Folder is now TheoryVault. Refreshing launchers and cached paths.'
    Set-Location -LiteralPath $projectRoot
    & $python packaging\refresh_launchers.py 2>&1 | Out-File -LiteralPath (Join-Path $projectRoot $logName) -Append
    if ($LASTEXITCODE -ne 0) { throw 'Refreshing Python launchers failed' }

    $requiredPrefix = $projectRoot.TrimEnd('\') + '\'
    $caches = @(Get-ChildItem -LiteralPath $projectRoot -Directory -Recurse -Force -Filter '__pycache__' |
        Where-Object { $_.FullName -notlike '*\.git\*' } |
        Sort-Object { $_.FullName.Length } -Descending)
    foreach ($cache in $caches) {
        $fullPath = [System.IO.Path]::GetFullPath($cache.FullName)
        if (-not $fullPath.StartsWith($requiredPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            ($cache.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to remove unexpected cache path: $fullPath"
        }
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }

    Write-Status 'Running tests and rebuilding the executable and release archive.'
    $build = Start-Process -FilePath powershell.exe -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1 -Version v1.0 -SkipDependencyInstall' `
        -WorkingDirectory $projectRoot `
        -RedirectStandardOutput (Join-Path $projectRoot 'TheoryVault-build.log') `
        -RedirectStandardError (Join-Path $projectRoot 'TheoryVault-build-errors.log')
    if ($build.ExitCode -ne 0) { throw 'The Windows build failed; see TheoryVault-build logs' }
    $metadata = (Get-Item -LiteralPath (Join-Path $projectRoot 'dist\TheoryVault\TheoryVault.exe')).VersionInfo
    if ($metadata.ProductName -ne 'TheoryVault' -or $metadata.FileDescription -ne 'TheoryVault' -or
        $metadata.InternalName -ne 'TheoryVault' -or $metadata.OriginalFilename -ne 'TheoryVault.exe') {
        throw 'Executable branding validation failed'
    }
    Write-Status 'COMPLETE: folder renamed, launchers refreshed, tests passed, release rebuilt, and executable metadata verified.'
}
catch {
    Write-Status "FAILED: $($_.Exception.Message)"
    exit 1
}
