# Changelog


All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.8.1]

### Changed

- Charts.yaml artifacthub.io/changes

## [0.8.0]

### Added

- Added built-in MySQL and MariaDB support as alternatives to external databases.
- Added support for configuring environment variables via Helm values.

## [0.7.7]

### Changed

- Setup ArtifactHub annotations for better integration.

## [0.7.6]

### Added

- Support for Kubernetes 1.28+.

### Changed

- Updated Redis dependency to 23.1.1.

### Fixed

- Multi-architecture builds for AMD64 and ARM64.

### Security

- Remove platform argument to support AWS Graviton instances.
