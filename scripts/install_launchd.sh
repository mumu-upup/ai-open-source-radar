#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PLIST_TEMPLATE="$ROOT_DIR/launchd/com.codex.ai-open-source-daily.plist"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS/com.codex.ai-open-source-daily.plist"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python3}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN=$(command -v python3)
fi

mkdir -p "$LAUNCH_AGENTS" "$ROOT_DIR/logs"
sed -e "s|__ROOT__|$ROOT_DIR|g" -e "s|__PYTHON__|$PYTHON_BIN|g" "$PLIST_TEMPLATE" > "$PLIST_PATH"
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
echo "Installed $PLIST_PATH; runs daily at 08:00 Asia/Shanghai host time."
