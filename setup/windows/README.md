# Smarter Development Environment for Windows

The Smarter developer environment is Docker based, which helps to abstract away
many of the platform's run-time dependencies. However, there are still quite a
few things you'll need to install in order to get your Smarter developer
environment completely up and running.

## Local System Dependencies

Use setup.ps1 to automate installation where possible.

### Developer Environment IDE

| Package             | Description                                 |
| ------------------- | ------------------------------------------- |
| VS Code             | Extensible integrated developer environment |
| Visual Studio Build | C/C++ build tools (MSVC, Windows SDK)       |
| nvm-windows         | Node Version Manager for Windows            |
| Homebrew (optional) | Package manager for Windows (alternative)   |

### Build, Deploy & Management Tools

| Package        | Description                                     |
| -------------- | ----------------------------------------------- |
| Docker Desktop | Docker, docker-compose and docker CLI           |
| AWS CLI        | AWS CLI for managing AWS services               |
| kubectl        | Kubernetes CLI for cluster management           |
| Go             | Go programming language (Smarter CLI)           |
| jq             | Command-line JSON processor for CI-CD           |
| Node.js        | Node.js runtime (JS tooling and ReactJS builds) |

### Python Virtual Environment Dependencies

These low-level packages are only required for creating the local Python virtual
environment, which itself is only used for syntax and type checking inside of
VS Code. These are not actually used at run-time.

| Package             | Description                               |
| ------------------- | ----------------------------------------- |
| Python 3.13         | Python 3.13 interpreter                   |
| BLIS/OpenBLAS       | Math acceleration (BLAS-like)             |
| zlib                | Compression library for Python and others |
| zstd                | Fast lossless compression                 |
| libffi              | C extension support for Python            |
| OpenSSL             | SSL/TLS cryptography library              |
| libxml2             | XML parsing for Python and tools          |
| libxslt             | XSLT processing for XML transforms        |
| SQLite              | Lightweight SQL database (Python default) |
| MariaDB Connector C | MariaDB/MySQL client library              |
| GEOS                | Geometry engine for geospatial libs       |
| MySQL Client        | MySQL command-line client tools           |
