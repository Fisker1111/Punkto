# Punkto Codex finalize launcher for Windows PowerShell.
# Use when Codex completed scoped work in the working tree but could not write .git.

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

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) { Fail "Not a Git checkout: $RepoRoot" }

$Branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git branch --show-current failed' }
if ($Branch -ne 'pilot-1') { Fail "Finalize must run on pilot-1. Current branch: $Branch" }

$AllowedPaths = @(
    'docs/agent/CODEX_CURRENT_TASK.md',
    'pwa/app.js',
    'pwa/index.html',
    'pwa/ui-text.js'
)

$StatusLines = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) { Fail 'git status failed' }
if ($StatusLines.Count -eq 0) { Fail 'Working tree is clean; there is nothing to finalize.' 2 }

$DirtyPaths = @()
foreach ($Line in $StatusLines) {
    if ($Line.Length -lt 4) { continue }
    $Path = $Line.Substring(3).Trim()
    if ($Path -match ' -> ') { $Path = ($Path -split ' -> ')[-1].Trim() }
    $DirtyPaths += $Path
}

$Unexpected = @($DirtyPaths | Where-Object { $_ -notin $AllowedPaths })
if ($Unexpected.Count -gt 0) {
    Write-Host 'Unexpected dirty files found; refusing finalize:' -ForegroundColor Red
    $Unexpected | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 3
}

foreach ($Required in $AllowedPaths) {
    if ($Required -notin $DirtyPaths) {
        Fail "Expected Slice 3 recovery file is not modified: $Required" 4
    }
}

if (-not (Test-Path $TaskFile)) { Fail 'Task file is missing.' 5 }
$TaskText = Get-Content -Raw -Path $TaskFile
$TaskStatus = Get-CanonicalTaskStatus $TaskText
if (-not $TaskStatus -or $TaskStatus -notmatch '^\s*Status:\s*\*\*HOLD\b') {
    Fail "Task must already be HOLD before finalize. Current: $TaskStatus" 6
}

Write-Host 'Preserving completed Slice 3 working-tree changes:' -ForegroundColor Yellow
$DirtyPaths | ForEach-Object { Write-Host "  $_" }

# Bring in workflow-only commits that may have landed while Codex was working.
# This is safe only as a fast-forward. Git will refuse if one of those commits
# overlaps the dirty Slice 3 files; in that case we stop without discarding work.
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'git fetch origin failed' }

$HeadBefore = (git rev-parse HEAD).Trim()
$OriginHead = (git rev-parse origin/pilot-1).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git rev-parse failed' }

if ($HeadBefore -ne $OriginHead) {
    git merge --ff-only origin/pilot-1
    if ($LASTEXITCODE -ne 0) {
        Fail 'Could not fast-forward to origin/pilot-1 while preserving the dirty Slice 3 files. No work was discarded.' 7
    }
}

# Re-check after fast-forward.
$StatusLines = @(git status --porcelain)
$DirtyPaths = @()
foreach ($Line in $StatusLines) {
    if ($Line.Length -lt 4) { continue }
    $Path = $Line.Substring(3).Trim()
    if ($Path -match ' -> ') { $Path = ($Path -split ' -> ')[-1].Trim() }
    $DirtyPaths += $Path
}
$Unexpected = @($DirtyPaths | Where-Object { $_ -notin $AllowedPaths })
if ($Unexpected.Count -gt 0) { Fail 'Unexpected dirty files appeared after fast-forward.' 8 }

# Lightweight integrity gate before staging.
git diff --check
if ($LASTEXITCODE -ne 0) { Fail 'git diff --check failed. Fix whitespace/conflict issues before committing.' 9 }

# Stage exactly the four approved Slice 3 files and nothing else.
git add -- docs/agent/CODEX_CURRENT_TASK.md pwa/app.js pwa/index.html pwa/ui-text.js
if ($LASTEXITCODE -ne 0) { Fail 'git add failed' 10 }

$Staged = @(git diff --cached --name-only)
$UnexpectedStaged = @($Staged | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedStaged.Count -gt 0) {
    git reset
    Fail 'Unexpected staged files detected; staging was cleared.' 11
}
foreach ($Required in $AllowedPaths) {
    if ($Required -notin $Staged) {
        git reset
        Fail "Required Slice 3 file was not staged: $Required" 12
    }
}

git diff --cached --check
if ($LASTEXITCODE -ne 0) {
    git reset
    Fail 'Staged diff check failed; staging was cleared.' 13
}

$CommitMessage = 'feat(pilot1): add map bottom-sheet board'
git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) { Fail 'git commit failed' 14 }

$HeadAfter = (git rev-parse HEAD).Trim()
$ActualMessage = (git log -1 --pretty=%s).Trim()
if ($ActualMessage -ne $CommitMessage) { Fail "Unexpected commit message: $ActualMessage" 15 }

$CommitFiles = @(git diff-tree --no-commit-id --name-only -r $HeadAfter)
$UnexpectedCommitFiles = @($CommitFiles | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedCommitFiles.Count -gt 0) { Fail 'Finalize commit contains files outside Slice 3 scope.' 16 }

$DirtyAfterCommit = @(git status --porcelain)
if ($DirtyAfterCommit.Count -gt 0) {
    Write-Host 'Commit created, but working tree is not clean:' -ForegroundColor Red
    git status --short
    exit 17
}

git push origin pilot-1
if ($LASTEXITCODE -ne 0) { Fail 'git push failed; commit remains safely local.' 18 }

git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'final git fetch failed' 19 }
$OriginAfter = (git rev-parse origin/pilot-1).Trim()
if ($OriginAfter -ne $HeadAfter) { Fail "Push verification failed. Local=$HeadAfter Origin=$OriginAfter" 20 }

Write-Host "Slice 3 finalized and pushed: $HeadAfter" -ForegroundColor Green
Write-Host 'You can now tell ChatGPT: Codex done' -ForegroundColor Green
exit 0
