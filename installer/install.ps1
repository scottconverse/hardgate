# hardgate installer - PowerShell (Windows)
# Places SKILL.md, hard-gate.md, and disable-gate.md under <TargetHome>\.claude\
#
# Normal use: just run the script. It defaults TargetHome to $HOME.
# Test/CI use: pass -TargetHome <path> to install into an isolated directory.

[CmdletBinding()]
param(
    [string]$TargetHome = $HOME
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$ClaudeHome  = Join-Path $TargetHome '.claude'
$SkillDir    = Join-Path $ClaudeHome 'skills\hard-gate-installer'
$CommandsDir = Join-Path $ClaudeHome 'commands'

Write-Host 'hardgate installer' -ForegroundColor Cyan
Write-Host '=================='
Write-Host "  Target: $ClaudeHome"
Write-Host ''

# Refuse if source files missing
$Sources = @('SKILL.md', 'hard-gate.md', 'disable-gate.md')
foreach ($f in $Sources) {
    $src = Join-Path $ScriptDir $f
    if (-not (Test-Path $src)) {
        # Write to stderr explicitly — Write-Error under ErrorActionPreference=Stop
        # would throw before reaching `exit 2`, leaving the exit code wrong.
        [Console]::Error.WriteLine("ERROR: missing source file: $src")
        [Console]::Error.WriteLine("       Run this script from the unpacked installer directory.")
        exit 2
    }
}

# Create directories
New-Item -ItemType Directory -Path $SkillDir    -Force | Out-Null
New-Item -ItemType Directory -Path $CommandsDir -Force | Out-Null

# Back up existing files
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
function Backup-IfExists([string]$Path) {
    if (Test-Path $Path) {
        $bak = "$Path.bak-$Stamp"
        Copy-Item $Path $bak
        Write-Host "  backed up: $Path -> $bak"
    }
}
Backup-IfExists (Join-Path $SkillDir    'SKILL.md')
Backup-IfExists (Join-Path $CommandsDir 'hard-gate.md')
Backup-IfExists (Join-Path $CommandsDir 'disable-gate.md')

# Install
Copy-Item (Join-Path $ScriptDir 'SKILL.md')        (Join-Path $SkillDir    'SKILL.md')        -Force
Copy-Item (Join-Path $ScriptDir 'hard-gate.md')    (Join-Path $CommandsDir 'hard-gate.md')    -Force
Copy-Item (Join-Path $ScriptDir 'disable-gate.md') (Join-Path $CommandsDir 'disable-gate.md') -Force

Write-Host ''
Write-Host 'Installed:' -ForegroundColor Green
Write-Host "  $SkillDir\SKILL.md"
Write-Host "  $CommandsDir\hard-gate.md"
Write-Host "  $CommandsDir\disable-gate.md"
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Restart Claude Code / Cowork''s Code tab.'
Write-Host '  2. Type /hard-gate to install your first gate.'
Write-Host ''
Write-Host 'Documentation: https://scottconverse.github.io/hardgate/'
