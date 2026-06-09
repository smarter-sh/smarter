#!/usr/bin/env bash
###############################################################################
# Install Homebrew packages required to build key Python dependencies on macOS
# for this project (mariadb, lxml, pillow, and crypto-related extensions).
#
# Usage:
#   ./scripts/install-macos-python-build-deps.sh
#   ./scripts/install-macos-python-build-deps.sh --persist
#
# Options:
#   --persist    Append environment exports to shell profile (~/.zshrc or
#                ~/.bashrc) if they are missing.
#   --no-update  Skip brew update.
###############################################################################

set -euo pipefail

PERSIST_ENV=0
DO_UPDATE=1

for arg in "$@"; do
  case "$arg" in
    --persist)
      PERSIST_ENV=1
      ;;
    --no-update)
      DO_UPDATE=0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--persist] [--no-update]"
      exit 1
      ;;
  esac
done

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required but not installed."
  echo "Install it first: https://brew.sh"
  exit 1
fi

BREW_PREFIX="$(brew --prefix)"

PACKAGES=(
  pkg-config
  mariadb-connector-c
  openssl@3
  libffi
  libxml2
  libxslt
  zlib
  jpeg-turbo
  libtiff
  little-cms2
  webp
  freetype
  openjpeg
  redis
)

if [[ "$DO_UPDATE" -eq 1 ]]; then
  echo "==> Updating Homebrew..."
  brew update
fi

echo "==> Installing required Homebrew packages..."
brew install "${PACKAGES[@]}"

# Build flags to help pip compile C extensions when wheel fallback is needed.
OPENSSL_PREFIX="$(brew --prefix openssl@3)"
LIBFFI_PREFIX="$(brew --prefix libffi)"
LIBXML2_PREFIX="$(brew --prefix libxml2)"
LIBXSLT_PREFIX="$(brew --prefix libxslt)"
MARIADB_PREFIX="$(brew --prefix mariadb-connector-c)"

EXPORTS=(
  "export PKG_CONFIG_PATH=\"$MARIADB_PREFIX/lib/pkgconfig:$OPENSSL_PREFIX/lib/pkgconfig:$LIBFFI_PREFIX/lib/pkgconfig:$LIBXML2_PREFIX/lib/pkgconfig:$LIBXSLT_PREFIX/lib/pkgconfig:\${PKG_CONFIG_PATH:-}\""
  "export LDFLAGS=\"-L$MARIADB_PREFIX/lib -L$OPENSSL_PREFIX/lib -L$LIBFFI_PREFIX/lib -L$LIBXML2_PREFIX/lib -L$LIBXSLT_PREFIX/lib \${LDFLAGS:-}\""
  "export CPPFLAGS=\"-I$MARIADB_PREFIX/include -I$OPENSSL_PREFIX/include -I$LIBFFI_PREFIX/include -I$LIBXML2_PREFIX/include/libxml2 -I$LIBXSLT_PREFIX/include \${CPPFLAGS:-}\""
)

append_if_missing() {
  local line="$1"
  local file="$2"
  grep -qxF "$line" "$file" 2>/dev/null || echo "$line" >> "$file"
}

echo ""
echo "==> Environment exports for this shell session"
for line in "${EXPORTS[@]}"; do
  echo "$line"
  # shellcheck disable=SC1090
  eval "$line"
done

if [[ "$PERSIST_ENV" -eq 1 ]]; then
  SHELL_RC="$HOME/.zshrc"
  if [[ "${SHELL:-}" == *"bash" ]]; then
    SHELL_RC="$HOME/.bashrc"
  fi

  echo ""
  echo "==> Persisting exports to $SHELL_RC"
  for line in "${EXPORTS[@]}"; do
    append_if_missing "$line" "$SHELL_RC"
  done
  echo "Done. Open a new terminal or run: source $SHELL_RC"
fi

echo ""
echo "✅ Finished installing Homebrew dependencies for Python requirements."
echo "Next: pip install -r smarter/requirements/base.txt"
