#!/usr/bin/env bash
###############################################################################
# Script to install mysql-client via Homebrew and configure environment
# variables.
###############################################################################


set -e

# Check if mysql-client is already installed
if command -v mysql >/dev/null 2>&1; then
  echo "✅ mysql-client is already installed: $(mysql --version)"
  exit 0
fi

# Detect Homebrew prefix (Apple Silicon vs Intel)
BREW_PREFIX="$(brew --prefix)"

MYSQL_CLIENT_PATH="$BREW_PREFIX/opt/mysql-client"

echo "==> Updating Homebrew..."
brew update

echo "==> Installing mysql-client..."
brew install zstd mysql-client

# Determine shell config file (default to zsh)
SHELL_RC="$HOME/.zshrc"
if [[ "$SHELL" == *"bash" ]]; then
  SHELL_RC="$HOME/.bashrc"
fi

echo "==> Using shell config: $SHELL_RC"

# Helper to append only if not already present
append_if_missing () {
  LINE="$1"
  FILE="$2"
  grep -qxF "$LINE" "$FILE" 2>/dev/null || echo "$LINE" >> "$FILE"
}

echo "==> Configuring environment variables..."

append_if_missing "export PATH=\"$MYSQL_CLIENT_PATH/bin:\$PATH\"" "$SHELL_RC"
append_if_missing "export LDFLAGS=\"-L$MYSQL_CLIENT_PATH/lib\"" "$SHELL_RC"
append_if_missing "export CPPFLAGS=\"-I$MYSQL_CLIENT_PATH/include\"" "$SHELL_RC"
append_if_missing "export PKG_CONFIG_PATH=\"$MYSQL_CLIENT_PATH/lib/pkgconfig\"" "$SHELL_RC"

echo "==> Reloading shell configuration..."
# shellcheck disable=SC1090
source "$SHELL_RC" || true

echo "==> Verifying installation..."
if command -v mysql >/dev/null 2>&1; then
  mysql --version
  echo "✅ mysql-client installed and configured successfully."
else
  echo "⚠️ mysql not found in PATH. Restart your terminal or run:"
  echo "   source $SHELL_RC"
fi
