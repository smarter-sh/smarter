
# --------------------------------------------
# Ubuntu/Debian Environment Variables for Compilation/Linking
#
# IMPORTANT: use this .zshrc as a general template guide for MODIFYING YOUR EXISTING
# .zshrc, not as a complete replacement. Your existing .zshrc very likely contains
# settings that are unrelated to Smarter and which you currently need for other
# projects.
#
# These variables help build Python scientific packages (numpy, scipy, lxml, etc.)
# and other software that depends on native libraries installed via apt.
#
# - LDFLAGS: Linker search path for libraries (.so files)
# - CPPFLAGS: Preprocessor search path for headers (.h files)
# - PKG_CONFIG_PATH: Path for pkg-config .pc files
#

# 1. kubectl
# -------------------------
export KUBE_CONFIG_PATH="$HOME/.kube/config"

# 2. Docker Buildx
# -------------------------
export COMPOSE_BAKE=true

# 3. Python Configuration
# -----------------------
# Use system Python 3.10 as default
alias python="/usr/bin/python3.10"
alias python3="/usr/bin/python3.10"

# 4. Node Version Manager (nvm)
# -----------------------------
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# 5. Go
# -------------------------
export PATH="$PATH:$(go env GOPATH)/bin"

# 6. Scientific Python/Math Libraries
# -----------------------------------
export NPY_DISTUTILS_APPEND_FLAGS=1  # For SciPy pip installs
# blis
export LDFLAGS="$LDFLAGS -lblis"
# zlib
export LDFLAGS="$LDFLAGS -lz"
export CPPFLAGS="$CPPFLAGS -I/usr/include"
# zstd
export LDFLAGS="$LDFLAGS -lzstd"
# openblas
export LDFLAGS="$LDFLAGS -lopenblas"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/lib/x86_64-linux-gnu/pkgconfig"

# 7. Database Client Libraries
# ---------------------
# MariaDB
export LDFLAGS="$LDFLAGS -lmariadb"
# MySQL
export LDFLAGS="$LDFLAGS -lmysqlclient"

# 8. Crypto/SSL Libraries
# -----------------------
export LDFLAGS="$LDFLAGS -lssl -lcrypto"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/lib/x86_64-linux-gnu/pkgconfig"

# 9. XML/XSLT/Security Libraries
# ------------------------------
export CPPFLAGS="$CPPFLAGS -I/usr/include/libxml2 -I/usr/include/libxslt"
export LDFLAGS="$LDFLAGS -lxml2 -lxslt"

# 10. geos (Geometry Engine)
# -------------------------
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu/"
