<#
.SYNOPSIS
Copy Claude Code Game Studios into a project: a new folder or an existing repository.

.DESCRIPTION
scripts/adopt.sh does the same in bash; ADOPTING.md is the guide, and
studio-tests/test_adopt_scripts.py checks that both agree.

Adds and overwrites the framework-owned files below, and never deletes a file.
Keeps the project's own .claude/settings.json, .claude/agent-models.yaml,
technical-preferences.md, CLAUDE.md, AGENTS.md and project.yaml. Checks every
path it would write before writing any, and refuses a link, a folder where a
file goes, or a read-only file it would change. No network and no git.
Exit: 0 done, 1 refused or a write failed, 2 usage.

.EXAMPLE
pwsh scripts/adopt.ps1 -Target C:\src\my-game -DryRun

.EXAMPLE
pwsh scripts/adopt.ps1 C:\src\my-game --dry-run
#>
#Requires -Version 7.0
param(
    [Parameter(Position = 0)][string]$Target,
    [switch]$DryRun,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- The framework-owned paths: the one list this script copies -------------
$FrameworkDirs = @('.claude/agents', '.claude/skills', '.claude/rules', '.claude/hooks',
    '.claude/scripts', '.claude/engines', '.claude/genres', '.claude/docs')
$FrameworkFiles = @('.claude/statusline.sh')
# The MIT notice goes with the copy.
$LicenseSrc = 'LICENSE'
$LicenseDest = '.claude/LICENSE'
# Copied when the target has none, then the project's own (UPGRADING.md).
$ProjectOwned = '.claude/docs/technical-preferences.md'
# Copied when the target has none, then kept; a changed one gets the
# framework's copy beside it, for a merge by hand.
$AgentModels = '.claude/agent-models.yaml'
$AgentModelsSidecar = '.claude/agent-models.ccgs.yaml'
$AgentModelsReason = "the project's own; merge $AgentModelsSidecar into it by hand, then run bash .claude/scripts/agent-models.sh sync"
$Settings = '.claude/settings.json'
$SettingsSidecar = '.claude/settings.ccgs.json'
$SettingsReason = "the project's own; merge $SettingsSidecar into it by hand"
$GitignoreComment = '# Claude Code Game Studios: session state and logs the hooks write, personal settings, worktrees'
$GitignoreLines = @('production/session-state/', 'production/session-logs/', 'project.local.yaml', '.claude/worktrees/')
$GitattributesComment = '# Claude Code Game Studios: bash runs the hooks and helpers, so they stay LF on Windows'
$GitattributesLines = @('.claude/**/*.sh text eol=lf', '.claude/**/*.awk text eol=lf', '.claude/**/*.tsv text eol=lf')

function Write-Usage([switch]$ToError) {
    $text = "Usage: pwsh scripts/adopt.ps1 <target-dir> [--dry-run]   (or -Target <dir> -DryRun)`n" +
        'Copies the Claude Code Game Studios framework into <target-dir>. See ADOPTING.md.'
    if ($ToError) { [Console]::Error.WriteLine($text) } else { Write-Output $text }
}

foreach ($arg in @($Rest | Where-Object { $null -ne $_ })) {
    switch -CaseSensitive ($arg) {
        '--dry-run' { $DryRun = [switch]::new($true); continue }
        { $_ -in '-h', '--help' } { $Help = [switch]::new($true); continue }
        { $_.StartsWith('-') } { Write-Usage -ToError; [Console]::Error.WriteLine("Unknown option: $arg"); exit 2 }
        default {
            if ($Target) { Write-Usage -ToError; [Console]::Error.WriteLine('One target only.'); exit 2 }
            $Target = $arg
        }
    }
}
if ($Help) { Write-Usage; exit 0 }
if (-not $Target) { Write-Usage -ToError; exit 2 }

$Sep = [IO.Path]::DirectorySeparatorChar
function Get-LinkTarget([string]$Path) {
    try { return [IO.FileInfo]::new($Path).LinkTarget } catch { return $null }
}
# The path with every symlink and junction on the way resolved, as bash's
# `pwd -P` gives it; GetFullPath also expands Windows short (8.3) names.
function Resolve-RealPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    for ($hop = 0; $hop -lt 64; $hop++) {
        $root = [IO.Path]::GetPathRoot($full)
        $parts = @($full.Substring($root.Length).Split([char[]]@('\', '/'), [StringSplitOptions]::RemoveEmptyEntries))
        $cur = $root
        $next = $null
        for ($i = 0; $i -lt $parts.Count; $i++) {
            $cur = [IO.Path]::Combine($cur, $parts[$i])
            $link = Get-LinkTarget $cur
            if ($link) {
                $next = [IO.Path]::GetFullPath($link, [IO.Path]::GetDirectoryName($cur))
                if ($i + 1 -lt $parts.Count) { $next = [IO.Path]::Combine(@($next) + $parts[($i + 1)..($parts.Count - 1)]) }
                break
            }
        }
        if (-not $next) { return $cur.TrimEnd('\', '/') }
        $full = [IO.Path]::GetFullPath($next)
    }
    throw "Too many links in $Path"
}

$Src = Resolve-RealPath (Join-Path $PSScriptRoot '..')
if (-not (Test-Path -LiteralPath $Target)) { [Console]::Error.WriteLine("Refused: $Target does not exist."); exit 1 }
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { [Console]::Error.WriteLine("Refused: $Target is not a directory."); exit 1 }
$Tgt = Resolve-RealPath (Resolve-Path -LiteralPath $Target).ProviderPath

$Comparison = if ($IsWindows) { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
$SrcKey = $Src.TrimEnd('\', '/') + $Sep
$TgtKey = $Tgt.TrimEnd('\', '/') + $Sep
if ($TgtKey.StartsWith($SrcKey, $Comparison)) {
    [Console]::Error.WriteLine("Refused: $Target is the framework repository or inside it."); exit 1
}

function Get-Full([string]$Root, [string]$Rel) { Join-Path $Root ($Rel -replace '/', $Sep) }
function Stop-Refused([string]$Heading, [Collections.Generic.List[string]]$Problems) {
    $Problems.Sort([StringComparer]::Ordinal)
    [Console]::Error.WriteLine("Refused: $Heading")
    foreach ($p in $Problems) { [Console]::Error.WriteLine($p) }
    [Console]::Error.WriteLine('Nothing was written.')
    exit 1
}

# --- Every path the run may write, checked before anything is written -------
$list = [Collections.Generic.List[string]]::new()
foreach ($dir in $FrameworkDirs) {
    $full = Get-Full $Src $dir
    if (-not (Test-Path -LiteralPath $full -PathType Container)) { continue }
    foreach ($file in [IO.Directory]::EnumerateFiles($full, '*', [IO.SearchOption]::AllDirectories)) {
        $list.Add($file.Substring($SrcKey.Length).Replace('\', '/'))
    }
}
$list.Sort([StringComparer]::Ordinal)
$dests = @($FrameworkFiles) + @($LicenseDest, $AgentModels, $AgentModelsSidecar, $Settings, $SettingsSidecar,
    'CLAUDE.md', '.gitignore', '.gitattributes') + $list

$problems = [Collections.Generic.List[string]]::new()
$parents = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($rel in $dests) {
    $p = Get-Full $Tgt $rel
    if (Get-LinkTarget $p) { $problems.Add("  $rel (a link)") }
    elseif ([IO.Directory]::Exists($p)) { $problems.Add("  $rel (a folder where a file goes)") }
    $dir = $rel
    while ($dir.Contains('/')) {
        $dir = $dir.Substring(0, $dir.LastIndexOf('/'))
        if (-not $parents.Add($dir)) { break }
    }
}
foreach ($dir in $parents) {
    $p = Get-Full $Tgt $dir
    if (Get-LinkTarget $p) { $problems.Add("  $dir (a link)") }
    elseif ([IO.File]::Exists($p)) { $problems.Add("  $dir (a file where a folder goes)") }
}
if ($problems.Count) { Stop-Refused "$Target has paths this script would write through or over:" $problems }

# --- The plan: every action line, and the writes they stand for -------------
$Counts = [ordered]@{ ADD = 0; OVERWRITE = 0; UNCHANGED = 0; SKIP = 0; APPEND = 0 }
$Lines = [Collections.Generic.List[string]]::new()
$CopyQueue = [Collections.Generic.List[string[]]]::new()
$Changes = [Collections.Generic.List[string]]::new()
function Add-Plan([string]$Action, [string]$Path, [string]$Reason) {
    if ($Reason) { $Lines.Add("$Action $Path ($Reason)") } else { $Lines.Add("$Action $Path") }
    $Counts[$Action]++
    if ($Action -in 'OVERWRITE', 'APPEND') { $Changes.Add($Path) }
}
function Test-SameFile([string]$A, [string]$B) {
    $fa = [IO.FileInfo]::new($A); $fb = [IO.FileInfo]::new($B)
    if ($fa.Length -ne $fb.Length) { return $false }
    $ha = [Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($A))
    $hb = [Security.Cryptography.SHA256]::HashData([IO.File]::ReadAllBytes($B))
    return [Convert]::ToHexString($ha) -eq [Convert]::ToHexString($hb)
}
# One framework file to a target path: ADD, OVERWRITE or UNCHANGED; $Keep turns
# OVERWRITE into SKIP.
function Add-FilePlan([string]$FromRel, [string]$ToRel, [string]$Keep) {
    $to = Get-Full $Tgt $ToRel
    if (-not [IO.File]::Exists($to)) { Add-Plan ADD $ToRel; $CopyQueue.Add(@($FromRel, $ToRel)) }
    elseif (Test-SameFile (Get-Full $Src $FromRel) $to) { Add-Plan UNCHANGED $ToRel }
    elseif ($Keep) { Add-Plan SKIP $ToRel $Keep }
    else { Add-Plan OVERWRITE $ToRel; $CopyQueue.Add(@($FromRel, $ToRel)) }
}
# A file that is the project's own once it exists; a changed one is kept and
# the framework's copy goes to the sidecar.
function Add-KeptPlan([string]$Rel, [string]$Sidecar, [string]$Reason) {
    $to = Get-Full $Tgt $Rel
    if (-not [IO.File]::Exists($to)) { Add-Plan ADD $Rel; $CopyQueue.Add(@($Rel, $Rel)) }
    elseif (Test-SameFile (Get-Full $Src $Rel) $to) { Add-Plan UNCHANGED $Rel }
    else { Add-Plan SKIP $Rel $Reason; Add-FilePlan $Rel $Sidecar }
}

foreach ($rel in $FrameworkFiles) {
    if ([IO.File]::Exists((Get-Full $Src $rel))) { Add-FilePlan $rel $rel }
}
if ([IO.File]::Exists((Get-Full $Src $LicenseSrc))) { Add-FilePlan $LicenseSrc $LicenseDest }
if ([IO.File]::Exists((Get-Full $Src $AgentModels))) { Add-KeptPlan $AgentModels $AgentModelsSidecar $AgentModelsReason }
foreach ($rel in $list) {
    $keep = if ($rel -eq $ProjectOwned) { "the project's own once it exists" } else { '' }
    Add-FilePlan $rel $rel $keep
}

Add-KeptPlan $Settings $SettingsSidecar $SettingsReason

$ownInstructions = @('CLAUDE.md', '.claude/CLAUDE.md', 'AGENTS.md') |
    Where-Object { Test-Path -LiteralPath (Get-Full $Tgt $_) } | Select-Object -First 1
if (-not $ownInstructions) { Add-Plan ADD CLAUDE.md; $CopyQueue.Add(@('CLAUDE.md', 'CLAUDE.md')) }
elseif ($ownInstructions -eq 'CLAUDE.md' -and (Test-SameFile (Get-Full $Src 'CLAUDE.md') (Get-Full $Tgt 'CLAUDE.md'))) {
    Add-Plan UNCHANGED CLAUDE.md
}
else { Add-Plan SKIP CLAUDE.md "the project has $ownInstructions; merge the framework's instructions by hand, see ADOPTING.md" }

if (Test-Path -LiteralPath (Get-Full $Tgt 'project.yaml')) { Add-Plan SKIP project.yaml "the project's own" }
else { Add-Plan SKIP project.yaml 'never written: run /start or /setup-engine, or write it by hand, see ADOPTING.md' }

# The lines a file lacks.
function Get-MissingLines([string]$Rel, [string[]]$Want) {
    $file = Get-Full $Tgt $Rel
    $text = if ([IO.File]::Exists($file)) { [IO.File]::ReadAllText($file) } else { '' }
    $have = $text -split "`n" | ForEach-Object { $_.TrimEnd("`r") }
    return @($Want | Where-Object { $have -cnotcontains $_ })
}
function Add-AppendPlan([string]$Rel, [string[]]$Missing) {
    if ($Missing.Count -eq 0) { Add-Plan UNCHANGED $Rel }
    elseif (-not [IO.File]::Exists((Get-Full $Tgt $Rel))) { Add-Plan ADD $Rel }
    else { Add-Plan APPEND $Rel ($Missing -join ' ') }
}
$gitignoreMissing = @(Get-MissingLines '.gitignore' $GitignoreLines)
$gitattributesMissing = @(Get-MissingLines '.gitattributes' $GitattributesLines)
Add-AppendPlan '.gitignore' $gitignoreMissing
Add-AppendPlan '.gitattributes' $gitattributesMissing

# A read-only file the run would change refuses the whole run (a Perforce
# workspace keeps files read-only until they are checked out).
$readOnly = [Collections.Generic.List[string]]::new()
foreach ($rel in $Changes) {
    if ([IO.File]::GetAttributes((Get-Full $Tgt $rel)).HasFlag([IO.FileAttributes]::ReadOnly)) { $readOnly.Add("  $rel") }
}
if ($readOnly.Count) {
    Stop-Refused "these files in $Target are read-only and the run would change them; make them writable (in Perforce, check them out) and run again:" $readOnly
}

# --- Report, then write ------------------------------------------------------
Write-Output "Target: $Target"
if ($DryRun) { Write-Output 'Dry run: nothing is written.' }
$Lines | ForEach-Object { Write-Output $_ }

function Stop-Failed([string]$Rel) {
    [Console]::Error.WriteLine("Copy failed: $Rel could not be written in ${Target}; the lines above may be only partly done.")
    exit 1
}
# Append the missing lines once, in the file's own line endings.
function Add-Lines([string]$Rel, [string]$Comment, [string[]]$Missing) {
    if ($Missing.Count -eq 0) { return }
    $file = Get-Full $Tgt $Rel
    try {
        $text = if ([IO.File]::Exists($file)) { [IO.File]::ReadAllText($file) } else { '' }
        $eol = if ($text.Contains("`r")) { "`r`n" } else { "`n" }
        $add = ''
        if ($text.Length -gt 0) {
            if (-not $text.EndsWith("`n")) { $add = $eol }
            $add += $eol
        }
        $add += (@($Comment) + $Missing | ForEach-Object { "$_$eol" }) -join ''
        [IO.File]::AppendAllText($file, $add, [Text.UTF8Encoding]::new($false))
    }
    catch { Stop-Failed $Rel }
}

if (-not $DryRun) {
    foreach ($pair in $CopyQueue) {
        $to = Get-Full $Tgt $pair[1]
        try {
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($to))
            [IO.File]::Copy((Get-Full $Src $pair[0]), $to, $true)
        }
        catch { Stop-Failed $pair[1] }
    }
    Add-Lines '.gitignore' $GitignoreComment $gitignoreMissing
    Add-Lines '.gitattributes' $GitattributesComment $gitattributesMissing
}

Write-Output ("Summary: {0} added, {1} overwritten, {2} unchanged, {3} skipped, {4} appended." -f
    $Counts.ADD, $Counts.OVERWRITE, $Counts.UNCHANGED, $Counts.SKIP, $Counts.APPEND)
if ($DryRun) { Write-Output 'Dry run: nothing was written.' }
exit 0
