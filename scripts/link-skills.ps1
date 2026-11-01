[CmdletBinding()]
param(
    [string]$CodexSkillsPath = $(if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $HOME '.codex\skills' }),
    [string]$AgentSkillsPath = $(Join-Path $HOME '.agents\skills'),
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$plan = @()
$names = @{}

foreach ($bucket in @('engineering', 'productivity', 'in-progress')) {
    $bucketPath = Join-Path $repoRoot "skills\$bucket"
    if (-not (Test-Path -LiteralPath $bucketPath -PathType Container)) { continue }
    foreach ($skill in Get-ChildItem -LiteralPath $bucketPath -Directory) {
        if (-not (Test-Path -LiteralPath (Join-Path $skill.FullName 'SKILL.md') -PathType Leaf)) { continue }
        if ($names.ContainsKey($skill.Name)) { throw "Duplicate skill name: $($skill.Name)" }
        $names[$skill.Name] = $true
        foreach ($root in @($CodexSkillsPath, $AgentSkillsPath) | Select-Object -Unique) {
            $source = $skill.FullName
            $destination = Join-Path ([IO.Path]::GetFullPath($root)) $skill.Name
            $existing = Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
            if ($null -ne $existing) {
                $target = @($existing.Target) | Select-Object -First 1
                if ($existing.LinkType -and $target) {
                    if (-not [IO.Path]::IsPathRooted($target)) { $target = Join-Path $existing.Parent.FullName $target }
                    if ([IO.Path]::GetFullPath($target).TrimEnd('\', '/') -eq $source.TrimEnd('\', '/')) {
                        Write-Output "Already linked: $destination"
                        continue
                    }
                }
                throw "Refusing to overwrite existing skill: $destination"
            }
            $plan += [PSCustomObject]@{ Source = $source; Destination = $destination }
        }
    }
}

foreach ($entry in $plan) {
    if ($DryRun) {
        Write-Output "Would link: $($entry.Destination) -> $($entry.Source)"
        continue
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $entry.Destination) -Force | Out-Null
    try {
        New-Item -ItemType SymbolicLink -Path $entry.Destination -Value $entry.Source -ErrorAction Stop | Out-Null
    } catch {
        if ($env:OS -ne 'Windows_NT') { throw }
        New-Item -ItemType Junction -Path $entry.Destination -Value $entry.Source -ErrorAction Stop | Out-Null
    }
    Write-Output "Linked: $($entry.Destination) -> $($entry.Source)"
}
