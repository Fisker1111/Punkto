# Punkto Codex resume/finalize runner for interrupted Windows Codex tasks.
# Preserves an existing dirty scoped working tree, asks Codex to finish the
# canonical ACTIVE task, then host-side PowerShell validates/commits/pushes.

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
if ($Branch -ne 'pilot-1') { Fail "Resume must run on pilot-1. Current branch: $Branch" }

# Slice 3.6 expected/optional code scope. This runner refuses anything else.
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

$RequiredFinalPaths = @(
    'docs/agent/CODEX_CURRENT_TASK.md',
    'pwa/ARCHITECTURE.md',
    'pwa/app.js',
    'pwa/ui-map.js',
    'pwa/ui-board.js'
)

$DirtyBefore = Get-DirtyPaths
if ($DirtyBefore.Count -eq 0) { Fail 'Working tree is clean. Use .\punkto-codex.ps1 instead.' 2 }
$Unexpected = @($DirtyBefore | Where-Object { $_ -notin $AllowedPaths })
if ($Unexpected.Count -gt 0) {
    Write-Host 'Unexpected dirty files found; refusing resume:' -ForegroundColor Red
    $Unexpected | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 3
}

Write-Host 'Preserving interrupted scoped edits:' -ForegroundColor Yellow
$DirtyBefore | ForEach-Object { Write-Host "  $_" }

# Resolve real standalone Codex + Windows resources.
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
        foreach ($Candidate in @((Join-Path $ReleaseRoot 'codex.exe'), (Join-Path $ReleaseRoot 'bin\codex.exe'))) {
            if (Test-Path $Candidate) { $CodexExe = $Candidate; break }
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
if (-not $CodexExe) { Fail 'Codex CLI was not found.' }

# Fetch and allow only a safe fast-forward while preserving dirty files.
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'git fetch origin failed' }
$HeadBeforeFF = (git rev-parse HEAD).Trim()
$OriginHead = (git rev-parse origin/pilot-1).Trim()
if ($LASTEXITCODE -ne 0) { Fail 'git rev-parse failed' }
if ($HeadBeforeFF -ne $OriginHead) {
    git merge --ff-only origin/pilot-1
    if ($LASTEXITCODE -ne 0) {
        Fail 'Could not fast-forward to origin/pilot-1 while preserving interrupted edits. Nothing was discarded.' 4
    }
}

$BaseHead = (git rev-parse HEAD).Trim()
$CanonicalTask = git show 'origin/pilot-1:docs/agent/CODEX_CURRENT_TASK.md'
if ($LASTEXITCODE -ne 0) { Fail 'Could not read canonical task from origin/pilot-1' }
$CanonicalTaskText = ($CanonicalTask -join "`n")
$CanonicalStatus = Get-CanonicalTaskStatus $CanonicalTaskText
if (-not $CanonicalStatus -or $CanonicalStatus -notmatch '^\s*Status:\s*\*\*ACTIVE\b') {
    Fail "Canonical task is not ACTIVE: $CanonicalStatus" 5
}

$ResumeInstruction = @'

## INTERRUPTED-RUN RESUME MODE

A previous Codex attempt on this exact canonical task was interrupted after making substantial local edits. The working tree is intentionally dirty and those edits MUST be preserved.

Mandatory rules:
- DO NOT reset, checkout, restore, revert, stash, clean, or discard existing modifications.
- First inspect `git status`, `git diff --stat`, and the current diffs in every modified/new file.
- Continue from the partial implementation; do not restart the refactor from scratch unless a specific broken edit must be corrected.
- Finish the canonical Slice 3.6 task exactly as written.
- Keep behavior and visuals unchanged.
- Do not deploy and do not start Slice 4.
- Do NOT commit or push. The outer trusted PowerShell runner will validate, commit, and push because native Windows Codex cannot reliably write `.git`.

Before returning:
1. Run the canonical task's automated checks where possible.
2. Ensure `pwa/ARCHITECTURE.md` reflects the final module ownership.
3. Change the FIRST task Status line to exactly:
   `Status: **HOLD — Slice 3.6 implemented, awaiting CI/review**`
4. Leave the complete finished implementation in the working tree and stop.

Do not merely describe remaining work. Finish it in the working tree.
'@

$Prompt = $CanonicalTaskText + $ResumeInstruction
Write-Host "Resuming Codex from exact Git base $BaseHead" -ForegroundColor Green
Write-Host 'Existing edits are protected by path-scope checks; host PowerShell will commit after validation.' -ForegroundColor DarkGray

& $CodexExe exec --dangerously-bypass-approvals-and-sandbox --cd $RepoRoot $Prompt
$CodexExit = $LASTEXITCODE
Write-Host ''
Write-Host "Codex exit code: $CodexExit"
if ($CodexExit -ne 0) {
    Write-Host 'Codex stopped/faulted again. Existing edits remain untouched.' -ForegroundColor Yellow
    git status --short
    exit $CodexExit
}

$DirtyAfter = Get-DirtyPaths
$UnexpectedAfter = @($DirtyAfter | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedAfter.Count -gt 0) {
    Write-Host 'Codex touched files outside Slice 3.6 scope; refusing finalize:' -ForegroundColor Red
    $UnexpectedAfter | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 6
}
foreach ($Required in $RequiredFinalPaths) {
    if ($Required -notin $DirtyAfter) { Fail "Required final Slice 3.6 file is not modified: $Required" 7 }
}

$TaskAfter = Get-Content -Raw -Path $TaskFile
$StatusAfter = Get-CanonicalTaskStatus $TaskAfter
if (-not $StatusAfter -or $StatusAfter -notmatch '^\s*Status:\s*\*\*HOLD — Slice 3\.6 implemented, awaiting CI/review\*\*\s*$') {
    Fail "Task did not return to the required HOLD state: $StatusAfter" 8
}

# Host-side hard checks.
git diff --check
if ($LASTEXITCODE -ne 0) { Fail 'git diff --check failed' 9 }

$JsChecks = @(
    'pwa/app.js',
    'pwa/ui-shell.js',
    'pwa/ui-text.js',
    'pwa/ui-map.js',
    'pwa/ui-board.js',
    'pwa/ui-create.js',
    'pwa/ui-settings.js',
    'pwa/key-management.js',
    'pwa/sw.js'
)
foreach ($File in $JsChecks) {
    & node --check $File
    if ($LASTEXITCODE -ne 0) { Fail "node --check failed: $File" 10 }
}

foreach ($ModuleFile in @('pwa/app.js','pwa/ui-map.js','pwa/ui-board.js')) {
    Get-Content -Raw -Path $ModuleFile | node --input-type=module --check
    if ($LASTEXITCODE -ne 0) { Fail "ES module parse failed: $ModuleFile" 11 }
}

# Relay suite: required to run; failure blocks this host-side finalize for safety.
$PythonCmd = $null
$PythonArgs = @()
if (Get-Command python3 -ErrorAction SilentlyContinue) { $PythonCmd = 'python3' }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PythonCmd = 'python' }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $PythonCmd = 'py'; $PythonArgs = @('-3') }
else { Fail 'No Python command found for relay/test_relay.py' 12 }
& $PythonCmd @PythonArgs 'relay/test_relay.py'
if ($LASTEXITCODE -ne 0) { Fail 'relay/test_relay.py failed; implementation preserved but not committed.' 13 }

# Stage exactly the final allowed dirty set.
$DirtyAfter = Get-DirtyPaths
$UnexpectedAfter = @($DirtyAfter | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedAfter.Count -gt 0) { Fail 'Unexpected dirty path appeared before staging.' 14 }

git add -- $DirtyAfter
if ($LASTEXITCODE -ne 0) { Fail 'git add failed' 15 }
$Staged = @(git diff --cached --name-only)
$UnexpectedStaged = @($Staged | Where-Object { $_ -notin $AllowedPaths })
if ($UnexpectedStaged.Count -gt 0) {
    git reset
    Fail 'Unexpected staged files detected; staging cleared.' 16
}
git diff --cached --check
if ($LASTEXITCODE -ne 0) { git reset; Fail 'Staged diff check failed; staging cleared.' 17 }

$CommitMessage = 'refactor(pilot1): modularize map and board UI'
git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) { Fail 'git commit failed' 18 }
$HeadAfter = (git rev-parse HEAD).Trim()
$ActualMessage = (git log -1 --pretty=%s).Trim()
if ($ActualMessage -ne $CommitMessage) { Fail "Unexpected commit message: $ActualMessage" 19 }

$DirtyPostCommit = @(git status --porcelain)
if ($DirtyPostCommit.Count -gt 0) {
    git status --short
    Fail 'Commit created but working tree is still dirty.' 20
}

git push origin pilot-1
if ($LASTEXITCODE -ne 0) { Fail 'git push failed; commit remains safely local.' 21 }
git fetch origin
if ($LASTEXITCODE -ne 0) { Fail 'final git fetch failed' 22 }
$OriginAfter = (git rev-parse origin/pilot-1).Trim()
if ($OriginAfter -ne $HeadAfter) { Fail "Push verification failed. Local=$HeadAfter Origin=$OriginAfter" 23 }

Write-Host "Slice 3.6 resumed, validated, committed and pushed: $HeadAfter" -ForegroundColor Green
Write-Host 'You can now tell ChatGPT: Codex done' -ForegroundColor Green
exit 0
