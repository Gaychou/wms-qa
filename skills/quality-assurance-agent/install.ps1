param(
  # 规范名 claude-code（与 npx skills 等生态工具一致）；claude 保留为旧别名
  [ValidateSet("codex", "claude-code", "claude")]
  [string]$Target = "claude-code",
  [string]$SkillsPath = "",
  [switch]$Force
)

# 旧名 claude 归一为 claude-code
if ($Target -eq "claude") { $Target = "claude-code" }

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

# 必须显式检查原生命令的退出码。
# $ErrorActionPreference = "Stop" 管不住原生命令的 stderr：只有 PowerShell 把 stderr
# 包成 ErrorRecord 时才会中断。而 CI / 自动化常把 stderr 重定向到文件（OS 层），
# 这时不会被包装——脚本会带着失败的退出码继续跑完，打印 "Install complete." 并以 0 退出。
# 终端里手敲看不出问题，自动化下就是静默失败。
if ($LASTEXITCODE -ne 0) {
  [Console]::Error.WriteLine("install-skill failed (exit $LASTEXITCODE)")
  exit $LASTEXITCODE
}

$DestinationRoot = $SkillsPath
if (-not $DestinationRoot) {
  if ($Target -eq "claude-code") {
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

# 不再生成 bin/ 下的 ming-qa shim：脚本由 skill 通过 ${CLAUDE_SKILL_DIR} 等方式定位，
# 命令由 agent 执行，人不需要在 PATH 上放一个 ming-qa。

# 本脚本只把 skill 文件复制到目标 skills 目录，不修改用户 PATH。
Write-Output "Install complete."
Write-Output "Skills installed to: $DestinationRoot"
Write-Output "Next: open your agent and say"
Write-Output "      use quality-assurance-agent to run acceptance testing on <your module>"
Write-Output "      the skill runs the CLI itself -- no command to type by hand."
