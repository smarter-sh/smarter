# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.14.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.14.0-alpha.4...v0.14.0-alpha.5) (2026-05-16)

### Bug Fixes

* cors get_response() ([e04d09b](https://github.com/smarter-sh/smarter/commit/e04d09b95e05e35c3cf9c35e26f1399e15bb5e8d))

## [0.14.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.13.223...v0.14.0-alpha.1) (2026-05-14)

### Key Highlights

- As [The Smarter Project](https://smarter.sh/) nears a quarter million lines of
  source code, we decided to clean house on this release. Technical features
  that address access, security and performance have been pushed downwards into
  Smarter's support subsystems, leading to application source code that is easier
  for new contributors to discover, read and understand.

- The desktop installation of Smarter has been simplified for developers
  as well as for anyone who is evaluating the platform.

- We hardened security for production cloud use with the introduction
  of technologies like [Calico](https://docs.tigera.io/calico/latest/about/)
  that make it easier to manage fine-grained cloud security policies by service.

Add, we made improvements to the existing platform...

#### Test Coverage

We added around 200 unit tests on this release, continuing our commitment to
shore up test [coverage](https://coverage.readthedocs.io/en/7.14.0/) on the
low-level layers of the stack where reliability and stability matter the most.

#### Documentation

We redoubled efforts to generate comprehensive platform-wide [Sphinx](https://www.sphinx-doc.org/en/master/)
[Read the Docs](https://docs.smarter.sh/en/latest/) documentation.
We're pleased to report that every module in the codebase now conforms
to Sphinx standards.

#### Accessibility

We improved the "1-click" desktop installation methodology for Windows
and Mac, reducing complexity of this operation, namely by minimizing
system package requirements for each operating system.

We also introduced expanded Helm installation options for Kubernetes
users. You now have multiple SQL service installation options.

#### Security

We hardened security for production cloud installations. Namely, we introduced
[Calico](https://docs.tigera.io/calico/latest/about/), a high-performance
networking and network security solution for Kubernetes. It provides container
networking interface (CNI) plugins that allow pods to communicate.
We're using Calico to enforce network policies, secure traffic with encryption,
and to enable observability across cloud, on-premises, and edge Kubernetes environments.

Additionally, we also did the following:

- created dedicated security policies for each service
- removed wildcards from all DNS records
- narrowed ingress and egress port ranges
- where possible, narrowed CIDR ranges for backend services
- introduced a new bastion admin Kubernetes pod that replaces the dedicated EC2
  bastion server. The bastion pod can be deployed on demand and then immediately
  disposed of, further minimizing the existence of a major attack surface. Separately,
  this also reduces your cloud bill by around $30 USD per month -- woo hoo!

#### Refactored Django apps

[Secret](./smarter/smarter/apps/secret/) and [Connection](./smarter/smarter/apps/connection/)
are now dedicated Django apps, paving the way for us to significantly expand the
feature set in future releases.

#### ASGI

We transitioned from WSGI to [ASGI](./smarter/smarter/asgi.py) on this release,
introducing asynchronous request features to the platform. We're presently using
these to serve personalized real-time Python server logs to the web console, an
exciting diagnostics feature for prompt engineers which we aspire to keep building
on in the future.

#### ReactJS

We transitioned much of the web console to [ReactJS front ends](./smarter/react/)
on this release. The dashboard, prompts list, prompting passthrough tool, and
server logs have all been implemented in ReactJS.

We've introduced a robust strategy for integrating React-Django that we believe
grants autonamy to front-end developers while maintaining resilient CI-CD processes.

#### Role-Based Access

We introduced RBAC to the SAM Architecture, greatly simplifying how resource access
is managed at the source code level. Specifically, we introduced two new methods
to Django's ORM manager, with_read_permission_for(`Student_in_course_123`) and
with_owernship_permission_for(`Instuctor_in_course_123`) that mask the
complexities of record selection, caching and cache invalidations,
while simultaneously making the source code more readable.
[Learn more here](./smarter/smarter/apps/account/models/metadata_with_ownership.py).

#### Service Layer Replacements

We transitioned from MySQL to [MariaDB](https://mariadb.org/), and from Nginx
to [Traefik](https://traefik.io/traefik), as both of the former
products decided to sunset support for their community versions in favor
of paid support plans which this project cannot afford.

#### Django v6

We upgraded to [Django 6.0](https://www.djangoproject.com/)! We're thrilled to
have access to Django's newest platform version. We also updated important PyPi
packages including celery, cryptography, django, levenshtein, nltk, pandas,
pinecone, pydantic, redis, requests, sphinx and urllib.

#### Django Reverse URLs

We implemented a class-based approach to working with named URLS that
significantly improves both code quality as well as tracability between
Django views and templates and the URL paths which they reference. See
[this example implementation](./smarter/smarter/apps/account/urls.py).

#### Logging

We introduced [user-based log streams](./smarter/smarter/lib/logging/redis_log_handler.py),
implemented with a combination of [Django middleware](https://docs.djangoproject.com/en/6.0/topics/http/middleware/),
Python [contextvars](https://docs.python.org/3.7/library/contextvars.html) and
Redis cache. This sends personalized streams of real-time Python server log data
to the web console, a highly effective diagnostics and trouble shooting
tool for prompt engineers. Users are able see the real-time server level execution
of sophisticated multi-step LLM prompts. This "best of both worlds" feature allows
prompt engineers to leverage Smarter's ease of use for designing sophsticated
prompts without losing visibility into what actually transpires between their
prompts and the LLM API.

#### Performance

We introduced internal resource caching to the SAM Architecture, greatly
reducing server workloads for the most common kinds of object lookups.

### New Features

- Vector Store App. This is scaffolding work towards an eventual release of a
  full-featured Vector store subsystem for developing custom RAG applications.
  - add dedicated sections for vectorstore, embeddings, indexModel ([3971c33](https://github.com/smarter-sh/smarter/commit/3971c3391d0b76ee33aea3dead83b682c1d59683))
  - code SAMVectorstoreBroker ([a1a8126](https://github.com/smarter-sh/smarter/commit/a1a81266ab47f0466fe24ad744ffceec3dad56f1))
  - code SAMVectorstoreBroker ([62c939a](https://github.com/smarter-sh/smarter/commit/62c939ac7db3f779665c64f45fc61286202e3a30))
  - code SAMVectorstoreBroker ([052c0aa](https://github.com/smarter-sh/smarter/commit/052c0aa8201c1736490893073cb32414ee88e8c5))
  - configure asgi websocket protocol ([77cfbc8](https://github.com/smarter-sh/smarter/commit/77cfbc827be474363b2576e1c3e5256967d018da))
  - scaffold example manifest ([c09f935](https://github.com/smarter-sh/smarter/commit/c09f9355a3648cdad88176d7fd8f483b11018600))
  - scaffold example manifest ([76ea4e5](https://github.com/smarter-sh/smarter/commit/76ea4e50a114ea64ecfcd360e08ae18207f1074c))
  - scaffold Pydantic SAM model ([82983d7](https://github.com/smarter-sh/smarter/commit/82983d7bffd6be6745bebd944fa8532091c05540))
  - scaffold urls, detail and list views ([7e2edac](https://github.com/smarter-sh/smarter/commit/7e2edac716828a1c2a17242915044121e7500775))
  - scaffold vectorstore app ([6855202](https://github.com/smarter-sh/smarter/commit/6855202982310e1ba8246c4dd87168a955948da0))
  - scaffold Vectorstore SAM broker ([bc19abb](https://github.com/smarter-sh/smarter/commit/bc19abbc1df4d8bf40d3359352821eed708f12de))
  - setup example_manifest ([f2d14d0](https://github.com/smarter-sh/smarter/commit/f2d14d0f9ac81295479116bae230a52cf0df90ed))
  - create vectorstore signal, receivers, html template, urls ([b1053df](https://github.com/smarter-sh/smarter/commit/b1053df9144025ab26392823b76918584a7d1897))
  - implement pinecone backend ([bd8fb71](https://github.com/smarter-sh/smarter/commit/bd8fb71a8e069ed0e5f67091c267be2780b38466))
  - map SAM fields to ORM models ([dfa4c4c](https://github.com/smarter-sh/smarter/commit/dfa4c4c0b2d4f233b999b568172de6e65fefd540))
- React UI for Dashboard, Logs, Prompts List, and Prompt Passthrough apps
  - scaffold prompt (text completion) api endpoints ([175e80e](https://github.com/smarter-sh/smarter/commit/175e80e5f09ebc933177260792a8c24e0e48051d))
  - scaffold prompt passthrough react component ([1da000a](https://github.com/smarter-sh/smarter/commit/1da000a772ab9498929a2df1c382b513f11b3ffe))
  - scaffold prompt passthrough UI ([c88216f](https://github.com/smarter-sh/smarter/commit/c88216f0f0fffc6f4a86e8c56bf483940ec91841))
  - scaffold React dashboard component ([c68d21d](https://github.com/smarter-sh/smarter/commit/c68d21d1ad283c2137a42602f22a4ec5d95d6879))
  - scaffold terminal emulator ([56e1848](https://github.com/smarter-sh/smarter/commit/56e18485c48e3bf136faa08708c9b4f3ca8f3b34))
  - add providers api ([aa717c3](https://github.com/smarter-sh/smarter/commit/aa717c32badbdb9b59bd901f10f352d07603cabd))
  - code passthrough_chat_provider ([efdea9a](https://github.com/smarter-sh/smarter/commit/efdea9a4d6706f759d900a795f94042f60a80234))
  - create /api/v1/account/batch-create-users/ ([d9d8416](https://github.com/smarter-sh/smarter/commit/d9d84169e7dedc3c1d6a3c237e66a64d06d3240e))
  - create /api/v1/account/batch-create-users/ ([805ed97](https://github.com/smarter-sh/smarter/commit/805ed97744fc9ce68d8eef0f421239ed86fe69df))
  - create a pure LLM chat completion passthrough view ([ff8072c](https://github.com/smarter-sh/smarter/commit/ff8072ce9554a4a0d8a2ff2c2d010ecc3b5cf772))
  - prompt passthrough component ([eedd1b2](https://github.com/smarter-sh/smarter/commit/eedd1b277f92d4df67fb69c1548d5242a406a57b))
  - re-scaffold terminal component ([7939ffe](https://github.com/smarter-sh/smarter/commit/7939ffe252296728a2836525adb779246013128d))
  - create passthrough component ([ddd5150](https://github.com/smarter-sh/smarter/commit/ddd5150b2ce123c4f0c64b6dbdd3d3e9d8a4b6df))
  - get passthrough component working ([0febd43](https://github.com/smarter-sh/smarter/commit/0febd43b15f2714f6ebf2460ec8f590b918dd811))
  - openai-compatible passthrough request ([0d6cfa7](https://github.com/smarter-sh/smarter/commit/0d6cfa7a720839f30cad942149cb57b0fee3fcc9))
  - port html widgets to react ([d3400ba](https://github.com/smarter-sh/smarter/commit/d3400ba6708fcb1831002e37c96c2bcc90cae314))
  - style passthrough component ([9fe56d3](https://github.com/smarter-sh/smarter/commit/9fe56d3b0e34566a9dc6bc54ce60cd62a67f19ab))
  - style the terminal app ([54b4225](https://github.com/smarter-sh/smarter/commit/54b422545a117fac386ac2bda2c0c21a565a19ec))
  - terminal window should display all log data, including what already was generated ([be6044c](https://github.com/smarter-sh/smarter/commit/be6044c1b11bd455450db66a5100873b5c29e200))
  - work on passthrough prompt UX ([e9ee16a](https://github.com/smarter-sh/smarter/commit/e9ee16a62c5d40d1ba5ec1a054f746cc416baf61))
- User-based Logging Streams
  - batch redis entries, and make stream more thread friendly ([5c3328d](https://github.com/smarter-sh/smarter/commit/5c3328df946febcf46044363312c90d1ab706e15))
  - create a redis-based streaming logger handler ([82b1958](https://github.com/smarter-sh/smarter/commit/82b1958cf6ef8eddbc7f04e3429a56369c791510))
  - create db migrations and admin ([82b77ea](https://github.com/smarter-sh/smarter/commit/82b77ea0bbdefd24e8ff8a8ca91c6ce68bd7a9c4))
  - dashboard server logs ([b7630f1](https://github.com/smarter-sh/smarter/commit/b7630f11dd71f3966f82808a7ff2efeba7b80370))
  - reconfigure for asgi ([1a10f97](https://github.com/smarter-sh/smarter/commit/1a10f978d7ac49575b59b804b0f614e607125cb4))
  - setup TTL for log streams ([b5ba41c](https://github.com/smarter-sh/smarter/commit/b5ba41ccf7b571bab8179b0e29f1f5ae60d51407))
  - setup waffle switch to control terminal app feature ([442e89f](https://github.com/smarter-sh/smarter/commit/442e89f4aad675211369d461918b9329478dd7c6))
  - switch to redis cache ([a6ea3e0](https://github.com/smarter-sh/smarter/commit/a6ea3e0894e9aa794c21c91b2b1c98c53110fd04))
- RBAC
  - override Manager functions ([01bfd50](https://github.com/smarter-sh/smarter/commit/01bfd504a45687dcbfcd943b5d18ce813c05aaa5))
  - override Manager functions ([afb4dd3](https://github.com/smarter-sh/smarter/commit/afb4dd320d5febf2a81b46e52e160392cd5a2a2d))
  - switch to with_ownership_permission_for() ([7048938](https://github.com/smarter-sh/smarter/commit/70489382ca003a296d0eb2457ac0b90470938ba2))
  - switch to with_read_permission_for() ([02b654e](https://github.com/smarter-sh/smarter/commit/02b654efdaa1d3cb802b3d3ca5de2dd0dc9238b7))
- update bandit, black, celery, cryptography, django, google-genai, levenshtein, mypy, mysqlclient, nltk, openmeteo, pandas, pinecone, pre-commit, pydantic, redis, requests, sphinx, tox, urllib ([7215a0e](https://github.com/smarter-sh/smarter/commit/7215a0e81006201fa460e7c772907ea3109ce205))

### Bug Fixes

- add error handling to every db operation ([8326a34](https://github.com/smarter-sh/smarter/commit/8326a34b98b3f877ee229247c2bef30fd641f759))
- add error handling to every db operation ([ed3cb9c](https://github.com/smarter-sh/smarter/commit/ed3cb9c1f7ee4b56534bfb6c2f27741e90febf3a))
- add new function definition keys ([365f783](https://github.com/smarter-sh/smarter/commit/365f783877780f8edecd7ba9cf5a6be772dd2766))
- add pint for metric/uscs conversions ([b9d9ff9](https://github.com/smarter-sh/smarter/commit/b9d9ff9d59b6a2b4e9a7c7164c0ee393f4eeb6ae))
- add Provider to ChatDbMixin ([dc2e492](https://github.com/smarter-sh/smarter/commit/dc2e492d1a4887539c7513d26a52b81d9a4af90d))
- add Provider.default_model ([033db0b](https://github.com/smarter-sh/smarter/commit/033db0b94a6e14a2e2392b4d0252fb3ad18104eb))
- add Provider.default_model ([26436bc](https://github.com/smarter-sh/smarter/commit/26436bcfbf0884fa76064036e425ea4bb9e40e68))
- add snowfall, weathercode, windspeed_10m, winddirection_10m, windgusts_10m, cloudcover ([fdb447c](https://github.com/smarter-sh/smarter/commit/fdb447c6b063cbac09b8744f8fedf3c9c14a1573))
- AttributeError: 'NoneType' object has no attribute 'validate' ([f193275](https://github.com/smarter-sh/smarter/commit/f193275f1f0763b918d88fc6836ad79d57c4d634))
- fail gracefully when name is not provided ([1adc583](https://github.com/smarter-sh/smarter/commit/1adc5831600a67fcbf1e1170e6df493c74707502))
- fully validate manifest connection field ([c8d3507](https://github.com/smarter-sh/smarter/commit/c8d3507ea4e658080d57241b0ef2ebc8cbc84918))
- give the cache a filename ([bad5bc3](https://github.com/smarter-sh/smarter/commit/bad5bc3f2c28e3531f5261c43d806c8f97753a53))
- make most Account fields optional. freeze UserProfile and Account.account_number ([5d3c82d](https://github.com/smarter-sh/smarter/commit/5d3c82dc1506a654b5ff4bc61a58fe4866e9ae61))
- middleware infinite recursion edge problem ([0cd1819](https://github.com/smarter-sh/smarter/commit/0cd1819151fedb7e569a3affef9329604b210c20))
- post-deployment bugs ([44f2fc9](https://github.com/smarter-sh/smarter/commit/44f2fc9a51e87b8b910e810cef4f7a43fc38a0c9))
- pop related fields from django orm ([1f2f94f](https://github.com/smarter-sh/smarter/commit/1f2f94f6ff3ff1ca386f8ce4a57c8d6e8d4b725c))
- qualify that request.user is a User ([0ca1255](https://github.com/smarter-sh/smarter/commit/0ca12552728f8ab943b0451644933013f8fa65ce))
- remove page caching ([0f9e696](https://github.com/smarter-sh/smarter/commit/0f9e6969a566c996de4179694b301345d9f433aa))
- requests cache path ([615d148](https://github.com/smarter-sh/smarter/commit/615d1480ef06bf890d53e6015e2902d9bf7fe47f))
- revert to old style ([67f7c24](https://github.com/smarter-sh/smarter/commit/67f7c24baac9ece3644153c8789e573c0f641e2b))
- use HTTP_X_FORWARDED_PROTO to determine protocol of originating request ([bb4f050](https://github.com/smarter-sh/smarter/commit/bb4f05056bca443b118379fa0b696f690fde75cf))
- use Pydantic for validations ([90c24f7](https://github.com/smarter-sh/smarter/commit/90c24f7932d3f4f0aa27f1a1758598403621f32d))
- validate email address ([2874f7e](https://github.com/smarter-sh/smarter/commit/2874f7e3b507fbf0f83e0503186b323478d7a72a))

## [0.14.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.14.0-alpha.1...v0.14.0-alpha.2) (2026-05-15)

### Bug Fixes

- add waffle switches for all custom middleware ([285fafd](https://github.com/smarter-sh/smarter/commit/285fafd5e280de6386884d37261b061368511c20))

## [0.14.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.14.0-alpha.2...v0.14.0-alpha.3) (2026-05-15)

### Bug Fixes

- ensure that all middleware always returns a response ([63f8bb5](https://github.com/smarter-sh/smarter/commit/63f8bb551f8646e32da5dc18c1a3212c4ebf9436))

## [0.14.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.14.0-alpha.3...v0.14.0-alpha.4) (2026-05-16)

### Bug Fixes

- convert to asgi compatible middleware ([a4ab703](https://github.com/smarter-sh/smarter/commit/a4ab703fd148da545cd19d5a9c554158528a561c))

## [0.13](./changelogs/CHANGELOG-v0.13.md) (2026-04-19)

## [0.12](./changelogs/CHANGELOG-v0.12.md) (2025-06-02)

## [0.11](./changelogs/CHANGELOG-v0.11.md) (2025-04-27)

## [Project Inception Through 0.10](./changelogs/CHANGELOG-v0.10.md) (2025-04-11)
