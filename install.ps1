# axs installer for Windows PowerShell:
#   irm https://raw.githubusercontent.com/kuwa72/ax/main/install.ps1 | iex
# Env:
#   AXS_BIN_DIR  install target dir   (default: $env:USERPROFILE\.local\bin)
#   AXS_REF      git ref to fetch     (default: main)
#   AXS_SRC      full source URL      (overrides AXS_REF)
$ErrorActionPreference = "Stop"

$binDir = $env:AXS_BIN_DIR
if (-not $binDir) { $binDir = Join-Path $env:USERPROFILE ".local\bin" }
$ref = $env:AXS_REF
if (-not $ref) { $ref = "main" }
$src = $env:AXS_SRC
if (-not $src) {
    $src = "https://raw.githubusercontent.com/kuwa72/ax/$ref/axs"
}

function Warn($msg) { Write-Host "axs: warn: $msg" -ForegroundColor Yellow }

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Warn "python not found in PATH (required)"
}
if (-not (Get-Command fzf -ErrorAction SilentlyContinue)) {
    Warn "fzf not found in PATH (required, >=0.44)"
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$dst = Join-Path $binDir "axs"
Invoke-WebRequest -UseBasicParsing -Uri $src -OutFile $dst

# Windows has no shebang support, so an extension-less Python script is not
# directly runnable. Install a .cmd shim that forwards to python.
$shim = Join-Path $binDir "axs.cmd"
$shimBody = "@echo off`r`npython `"%~dp0axs`" %*`r`n"
[System.IO.File]::WriteAllText($shim, $shimBody, [System.Text.Encoding]::ASCII)

Write-Host "axs: installed to $dst"
$pathDirs = $env:PATH -split ";"
if ($pathDirs -notcontains $binDir) {
    Write-Host "axs: add to PATH: setx PATH `"$binDir;`$env:PATH`""
}
