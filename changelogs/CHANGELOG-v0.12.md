# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this
project adheres to [Semantic Versioning](http://semver.org/).

## [0.12.0](https://github.com/smarter-sh/smarter/compare/v0.11.0...v0.12.0) (2025-06-02)

### Major Features

- **Secrets**. A new object type for securely managing sensitive data like passwords, api keys and credentials. Works like a Kubernetes secret, where the secret is encrypted using a common key that enables you to drecrypt it real-time, as needed.
- **ApiPlugin + ApiConnection**. A new Smarter Plugin class that enables user defined, strongly typed, real time data retrieval from remote Api's during LLM prompting via both function calling and traditional single-pass RAG.
- **SqlPlugin + SqlConnection**. Ditto, but for remote Sql databases.

### Refactoring

- **AccountMixin + SmarterRequestMixin**. We created two new mixins that consolidate handling logic for working with http requests and for account resources like Users and UserProfiles. We retired thousands of lines of redundant code and achieved a 10x performance improvement on api request initializations. This obviously affords us considerable improvement to reliability. high caching levels.

- **Name-spaced url schemes for reverse urls**, so that name spaces now match the actual Python module organizational scheme. For example, `{% url 'api:apply' %}`is now `{% url 'api:v1:cli:apply' %}`, which matches the Python path, `smarter.apps.api.v1.cli`.
- **Django signals**. Fully migrated to event-driven Django signals to pave the way towards our vision for a more pluggable, extensible platform architecture.
- **Standardized Casing**. Standardized transformations between Pydantic models and Django ORM. Pydantic fields are now strictly camelCase, while DjangoORM continues to enforce strict snake_case. This greatly simplifies implementation logic in Smarter Broker classes and enabled us to remove copious amounts of transformation logic from legacy Brokers.
- **Testing**. The entire unit test bank has been completely refactored to use a new family of Classes that provide more consistent setup and teardown of unit tests.

### Performance & reliability

- **Testing Coverages**. Our testing coverage ratio is back to par, with 300+ new unit tests added to the legacy code base.
- **Enumerations**. More enumerations throughout the codebase enable more consistent and coherent cli error messagages.
- **Caching**. Caching is now tightly coupled to AccountMixin and SmarterRequestMixin and has been extensively refactored to cover more edge cases.
- **Logging**. Improved logging, mostly as a result of new Django signals that we've added to all Django apps.

### Features

- add business rule validations to PluginDataApi ([9c71f44](https://github.com/smarter-sh/smarter/commit/9c71f44a8edf27a438a4b2c07516c3c3a89576f6))
- add more granular error reporting to smarter.apps.api.v1.cli.views.base.CliBaseApiView ([8f1efaf](https://github.com/smarter-sh/smarter/commit/8f1efaf8238819fa64ff2b9a90436f2931fdf111))
- add new manifest kinds to PluginController ([bc50bfe](https://github.com/smarter-sh/smarter/commit/bc50bfe7afc8af325dc79071db3c5a4e49dac7f3))
- add pre and post signals for all chatbot tasks ([eb78824](https://github.com/smarter-sh/smarter/commit/eb78824a2c5f55c208135eb2afecc90d9ca07235))
- add pydantic models for parameters and testValues ([cc10324](https://github.com/smarter-sh/smarter/commit/cc103245df34486f148b0f19d210b8064a25e0dc))
- add signals to ApiConnection ([480cc31](https://github.com/smarter-sh/smarter/commit/480cc31bf537821c74d4e8856a791578a77bc5a4))
- add signals to get_current_weather() ([910313c](https://github.com/smarter-sh/smarter/commit/910313c3a7fa0a69d869682b54888ae06c30c18b))
- add smarter.apps.api.receivers.api_request_completed ([779668d](https://github.com/smarter-sh/smarter/commit/779668db2f8b1a891d197a1ab80ec20ad2a44bff))
- add smarter.apps.api.receivers.api_request_initiated ([1c25c89](https://github.com/smarter-sh/smarter/commit/1c25c89022bf3348fd79a16e20b0204e5fe63bfe))
- build Pydantic models for urlparams and http request headers ([882034c](https://github.com/smarter-sh/smarter/commit/882034c680e86fed881b16baf33645a527b77e6f))
- code connection models ([d45f428](https://github.com/smarter-sh/smarter/commit/d45f428d2e294f4a9239f594befc5b5b504ee891))
- code Connection view and template ([84b1688](https://github.com/smarter-sh/smarter/commit/84b1688d75a8346942dd8a57f14b323ab0f6746b))
- code SAMApiConnectionBroker and SAMSqlConnectionBroker ([7d047f2](https://github.com/smarter-sh/smarter/commit/7d047f2705416976cff680c8cec7061843467109))
- create django admin models and manifest model for api_connection ([8fa0a69](https://github.com/smarter-sh/smarter/commit/8fa0a698b4bad0665f8a4f8a70dc0613a5806817))
- create manifest models for PluginDataApi and PluginDataSql ([cdb117c](https://github.com/smarter-sh/smarter/commit/cdb117c037e4447e3bf20f1e28aab4d703496b19))
- create PluginApi ([fd8aa1b](https://github.com/smarter-sh/smarter/commit/fd8aa1b50e28443551961a9440e0a673a483531c))
- create SmarterCamelCaseSerializer for transforming django orm fields to SAM camelCase labels ([8e576c7](https://github.com/smarter-sh/smarter/commit/8e576c7a1aa0a0e0878ca667c4c075b375ffa3e9))
- create static api end points to use for unit tests ([2d62f3e](https://github.com/smarter-sh/smarter/commit/2d62f3e4a36857048d1aa3039bfb477547f5acb9))
- implement Connection and Plugin list views ([135742b](https://github.com/smarter-sh/smarter/commit/135742b77855ca4db657ac17f5073e63c26b01d5))
- implement SAMApiPluginBroker, SAMSqlPluginBroker, SAMApiConnectionBroker, SAMSqlConnectionBroker ([353aa72](https://github.com/smarter-sh/smarter/commit/353aa7225c89f7ab99106dde9263cf38bce9cf6e))
- scaffold ApiPlugin and SqlPlugin ([7ad3146](https://github.com/smarter-sh/smarter/commit/7ad3146f7724d93c5e865d348cb5142c8047390d))
- scaffold Connection and Plugin views ([4697291](https://github.com/smarter-sh/smarter/commit/469729126dcbb4bfc1ae96306dc4c1ef4bf588cf))
- scaffold PluginDataApi ([3e87099](https://github.com/smarter-sh/smarter/commit/3e87099eed12c0dc74c90892b56a424402d45892))
- scaffold SAMApiConnectionBroker ([2cd5e01](https://github.com/smarter-sh/smarter/commit/2cd5e01a5cb82c0518742a9fe03d77c3b1367a37))
- standardize all resource names originating from metadata.name to snake_case ([939a0a4](https://github.com/smarter-sh/smarter/commit/939a0a4dd3f8a896d155c2cd1ba3644ebdc5b80e))
- update manifest for new orm fields ([58ef7c6](https://github.com/smarter-sh/smarter/commit/58ef7c6c8b0c9283ec0519e7819be758dba7690d))
- use Pydantic to validate example_manifest(), get() and describe() ([365d3ff](https://github.com/smarter-sh/smarter/commit/365d3ff0d616002724c195fa46b3619c45c11f3b))

### Bug Fixes

- add cache invalidations for all functions decorated with [@cache](https://github.com/cache)\_results ([284f2c0](https://github.com/smarter-sh/smarter/commit/284f2c080789b971dfda543d63103e62b9ff4c74))
- add logic to read url from PreparedRequest object ([c4bae94](https://github.com/smarter-sh/smarter/commit/c4bae9411f5dab5914ae3f89c48ebc0de2ce1269))
- add missing url path /<int:chatbot_id>/config/ ([0c9d2f1](https://github.com/smarter-sh/smarter/commit/0c9d2f17234d86b2ff3a25ff5f8b81deef68510b))
- amnesty for /admin/ urls ([4ac6596](https://github.com/smarter-sh/smarter/commit/4ac6596a0d25551ded2698d2f55a6ddcfc09fc9f))
- anyone from the same account can edit ([ab72c99](https://github.com/smarter-sh/smarter/commit/ab72c9950b7405350026c0a945b84b5c37e414ce))
- broken create_charge() handler ([fadcb8e](https://github.com/smarter-sh/smarter/commit/fadcb8eab1778a94a817a6d725b1d07153ad9fef))
- broker initialization and token authentication bugs ([ca1b488](https://github.com/smarter-sh/smarter/commit/ca1b48832a9529688df14bd6f5066c4cbe414cac))
- chatbot deployment logic ([f038e62](https://github.com/smarter-sh/smarter/commit/f038e6286b7acc57aae03e73b4e69cb42f629b2f))
- ChatBot.sandbox_host should return a domain, not a url ([73e1ba6](https://github.com/smarter-sh/smarter/commit/73e1ba6b7e37309a8db8f40d1bab85e1c6edf76c))
- ChatBotHelper().api_host ([e3b2f25](https://github.com/smarter-sh/smarter/commit/e3b2f2578b2c89c5ab5bf00001841cc762aae5ba))
- correct KIND ([a3c5643](https://github.com/smarter-sh/smarter/commit/a3c5643305a68aedfa7133401099b6123e094bca))
- create a non-camel case serializer for PromptConfigView ([51a6a35](https://github.com/smarter-sh/smarter/commit/51a6a3563f7c5d6bbb21e0060b1dc439f7b6de59))
- index created_at and updated_at ([0beb107](https://github.com/smarter-sh/smarter/commit/0beb107040e6ed76ffcbbe8009d34e18ed11b0e5))
- initialization logic of AccountMixin ([5aa92c9](https://github.com/smarter-sh/smarter/commit/5aa92c9bf03aa126abd9879674a1ba90c682aac7))
- is_token_auth() should compare str to str ([1ba2c3a](https://github.com/smarter-sh/smarter/commit/1ba2c3a519cd50c22e563a5ec9e4d2116b48eb81))
- mixin initialization problems with DRF view classes ([2941a6e](https://github.com/smarter-sh/smarter/commit/2941a6e75b54c5981fbf79dd572804c557aab43c))
- move csrf_exempt decorator from class definitions to dispatch() ([80bced8](https://github.com/smarter-sh/smarter/commit/80bced889443d0c1fd628c9807ad8c5ccb265691))
- NO RECURSION PLEASE ([76df40a](https://github.com/smarter-sh/smarter/commit/76df40a466be65b27790a8a8909f6aec762660f7))
- null values that break openai api-compatible providers like MetaAI and GoogleAi ([cd3847d](https://github.com/smarter-sh/smarter/commit/cd3847d6e2a73e85ab6ab78eba18184f57c1e0bb))
- plugin_selector_history is a QuerySet ([4486180](https://github.com/smarter-sh/smarter/commit/4486180eae2927a49675567026fd0fed57496bd2))
- propagate session_key to other classes that we instantiate ([401222c](https://github.com/smarter-sh/smarter/commit/401222ca1eea0f17f85ba08f78cd66ee40493098))
- receiver parameters ([19ec9a2](https://github.com/smarter-sh/smarter/commit/19ec9a254e71231bfd07099322caa56d3ca1c342))
- setup a common url end point amnesty list ([3bab974](https://github.com/smarter-sh/smarter/commit/3bab97427a8f236cc355250178de14e0c16d62d1))
- str() should return **\*** followed by last 4 characters of digest ([a514196](https://github.com/smarter-sh/smarter/commit/a514196b6c41734dfe62bb76d4ba57e5a032d78d))
- type check what we believe to be a HttpRequest object ([cf375e4](https://github.com/smarter-sh/smarter/commit/cf375e4e2c6b1469c5a80bc8057474b6a610b583))
- when possible, override account based on account number in named url ([44da6ff](https://github.com/smarter-sh/smarter/commit/44da6fff9b08de61127957cb3c6676671af1e479))
