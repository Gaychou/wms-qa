param(
  [ValidateSet("codex", "claude")]
  [string]$Target = "claude",
  [string]$SkillsPath = "",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Cli = Join-Path $SkillRoot "scripts\qa_agent.py"

function Get-PythonCommand {
  # 使用逗号前缀强制返回数组，避免 PowerShell 对单元素数组自动解包为标量字符串
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return ,@("python")
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return ,@("py", "-3")
  }
  throw "python/py was not found in PATH."
}

$PythonCommand = @(Get-PythonCommand)
$argsList = @($Cli, "install-skill", "--target", $Target)
if ($SkillsPath) {
  $argsList += @("--path", $SkillsPath)
}
if ($Force) {
  $argsList += "--force"
}

# 可执行文件 + 其固定参数（如 py -3）合并为完整命令行，再统一追加动态 argsList
$fullCommand = $PythonCommand + $argsList
& $fullCommand[0] @($fullCommand[1..($fullCommand.Count - 1)])

$DestinationRoot = $SkillsPath
if (-not $DestinationRoot) {
  if ($Target -eq "claude") {
    $UserHome = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
    $DestinationRoot = Join-Path $UserHome ".claude\skills"
  } elseif ($env:CODEX_HOME) {
    $DestinationRoot = Join-Path $env:CODEX_HOME "skills"
  } else {
    # 优先使用 Windows 官方保证存在的 USERPROFILE，回退到 PowerShell $HOME
    $UserHome = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
    $DestinationRoot = Join-Path $UserHome ".codex\skills"
  }
}

$Destination = Join-Path $DestinationRoot "quality-assurance-agent"
$BinDir = Join-Path $Destination "bin"
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

$Ps1Shim = Join-Path $BinDir "ming-qa.ps1"
$Ps1Content = @"
param(
  [Parameter(ValueFromRemainingArguments = `$true)]
  [string[]]`$RemainingArgs
)

`$SkillRoot = Split-Path -Parent (Split-Path -Parent `$MyInvocation.MyCommand.Path)
`$Script = Join-Path `$SkillRoot "scripts\qa_agent.py"
`$Python = Get-Command python -ErrorAction SilentlyContinue
if (`$Python) {
  & python `$Script @RemainingArgs
  exit `$LASTEXITCODE
}

`$Py = Get-Command py -ErrorAction SilentlyContinue
if (`$Py) {
  & py -3 `$Script @RemainingArgs
  exit `$LASTEXITCODE
}

throw "python/py not found in PATH."
"@
Set-Content -LiteralPath $Ps1Shim -Value $Ps1Content -Encoding UTF8

$CmdShim = Join-Path $BinDir "ming-qa.cmd"
$CmdContent = @"
@echo off
setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "SKILL_ROOT=%SCRIPT_DIR%.."
set "SCRIPT=%SKILL_ROOT%\scripts\qa_agent.py"

where python >nul 2>nul
if not errorlevel 1 (
  python "%SCRIPT%" %*
  exit /b %errorlevel%
)

where python3 >nul 2>nul
if not errorlevel 1 (
  python3 "%SCRIPT%" %*
  exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%SCRIPT%" %*
  exit /b %errorlevel%
)

echo python3/python/py not found in PATH. 1>&2
exit /b 1
"@
Set-Content -LiteralPath $CmdShim -Value $CmdContent -Encoding ASCII

# 无扩展名的 sh 版 shim，供 Git Bash / MSYS / WSL 直接调用 `ming-qa`
$ShShim = Join-Path $BinDir "ming-qa"
$ShContent = @"
#!/usr/bin/env sh
set -eu
script_dir=`$(CDPATH='' cd -- "`$(dirname -- "`$0")/.." && pwd)
if [ -n "`${PYTHON:-}" ]; then
  python_bin="`$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1; then
  python_bin=python
else
  echo "python3/python not found in PATH" >&2
  exit 1
fi
exec "`$python_bin" "`$script_dir/scripts/qa_agent.py" "`$@"
"@
# 用 LF 行尾 + 无 BOM 写入，避免 sh 因 CRLF/BOM 解析失败
$ShContentLf = $ShContent -replace "`r`n", "`n"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ShShim, $ShContentLf, $Utf8NoBom)

Write-Output "Created shims: $Ps1Shim, $CmdShim, $ShShim"

# 本脚本只把 skill 文件复制到目标 skills 目录，并生成局部 shim。
# 它不会修改你的用户 PATH；想让终端直接敲 ming-qa，把生成的 bin 目录自行加进 PATH。
Write-Output "Install complete."
Write-Output "Skills installed to: $DestinationRoot"
Write-Output "Next: $Destination\bin\ming-qa.ps1 init-project --repo ."
