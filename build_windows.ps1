[CmdletBinding()]
param(
    [string]$Version = "",
    [switch]$SkipDependencyInstall,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = [System.IO.Path]::GetFullPath($projectRoot)

function Confirm-LastCommand([string]$Description) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Remove-BuildDirectory([string]$Path) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $requiredPrefix = $projectRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($requiredPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the project: $fullPath"
    }
    if (Test-Path -LiteralPath $fullPath) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
}

Push-Location $projectRoot
try {
    if (-not $Version) {
        if ($env:GITHUB_REF_NAME -and $env:GITHUB_REF_NAME -match '^v\d+\.\d+(?:\.\d+)?$') {
            $Version = $env:GITHUB_REF_NAME
        }
        elseif (Get-Command git -ErrorAction SilentlyContinue) {
            $exactTag = & git describe --tags --exact-match 2>$null
            if ($LASTEXITCODE -eq 0 -and $exactTag -match '^v\d+\.\d+(?:\.\d+)?$') {
                $Version = $exactTag
            }
        }
        if (-not $Version) {
            $Version = "v1.0"
        }
    }

    if ($Version -notmatch '^v?\d+\.\d+(?:\.\d+)?$') {
        throw "Version must look like v1.0, v1.0.1, 1.1.0, or 2.0.0. Received: $Version"
    }
    if (-not $Version.StartsWith("v")) {
        $Version = "v$Version"
    }
    $numericVersion = $Version.Substring(1)

    if ($SkipDependencyInstall) {
        $python = (Get-Command python -ErrorAction Stop).Source
    }
    else {
        $buildEnvironment = Join-Path $projectRoot ".build-venv"
        $python = Join-Path $buildEnvironment "Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python)) {
            $basePython = (Get-Command python -ErrorAction Stop).Source
            & $basePython -m venv $buildEnvironment
            Confirm-LastCommand "Creating the build virtual environment"
        }
        & $python -m pip install --upgrade pip
        Confirm-LastCommand "Upgrading pip"
        & $python -m pip install -r requirements.txt -r requirements-build.txt
        Confirm-LastCommand "Installing build dependencies"
    }

    if (-not $SkipTests) {
        & $python -m unittest discover -s tests -v
        Confirm-LastCommand "Automated tests"
    }

    Remove-BuildDirectory (Join-Path $projectRoot "build")
    Remove-BuildDirectory (Join-Path $projectRoot "dist")
    Remove-BuildDirectory (Join-Path $projectRoot "release")

    $runtimeDirectory = Join-Path $projectRoot "build\runtime"
    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $versionResource = Join-Path $runtimeDirectory "VERSION"
    Set-Content -LiteralPath $versionResource -Value $numericVersion -Encoding ascii

    $env:CRM_BUILD_VERSION = $numericVersion
    $env:CRM_VERSION_RESOURCE = $versionResource
    & $python -m PyInstaller --clean --noconfirm chess-repertoire.spec
    Confirm-LastCommand "PyInstaller"

    $distributionDirectory = Join-Path $projectRoot "dist\Chess Repertoire Memorizer"
    $builtExecutable = Join-Path $distributionDirectory "Chess Repertoire Memorizer.exe"
    if (-not (Test-Path -LiteralPath $builtExecutable)) {
        throw "PyInstaller did not create the expected executable: $builtExecutable"
    }

    & $python packaging\inspect_build.py $distributionDirectory
    Confirm-LastCommand "Packaged-resource inspection"

    $previousLocalAppData = $env:LOCALAPPDATA
    $smokeLocalAppData = Join-Path $projectRoot "build\smoke-localappdata"
    New-Item -ItemType Directory -Path $smokeLocalAppData -Force | Out-Null
    try {
        $env:LOCALAPPDATA = $smokeLocalAppData
        $smokeProcess = Start-Process `
            -FilePath $builtExecutable `
            -ArgumentList "--packaging-self-test" `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
        if ($smokeProcess.ExitCode -ne 0) {
            throw "Packaged executable self-test failed with exit code $($smokeProcess.ExitCode)."
        }
    }
    finally {
        $env:LOCALAPPDATA = $previousLocalAppData
    }
    $expectedUserDirectory = Join-Path $smokeLocalAppData "ChessRepertoireMemorizer\repertoire"
    if (-not (Test-Path -LiteralPath $expectedUserDirectory)) {
        throw "The packaged app did not create its per-user repertoire directory."
    }

    $releaseDirectory = Join-Path $projectRoot "release"
    New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
    $assetBaseName = "Chess-Repertoire-Memorizer-$Version-Windows"
    $releaseZip = Join-Path $releaseDirectory "$assetBaseName.zip"
    Compress-Archive `
        -Path (Join-Path $distributionDirectory "*") `
        -DestinationPath $releaseZip `
        -CompressionLevel Optimal

    Write-Host ""
    Write-Host "Windows release build completed successfully:"
    Write-Host "  $releaseZip"
}
finally {
    Remove-Item Env:CRM_BUILD_VERSION -ErrorAction SilentlyContinue
    Remove-Item Env:CRM_VERSION_RESOURCE -ErrorAction SilentlyContinue
    Pop-Location
}
