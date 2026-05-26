# Smarter Development Environment for macOS

The Smarter developer environment is Docker based, which helps to abstract
away many of the platform's run-time dependencies. However, there are
still quite a few things you'll need to install in order to get your Smarter
developer environment completely up and running.

## Local System Dependencies

Use setup.sh to automate installation where possible.

### Developer Environment IDE

| Package            | Description                                 |
| ------------------ | ------------------------------------------- |
| VS Code            | Extensible integrated developer environment |
| Xcode              | Apple macOS development environment         |
| Xcode Command Line | C/C++ build tools (clang, make)             |
| Homebrew           | Package manager for macOS                   |

### Build, Deploy & Management Tools

| Package        | Description                                     |
| -------------- | ----------------------------------------------- |
| k9s            | Kubernetes ASCII console admin software         |
| awscli         | AWS CLI for managing AWS services               |
| kubectl        | Kubernetes CLI for cluster management           |
| Docker Desktop | Docker, docker-compose and docker CLI           |
| jq             | Command-line JSON processor for CI-CD           |
| go             | Go programming language (Smarter CLI)           |
| node           | Node.js runtime (JS tooling and ReactJS builds) |
| nvm            | Node Version Manager                            |

### Python Virtual Environment Dependencies

These low-level packages are only required for creating the local
Python virtual environment which itself is only used for syntax and type
checking inside of VS Code. That is, these are not actually used at run-time.

| Package             | Description                                    |
| ------------------- | ---------------------------------------------- |
| python@3.13         | Python 3.13 interpreter                        |
| gcc                 | GNU Compiler Collection for native code builds |
| sqlite              | Lightweight SQL database (Python default)      |
| mariadb-connector-c | MariaDB/MySQL client library                   |
| mysql-client        | MySQL command-line client tools                |
| blis                | Math acceleration (BLAS-like)                  |
| zlib                | Compression library for Python and others      |
| zstd                | Fast lossless compression                      |
| openblas            | Optimized BLAS for numpy/scipy                 |
| libffi              | C extension support for Python                 |
| openssl             | SSL/TLS cryptography library                   |
| libxml2             | XML parsing for Python and tools               |
| libxslt             | XSLT processing for XML transforms             |
| geos                | Geometry engine for geospatial libs            |
