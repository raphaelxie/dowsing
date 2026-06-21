#!/usr/bin/env bash
# Install Dowsing skill for Claude Code and/or Cursor.
set -euo pipefail

REPO_URL="${DOWSING_REPO_URL:-https://github.com/raphaelxie/dowsing.git}"
CLAUDE_DIR="${HOME}/.claude/skills/dowsing"
CURSOR_DIR="${HOME}/.cursor/skills/dowsing"

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [claude|cursor|all]

  claude  Install to ~/.claude/skills/dowsing
  cursor  Install to ~/.cursor/skills/dowsing
  all     Install to both (default)

Environment:
  DOWSING_REPO_URL  Override git clone URL (default: GitHub repo)

After install:
  pip install -r <skill-dir>/requirements.txt
EOF
}

install_skill() {
  local target="$1"
  local label="$2"

  mkdir -p "$(dirname "$target")"
  if [[ -d "$target/.git" ]]; then
    echo "→ Updating $label at $target"
    git -C "$target" pull --ff-only
  elif [[ -e "$target" ]]; then
    echo "Error: $target exists and is not a git repo." >&2
    exit 1
  else
    echo "→ Cloning $label to $target"
    git clone "$REPO_URL" "$target"
  fi

  echo "→ Installing Python dependencies for $label"
  python3 -m pip install -q -r "$target/requirements.txt"
  echo "✓ $label ready at $target"
}

TARGET="${1:-all}"
case "$TARGET" in
  claude) install_skill "$CLAUDE_DIR" "Claude Code" ;;
  cursor) install_skill "$CURSOR_DIR" "Cursor" ;;
  all)
    install_skill "$CLAUDE_DIR" "Claude Code"
    install_skill "$CURSOR_DIR" "Cursor"
    ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown target: $TARGET" >&2; usage; exit 1 ;;
esac

cat <<'EOF'

Done. Trigger with: 失物占 · 找东西 · lost item · 我的 XX 丢了

Claude Code: restart or start a new session.
Cursor:      skills load automatically; start a new Agent chat.
EOF
