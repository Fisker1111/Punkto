# Punkto local Codex launcher for Windows PowerShell.
# Run from the repository with: .\punkto-codex.ps1

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$TaskFile = Join-Path $RepoRoot 'docs\agent\CODEX_CURRENT_TASK.md'

Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    throw "Not a Git checkout: $RepoRoot"
}

# Prefer the real standalone package binary on Windows rather than the PATH
# shim under AppData\Local\Programs\OpenAI\Codex\bin. Some Codex Windows
# builds can launch the shim successfully but then fail to discover the bundled
# sandbox helpers (codex-windows-sandbox-setup.exe / codex-command-runner.exe).
# The package binary has its matching codex-resources directory alongside it.
$CodexExe = $null
$StandaloneRoot = Join-Path $env:USERPROFILE '.codex\packages\standalone\current'
$StandaloneExe = Join-Path $StandaloneRoot 'bin\codex.exe'
$StandaloneResources = Join-Path $StandaloneRoot 'codex-resources'

if (Test-Path $StandaloneExe) {
    $CodexExe = $StandaloneExe
    if (Test-Path $StandaloneResources) {
        # Also make the bundled helpers directly discoverable for setup paths
        # that still resolve them by filename.
        $env:PATH = "$StandaloneResources;$env:PATH"
    }
}

# Fall back to normal PowerShell command resolution / known install locations
# only if the real standalone runtime is unavailable.
if (-not $CodexExe) {
    $CodexCommand = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($CodexCommand) {
        if ($CodexCommand.Path) {
            $CodexExe = $CodexCommand.Path
        } elseif ($CodexCommand.Source) {
            $CodexExe = $CodexCommand.Source
        } elseif ($CodexCommand.Definition) {
            $CodexExe = $CodexCommand.Definition
        }
    }
}

if (-not $CodexExe) {
    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin\codex.exe'),
        (Join-Path $env:USERPROFILE '.codex\bin\codex.exe'),
        (Join-Path $env:APPDATA 'npm\codex.cmd')
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $CodexExe = $Candidate
            break
        }
    }
}

if (-not $CodexExe) {
    $WhereResult = & where.exe codex 2>$null
    if ($LASTEXITCODE -eq 0 -and $WhereResult) {
        $CodexExe = @($WhereResult)[0]
    }
}

if (-not $CodexExe) {
    throw "Codex CLI was not found. Try: Get-Command codex | Format-List *  and  where.exe codex"
}

Write-Host "Using Codex: $CodexExe" -ForegroundColor DarkGray
if (Test-Path $StandaloneResources) {
    Write-Host "Codex resources: $StandaloneResources" -ForegroundColor DarkGray
}

# Never overwrite or mix with uncommitted human/agent work.
$dirtyBefore = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
if ($dirtyBefore) {
    Write-Host 'Working tree is not clean. Refusing to update or launch Codex.' -ForegroundColor Red
    git status --short
    exit 2
}

Write-Host 'Updating pilot-1 from GitHub...' -ForegroundColor Cyan
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'git fetch origin failed' }

git switch pilot-1
if ($LASTEXITCODE -ne 0) { throw 'git switch pilot-1 failed' }

git pull --ff-only origin pilot-1
if ($LASTEXITCODE -ne 0) { throw 'git pull --ff-only origin pilot-1 failed' }

if (-not (Test-Path $TaskFile)) {
    throw "Codex task file not found: $TaskFile"
}

$Task = Get-Content -Raw -Path $TaskFile

# Read only the canonical top-level Status line. The task body may mention the
# future HOLD status as part of its commit instructions, so scanning the whole
# file for the word HOLD would produce a false positive.
$StatusLine = ($Task -split "`r?`n" | Where-Object { $_ -match '^\s*Status:' } | Select-Object -First 1)
if (-not $StatusLine) {
    throw 'CODEX_CURRENT_TASK.md has no Status line. Refusing to launch Codex.'
}

if ($StatusLine -match '^\s*Status:\s*\*\*HOLD\b') {
    Write-Host 'CODEX_CURRENT_TASK.md is on HOLD. No Codex task was launched.' -ForegroundColor Yellow
    Write-Host 'Ask ChatGPT to activate the next implementation task, then run this script again.'
    exit 0
}

if ($StatusLine -notmatch '^\s*Status:\s*\*\*ACTIVE\b') {
    throw "Unrecognized task status: $StatusLine"
}

Write-Host $StatusLine -ForegroundColor Green

$Head = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse HEAD failed' }
Write-Host "Launching Codex from exact local HEAD $Head" -ForegroundColor Green
Write-Host "Task: $TaskFile" -ForegroundColor DarkGray

# Pass the task as one positional prompt rather than piping stdin. This keeps
# the launcher simple and avoids stdin/TTY edge cases in non-interactive Codex.
& $CodexExe exec $Task
$CodexExit = $LASTEXITCODE

Write-Host ''
Write-Host "Codex exit code: $CodexExit"
Write-Host 'Repository state after Codex:' -ForegroundColor Cyan
git status --short
git log -1 --oneline

exit $CodexExit
