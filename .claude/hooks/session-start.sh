#!/bin/bash
set -euo pipefail

# Only run in remote (Codespace) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install backend Python dependencies
pip install -r "$CLAUDE_PROJECT_DIR/backend/requirements.txt"

# Install frontend Node.js dependencies
cd "$CLAUDE_PROJECT_DIR/frontend"
npm install
