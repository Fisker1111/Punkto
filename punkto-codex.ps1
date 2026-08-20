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

# Resolve Codex robustly on Windows. Depending on how Codex was installed,
# PowerShell may be able to launch `codex` interactively while Get-Command
# inside a script does not resolve the same shim/app alias. Prefer the normal
# command resolution, then fall back to known standalone/npm locations and
# finally `where.exe`.
$CodexExe = $null
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

# HOLD is an intentional safety state between implementation tasks.
if ($Task -match 'Status:\s*\*\*HOLD') {
    Write-Host 'CODEX_CURRENT_TASK.md is on HOLD. No Codex task was launched.' -ForegroundColor Yellow
    Write-Host 'Ask ChatGPT to activate the next implementation task, then run this script again.'
    exit 0
}

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
