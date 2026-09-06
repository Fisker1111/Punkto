# Punkto Slice 3.6 host-side finalizer for Windows PowerShell.
# Use after Codex has completed the interrupted Slice 3.6 working-tree edits
# but local Node.js is unavailable. This script preserves the work, validates
# Git scope/status, commits, pushes, and relies on GitHub Pilot CI for JS syntax.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$TaskFile = Join-Path $RepoRoot 'docs\agent\CODEX_CURRENT_TASK.md'
Set-Location $RepoRoot

function Fail([string]$Message, [int]$Code = 1) {
    Write-Host $Message -ForegroundColor Red
    exit $Code
}

function Get-CanonicalTaskStatus([string]$TaskText) {
    return ($TaskText -split "`r?`n" | Where-Object { $_ -match '^\s*Status:' } | Select-Object -First 1)
}

function Get-DirtyPaths {
    $Lines = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { Fail 'git status failed' }
    $Paths = @()
    foreach ($Line in $Lines) {
        if ($Line.Length -lt 4) { continue }
        $Path = $Line.Substring(3).Trim()
        if ($Path -match ' -> ') { $Path = ($Path -split ' -> ')[-1].Trim() }
        $Paths += $Path
    }
    return @($Paths | Select-Object -Unique)
}

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) { Fail "Not a Git checkout: $RepoRoot" }
$Branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git branch --show-current failed' }
if ($Branch -ne 'pilot-1') { Fail "Finalize36 must run on pilot-1. Current branch: $Branch" }

$AllowedPaths = @(
    'docs/agent/CODEX_CURRENT_TASK.md',
    'pwa/ARCHITECTURE.md',
    'pwa/app.js',
    'pwa/ui-map.js',
    'pwa/ui-board.js',
    'pwa/ui-text.js',
    'pwa/index.html',
    'pwa/ui-shell.js'
)

$RequiredPaths = @(
    'docs/agent/CODEX_CURRENT_TASK.md',
    'pwa/ARCHITECTURE.md',
    'pwa/app.js',
    'pwa/ui-map.js',
    'pwa/ui-board.js'
)

$Dirty = Get-DirtyPaths
if ($Dirty.Count -eq 0) { Fail 'Working tree is clean; nothing to finalize.' 2 }
$Unexpected = @($Dirty | Where-Object { $_ -notin $AllowedPaths })
if ($Unexpected.Count -gt 0) {
    Write-Host 'Unexpected dirty files found; refusing finalize:' -ForegroundColor Red
    $Unexpected | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 3
}
foreach ($Required in $RequiredPaths) {
    if ($Required -notin $Dirty) { Fail "Required Slice 3.6 file is not modified: $Required" 4 }
}

if (-not (Test-Path $TaskFile)) { Fail 'Task file missing.' 5 }
$TaskText = Get-Content -Raw -Path $TaskFile
$TaskStatus = Get-CanonicalTaskStatus $TaskText
if (-not $TaskStatus -or $TaskStatus -notmatch '^\s*Status:\s*\*\*HOLD — Slice 3\.6 implemented, awaiting CI/review\*\*\s*$') {
    Fail "Task must be in completed Slice 3.6 HOLD state before finalize. Current: $TaskStatus" 6
}

Write-Host 'Finalizing completed Slice 3.6 working-tree changes:' -ForegroundColor Yellow
$Dirty | ForEach-Object { Write-Host "  $_" }

# Bring in non-overlapping workflow/helper commits only. Never reset/rebase dirty work.
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'git fetch origin failed' 7 }
$HeadBefore = (git rev-parse HEAD).Trim()
$OriginHead = (git rev-parse origin/pilot-1).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git rev-parse failed' 8 }
if ($HeadBefore -ne $OriginHead) {
    git merge --ff-only origin/pilot-1
    if ($LASTEXITCODE -ne 0) { Fail 'Could not fast-forward origin/pilot-1 while preserving dirty Slice 3.6 edits. Nothing was discarded.' 9 }
}

# Re-check after fast-forward.
$Dirty = Get-DirtyPaths
$Unexpected = @($Dirty | Where-Object { $_ -notin $AllowedPaths })
if ($Unexpected.Count -gt 0) { Fail 'Unexpected dirty path appeared after fast-forward.' 10 }
foreach ($Required in $RequiredPaths) {
    if ($Required -notin $Dirty) { Fail "Required Slice 3.6 file missing after fast-forward: $Required" 11 }
}

# Local Git integrity check. JS syntax is intentionally delegated to exact-SHA Pilot CI
# because this Windows host does not currently have node.exe on PATH.
git diff --check
if ($LASTEXITCODE -ne 0) { Fail 'git diff --check failed.' 12 }

# Stage exactly the approved dirty set.
git add -- $Dirty
if ($LASTEXITCODE -ne 0) { Fail 'git add failed' 13 }
$Staged = @(git diff --cached --name-only)
$UnexpectedStaged = @($Staged | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedStaged.Count -gt 0) {
    git reset
    Fail 'Unexpected staged files detected; staging cleared.' 14
}
foreach ($Required in $RequiredPaths) {
    if ($Required -notin $Staged) {
        git reset
        Fail "Required Slice 3.6 file was not staged: $Required" 15
    }
}
git diff --cached --check
if ($LASTEXITCODE -ne 0) { git reset; Fail 'Staged diff check failed; staging cleared.' 16 }

$CommitMessage = 'refactor(pilot1): modularize map and board UI'
git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) { Fail 'git commit failed' 17 }
$HeadAfter = (git rev-parse HEAD).Trim()
$ActualMessage = (git log -1 --pretty=%s).Trim()
if ($ActualMessage -ne $CommitMessage) { Fail "Unexpected commit message: $ActualMessage" 18 }

$CommitFiles = @(git diff-tree --no-commit-id --name-only -r $HeadAfter)
$UnexpectedCommit = @($CommitFiles | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedCommit.Count -gt 0) { Fail 'Commit contains files outside Slice 3.6 scope.' 19 }

$DirtyAfter = @(git status --porcelain)
if ($DirtyAfter.Count -gt 0) {
    git status --short
    Fail 'Commit created but working tree is still dirty.' 20
}

git push origin pilot-1
if ($LASTEXITCODE -ne 0) { Fail 'git push failed; commit remains safely local.' 21 }
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'final git fetch failed' 22 }
$OriginAfter = (git rev-parse origin/pilot-1).Trim()
if ($OriginAfter -ne $HeadAfter) { Fail "Push verification failed. Local=$HeadAfter Origin=$OriginAfter" 23 }

Write-Host "Slice 3.6 finalized and pushed: $HeadAfter" -ForegroundColor Green
Write-Host 'Local Node.js was unavailable; GitHub Pilot CI is now the hard syntax/module gate for this exact SHA.' -ForegroundColor Yellow
Write-Host 'You can now tell ChatGPT: Codex done' -ForegroundColor Green
exit 0
