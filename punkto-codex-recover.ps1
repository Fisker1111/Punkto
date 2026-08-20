# Punkto Codex recovery launcher for Windows PowerShell.
# Use ONLY when a previous Codex run left scoped Slice work uncommitted.
# Normal tasks should use .\punkto-codex.ps1

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

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    Fail "Not a Git checkout: $RepoRoot"
}

$Branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git branch --show-current failed' }
if ($Branch -ne 'pilot-1') {
    Fail "Recovery must run on pilot-1. Current branch: $Branch"
}

# Resolve the real standalone Codex release and its Windows sandbox helpers.
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
        foreach ($Candidate in @(
            (Join-Path $ReleaseRoot 'codex.exe'),
            (Join-Path $ReleaseRoot 'bin\codex.exe')
        )) {
            if (Test-Path $Candidate) {
                $CodexExe = $Candidate
                break
            }
        }
        $env:PATH = "$CodexResources;$env:PATH"
    }
}

if (-not $CodexExe) {
    $Cmd = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Cmd) {
        if ($Cmd.Path) { $CodexExe = $Cmd.Path }
        elseif ($Cmd.Source) { $CodexExe = $Cmd.Source }
        elseif ($Cmd.Definition) { $CodexExe = $Cmd.Definition }
    }
}

if (-not $CodexExe) {
    Fail 'Codex CLI was not found.'
}

Write-Host "Using Codex: $CodexExe" -ForegroundColor DarkGray
if ($CodexResources) {
    Write-Host "Codex resources: $CodexResources" -ForegroundColor DarkGray
}

# Recovery is intentionally the inverse of the normal launcher: it REQUIRES
# an existing dirty tree, but only in the known Slice 3 recovery paths.
$StatusLines = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) { Fail 'git status failed' }
if ($StatusLines.Count -eq 0) {
    Fail 'Working tree is clean. Use .\punkto-codex.ps1 instead of recovery.' 2
}

$AllowedDirtyPaths = @(
    'docs/agent/CODEX_CURRENT_TASK.md',
    'pwa/app.js',
    'pwa/index.html',
    'pwa/ui-text.js'
)

$DirtyPaths = @()
foreach ($Line in $StatusLines) {
    if ($Line.Length -lt 4) { continue }
    $Path = $Line.Substring(3).Trim()
    if ($Path -match ' -> ') {
        $Path = ($Path -split ' -> ')[-1].Trim()
    }
    $DirtyPaths += $Path
}

$Unexpected = @($DirtyPaths | Where-Object { $_ -notin $AllowedDirtyPaths })
if ($Unexpected.Count -gt 0) {
    Write-Host 'Unexpected dirty files found; refusing recovery:' -ForegroundColor Red
    $Unexpected | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 3
}

Write-Host 'Recovering these existing scoped edits:' -ForegroundColor Yellow
$DirtyPaths | ForEach-Object { Write-Host "  $_" }

# Fetch only. Do NOT pull/rebase/reset over the dirty recovery tree.
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'git fetch origin failed' }

$HeadBefore = (git rev-parse HEAD).Trim()
$OriginBefore = (git rev-parse origin/pilot-1).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git rev-parse failed' }
if ($HeadBefore -ne $OriginBefore) {
    Fail "Local HEAD must equal origin/pilot-1 before recovery. Local=$HeadBefore Origin=$OriginBefore`nBecause the tree is dirty, do not merge/rebase inside recovery. Pull the workflow-only commit first, then rerun recovery." 4
}

# Always use the canonical task from Git, not the locally modified task file.
$CanonicalTask = git show 'origin/pilot-1:docs/agent/CODEX_CURRENT_TASK.md'
if ($LASTEXITCODE -ne 0) { Fail 'Could not read canonical task from origin/pilot-1' }
$CanonicalTaskText = ($CanonicalTask -join "`n")
$CanonicalStatus = Get-CanonicalTaskStatus $CanonicalTaskText
if (-not $CanonicalStatus -or $CanonicalStatus -notmatch '^\s*Status:\s*\*\*ACTIVE\b') {
    Fail "Canonical task is not ACTIVE: $CanonicalStatus" 5
}

$RecoveryInstruction = @'

## RECOVERY MODE — preserve existing partial implementation

A previous Codex attempt on this exact task was interrupted after making local edits.
The working tree is intentionally dirty and those edits are the partial Slice 3 implementation to recover.

Mandatory recovery rules:

- DO NOT reset, checkout, restore, revert, stash, clean, or discard the existing modifications.
- First inspect `git status`, `git diff`, and the modified files.
- Treat the existing edits as your own previous partial work.
- Review them against the canonical task above, then continue/fix/finish the implementation.
- Stay within the original Slice 3 scope. Do not start Slice 4.
- Do not deploy.

Before completion:

1. run every automated check required by the canonical task;
2. perform the practical local/manual checks requested by the canonical task;
3. change the first canonical task Status line to exactly:
   `Status: **HOLD — Slice 3 implemented, awaiting CI/review**`
4. commit the completed scoped work with exactly:
   `feat(pilot1): add map bottom-sheet board`
5. push the commit to `origin/pilot-1`;
6. stop.

Do not merely report success. The recovery is complete only when the commit is pushed and the task status is HOLD.
'@

$Prompt = $CanonicalTaskText + $RecoveryInstruction

Write-Host "Launching recovery from exact HEAD $HeadBefore" -ForegroundColor Green
& $CodexExe exec $Prompt
$CodexExit = $LASTEXITCODE

Write-Host ''
Write-Host "Codex exit code: $CodexExit"
Write-Host 'Repository state after recovery:' -ForegroundColor Cyan
git status --short
git log -1 --oneline

if ($CodexExit -ne 0) {
    Fail 'Codex recovery process failed.' $CodexExit
}

$HeadAfter = (git rev-parse HEAD).Trim()
if ($HeadAfter -eq $HeadBefore) {
    Fail 'Codex returned without creating the required recovery commit.' 6
}

if (-not (Test-Path $TaskFile)) {
    Fail 'Task file disappeared during recovery.' 7
}
$TaskAfter = Get-Content -Raw -Path $TaskFile
$StatusAfter = Get-CanonicalTaskStatus $TaskAfter
if (-not $StatusAfter -or $StatusAfter -notmatch '^\s*Status:\s*\*\*HOLD\b') {
    Fail "Recovery commit exists, but task did not return to HOLD: $StatusAfter" 8
}

$DirtyAfter = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) { Fail 'final git status failed' }
if ($DirtyAfter.Count -gt 0) {
    Write-Host 'Recovery commit exists, but working tree is still dirty:' -ForegroundColor Red
    git status --short
    exit 9
}

git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'final git fetch origin failed' }
$OriginAfter = (git rev-parse origin/pilot-1).Trim()
if ($OriginAfter -ne $HeadAfter) {
    Fail "Recovery commit was not pushed to origin/pilot-1. Local=$HeadAfter Origin=$OriginAfter" 10
}

Write-Host "Codex recovery completed and pushed: $HeadAfter" -ForegroundColor Green
Write-Host 'You can now tell ChatGPT: Codex done' -ForegroundColor Green
exit 0
