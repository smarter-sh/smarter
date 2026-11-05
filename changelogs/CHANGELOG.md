# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.42.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.6...v0.42.7-alpha.1) (2026-11-05)

### Bug Fixes

* **helm:** keep the autoscaler from evicting the only redis pod ([6fcf2eb](https://github.com/smarter-sh/smarter/commit/6fcf2eb6649699b24548efd7632654ff566d4d8e)), closes [#929](https://github.com/smarter-sh/smarter/issues/929)

## [0.42.6](https://github.com/smarter-sh/smarter/compare/v0.42.5...v0.42.6) (2026-11-05)

### Bug Fixes

- **django:** match hashed ids only as whole url path segments ([e47268c](https://github.com/smarter-sh/smarter/commit/e47268cced22801c2d39b250e7c002a1c3d0cf57)), closes [#924](https://github.com/smarter-sh/smarter/issues/924)
- **prompt:** save long tool call arguments, don't retry DataError ([f546cd1](https://github.com/smarter-sh/smarter/commit/f546cd1979fd62e712da1b50e4c320f84ef47853)), closes [#923](https://github.com/smarter-sh/smarter/issues/923)

## [0.42.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.5...v0.42.6-alpha.1) (2026-11-05)

### Bug Fixes

- **django:** match hashed ids only as whole url path segments ([e47268c](https://github.com/smarter-sh/smarter/commit/e47268cced22801c2d39b250e7c002a1c3d0cf57)), closes [#924](https://github.com/smarter-sh/smarter/issues/924)
- **prompt:** save long tool call arguments, don't retry DataError ([f546cd1](https://github.com/smarter-sh/smarter/commit/f546cd1979fd62e712da1b50e4c320f84ef47853)), closes [#923](https://github.com/smarter-sh/smarter/issues/923)

## [0.42.5](https://github.com/smarter-sh/smarter/compare/v0.42.4...v0.42.5) (2026-11-05)

### Bug Fixes

- **llmclient:** log a request without a body at DEBUG in handle_llmclient_called(), not ERROR ([6f030a3](https://github.com/smarter-sh/smarter/commit/6f030a309d617c23fb7d557eef2c50af452ba421)), closes [#925](https://github.com/smarter-sh/smarter/issues/925)
- **settings:** keep the Fernet key out of its validation error ([9e0da64](https://github.com/smarter-sh/smarter/commit/9e0da644d27b18aa5c2532c1c8b18bf093d4bde7))

### Refactoring

- **api:** delete the per-app api urlconfs that nothing mounts ([16f0a5c](https://github.com/smarter-sh/smarter/commit/16f0a5c4ada9e0ccc23fa2eac25723226ab38ff6))
- **api:** move the console's React endpoints under /api/web/ ([0928951](https://github.com/smarter-sh/smarter/commit/0928951c891503f37bc307d7aff58523ad87839e))

## [0.42.5-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.5-alpha.1...v0.42.5-alpha.2) (2026-11-05)

### Bug Fixes

- **llmclient:** log a request without a body at DEBUG in handle_llmclient_called(), not ERROR ([6f030a3](https://github.com/smarter-sh/smarter/commit/6f030a309d617c23fb7d557eef2c50af452ba421)), closes [#925](https://github.com/smarter-sh/smarter/issues/925)

## [0.42.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.4...v0.42.5-alpha.1) (2026-11-05)

### Bug Fixes

- **settings:** keep the Fernet key out of its validation error ([9e0da64](https://github.com/smarter-sh/smarter/commit/9e0da644d27b18aa5c2532c1c8b18bf093d4bde7))

### Refactoring

- **api:** delete the per-app api urlconfs that nothing mounts ([16f0a5c](https://github.com/smarter-sh/smarter/commit/16f0a5c4ada9e0ccc23fa2eac25723226ab38ff6))
- **api:** move the console's React endpoints under /api/web/ ([0928951](https://github.com/smarter-sh/smarter/commit/0928951c891503f37bc307d7aff58523ad87839e))

## [0.42.4](https://github.com/smarter-sh/smarter/compare/v0.42.3...v0.42.4) (2026-11-05)

### Bug Fixes

- **deps:** bump pinned python requirements to their latest releases ([d4743e3](https://github.com/smarter-sh/smarter/commit/d4743e3c939daba89636760e0b4ef5219c9dd3df))

## [0.42.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.3...v0.42.4-alpha.1) (2026-11-05)

### Bug Fixes

- **deps:** bump pinned python requirements to their latest releases ([d4743e3](https://github.com/smarter-sh/smarter/commit/d4743e3c939daba89636760e0b4ef5219c9dd3df))

## [0.42.3](https://github.com/smarter-sh/smarter/compare/v0.42.2...v0.42.3) (2026-11-05)

### Bug Fixes

- **drf:** keep yaml parser internals out of the 400 response ([d64c9f5](https://github.com/smarter-sh/smarter/commit/d64c9f5b4be814e7342a1950c4d1a7e0ba4b0cf5))
- **lib:** cache only payment answers, wire drf permission classes ([3940f2b](https://github.com/smarter-sh/smarter/commit/3940f2b3860127fca78f02a616a18e1388afde80))
- **lib:** stop credential leaks, fix token expiry and json encoding ([17dcee1](https://github.com/smarter-sh/smarter/commit/17dcee1ad4fa2253a69843e0a8a885722f26dbad))

### Performance

- **lib:** authenticate api keys once per request, cut redis calls ([4719073](https://github.com/smarter-sh/smarter/commit/4719073fa759a72e4d3526f8279817130b518008))
- **lib:** fix stale caches, lighten broker dependency queries ([c2b5c40](https://github.com/smarter-sh/smarter/commit/c2b5c408dcba016a6f5e20b07e61046dc7782684))

## [0.42.3-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.42.3-alpha.2...v0.42.3-alpha.3) (2026-11-05)

### Bug Fixes

- **drf:** keep yaml parser internals out of the 400 response ([d64c9f5](https://github.com/smarter-sh/smarter/commit/d64c9f5b4be814e7342a1950c4d1a7e0ba4b0cf5))

## [0.42.3-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.3-alpha.1...v0.42.3-alpha.2) (2026-11-05)

### Bug Fixes

- **lib:** cache only payment answers, wire drf permission classes ([3940f2b](https://github.com/smarter-sh/smarter/commit/3940f2b3860127fca78f02a616a18e1388afde80))

### Performance

- **lib:** fix stale caches, lighten broker dependency queries ([c2b5c40](https://github.com/smarter-sh/smarter/commit/c2b5c408dcba016a6f5e20b07e61046dc7782684))

## [0.42.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.2...v0.42.3-alpha.1) (2026-11-04)

### Bug Fixes

- **lib:** stop credential leaks, fix token expiry and json encoding ([17dcee1](https://github.com/smarter-sh/smarter/commit/17dcee1ad4fa2253a69843e0a8a885722f26dbad))

### Performance

- **lib:** authenticate api keys once per request, cut redis calls ([4719073](https://github.com/smarter-sh/smarter/commit/4719073fa759a72e4d3526f8279817130b518008))

## [0.42.2](https://github.com/smarter-sh/smarter/compare/v0.42.1...v0.42.2) (2026-11-04)

### Bug Fixes

- **mcpserver:** log a tool call's argument names at INFO, and its values only at DEBUG ([0490183](https://github.com/smarter-sh/smarter/commit/04901837d15b862e713ab6d78716f5d99e1197e4)), closes [#918](https://github.com/smarter-sh/smarter/issues/918)

### Performance

- **doodle:** read the theme catalog once and skip unneeded svg text ([1c9d3a8](https://github.com/smarter-sh/smarter/commit/1c9d3a83f89ce362fda40e949b9214d2ee54577a))

## [0.42.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.2-alpha.1...v0.42.2-alpha.2) (2026-11-04)

### Bug Fixes

- **mcpserver:** log a tool call's argument names at INFO, and its values only at DEBUG ([0490183](https://github.com/smarter-sh/smarter/commit/04901837d15b862e713ab6d78716f5d99e1197e4)), closes [#918](https://github.com/smarter-sh/smarter/issues/918)

## [0.42.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.1...v0.42.2-alpha.1) (2026-11-04)

### Performance

- **doodle:** read the theme catalog once and skip unneeded svg text ([1c9d3a8](https://github.com/smarter-sh/smarter/commit/1c9d3a83f89ce362fda40e949b9214d2ee54577a))

## [0.42.1](https://github.com/smarter-sh/smarter/compare/v0.42.0...v0.42.1) (2026-11-04)

### Bug Fixes

- **doodle:** link the AI credit's Learn how to the blog post ([f00ac5c](https://github.com/smarter-sh/smarter/commit/f00ac5cac5fb7d16859c239a9cbae491c428c6c7))

## [0.42.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.0...v0.42.1-alpha.1) (2026-11-04)

### Bug Fixes

- **doodle:** link the AI credit's Learn how to the blog post ([f00ac5c](https://github.com/smarter-sh/smarter/commit/f00ac5cac5fb7d16859c239a9cbae491c428c6c7))

## [0.42.0](https://github.com/smarter-sh/smarter/compare/v0.41.4...v0.42.0) (2026-11-04)

### Features

- **doodle:** add the sign-in page's doodle of the day ([0df9280](https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302))
- **doodle:** let Smarter AI applications choose and draw the doodle ([d07b91f](https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1))
- **doodle:** let Smarter AI applications choose and draw the doodle ([a5b491b](https://github.com/smarter-sh/smarter/commit/a5b491b823119c4388309e39687ebe031c2b4ed4))
- **doodle:** let the doodle editor follow trends, and check its tone ([2e6cb08](https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8))
- **doodle:** let the doodle editor follow trends, and check its tone ([210c935](https://github.com/smarter-sh/smarter/commit/210c9357e3744f0fb3f39620b84d05c580880dcd))

## [0.42.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.3...v0.42.0-alpha.4) (2026-11-04)

### Features

- **doodle:** let the doodle editor follow trends, and check its tone ([2e6cb08](https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8))

## [0.42.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.2...v0.42.0-alpha.3) (2026-11-04)

### Features

- **doodle:** let the doodle editor follow trends, and check its tone ([210c935](https://github.com/smarter-sh/smarter/commit/210c9357e3744f0fb3f39620b84d05c580880dcd))

## [0.42.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.1...v0.42.0-alpha.2) (2026-11-04)

### Features

- **doodle:** let Smarter AI applications choose and draw the doodle ([d07b91f](https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1))
- **doodle:** let Smarter AI applications choose and draw the doodle ([a5b491b](https://github.com/smarter-sh/smarter/commit/a5b491b823119c4388309e39687ebe031c2b4ed4))

## [0.42.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.4...v0.42.0-alpha.1) (2026-11-03)

### Features

- **doodle:** add the sign-in page's doodle of the day ([0df9280](https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302))
