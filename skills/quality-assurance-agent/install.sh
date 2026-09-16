#!/usr/bin/env sh
set -eu

skill_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cli="$skill_root/scripts/qa_agent.py"

if [ -n "${PYTHON:-}" ]; then
  python_bin="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1; then
  python_bin=python
else
  echo "python3/python not found in PATH" >&2
  exit 1
fi

skills_path=""
force=""
target="claude"

while [ $# -gt 0 ]; do
  case "$1" in
    --skills-path)
      skills_path=${2:-}
      shift 2
      ;;
    --force)
      force="--force"
      shift
      ;;
    --target)
      target=${2:-claude}
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./install.sh [--target claude|codex] [--skills-path PATH] [--force]

For macOS, Linux, and Windows Git Bash / MSYS / WSL.
On native Windows CMD / PowerShell, use install.ps1 instead.

  --target claude|codex Install into Claude Code or Codex skills dir (default claude)
  --skills-path PATH   Install into a custom skills directory
  --force              Overwrite an existing installation

This script only copies skill files into the target skills directory. It does
not modify your shell profile (~/.bashrc, ~/.zshrc, ~/.bash_profile).

Preferred install methods, no clone required:
  npx skills add mingdui/ming-qa -g
  /plugin marketplace add mingdui/ming-qa
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

install_args="$cli install-skill --target $target"
if [ -n "$skills_path" ]; then
  install_args="$install_args --path $skills_path"
fi
if [ -n "$force" ]; then
  install_args="$install_args $force"
fi

# shellcheck disable=SC2086
"$python_bin" $install_args

if [ -n "$skills_path" ]; then
  destination_root="$skills_path"
elif [ "$target" = "claude" ]; then
  destination_root="$HOME/.claude/skills"
elif [ -n "${CODEX_HOME:-}" ]; then
  destination_root="$CODEX_HOME/skills"
else
  destination_root="$HOME/.codex/skills"
fi

printf 'Install complete.\n'
printf 'Skills installed to: %s\n' "$destination_root"
printf 'Next: %s init-project --repo .\n' "$destination_root/quality-assurance-agent/bin/ming-qa"
