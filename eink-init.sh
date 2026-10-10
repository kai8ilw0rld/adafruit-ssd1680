#!/bin/bash

# The project folder is wherever this script lives
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PYTHON="$PROJECT_DIR/env/bin/python"
LOG="$PROJECT_DIR/eink.log"

# Show the info screen once at boot (log is reset on each boot)
"$PYTHON" "$PROJECT_DIR/info.py" > "$LOG" 2>&1

# Hand over to the button loop (replaces this shell, so no deactivate needed)
exec "$PYTHON" -u "$PROJECT_DIR/buttoncontrol.py" >> "$LOG" 2>&1