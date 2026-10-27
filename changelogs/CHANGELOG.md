# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.36.27-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.27-alpha.1...v0.36.27-alpha.2) (2026-10-27)

### Bug Fixes

* **tests:** bind the junit report file with a runner subclass ([0564237](https://github.com/smarter-sh/smarter/commit/0564237cedbf9607badca15b0b2c41c670872623))

## [0.36.27-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.26...v0.36.27-alpha.1) (2026-10-27)

### Bug Fixes

* **tests:** import iter_test_cases from django.test.utils ([00de8e1](https://github.com/smarter-sh/smarter/commit/00de8e16c314d455ef3ee9fe7ab45b5c0917ecba))

## [0.36.26](https://github.com/smarter-sh/smarter/compare/v0.36.25...v0.36.26) (2026-10-27)

### Bug Fixes

* **logging:** keep chat prompts and session keys out of the INFO log ([6f840c4](https://github.com/smarter-sh/smarter/commit/6f840c4414c44f37cfefdbea024181d4dbc43ea6))

## [0.36.25](https://github.com/smarter-sh/smarter/compare/v0.36.24...v0.36.25) (2026-10-27)

### Bug Fixes

* **account:** save seed users and the admin account only when changed ([2209de8](https://github.com/smarter-sh/smarter/commit/2209de8b0f2a145a45a8e9976ed35d5a9fda376b))
* **common:** scale resource limit warnings with uvicorn workers ([91e9ecb](https://github.com/smarter-sh/smarter/commit/91e9ecb28f5f2e298d036c8b3d4a988f3514a92b))
* **dashboard:** keep the h2 markup out of the manifest page title ([b0d2c96](https://github.com/smarter-sh/smarter/commit/b0d2c96711e5aa317e6c3bf9e48b5d8b57df9e61))
* **logging:** log secret applies and plugin readiness once, at INFO ([c3a600b](https://github.com/smarter-sh/smarter/commit/c3a600b6fdddfb30a21d1e9a223b558c501623ac))

## [0.36.24](https://github.com/smarter-sh/smarter/compare/v0.36.23...v0.36.24) (2026-10-27)

### Bug Fixes

* **common:** tell type checkers formatted_class_name gets the class ([7954674](https://github.com/smarter-sh/smarter/commit/795467471d60c0c3095db8b4558eb0265f2a6cc2))
* **logging:** fix a leak and noise found in the init job log ([2a5dcfc](https://github.com/smarter-sh/smarter/commit/2a5dcfc15ea8d86cffe2e1c262ae40430825552e))
* **server:** quiet the startup log and shorten its banner ([f30bb43](https://github.com/smarter-sh/smarter/commit/f30bb43ebe5cfbdca0b8e1acd6b2b2cf789af33c))
* **settings:** keep broker, cache and sessions in separate redis dbs ([4747562](https://github.com/smarter-sh/smarter/commit/4747562cfdfa9b4dc8f29448d0dfe823cef98d0e))

### Refactoring

* **logging:** call SmarterFormattedText instead of formatted_text ([ca72ef0](https://github.com/smarter-sh/smarter/commit/ca72ef0d7ca66c495ffc63d0d14544449b6e6ee3))

### Performance

* **helm:** run 2 uvicorn workers per app pod, one per core ([ee15430](https://github.com/smarter-sh/smarter/commit/ee154308190d8f058567aa752d56ca2d2a82ee71))

## [0.36.24-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.23...v0.36.24-alpha.1) (2026-10-27)

### Bug Fixes

* **logging:** fix a leak and noise found in the init job log ([2a5dcfc](https://github.com/smarter-sh/smarter/commit/2a5dcfc15ea8d86cffe2e1c262ae40430825552e))
* **server:** quiet the startup log and shorten its banner ([f30bb43](https://github.com/smarter-sh/smarter/commit/f30bb43ebe5cfbdca0b8e1acd6b2b2cf789af33c))
* **settings:** keep broker, cache and sessions in separate redis dbs ([4747562](https://github.com/smarter-sh/smarter/commit/4747562cfdfa9b4dc8f29448d0dfe823cef98d0e))

### Refactoring

* **logging:** call SmarterFormattedText instead of formatted_text ([ca72ef0](https://github.com/smarter-sh/smarter/commit/ca72ef0d7ca66c495ffc63d0d14544449b6e6ee3))

### Performance

* **helm:** run 2 uvicorn workers per app pod, one per core ([ee15430](https://github.com/smarter-sh/smarter/commit/ee154308190d8f058567aa752d56ca2d2a82ee71))

## [0.36.23](https://github.com/smarter-sh/smarter/compare/v0.36.22...v0.36.23) (2026-10-27)

### Bug Fixes

* **asgi:** print a startup banner with the logo and server config ([6d54695](https://github.com/smarter-sh/smarter/commit/6d5469589970abc5f5915b8a50549c4950219646))
* **react:** unmount each story after its test to stop a teardown error ([a7d0df8](https://github.com/smarter-sh/smarter/commit/a7d0df85a1ae55e4b9ba9525bd818e38292b5226))

## [0.36.23-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.23-alpha.1...v0.36.23-alpha.2) (2026-10-27)

### Bug Fixes

* **react:** unmount each story after its test to stop a teardown error ([a7d0df8](https://github.com/smarter-sh/smarter/commit/a7d0df85a1ae55e4b9ba9525bd818e38292b5226))

## [0.36.23-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.22...v0.36.23-alpha.1) (2026-10-27)

### Bug Fixes

* **asgi:** print a startup banner with the logo and server config ([6d54695](https://github.com/smarter-sh/smarter/commit/6d5469589970abc5f5915b8a50549c4950219646))

## [0.36.22](https://github.com/smarter-sh/smarter/compare/v0.36.21...v0.36.22) (2026-10-27)

### Bug Fixes

* **logging:** cut init job log noise and mask the cloud account id ([14c9afe](https://github.com/smarter-sh/smarter/commit/14c9afe79c6e9b49889f7bbe3077df2c01a5a0e5))

## [0.36.21](https://github.com/smarter-sh/smarter/compare/v0.36.20...v0.36.21) (2026-10-26)

### Bug Fixes

* **helm:** run the bastion pod as non-root with only the env it needs ([3fbe35d](https://github.com/smarter-sh/smarter/commit/3fbe35d133c011a1a5a596d1106115c0e681b8da))
* **infrastructure:** no wildcard SAN on custom-domain certificates ([d42b9a0](https://github.com/smarter-sh/smarter/commit/d42b9a08e2b998cebe5a8d2bdddcf15752bc811e))
* **prompt:** build a new session's thread on the server ([2ca56e8](https://github.com/smarter-sh/smarter/commit/2ca56e844538b415cf5874e23aa4338dd980cd62))
* **secret:** a user can read only the Secrets their account owns ([a8c56b1](https://github.com/smarter-sh/smarter/commit/a8c56b17d14a223077afc8266704052c38973213))
* **settings:** validate database settings, move Helm env to a Secret ([6c2d421](https://github.com/smarter-sh/smarter/commit/6c2d4212cef63b0af9ea74ef7e7681d2d9129131))

### Refactoring

* **api:** take SAMKinds and the journal enums from smarter-types ([dd2276e](https://github.com/smarter-sh/smarter/commit/dd2276edd26d6f6efc9ac7074d1c2a0470376fdb))
* **cache:** use the cache-results package from pypi ([6ec3aa9](https://github.com/smarter-sh/smarter/commit/6ec3aa915d2e36e0bf08f93c52d8a71f06e2b5d7))

## [0.36.21-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.36.21-alpha.2...v0.36.21-alpha.3) (2026-10-26)

### Bug Fixes

* **infrastructure:** no wildcard SAN on custom-domain certificates ([d42b9a0](https://github.com/smarter-sh/smarter/commit/d42b9a08e2b998cebe5a8d2bdddcf15752bc811e))
* **prompt:** build a new session's thread on the server ([2ca56e8](https://github.com/smarter-sh/smarter/commit/2ca56e844538b415cf5874e23aa4338dd980cd62))
* **secret:** a user can read only the Secrets their account owns ([a8c56b1](https://github.com/smarter-sh/smarter/commit/a8c56b17d14a223077afc8266704052c38973213))

## [0.36.21-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.21-alpha.1...v0.36.21-alpha.2) (2026-10-26)

### Bug Fixes

* **helm:** run the bastion pod as non-root with only the env it needs ([3fbe35d](https://github.com/smarter-sh/smarter/commit/3fbe35d133c011a1a5a596d1106115c0e681b8da))

## [0.36.21-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.20...v0.36.21-alpha.1) (2026-10-26)

### Bug Fixes

* **settings:** validate database settings, move Helm env to a Secret ([6c2d421](https://github.com/smarter-sh/smarter/commit/6c2d4212cef63b0af9ea74ef7e7681d2d9129131))

### Refactoring

* **api:** take SAMKinds and the journal enums from smarter-types ([dd2276e](https://github.com/smarter-sh/smarter/commit/dd2276edd26d6f6efc9ac7074d1c2a0470376fdb))
* **cache:** use the cache-results package from pypi ([6ec3aa9](https://github.com/smarter-sh/smarter/commit/6ec3aa915d2e36e0bf08f93c52d8a71f06e2b5d7))

## [0.36.20](https://github.com/smarter-sh/smarter/compare/v0.36.19...v0.36.20) (2026-10-25)

### Bug Fixes

* **account:** key cached profile and ownership lookups by id ([de51422](https://github.com/smarter-sh/smarter/commit/de5142282d737be306c5c45cfb1610b84d9b86b0))
* **cache:** refuse unsafe key arguments and depend only on Django ([c6c95d7](https://github.com/smarter-sh/smarter/commit/c6c95d7f413512e577a033c9fe194bfbb975dd49))

## [0.36.20-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.19...v0.36.20-alpha.1) (2026-10-25)

### Bug Fixes

* **account:** key cached profile and ownership lookups by id ([de51422](https://github.com/smarter-sh/smarter/commit/de5142282d737be306c5c45cfb1610b84d9b86b0))
* **cache:** refuse unsafe key arguments and depend only on Django ([c6c95d7](https://github.com/smarter-sh/smarter/commit/c6c95d7f413512e577a033c9fe194bfbb975dd49))

## [0.36.19](https://github.com/smarter-sh/smarter/compare/v0.36.18...v0.36.19) (2026-10-25)

### Bug Fixes

* **cache:** warn when a cache key falls back to str() of an argument ([f691ae9](https://github.com/smarter-sh/smarter/commit/f691ae9515b304465b4ec67de8c020ea3e2861c9))

## [0.36.18](https://github.com/smarter-sh/smarter/compare/v0.36.17...v0.36.18) (2026-10-25)

### Bug Fixes

* **cache:** harden cache_results keys, logging, startup and methods ([33c7b93](https://github.com/smarter-sh/smarter/commit/33c7b93276406d39078786b744ca77d91d9784a7))

## [0.36.17](https://github.com/smarter-sh/smarter/compare/v0.36.16...v0.36.17) (2026-10-23)

### Bug Fixes

* **account:** identify user profiles by pk and mask their company name ([3ed579d](https://github.com/smarter-sh/smarter/commit/3ed579d0e78ae8f9a31195edd4b7926deda0479f))

### Refactoring

* **docs:** replace drf-yasg with scalar and the openapi contract ([3c0c952](https://github.com/smarter-sh/smarter/commit/3c0c9522ba580ad24576d5713615c5817f56522f))

## [0.36.16](https://github.com/smarter-sh/smarter/compare/v0.36.15...v0.36.16) (2026-10-23)

### Bug Fixes

* **logging:** batch redis log publishing, quiet init job noise ([505c424](https://github.com/smarter-sh/smarter/commit/505c42495ce51940acf4151806ff500867186b04))
* **react:** add a refresh button to the top of every list view ([b89c792](https://github.com/smarter-sh/smarter/commit/b89c79281de010231515c4ba6a5f3296bbfb551d))

## [0.36.16-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.16-alpha.1...v0.36.16-alpha.2) (2026-10-23)

### Bug Fixes

* **react:** add a refresh button to the top of every list view ([b89c792](https://github.com/smarter-sh/smarter/commit/b89c79281de010231515c4ba6a5f3296bbfb551d))

## [0.36.16-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.15...v0.36.16-alpha.1) (2026-10-23)

### Bug Fixes

* **logging:** batch redis log publishing, quiet init job noise ([505c424](https://github.com/smarter-sh/smarter/commit/505c42495ce51940acf4151806ff500867186b04))

## [0.36.15](https://github.com/smarter-sh/smarter/compare/v0.36.14...v0.36.15) (2026-10-23)

### Bug Fixes

* **llmtool:** stop plugin() from storing a raw dict as the manifest ([084af56](https://github.com/smarter-sh/smarter/commit/084af569d2c1675d9e56f95918a8edcade5e5609))

## [0.36.15-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.14...v0.36.15-alpha.1) (2026-10-23)

### Bug Fixes

* **llmtool:** stop plugin() from storing a raw dict as the manifest ([084af56](https://github.com/smarter-sh/smarter/commit/084af569d2c1675d9e56f95918a8edcade5e5609))

## [0.36.14](https://github.com/smarter-sh/smarter/compare/v0.36.13...v0.36.14) (2026-10-23)

### Bug Fixes

* **account:** stop printing generated passwords in create_user ([fcae349](https://github.com/smarter-sh/smarter/commit/fcae3494c6d1386a2c0b26cbe37c62d24ebb28f0))
* **helm:** size celery worker and beat memory requests to real use ([d4bbd95](https://github.com/smarter-sh/smarter/commit/d4bbd952473d1491ebf10a130980153c2b852efa))
* **helm:** stop running makemigrations in the init job ([236ada0](https://github.com/smarter-sh/smarter/commit/236ada02aafd4c7dbcc26bdc1ecb8858ebe621f1))
* **logging:** format log origins consistently and quiet the init job ([b33a631](https://github.com/smarter-sh/smarter/commit/b33a631cd13a702dc14541323d757cba290af9db))

## [0.36.14-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.36.14-alpha.2...v0.36.14-alpha.3) (2026-10-23)

### Bug Fixes

* **account:** stop printing generated passwords in create_user ([fcae349](https://github.com/smarter-sh/smarter/commit/fcae3494c6d1386a2c0b26cbe37c62d24ebb28f0))

## [0.36.14-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.36.14-alpha.1...v0.36.14-alpha.2) (2026-10-23)

### Bug Fixes

* **helm:** stop running makemigrations in the init job ([236ada0](https://github.com/smarter-sh/smarter/commit/236ada02aafd4c7dbcc26bdc1ecb8858ebe621f1))
* **logging:** format log origins consistently and quiet the init job ([b33a631](https://github.com/smarter-sh/smarter/commit/b33a631cd13a702dc14541323d757cba290af9db))

## [0.36.14-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.13...v0.36.14-alpha.1) (2026-10-23)

### Bug Fixes

* **helm:** size celery worker and beat memory requests to real use ([d4bbd95](https://github.com/smarter-sh/smarter/commit/d4bbd952473d1491ebf10a130980153c2b852efa))

## [0.36.13](https://github.com/smarter-sh/smarter/compare/v0.36.12...v0.36.13) (2026-10-23)

### Bug Fixes

* **listview:** give the cached page's request the platform host ([f7d8875](https://github.com/smarter-sh/smarter/commit/f7d887563eb15fd11f0b75e81a3acc12588f1df9))

## [0.36.12](https://github.com/smarter-sh/smarter/compare/v0.36.11...v0.36.12) (2026-10-23)

### Bug Fixes

* **react:** hide the list views' intro box on phones ([577e55a](https://github.com/smarter-sh/smarter/commit/577e55a3640b1f0c313c457998325827422e38e1))

### Performance

* **listview:** cache list pages per user and remove per-row queries ([b7377d8](https://github.com/smarter-sh/smarter/commit/b7377d8ad815bd323e2dc04b9ffb26f4567a1498))

## [0.36.11](https://github.com/smarter-sh/smarter/compare/v0.36.10...v0.36.11) (2026-10-22)

### Bug Fixes

* **logging:** quiet false errors, mask pii, skip unchanged re-applies ([ec71cd3](https://github.com/smarter-sh/smarter/commit/ec71cd361331599253b761f5a1281cf95b91ebd6))

## [0.36.11-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.10...v0.36.11-alpha.1) (2026-10-22)

### Bug Fixes

* **logging:** quiet false errors, mask pii, skip unchanged re-applies ([ec71cd3](https://github.com/smarter-sh/smarter/commit/ec71cd361331599253b761f5a1281cf95b91ebd6))

## [0.36.10](https://github.com/smarter-sh/smarter/compare/v0.36.9...v0.36.10) (2026-10-22)

### Bug Fixes

* **chat:** add silly nouns and scientific adjectives to the banter ([7fc78fd](https://github.com/smarter-sh/smarter/commit/7fc78fd9b74f8263ba0cf8f6eecff736641e05d6))

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
