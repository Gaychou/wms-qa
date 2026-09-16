param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$RemainingArgs
)

$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $SkillRoot "scripts\qa_agent.py"
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
  & python $Script @RemainingArgs
  exit $LASTEXITCODE
}

$Py = Get-Command py -ErrorAction SilentlyContinue
if ($Py) {
  & py -3 $Script @RemainingArgs
  exit $LASTEXITCODE
}

throw "python/py not found in PATH."
