# --------------------------------------------
# macOS Environment Variables for Compilation/Linking
#
# IMPORTANT: use this .zshrc as a general template guide for MODIFYING YOUR EXISTING
# .zshrc, not as a complete replacement. Your existing .zshrc very likely contains
# settings that are unrelated to Smarter and which you currently need for other
# projects.
#
# About Environment Variables for Compilation/Linking:
#
# - LDFLAGS: Tells the linker where to find libraries (.dylib/.so files) during compilation or when building Python packages with native extensions.
#   Example: export LDFLAGS="-L/path/to/lib" adds /path/to/lib to the library search path.
#
# - CPPFLAGS: Tells the C/C++ preprocessor where to find header files (.h) needed for compiling C/C++ code or Python extensions.
#   Example: export CPPFLAGS="-I/path/to/include" adds /path/to/include to the header search path.
#
# - PKG_CONFIG_PATH: Tells pkg-config where to find .pc files that describe how to compile and link against libraries.
#   Example: export PKG_CONFIG_PATH="/path/to/lib/pkgconfig" helps build tools locate library metadata.
#
# These variables are especially important for building Python scientific packages (like numpy, scipy, lxml) or other software that depends on native libraries installed via Homebrew or other package managers.
#

# 1. kubectl
# -------------------------
export KUBE_CONFIG_PATH="$HOME/.kube/config"

# 2. Docker Buildx
# -------------------------
export COMPOSE_BAKE=true
export PATH="$PATH:/usr/local/bin/docker-compose"


# 3. Python Configuration
# -------------------------
# Use Homebrew Python 3.13 as default
alias python="/usr/local/bin/python3.13"
alias python3="/usr/local/bin/python3.13"
export LDFLAGS="-L/opt/homebrew/opt/python@3.13/lib"
export CPPFLAGS="-I/opt/homebrew/opt/python@3.13/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/python@3.13/lib/pkgconfig"

 # 4. Homebrew Aliases and Shellenv
 # --------------------------------
 #
 # Homebrew can be installed for both ARM (Apple Silicon) and Intel (x86_64)
 # architectures on macOS. Some formulae only work on one architecture.
 #
 # - brew86: Runs Homebrew under Intel emulation for x86_64-only packages.
 # - brewARM: Runs the ARM-native Homebrew (Apple Silicon, default).
 # - brew: Alias for ARM Homebrew for convenience.
 # - eval "$(brewARM shellenv)": Sets up environment variables so your shell
 #   uses the correct Homebrew paths and configuration for ARM.
 #
 # This setup makes it easy to switch between ARM and Intel Homebrew and
 # ensures your shell uses the right environment for most tasks.
 #
export PATH="$PATH:/opt/homebrew/bin:/opt/homebrew/sbin"
alias brew86="arch -x86_64 /usr/local/homebrew/bin/brew"
alias brewARM="/opt/homebrew/bin/brew"
alias brew="/opt/homebrew/bin/brew"
eval "$(brewARM shellenv)"

# 5. Node Version Manager (nvm)
# -----------------------------
export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"
[ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"

# 6. Go
# ------
export PATH="$PATH:$(go env GOPATH)/bin"

# 7. Scientific Python/Math Libraries
# -----------------------------------
export NPY_DISTUTILS_APPEND_FLAGS=1  # For SciPy pip installs
# blis
# -----
# BLIS is a high-performance library for basic linear algebra operations.
# It accelerates matrix and vector math, and is used by numpy, scipy, and
# other scientific Python packages for fast computations.
export LDFLAGS="$LDFLAGS -L/usr/local/opt/blis/lib"

# zlib
# -----
# zlib is a widely used compression library for reading and writing compressed
# data (such as .gz files). It is required by Python, git, and many other tools
# for handling compressed streams and files.
export LDFLAGS="$LDFLAGS -L/usr/local/opt/zlib/lib"
export CPPFLAGS="$CPPFLAGS -I/usr/local/opt/zlib/include"

# zstd
# -----
# Zstandard (zstd) is a modern, fast compression algorithm and library. It
# provides high compression ratios and speed, and is used by many modern tools
# for compressing and decompressing files efficiently.
export LDFLAGS="$LDFLAGS -L/opt/homebrew/Cellar/zstd/1.5.7/lib"
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/Cellar/zstd/1.5.7/include"
# openblas
# -----
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/openblas/lib/pkgconfig"
export OPENBLAS="$(brewARM --prefix openblas)"
export MACOSX_DEPLOYMENT_TARGET=11.6

# 8. Database Client Libraries
# ---------------------
# MariaDB
export PATH="$PATH:/opt/homebrew/opt/mariadb-connector-c/bin"
export LDFLAGS="$LDFLAGS -L/opt/homebrew/opt/mariadb-connector-c/lib"
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/opt/mariadb-connector-c/include"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/mariadb-connector-c/lib/pkgconfig"

# MySQL (sometimes needed for MySQL-specific features or compatibility)
export LDFLAGS="$LDFLAGS -L/opt/homebrew/opt/mysql-client/lib"
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/opt/mysql-client/include"
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/mysql-client/lib/pkgconfig"
export MYSQLCLIENT_CFLAGS=$(/opt/homebrew/opt/mysql-client/bin/mysql_config --cflags)
export MYSQLCLIENT_LDFLAGS=$(/opt/homebrew/opt/mysql-client/bin/mysql_config --libs)

# 9. Crypto/SSL Libraries
# -----------------------
export LDFLAGS="$LDFLAGS -L/opt/homebrew/opt/openssl@1.1/lib"
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/opt/openssl@1.1/include"
export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/openssl@1.1/lib/pkgconfig"

# 10. XML/XSLT/Security Libraries
# ------------------------------
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/opt/libxml2/include -I/opt/homebrew/opt/libxslt/include -I/opt/homebrew/opt/xmlsec1/include"
export LDFLAGS="$LDFLAGS -L/opt/homebrew/opt/libxml2/lib -L/opt/homebrew/opt/libxslt/lib -L/opt/homebrew/opt/xmlsec1/lib"
export CFLAGS="$CFLAGS -I/opt/homebrew/opt/libxml2/include -I/opt/homebrew/opt/libxslt/include -I/opt/homebrew/opt/xmlsec1/include"
export PATH="/opt/homebrew/opt/libxml2/bin:$PATH"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/libxml2/lib/pkgconfig:/opt/homebrew/opt/libxslt/lib/pkgconfig:/opt/homebrew/opt/xmlsec1/lib/pkgconfig"

# 11. lxml (Python XML bindings)
# -----------------------------
export LDFLAGS="$LDFLAGS -L/opt/homebrew/opt/libxslt/lib"
export CPPFLAGS="$CPPFLAGS -I/opt/homebrew/opt/libxslt/include"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/libxslt/lib/pkgconfig"

# 12. geos (Geometry Engine)
# -------------------------
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/geos/lib/"
