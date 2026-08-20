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

# Prefer the actual standalone release binary whose bundled Windows sandbox
# helpers live in the matching codex-resources directory. Recent Windows Codex
# builds have had packaging/lookup regressions where the AppData PATH shim can
# start Codex but cannot find codex-windows-sandbox-setup.exe or
# codex-command-runner.exe.
$CodexExe = $null
$CodexResources = $null
$StandaloneBase = Join-Path $env:USERPROFILE '.codex\packages\standalone'

if (Test-Path $StandaloneBase) {
    $SetupHelper = Get-ChildItem -Path $StandaloneBase -Filter 'codex-windows-sandbox-setup.exe' -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($SetupHelper) {
        $CodexResources = Split-Path $SetupHelper.FullName -Parent
        $ReleaseRoot = Split-Path $CodexResources -Parent
        $ReleaseCandidates = @(
            (Join-Path $ReleaseRoot 'codex.exe'),
            (Join-Path $ReleaseRoot 'bin\codex.exe')
        )
        foreach ($Candidate in $ReleaseCandidates) {
            if (Test-Path $Candidate) {
                $CodexExe = $Candidate
                break
            }
        }

        # This helps helper lookups that still consult PATH. The preferred
        # release binary above should also be able to find this directory as
        # its adjacent codex-resources folder.
        $env:PATH = "$CodexResources;$env:PATH"
    }
}

# Older standalone layout fallback.
if (-not $CodexExe) {
    $StandaloneRoot = Join-Path $StandaloneBase 'current'
    $StandaloneExe = Join-Path $StandaloneRoot 'bin\codex.exe'
    $StandaloneResources = Join-Path $StandaloneRoot 'codex-resources'
    if (Test-Path $StandaloneExe) {
        $CodexExe = $StandaloneExe
        if (Test-Path $StandaloneResources) {
            $CodexResources = $StandaloneResources
            $env:PATH = "$StandaloneResources;$env:PATH"
        }
    }
}

# Fall back to normal PowerShell command resolution / known install locations
# only if no real standalone release binary was found.
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
if ($CodexResources) {
    Write-Host "Codex resources: $CodexResources" -ForegroundColor DarkGray
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

function Get-CanonicalTaskStatus([string]$TaskText) {
    return ($TaskText -split "`r?`n" | Where-Object { $_ -match '^\s*Status:' } | Select-Object -First 1)
}

# Read only the canonical top-level Status line. The task body may mention the
# future HOLD status as part of its commit instructions.
$StatusLine = Get-CanonicalTaskStatus $Task
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

$HeadBefore = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse HEAD failed' }
Write-Host "Launching Codex from exact local HEAD $HeadBefore" -ForegroundColor Green
Write-Host "Task: $TaskFile" -ForegroundColor DarkGray

# Pass the task as one positional prompt rather than piping stdin.
& $CodexExe exec $Task
$CodexExit = $LASTEXITCODE

Write-Host ''
Write-Host "Codex exit code: $CodexExit"
Write-Host 'Repository state after Codex:' -ForegroundColor Cyan
git status --short
git log -1 --oneline

# Codex can occasionally return exit 0 even after reporting a blocked task.
# Treat success as a workflow state transition, not merely a process exit:
# ACTIVE must become HOLD, HEAD must move, and the new HEAD must be pushed.
$HeadAfter = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse HEAD after Codex failed' }
$TaskAfter = Get-Content -Raw -Path $TaskFile
$StatusAfter = Get-CanonicalTaskStatus $TaskAfter

if ($CodexExit -ne 0) {
    Write-Host 'Codex process failed. No deployment/review handoff is valid.' -ForegroundColor Red
    exit $CodexExit
}

if ($HeadAfter -eq $HeadBefore) {
    Write-Host 'Codex returned without creating the required implementation commit.' -ForegroundColor Red
    Write-Host 'Task remains incomplete even though the Codex process returned exit 0.' -ForegroundColor Red
    exit 3
}

if (-not $StatusAfter -or $StatusAfter -notmatch '^\s*Status:\s*\*\*HOLD\b') {
    Write-Host 'Codex created a commit but did not return the canonical task to HOLD.' -ForegroundColor Red
    exit 4
}

git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'final git fetch origin failed' }
$OriginHead = git rev-parse origin/pilot-1
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse origin/pilot-1 failed' }

if ($OriginHead -ne $HeadAfter) {
    Write-Host "Local Codex commit was not pushed to origin/pilot-1. Local=$HeadAfter Origin=$OriginHead" -ForegroundColor Red
    exit 5
}

Write-Host "Codex task completed and pushed: $HeadAfter" -ForegroundColor Green
Write-Host 'You can now tell ChatGPT: Codex done' -ForegroundColor Green
exit 0
