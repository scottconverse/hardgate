# test-installer.ps1 — exercise install.ps1 end-to-end against an isolated HOME
#
# Mirrors scripts/test-installer.sh but targets the PowerShell installer.
# Runs on Windows (PowerShell 5.1+) and Linux/macOS (PowerShell 7+ / pwsh).
#
# Usage:
#     pwsh -File scripts/test-installer.ps1
#     powershell -ExecutionPolicy Bypass -File scripts/test-installer.ps1

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$Zip       = Join-Path $RepoRoot 'dist\hardgate-v1.0.1.zip'

if (-not (Test-Path $Zip)) {
    Write-Error "Installer zip not found: $Zip`nRun: python scripts/build-installer.py"
    exit 1
}

$Work = Join-Path ([System.IO.Path]::GetTempPath()) "hgtest-ps-$(Get-Random)"
New-Item -ItemType Directory -Path $Work -Force | Out-Null

$Script:Pass = 0
$Script:Fail = 0
function Pass([string]$msg) { Write-Host "  [PASS] $msg" -ForegroundColor Green;  $Script:Pass++ }
function Fail([string]$msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red;    $Script:Fail++ }

try {
    # =====================================================================
    Write-Host "=== TEST 1: zip integrity ==="
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [System.IO.Compression.ZipFile]::OpenRead($Zip)
        $entries = @($archive.Entries | ForEach-Object { $_.FullName })
        $archive.Dispose()
        Pass "zip opened, $($entries.Count) entries"
    }
    catch {
        Fail "zip read failed: $_"
    }

    # =====================================================================
    Write-Host ""
    Write-Host "=== TEST 2: install.ps1 happy path ==="
    Expand-Archive -Path $Zip -DestinationPath $Work -Force
    $Extracted = Join-Path $Work 'hardgate-v1.0.1'
    if (Test-Path $Extracted) { Pass "extracted directory exists" }
    else { Fail "missing extracted dir"; return }

    $FakeHome = Join-Path $Work 'home'
    New-Item -ItemType Directory -Path $FakeHome -Force | Out-Null

    # Pass -TargetHome to the installer so it writes into our isolated dir.
    # (Overriding $HOME in a child pwsh -Command does not reliably propagate
    # to the script's automatic $HOME — the parameter is the clean path.)
    $installScript = Join-Path $Extracted 'install.ps1'
    $log1 = Join-Path $Work 'install1.log'

    $pwsh = if ($PSVersionTable.PSVersion.Major -ge 6) { 'pwsh' } else { 'powershell' }
    $launch = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $installScript,
        '-TargetHome', $FakeHome
    )
    $proc = Start-Process -FilePath $pwsh -ArgumentList $launch `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log1 -RedirectStandardError "$log1.err"

    if ($proc.ExitCode -eq 0) { Pass "install.ps1 exit 0 (happy path)" }
    else { Fail "install.ps1 exit $($proc.ExitCode)" }

    $expected = @(
        '.claude\skills\hard-gate-installer\SKILL.md',
        '.claude\commands\hard-gate.md',
        '.claude\commands\disable-gate.md'
    )
    foreach ($rel in $expected) {
        $full = Join-Path $FakeHome $rel
        if (Test-Path $full) { Pass "installed $rel" }
        else { Fail "missing $rel" }
    }

    # sha256 comparison
    $pairs = @(
        @{ Src = 'SKILL.md';        Dst = '.claude\skills\hard-gate-installer\SKILL.md' },
        @{ Src = 'hard-gate.md';    Dst = '.claude\commands\hard-gate.md' },
        @{ Src = 'disable-gate.md'; Dst = '.claude\commands\disable-gate.md' }
    )
    foreach ($pair in $pairs) {
        $srcHash = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $RepoRoot $pair.Src)).Hash
        $dstHash = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $FakeHome $pair.Dst)).Hash
        if ($srcHash -eq $dstHash) { Pass "sha256 match for $($pair.Src)" }
        else { Fail "sha256 mismatch for $($pair.Src)" }
    }

    # =====================================================================
    Write-Host ""
    Write-Host "=== TEST 3: re-run creates .bak-* ==="
    Set-Content -Path (Join-Path $FakeHome '.claude\commands\hard-gate.md') -Value 'SENTINEL_MODIFIED'
    Start-Sleep -Seconds 1

    $log2 = Join-Path $Work 'install2.log'
    $proc2 = Start-Process -FilePath $pwsh -ArgumentList $launch `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log2 -RedirectStandardError "$log2.err"

    $backups = @(Get-ChildItem -Path (Join-Path $FakeHome '.claude\commands') `
                 -Filter 'hard-gate.md.bak-*' -ErrorAction SilentlyContinue)
    if ($backups.Count -ge 1) { Pass "backup file created ($($backups.Count))" }
    else { Fail "no backup created" }

    if ($backups.Count -gt 0) {
        $bakContent = (Get-Content $backups[0].FullName -Raw).Trim()
        if ($bakContent -eq 'SENTINEL_MODIFIED') { Pass "backup preserved modified content" }
        else { Fail "backup content was '$bakContent'" }
    }

    $reinstalled = Get-Content (Join-Path $FakeHome '.claude\commands\hard-gate.md') -Raw
    if ($reinstalled -match 'Load and follow') { Pass "reinstalled file has real content" }
    else { Fail "reinstalled file content wrong" }

    # =====================================================================
    Write-Host ""
    Write-Host "=== TEST 4: refuses when sources missing (exit 2) ==="
    $Bare = Join-Path $Work 'bare'
    New-Item -ItemType Directory -Path $Bare -Force | Out-Null
    Copy-Item (Join-Path $Extracted 'install.ps1') (Join-Path $Bare 'install.ps1')

    $bareScript = Join-Path $Bare 'install.ps1'
    $log3 = Join-Path $Work 'install3.log'
    $bareLaunch = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $bareScript,
        '-TargetHome', $FakeHome
    )
    $proc3 = Start-Process -FilePath $pwsh -ArgumentList $bareLaunch `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log3 -RedirectStandardError "$log3.err"

    if ($proc3.ExitCode -eq 2) { Pass "refused with exit 2" }
    else { Fail "expected exit 2, got $($proc3.ExitCode)" }

    $errText = (Get-Content "$log3.err" -Raw -ErrorAction SilentlyContinue)
    if ($errText -and $errText -match 'missing') { Pass "error message mentions 'missing'" }
    else { Fail "no 'missing' in stderr" }
}
finally {
    Remove-Item -Path $Work -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "=============================================="
Write-Host "  Results: PASS=$Script:Pass  FAIL=$Script:Fail"
Write-Host "=============================================="
exit $Script:Fail
