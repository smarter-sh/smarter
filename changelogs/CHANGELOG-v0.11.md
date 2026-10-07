# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this
project adheres to [Semantic Versioning](http://semver.org/).

## [0.11.0](https://github.com/smarter-sh/smarter/compare/v0.10.23...v0.11.0) (2025-04-27)

### Bug Fixes

- cache misses due to AnonymousUser ([80de0e2](https://github.com/smarter-sh/smarter/commit/80de0e266562b61fbf2e1a248a44ff1e079a3e00))
- cache the base context ([a153da9](https://github.com/smarter-sh/smarter/commit/a153da98e55ecd5cfe9ad15367fc5ecb978f3f94))
- cache_results() decorator wasn't finding valid cached items ([fc43a1b](https://github.com/smarter-sh/smarter/commit/fc43a1b22339e2d02371bda5a3db70ce53890ccf))
- cronic cache misses ([23d039d](https://github.com/smarter-sh/smarter/commit/23d039d42292c57e3ed83e6af302e818e21177db))
- fixup hashkey so that it's still readable ([499bdf5](https://github.com/smarter-sh/smarter/commit/499bdf5c917c1301f9254a0093715e76232c3524))
- json schema should not require status field ([6868f5c](https://github.com/smarter-sh/smarter/commit/6868f5c5bc2ea2a4c07f97679cbe2d9bc0a5226c))
- work on dispatch() life cycle execution thread ([0761c57](https://github.com/smarter-sh/smarter/commit/0761c57211fc38185761cb7d1894a0a0d49f6aa5))

### Features

- add console UI components for Secrets ([ccf78d8](https://github.com/smarter-sh/smarter/commit/ccf78d81576b58ec028ff15b34f59c3e57b9d215))
- add data entry form for new secret ([4797e25](https://github.com/smarter-sh/smarter/commit/4797e25e90f87414626f819f7c0e29d8fe4ee6ed))
- add django admin form for Secret and created dedicated FERNET_ENCRYPTION_KEY ([65c127f](https://github.com/smarter-sh/smarter/commit/65c127f6d8cc2ed78ef2ec00d3869123656a21df))
- add Fernet encryption key to CI-CD workflows and Helm chart ([19a7686](https://github.com/smarter-sh/smarter/commit/19a76863a5990feed463d063263ab3bfb7e9a4e2))
- add Secret unit tests ([b88af41](https://github.com/smarter-sh/smarter/commit/b88af410c383cc06ec0fe9bd4124030cf995d4d9))
- configure action buttons for data entry form ([c7bb2a0](https://github.com/smarter-sh/smarter/commit/c7bb2a0eb2386b987b2083fa5778675bbae4f211))
- configure data entry form ([f5c02ae](https://github.com/smarter-sh/smarter/commit/f5c02ae11e018b9696761d871883cc7c5362aace))
- create account.Secrets model ([d0e0e00](https://github.com/smarter-sh/smarter/commit/d0e0e000f5ff80b60cd06679a42e68fb459b9707))
- scaffold dashboard UI widgets ([6583ec4](https://github.com/smarter-sh/smarter/commit/6583ec4b562644b613d4591266646de1418e599c))
- scaffold Secret broker and model ([f9e2850](https://github.com/smarter-sh/smarter/commit/f9e2850302e37de53f8594b13663ed9cea55f8af))
- scaffold Secret broker and model ([d3904a4](https://github.com/smarter-sh/smarter/commit/d3904a4af406371f0dd1c5896868a96d45bd1e5f))

## [0.11.0](https://github.com/smarter-sh/smarter/compare/v0.10.23...v0.11.0) (2025-04-27)

### Bug Fixes

- cache misses due to AnonymousUser ([80de0e2](https://github.com/smarter-sh/smarter/commit/80de0e266562b61fbf2e1a248a44ff1e079a3e00))
- cache the base context ([a153da9](https://github.com/smarter-sh/smarter/commit/a153da98e55ecd5cfe9ad15367fc5ecb978f3f94))
- cache_results() decorator wasn't finding valid cached items ([fc43a1b](https://github.com/smarter-sh/smarter/commit/fc43a1b22339e2d02371bda5a3db70ce53890ccf))
- cronic cache misses ([23d039d](https://github.com/smarter-sh/smarter/commit/23d039d42292c57e3ed83e6af302e818e21177db))
- fixup hashkey so that it's still readable ([499bdf5](https://github.com/smarter-sh/smarter/commit/499bdf5c917c1301f9254a0093715e76232c3524))
- json schema should not require status field ([6868f5c](https://github.com/smarter-sh/smarter/commit/6868f5c5bc2ea2a4c07f97679cbe2d9bc0a5226c))
- work on dispatch() life cycle execution thread ([0761c57](https://github.com/smarter-sh/smarter/commit/0761c57211fc38185761cb7d1894a0a0d49f6aa5))

### Features

- add console UI components for Secrets ([ccf78d8](https://github.com/smarter-sh/smarter/commit/ccf78d81576b58ec028ff15b34f59c3e57b9d215))
- add data entry form for new secret ([4797e25](https://github.com/smarter-sh/smarter/commit/4797e25e90f87414626f819f7c0e29d8fe4ee6ed))
- add django admin form for Secret and created dedicated FERNET_ENCRYPTION_KEY ([65c127f](https://github.com/smarter-sh/smarter/commit/65c127f6d8cc2ed78ef2ec00d3869123656a21df))
- add Fernet encryption key to CI-CD workflows and Helm chart ([19a7686](https://github.com/smarter-sh/smarter/commit/19a76863a5990feed463d063263ab3bfb7e9a4e2))
- add Secret unit tests ([b88af41](https://github.com/smarter-sh/smarter/commit/b88af410c383cc06ec0fe9bd4124030cf995d4d9))
- configure action buttons for data entry form ([c7bb2a0](https://github.com/smarter-sh/smarter/commit/c7bb2a0eb2386b987b2083fa5778675bbae4f211))
- configure data entry form ([f5c02ae](https://github.com/smarter-sh/smarter/commit/f5c02ae11e018b9696761d871883cc7c5362aace))
- create account.Secrets model ([d0e0e00](https://github.com/smarter-sh/smarter/commit/d0e0e000f5ff80b60cd06679a42e68fb459b9707))
- scaffold dashboard UI widgets ([6583ec4](https://github.com/smarter-sh/smarter/commit/6583ec4b562644b613d4591266646de1418e599c))
- scaffold Secret broker and model ([f9e2850](https://github.com/smarter-sh/smarter/commit/f9e2850302e37de53f8594b13663ed9cea55f8af))
- scaffold Secret broker and model ([d3904a4](https://github.com/smarter-sh/smarter/commit/d3904a4af406371f0dd1c5896868a96d45bd1e5f))
