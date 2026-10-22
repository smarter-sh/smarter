# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.36.10-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.9...v0.36.10-alpha.1) (2026-10-22)

### Bug Fixes

* **chat:** add silly nouns and scientific adjectives to the banter ([7fc78fd](https://github.com/smarter-sh/smarter/commit/7fc78fd9b74f8263ba0cf8f6eecff736641e05d6))

## [0.36.9](https://github.com/smarter-sh/smarter/compare/v0.36.8...v0.36.9) (2026-10-22)

### Bug Fixes

* **chat:** reply with a bubble of idle banter while a prompt runs ([aa3352f](https://github.com/smarter-sh/smarter/commit/aa3352f3e866d645f9db0928fc801aef7b803dd9))
* **provider:** send MCP instructions once, and cap the chat history ([504f37a](https://github.com/smarter-sh/smarter/commit/504f37a7fb1bc3ec3cd15ec0db054ce9d26f0495))

## [0.36.8](https://github.com/smarter-sh/smarter/compare/v0.36.7...v0.36.8) (2026-10-22)

### Bug Fixes

* **onboarding:** listen for the spotlight click before the note shows ([fcbd508](https://github.com/smarter-sh/smarter/commit/fcbd5085b87c515ca3dfdda147a08a24568f4b00))

## [0.36.8-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.7...v0.36.8-alpha.1) (2026-10-22)

### Bug Fixes

* **onboarding:** listen for the spotlight click before the note shows ([fcbd508](https://github.com/smarter-sh/smarter/commit/fcbd5085b87c515ca3dfdda147a08a24568f4b00))

## [0.36.7](https://github.com/smarter-sh/smarter/compare/v0.36.6...v0.36.7) (2026-10-22)

### Bug Fixes

- **logging:** suppress never-retrieved CancelledError from shield ([5ddd273](https://github.com/smarter-sh/smarter/commit/5ddd273527ff5cbccb9e8176146d3713be1036d6))

## [0.36.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.6...v0.36.7-alpha.1) (2026-10-22)

### Bug Fixes

- **logging:** suppress never-retrieved CancelledError from shield ([5ddd273](https://github.com/smarter-sh/smarter/commit/5ddd273527ff5cbccb9e8176146d3713be1036d6))

## [0.36.6](https://github.com/smarter-sh/smarter/compare/v0.36.5...v0.36.6) (2026-10-22)

### Bug Fixes

- **platform:** harden app pods against hangs, slow starts and load ([2820456](https://github.com/smarter-sh/smarter/commit/282045652adc34fa30c80e23455f587000ba28de))
- **platform:** repair tests and contract left by the manifests move ([2c4c5ab](https://github.com/smarter-sh/smarter/commit/2c4c5ab12acda85b3c958e4efe41e6cfce07e3c5))

## [0.36.6-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.6-alpha.1...v0.36.6-alpha.2) (2026-10-22)

### Bug Fixes

- **platform:** harden app pods against hangs, slow starts and load ([2820456](https://github.com/smarter-sh/smarter/commit/282045652adc34fa30c80e23455f587000ba28de))

## [0.36.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.5...v0.36.6-alpha.1) (2026-10-22)

### Bug Fixes

- **platform:** repair tests and contract left by the manifests move ([2c4c5ab](https://github.com/smarter-sh/smarter/commit/2c4c5ab12acda85b3c958e4efe41e6cfce07e3c5))

## [0.36.5](https://github.com/smarter-sh/smarter/compare/v0.36.4...v0.36.5) (2026-10-22)

### Bug Fixes

- **helm:** harden the nightly database backup and its setup script ([c9982d0](https://github.com/smarter-sh/smarter/commit/c9982d0d31acd49a898691e16b273f89524f4037))
- **platform:** consolidate the init job, back up as a read-only user ([0b8e937](https://github.com/smarter-sh/smarter/commit/0b8e937ff279ac27f3e131c6eb6856056a301071))
- **plugin:** fail clearly when a new plugin has no user profile ([3aca51e](https://github.com/smarter-sh/smarter/commit/3aca51ef2019a172b8ed29c344f653a676020535))

### Refactoring

- **account:** run stackademy's course database script at init ([febc361](https://github.com/smarter-sh/smarter/commit/febc361ca5e2c74a50a5c8f7a51e0ee65f458d11))
- **platform:** load example manifests from their own repository ([3cd7165](https://github.com/smarter-sh/smarter/commit/3cd7165007e93fa421a2e565959dab375419cb07))

## [0.36.5-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.5-alpha.1...v0.36.5-alpha.2) (2026-10-22)

### Bug Fixes

- **platform:** consolidate the init job, back up as a read-only user ([0b8e937](https://github.com/smarter-sh/smarter/commit/0b8e937ff279ac27f3e131c6eb6856056a301071))

## [0.36.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.4...v0.36.5-alpha.1) (2026-10-22)

### Bug Fixes

- **helm:** harden the nightly database backup and its setup script ([c9982d0](https://github.com/smarter-sh/smarter/commit/c9982d0d31acd49a898691e16b273f89524f4037))

## [0.36.4](https://github.com/smarter-sh/smarter/compare/v0.36.3...v0.36.4) (2026-10-21)

### Bug Fixes

- **react:** add the Did you know? fact of the day to ui-widgets ([b6e2aa4](https://github.com/smarter-sh/smarter/commit/b6e2aa4f6ed95cb418f43cf056a6d1ebe50d7ea9))
- **request:** log anonymous not-ready and session lines at debug ([baafe51](https://github.com/smarter-sh/smarter/commit/baafe5111d4f8d8847be57acf761a9493b7e99ee))

## [0.36.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.3...v0.36.4-alpha.1) (2026-10-21)

### Bug Fixes

- **request:** log anonymous not-ready and session lines at debug ([baafe51](https://github.com/smarter-sh/smarter/commit/baafe5111d4f8d8847be57acf761a9493b7e99ee))

## [0.36.3](https://github.com/smarter-sh/smarter/compare/v0.36.2...v0.36.3) (2026-10-21)

### Bug Fixes

- **helm:** use the maintainer key that helm recognizes ([199bd6c](https://github.com/smarter-sh/smarter/commit/199bd6c2aa8312832a34f8ee2c8c4d8450263208))
- **prompt:** compare a receiver's iteration only when it is an int ([48f6561](https://github.com/smarter-sh/smarter/commit/48f65617ff6f94e2560edc0c2bce1e75edaa41bf))

### Refactoring

- **llmclient:** load stackademy from its own github repository ([1d3d05d](https://github.com/smarter-sh/smarter/commit/1d3d05d64975f701a6506a760af16c161479b56a))

## [0.36.3-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.3-alpha.1...v0.36.3-alpha.2) (2026-10-21)

### Bug Fixes

- **helm:** use the maintainer key that helm recognizes ([199bd6c](https://github.com/smarter-sh/smarter/commit/199bd6c2aa8312832a34f8ee2c8c4d8450263208))

### Refactoring

- **llmclient:** load stackademy from its own github repository ([1d3d05d](https://github.com/smarter-sh/smarter/commit/1d3d05d64975f701a6506a760af16c161479b56a))

## [0.36.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.2...v0.36.3-alpha.1) (2026-10-21)

### Bug Fixes

- **prompt:** compare a receiver's iteration only when it is an int ([48f6561](https://github.com/smarter-sh/smarter/commit/48f65617ff6f94e2560edc0c2bce1e75edaa41bf))

## [0.36.2](https://github.com/smarter-sh/smarter/compare/v0.36.1...v0.36.2) (2026-10-21)

### Bug Fixes

- **llmtool:** keep image urls that only refuse the server's check ([2603dc7](https://github.com/smarter-sh/smarter/commit/2603dc736b91814e4e3aaeb57866f166c4260889))
- **prompt:** harden chat sessions, prompt errors and CORS headers ([8105d9e](https://github.com/smarter-sh/smarter/commit/8105d9e002cf6e0f88f73ac48d0b24a3b3384da7))
- **provider:** let the llm call tools in more than one round ([003fcfe](https://github.com/smarter-sh/smarter/commit/003fcfe2b287e01d2a0ab9f9cd848220de3d1f1f))
- **react:** load chat images without a referer, and describe failures ([04079af](https://github.com/smarter-sh/smarter/commit/04079af05c2fbdb329ae17ef2c7b283511b573b2))

## [0.36.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.1...v0.36.2-alpha.1) (2026-10-21)

### Bug Fixes

- **llmtool:** keep image urls that only refuse the server's check ([2603dc7](https://github.com/smarter-sh/smarter/commit/2603dc736b91814e4e3aaeb57866f166c4260889))
- **prompt:** harden chat sessions, prompt errors and CORS headers ([8105d9e](https://github.com/smarter-sh/smarter/commit/8105d9e002cf6e0f88f73ac48d0b24a3b3384da7))
- **provider:** let the llm call tools in more than one round ([003fcfe](https://github.com/smarter-sh/smarter/commit/003fcfe2b287e01d2a0ab9f9cd848220de3d1f1f))
- **react:** load chat images without a referer, and describe failures ([04079af](https://github.com/smarter-sh/smarter/commit/04079af05c2fbdb329ae17ef2c7b283511b573b2))

## [0.36.1](https://github.com/smarter-sh/smarter/compare/v0.36.0...v0.36.1) (2026-10-21)

### Bug Fixes

- **react:** build the ui-chat library before the apps that import it ([447d1b6](https://github.com/smarter-sh/smarter/commit/447d1b6ea9eb0a28c1ff659d3c33b8fdc7659a1a))

## [0.36.0](https://github.com/smarter-sh/smarter/compare/v0.35.3...v0.36.0) (2026-10-21)

### Features

- **react:** add [@smarter](https://github.com/smarter).sh/ui-widgets, the dashboard's widgets on npm ([59cbfb2](https://github.com/smarter-sh/smarter/commit/59cbfb28977283167bff29cfd1f2e625b8da3a9b))

### Bug Fixes

- **account:** report management command errors without stack traces ([7d0c55e](https://github.com/smarter-sh/smarter/commit/7d0c55e71cfa499c6b713f4cfcd562f89e95bcdb))
- **account:** translate account emails into the user's language ([1179b96](https://github.com/smarter-sh/smarter/commit/1179b96d141e4744c68ac336fe39dd44f37a0e18))
- **chat:** paste plain text into the message input ([56f0c00](https://github.com/smarter-sh/smarter/commit/56f0c00756f40ce0175e726db6fec9cd9aca99f4))
- **mcpserver:** stop indexing the archived smarter-chat repository ([2790aad](https://github.com/smarter-sh/smarter/commit/2790aad26fb55e32cc58b61aa14b93c7d3494cbc))
- **react:** keep the Extensions widget light in dark mode ([37cd619](https://github.com/smarter-sh/smarter/commit/37cd6194dba8488534f480d2de7188706db996d5))
- **react:** point [@smarter](https://github.com/smarter).sh/ui-chat's repository at smarter ([82a4865](https://github.com/smarter-sh/smarter/commit/82a4865742d7a9122f1456f58e266e67bf0aac15))
- **react:** track smarter-chat's .storybook folder, which tests import ([6564c27](https://github.com/smarter-sh/smarter/commit/6564c271cb971f93033e4d5cd4d588a419abc2c8))

### Refactoring

- **react:** move ResourceTree into [@smarter](https://github.com/smarter).sh/ui-widgets ([5234456](https://github.com/smarter-sh/smarter/commit/52344569bcda351d95def2ec6fa2a9a7768f0733))
- **react:** move smarter-chat into this repository ([6ba24f8](https://github.com/smarter-sh/smarter/commit/6ba24f860f19de140224fc3e4fa52249b87b2ccc))
- **react:** rename the npm packages' folders to smarter.sh-\* ([1889899](https://github.com/smarter-sh/smarter/commit/1889899da885511db3f3a43fe25f219b6bafb21e))

## [0.36.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.36.0-alpha.4...v0.36.0-alpha.5) (2026-10-21)

### Bug Fixes

- **chat:** paste plain text into the message input ([56f0c00](https://github.com/smarter-sh/smarter/commit/56f0c00756f40ce0175e726db6fec9cd9aca99f4))
- **react:** keep the Extensions widget light in dark mode ([37cd619](https://github.com/smarter-sh/smarter/commit/37cd6194dba8488534f480d2de7188706db996d5))

### Refactoring

- **react:** move ResourceTree into [@smarter](https://github.com/smarter).sh/ui-widgets ([5234456](https://github.com/smarter-sh/smarter/commit/52344569bcda351d95def2ec6fa2a9a7768f0733))

## [0.36.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.36.0-alpha.3...v0.36.0-alpha.4) (2026-10-21)

### Bug Fixes

- **mcpserver:** stop indexing the archived smarter-chat repository ([2790aad](https://github.com/smarter-sh/smarter/commit/2790aad26fb55e32cc58b61aa14b93c7d3494cbc))

### Refactoring

- **react:** rename the npm packages' folders to smarter.sh-\* ([1889899](https://github.com/smarter-sh/smarter/commit/1889899da885511db3f3a43fe25f219b6bafb21e))

## [0.36.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.36.0-alpha.2...v0.36.0-alpha.3) (2026-10-21)

### Bug Fixes

- **react:** point [@smarter](https://github.com/smarter).sh/ui-chat's repository at smarter ([82a4865](https://github.com/smarter-sh/smarter/commit/82a4865742d7a9122f1456f58e266e67bf0aac15))

## [0.36.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.0-alpha.1...v0.36.0-alpha.2) (2026-10-21)

### Bug Fixes

- **react:** track smarter-chat's .storybook folder, which tests import ([6564c27](https://github.com/smarter-sh/smarter/commit/6564c271cb971f93033e4d5cd4d588a419abc2c8))

### Refactoring

- **react:** move smarter-chat into this repository ([6ba24f8](https://github.com/smarter-sh/smarter/commit/6ba24f860f19de140224fc3e4fa52249b87b2ccc))

## [0.36.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.35.4-alpha.2...v0.36.0-alpha.1) (2026-10-21)

### Features

- **react:** add [@smarter](https://github.com/smarter).sh/ui-widgets, the dashboard's widgets on npm ([59cbfb2](https://github.com/smarter-sh/smarter/commit/59cbfb28977283167bff29cfd1f2e625b8da3a9b))
