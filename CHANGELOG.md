## [0.10.19](https://github.com/smarter-sh/smarter/compare/v0.10.18...v0.10.19) (2025-03-28)


### Bug Fixes

* add a SmarterConfigurationError to the stack trace ([19143d3](https://github.com/smarter-sh/smarter/commit/19143d3b6b25c98c85cc892b59011d16d7694c8b))
* avoid unnecessarily attempting to create a new chat session unless we have a session_key ([1a4e86d](https://github.com/smarter-sh/smarter/commit/1a4e86d9d63962f3187e5ae63323065b5ee88630))
* only log and send django signal if we know that this is a chatbot. ([3478390](https://github.com/smarter-sh/smarter/commit/3478390338fba4be3c8df24d3871b8a98ba85be3))
* wait 10 seconds before attempting health check ([1c647f8](https://github.com/smarter-sh/smarter/commit/1c647f8873aeca9c25a77d83171088da2fd39a96))

## [0.10.18](https://github.com/smarter-sh/smarter/compare/v0.10.17...v0.10.18) (2025-03-21)


### Bug Fixes

* csrf exceptions for chatbots ([5a47e77](https://github.com/smarter-sh/smarter/commit/5a47e77693de415f073762b05a81bcf325925d06))
* pass request object to ChatBotHelper ([62af264](https://github.com/smarter-sh/smarter/commit/62af264b21bfb61f0dcd65686cce34041bb06b6c))

## [0.10.17](https://github.com/smarter-sh/smarter/compare/v0.10.16...v0.10.17) (2025-03-21)


### Bug Fixes

* session_key ([66cbe68](https://github.com/smarter-sh/smarter/commit/66cbe68bbb29e66579682cc3b0ce0716ed939588))

## [0.10.16](https://github.com/smarter-sh/smarter/compare/v0.10.15...v0.10.16) (2025-03-19)


### Bug Fixes

* bug fix where environment url was initializing as a chatbot ([51273a8](https://github.com/smarter-sh/smarter/commit/51273a8b2cf99a01a2209b1618a5e13e388c60a5))
* csrf exempt ApiV1CliChatApiView and ApiV1CliChatConfigApiView ([cb812f1](https://github.com/smarter-sh/smarter/commit/cb812f1efade9ae447c7663a3d678d1828c7ba73))
* if there's no chatbot then return None ([31724a4](https://github.com/smarter-sh/smarter/commit/31724a45f303f9781d6177d9bcc0bcba901ac436))
* remove authentication requirement ([6cff04e](https://github.com/smarter-sh/smarter/commit/6cff04ed20d9f6c6697593d4e4281de491502294))
* request object sometimes is not set. use self.url ([5e981f4](https://github.com/smarter-sh/smarter/commit/5e981f497c367c5a8ebfc27dea135bd096c0a1cb))

## [0.10.15](https://github.com/smarter-sh/smarter/compare/v0.10.14...v0.10.15) (2025-03-18)


### Bug Fixes

* environment api domain is hosted from root domain ([fd4f930](https://github.com/smarter-sh/smarter/commit/fd4f9305b7fba4b58de7392d1f423385bb80a347))
* parent domain should be root domain ([f54fb14](https://github.com/smarter-sh/smarter/commit/f54fb144756792442443a785a7534bbe3ddb95ba))
* wrap the entire load process in a try block ([7509b7b](https://github.com/smarter-sh/smarter/commit/7509b7b99869df5797420321db2f4baa0836b0a3))

## [0.10.14](https://github.com/smarter-sh/smarter/compare/v0.10.13...v0.10.14) (2025-03-17)


### Bug Fixes

* Add chatbot deploy, undeploy and delete signals and receivers. Add KubernetesHelper functions to delete ingress resources. Refactor chatbot task logging ([3c4a7db](https://github.com/smarter-sh/smarter/commit/3c4a7db8f22034035eab6f0b44a5ac51e1455e16))
* add ChatBot.tls_certificate_issuance_status ([e771c22](https://github.com/smarter-sh/smarter/commit/e771c22bd7dfc40f5372f784d3a80f2c96657aa5))
* add ChatBot.tls_certificate_issuance_status ([39bf944](https://github.com/smarter-sh/smarter/commit/39bf94455c3533df08a217ac0570a7eb435f8912))
* add mysql root credentials ([08db79c](https://github.com/smarter-sh/smarter/commit/08db79c57c9498263472c04034db6be172908d95))
* add verifications for ingress, certificate, secret ([07b655d](https://github.com/smarter-sh/smarter/commit/07b655d1b5386c254496303e2163bca60d8e0b13))
* CSRF_TRUSTED_ORIGINS = [smarter_settings.environment_domain, smarter_settings.api_domain, smarter_settings.customer_api_domain] ([31541b0](https://github.com/smarter-sh/smarter/commit/31541b0d72947a847ab5bd16899aaa066c582458))
* don't wait if the tls cert is already verified ([bc997ec](https://github.com/smarter-sh/smarter/commit/bc997ece515150b9b4241e1210d70ed734344e0a))
* enable the dismiss button on the password reset confirmation modal ([3ac954b](https://github.com/smarter-sh/smarter/commit/3ac954b1f9dc05a9bb897660b10f82a6e8840200))
* environment_api_domain should reside inside platform domain ([7ce6a8e](https://github.com/smarter-sh/smarter/commit/7ce6a8e5dc5d01d81923f2528faf77a3e09cd380))
* exempt known benign file extensions ([dfaf2b5](https://github.com/smarter-sh/smarter/commit/dfaf2b54b821aa533a6f0f66027b62ea218d7319))
* explicitly initialize AccountMixin() in __init__() ([46da800](https://github.com/smarter-sh/smarter/commit/46da800e92cddd2a3b86114afe645ed1845196bb))
* namespace ([e5e4d8a](https://github.com/smarter-sh/smarter/commit/e5e4d8a8b9212599901ddfc8eba885678ae138a8))
* only send deployment emails to primary point of contact for account ([d5ceba7](https://github.com/smarter-sh/smarter/commit/d5ceba71b64d4f2e8a11e9bed764396d8af9154f))
* only wait if the tls cert is not yet verified ([99a9b2e](https://github.com/smarter-sh/smarter/commit/99a9b2e29fe84c198a138337b6b75bbb3e3df9f2))
* override __call__() ([5d7b115](https://github.com/smarter-sh/smarter/commit/5d7b11510ee9c39fef5d1614f853c6a4f797ab08))
* override __call__() ([4691899](https://github.com/smarter-sh/smarter/commit/46918990da1c82cc568a0155bddc47054c72b7b6))
* split user creation from password update ([72a0b4e](https://github.com/smarter-sh/smarter/commit/72a0b4e8b8fcfa7b812ae210f6e4ac754a2cd0dd))
* user is not longer 1:1 with user_profile ([862fa85](https://github.com/smarter-sh/smarter/commit/862fa851ff6367f48d791da1d61df55aad33e5f8))
* user is not longer 1:1 with user_profile ([ba145f0](https://github.com/smarter-sh/smarter/commit/ba145f026155268a67f054ee008bed49d9d1f9af))

## [0.10.13](https://github.com/smarter-sh/smarter/compare/v0.10.12...v0.10.13) (2025-02-14)


### Bug Fixes

* allow password reset urls ([f08e397](https://github.com/smarter-sh/smarter/commit/f08e397531bf2069ba8274691db94e786bedf62c))
* allow password reset urls ([a70652d](https://github.com/smarter-sh/smarter/commit/a70652da9e09a425e57fe0e2dd2bc0f7b4aa4711))

# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.10.12](https://github.com/smarter-sh/smarter/compare/v0.10.11...v0.10.12) (2025-02-14)

### Bug Fixes

- add a logged in receiver to verify UserProfile for authenticated user ([fb35a97](https://github.com/smarter-sh/smarter/commit/fb35a97bbeaf872ee41b7fb60d2d1500b1e1e16a))
- set SOCIAL_AUTH_LINKEDIN_OAUTH2_SCOPE ([563bc8e](https://github.com/smarter-sh/smarter/commit/563bc8e30e26b907a7fecfd62d276601ea121479))
- stop echoing the new pwd to the console ([d1836ee](https://github.com/smarter-sh/smarter/commit/d1836ee44183c6efdb1f79f2b2ce6f634e12978d))
- whoami, status, version don't have a manifest kind ([c01d841](https://github.com/smarter-sh/smarter/commit/c01d84183bd26ce955c5c6cc90d39409fe3c3874))

## [0.10.11](https://github.com/smarter-sh/smarter/compare/v0.10.10...v0.10.11) (2025-02-11)

### Bug Fixes

- back-peddle on blending Smarter account bots with other accounts ([715e237](https://github.com/smarter-sh/smarter/commit/715e237cebeaff0982b9df24b7257d9d3601cb66))
- remove functionality to combine Smarter account chatbots ([9f58f8a](https://github.com/smarter-sh/smarter/commit/9f58f8ad04c1a4ff2661bfd57161d97d170ce5c6))

## [0.10.10](https://github.com/smarter-sh/smarter/compare/v0.10.9...v0.10.10) (2025-02-11)

### Bug Fixes

- check for SAMPluginSpecSelectorKeyDirectiveValues.ALWAYS in selected() ([b841915](https://github.com/smarter-sh/smarter/commit/b8419154cb202705006cf1e61624c55bdec0c174))
- consider that user_profile might be NoneType ([ee51324](https://github.com/smarter-sh/smarter/commit/ee51324902d91caa5a33d113fee62ebede49a54e))
- search_terms must allow nulls and blanks ([f4f71f3](https://github.com/smarter-sh/smarter/commit/f4f71f362ab5c72d1ec6fb56db6e766f93af1b37))
- set SOCIAL_AUTH_LINKEDIN_OAUTH2_SCOPE ([39a91e1](https://github.com/smarter-sh/smarter/commit/39a91e1553a923d913310395f9d14eecc9639a6d))

## [0.10.9](https://github.com/smarter-sh/smarter/compare/v0.10.8...v0.10.9) (2025-02-10)

### Bug Fixes

- if we have both plugin_meta AND manifest, then the manifest takes precedence ([ddfd25a](https://github.com/smarter-sh/smarter/commit/ddfd25a89b92ffd461650e9be8cda4766a9b22a5))

## [0.10.8](https://github.com/smarter-sh/smarter/compare/v0.10.7...v0.10.8) (2025-02-09)

### Bug Fixes

- convert url params into valid strings ([f12346a](https://github.com/smarter-sh/smarter/commit/f12346ad878e2ec248991988351bceed837e0683))
- get_model_titles() should return titles in underscored lower case ([6a31bb6](https://github.com/smarter-sh/smarter/commit/6a31bb61cd6b086b6139a93aca4b0a8f9709b33c))
- send all table output in camelCase ([81a49bb](https://github.com/smarter-sh/smarter/commit/81a49bb7ef035284a7a0a769ac73492eaaa818ef))

## [0.10.7](https://github.com/smarter-sh/smarter/compare/v0.10.6...v0.10.7) (2025-02-09)

### Bug Fixes

- check isinstance(request, WSGIRequest) ([8e2492e](https://github.com/smarter-sh/smarter/commit/8e2492ebb66b06bfaf868f85ebf7022d0cbb1d91))
- fully inspect request before attempting to do anything with it ([19f9ace](https://github.com/smarter-sh/smarter/commit/19f9ace2ea74bb8ea31dc66b501c61f8c74e4f57))
- initialize the admin for the account when we only have an account number ([7770406](https://github.com/smarter-sh/smarter/commit/7770406e658ccbabb0add0bfb1d3e6bd944373f5))
- look for mysql db errors ([c41e21f](https://github.com/smarter-sh/smarter/commit/c41e21f461d8d7cd6fb609c4b88da09894953c44))
- set api keys for googleai and metaai ([26596fb](https://github.com/smarter-sh/smarter/commit/26596fb531339ae5421a71e2efb16d2c47392dd1))
- SmarterRequestMixin should ignore paths for django /admin/ and /docs/ ([cb777f7](https://github.com/smarter-sh/smarter/commit/cb777f70b140d40f5db62c57fc78e79efb406a05))

## [0.10.6](https://github.com/smarter-sh/smarter/compare/v0.10.5...v0.10.6) (2025-02-04)

This is a major low-level refactoring of business logic for Account and WSGI request objects. Summarizing the nature of changes:

- moved most db insert/update/delete operations to asynchronous background tasks.
- refactor all account logic into [AccountMixin](./smarter/smarter/apps/account/mixins.py) to standardize business logic and to improve db caching
- refactor all WSGI request analysis into [SmarterRequestMixin](./smarter/smarter/lib/django/request.py) to standardize identification of chat and chatbot requests and to improve cache performance.

### Bug Fixes

- add a generic Exception handler for cases where Python doesn't catch AttributeError ([42a757b](https://github.com/smarter-sh/smarter/commit/42a757b4e44824887389f57aaa4ea1236000f585))
- add account to Chat.objects.create() ([9cb4e0c](https://github.com/smarter-sh/smarter/commit/9cb4e0cf5cc48bb6f790ec71f304738768b92a4a))
- bad user attribute. changed 'user' to 'email' ([8fa4156](https://github.com/smarter-sh/smarter/commit/8fa4156195d2f224070d2b93afbaafbc7319ccaf))
- catch any exception on SAMJournal.objects.create() ([e2e3746](https://github.com/smarter-sh/smarter/commit/e2e3746e587c9e481df11086af56f90ea2750a0d))
- chatbot_id initialization from <int:chatbot_id>/chat/config/ ([2ed7f77](https://github.com/smarter-sh/smarter/commit/2ed7f771d8e9940af50600f135824698da0b3b25))
- ChatBotHelper and ChatBotApiBaseViewSet handling of named urls - https://example.3141-5926-5359.api.smarter.sh ([2bc5877](https://github.com/smarter-sh/smarter/commit/2bc5877cdd4e74373ff2e3818f10b6bd8fe722de))
- cleanup json dump ([24e62b5](https://github.com/smarter-sh/smarter/commit/24e62b5f1114605095483e9307ffa842a9cd79cf))
- ensure that ChatBotHelper still works with sandbox urls ([6bca39a](https://github.com/smarter-sh/smarter/commit/6bca39adccb61a792a238cb0cc56d128347df783))
- ensure that the url path includes /api/ ([4bfebb9](https://github.com/smarter-sh/smarter/commit/4bfebb9a149cf8e48c8fe32535b4d315e29cdb37))
- ensure that thing and command are present in journaled json error responses ([1110ef3](https://github.com/smarter-sh/smarter/commit/1110ef3ee5883f6f2e5120b4e320d548a6055513))
- ensure that thing and command are present in journaled json error responses ([e0cf9c3](https://github.com/smarter-sh/smarter/commit/e0cf9c3c03b637e08679b4f16c4b2658ee460e43))
- ensure that we can journal commands w no manifest ([5de8a5e](https://github.com/smarter-sh/smarter/commit/5de8a5e3cca0c47663c4294885f5c2f74ca417fe))
- fail more gracefully is we don't find the chatbot ([04f674c](https://github.com/smarter-sh/smarter/commit/04f674c8fa74d6be08ee9fe7e95586ca4da7c343))
- get the journal working with anonymous users ([ceb1d6b](https://github.com/smarter-sh/smarter/commit/ceb1d6bb7b994ec9e3a5c16d404a2630e54986b1))
- handle /smarter/<str:name> ([de979e0](https://github.com/smarter-sh/smarter/commit/de979e0d26fafb661a4561c0f1195c83a807eebf))
- handle cases where properties are unset after initialization ([188b72b](https://github.com/smarter-sh/smarter/commit/188b72ba0570a4b677e5c6507ae187ec914162a3))
- handle cases where properties are unset after initialization ([785d1e8](https://github.com/smarter-sh/smarter/commit/785d1e84844ff33a934f1bd166280def4376a2fc))
- handle cases where properties are unset after initialization ([84abe52](https://github.com/smarter-sh/smarter/commit/84abe5200de63fd9fd504d85d19f548665ccfd1d))
- initialize user_profile from user and account properties instead of local variables ([ececf82](https://github.com/smarter-sh/smarter/commit/ececf82d5c7e02751c7cc92fc936737e82b9b52e))
- instantiations from chatbot id ([e0bf9f1](https://github.com/smarter-sh/smarter/commit/e0bf9f134fcb66afa377dd0c3c9af2bbcbe6d563))
- is_named_url ([423eae8](https://github.com/smarter-sh/smarter/commit/423eae8b3f888b619cf58a9897e8f78682c2d440))
- journaled json error responses ([d6a1599](https://github.com/smarter-sh/smarter/commit/d6a15993c23a6cb72dcfdcb64ae763bc72dffac7))
- make bool defaults serializable ([3e88a43](https://github.com/smarter-sh/smarter/commit/3e88a43559d583c8640036bfca0a026638eb0331))
- only cache if we actually have an object. duhgit add . ([1dc01b2](https://github.com/smarter-sh/smarter/commit/1dc01b25ba0c9ff523ff3510910b64e246597caa))
- only create a new chat session if we have all of the data ([e96fc6f](https://github.com/smarter-sh/smarter/commit/e96fc6f9f38c15088f1d625db9a97c6a29e0e7c9))
- race condition when tearing down ([27a8729](https://github.com/smarter-sh/smarter/commit/27a8729a4592f10e8a2b6d6b2edf66e57dbbf736))
- recursion problems in self.cache due introduced by early read attempts ([25edb2a](https://github.com/smarter-sh/smarter/commit/25edb2a38ce0784b50dd7573086a3a6edc01aeed))
- remove /smarter/ endpoint ([0e12955](https://github.com/smarter-sh/smarter/commit/0e129553d96fbc757b1204d431d4069df4a66797))
- send a 403 response on auth failure ([7df3489](https://github.com/smarter-sh/smarter/commit/7df3489e9e3f73a36d21ee32602ba36c45d58065))
- set db password on each deployment, in case it changes ([df09b48](https://github.com/smarter-sh/smarter/commit/df09b48c5daf2b4b7b1c276a5880292168bb3a90))
- url_chatbot should take the form /api/v1/chatbots/{self.id}/ ([fc1662e](https://github.com/smarter-sh/smarter/commit/fc1662e089558218f8aa4e82ce9c8438baede1fd))

## [0.10.5](https://github.com/smarter-sh/smarter/compare/v0.10.4...v0.10.5) (2025-01-24)

### Bug Fixes

- add smarter demo bots to ChatBotHelper.**init**() ([52e7cdd](https://github.com/smarter-sh/smarter/commit/52e7cdd4b449e52779d7f747163927d2a102f82c))
- ChatConfigView() should always return json ([e1274bb](https://github.com/smarter-sh/smarter/commit/e1274bbb856062384d1ddbdb7a34111ee1e2833b))
- ChatConfigView() should always return json ([bbb04b4](https://github.com/smarter-sh/smarter/commit/bbb04b49b9f21c787213f7db8eb2b6d10ba4582f))
- ensure that we can fall back to a smarter chatbot if it exists ([a221491](https://github.com/smarter-sh/smarter/commit/a221491efd6b32c8ecd19b5ad58cc3c8c4e052b4))

## [0.10.4](https://github.com/smarter-sh/smarter/compare/v0.10.3...v0.10.4) (2025-01-23)

### Bug Fixes

- add first_name, last_name ([8ff338a](https://github.com/smarter-sh/smarter/commit/8ff338ab882857514434088cbda39ff9c9b2a809))
- give celery time to create records before making assertions ([0948076](https://github.com/smarter-sh/smarter/commit/0948076e75da9a2da651d83615bb90cacbd3951b))
- move PluginSelectorHistory.objects.create() to celery ([4dd28de](https://github.com/smarter-sh/smarter/commit/4dd28deb3d26149c26f1fc9da117648c18f9de04))
- provide a user_profile to Plugin whenever possible ([ab2a5fc](https://github.com/smarter-sh/smarter/commit/ab2a5fcd87847311c067d366040fec97574f810b))
- providers should not be singletons ([5d210fa](https://github.com/smarter-sh/smarter/commit/5d210faa68603829043a0134d5829b6a5bb6b38b))

## [0.10.3](https://github.com/smarter-sh/smarter/compare/v0.10.2...v0.10.3) (2025-01-22)

### Bug Fixes

- broken favicon link ([80c22ef](https://github.com/smarter-sh/smarter/commit/80c22ef175bc74c8009ec426feb6164dbb0acd12))
- broken link media/illustrations/sigma-1/17-dark.png ([bbce490](https://github.com/smarter-sh/smarter/commit/bbce490deecfb1e94a8742749250f352250fffcb))
- only show django admin, wagtail, changelog to superusers ([65183dd](https://github.com/smarter-sh/smarter/commit/65183dd60ad4865766df85cfc5e626c3126c8b40))

## [0.10.2](https://github.com/smarter-sh/smarter/compare/v0.10.1...v0.10.2) (2025-01-22)

### Bug Fixes

- broken plugins link ([99cc24d](https://github.com/smarter-sh/smarter/commit/99cc24d72a9abe881c000281e88333d69108bd8e))

## [0.10.1](https://github.com/smarter-sh/smarter/compare/v0.10.0...v0.10.1) (2025-01-22)

### Bug Fixes

- broken password reset url ([fb916a7](https://github.com/smarter-sh/smarter/commit/fb916a7c2fbceca5c323f002d11f171210c9ae4b))

# [0.10.0](https://github.com/smarter-sh/smarter/compare/v0.9.0...v0.10.0) (2025-01-22)

### Bug Fixes

- add toggle switch to display/hide system messages ([0d2e5dd](https://github.com/smarter-sh/smarter/commit/0d2e5dd713918a9d4100f2fe7b73dd9544742058))
- add toggle switch to display/hide system messages ([979c586](https://github.com/smarter-sh/smarter/commit/979c586b67a629f2934f2012a4cfb4b54ada9a94))
- ensure that all django objects are created via Celery ([9b4812b](https://github.com/smarter-sh/smarter/commit/9b4812b468e576b765c302c06d6d21b1c26adf8f))
- make verbose logging a function of a waffle switch ([8e90ee5](https://github.com/smarter-sh/smarter/commit/8e90ee5d8293b5f0e800d200e891892d127b86d4))
- send user credentials by email ([07d4dad](https://github.com/smarter-sh/smarter/commit/07d4dad4eba37c0151227c889c1a011857eee10d))
- sign in url should be a valid url instead of only a domain ([d37d30b](https://github.com/smarter-sh/smarter/commit/d37d30be2c073d13eabeeb1d47862ae93ff9b480))

### Features

- add an html welcome email for new accounts. ([310e137](https://github.com/smarter-sh/smarter/commit/310e137a101afc7f353ecf0b032eb144c045cf78))
- add DailyBillingRecord model ([8f29565](https://github.com/smarter-sh/smarter/commit/8f29565dd564052adf7c1ba1b93b5d23ea157cdd))
- cache chat instances by session_key ([9fb97e9](https://github.com/smarter-sh/smarter/commit/9fb97e977a7fe7a23fd65988cb450c5991ea9da3))
- create ProviderDbMixin as middleware for all async db operations ([1e5c964](https://github.com/smarter-sh/smarter/commit/1e5c9649dfae0897c1bf31f4fe34f8a481351849))
- echo tool return values to the chat console ([1b43c97](https://github.com/smarter-sh/smarter/commit/1b43c970ab15fe9c4c861af70558d08994c1df2b))
- log any cache hits ([35e04d3](https://github.com/smarter-sh/smarter/commit/35e04d3a548dbc9f401d2f9753ce26f2cd57ec2d))

## [0.10.1](https://github.com/smarter-sh/smarter/compare/v0.10.0...v0.10.1) (2025-01-22)

### Bug Fixes

- broken password reset url ([fb916a7](https://github.com/smarter-sh/smarter/commit/fb916a7c2fbceca5c323f002d11f171210c9ae4b))

# [0.10.0](https://github.com/smarter-sh/smarter/compare/v0.9.0...v0.10.0) (2025-01-22)

### Bug Fixes

- add toggle switch to display/hide system messages ([0d2e5dd](https://github.com/smarter-sh/smarter/commit/0d2e5dd713918a9d4100f2fe7b73dd9544742058))
- add toggle switch to display/hide system messages ([979c586](https://github.com/smarter-sh/smarter/commit/979c586b67a629f2934f2012a4cfb4b54ada9a94))
- ensure that all django objects are created via Celery ([9b4812b](https://github.com/smarter-sh/smarter/commit/9b4812b468e576b765c302c06d6d21b1c26adf8f))
- make verbose logging a function of a waffle switch ([8e90ee5](https://github.com/smarter-sh/smarter/commit/8e90ee5d8293b5f0e800d200e891892d127b86d4))
- send user credentials by email ([07d4dad](https://github.com/smarter-sh/smarter/commit/07d4dad4eba37c0151227c889c1a011857eee10d))
- sign in url should be a valid url instead of only a domain ([d37d30b](https://github.com/smarter-sh/smarter/commit/d37d30be2c073d13eabeeb1d47862ae93ff9b480))

### Features

- add an html welcome email for new accounts. ([310e137](https://github.com/smarter-sh/smarter/commit/310e137a101afc7f353ecf0b032eb144c045cf78))
- add DailyBillingRecord model ([8f29565](https://github.com/smarter-sh/smarter/commit/8f29565dd564052adf7c1ba1b93b5d23ea157cdd))
- cache chat instances by session_key ([9fb97e9](https://github.com/smarter-sh/smarter/commit/9fb97e977a7fe7a23fd65988cb450c5991ea9da3))
- create ProviderDbMixin as middleware for all async db operations ([1e5c964](https://github.com/smarter-sh/smarter/commit/1e5c9649dfae0897c1bf31f4fe34f8a481351849))
- echo tool return values to the chat console ([1b43c97](https://github.com/smarter-sh/smarter/commit/1b43c970ab15fe9c4c861af70558d08994c1df2b))
- log any cache hits ([35e04d3](https://github.com/smarter-sh/smarter/commit/35e04d3a548dbc9f401d2f9753ce26f2cd57ec2d))

## [0.9.0](https://github.com/smarter-sh/smarter/compare/v0.8.0...v0.9.0) (2025-01-14)

### Bug Fixes

- all docs paths should be relative to the ubuntu smarter_user home folder ([b7de813](https://github.com/smarter-sh/smarter/commit/b7de8139d0e02ccfe9d8778984539e43aaf86e22))
- chatbot_requests_serializer is many=False ([419825d](https://github.com/smarter-sh/smarter/commit/419825d472afc50db69ffb0f793d95648dbd8f4c))
- check whether user is authenticated before setting dashboard context ([b0f7d7a](https://github.com/smarter-sh/smarter/commit/b0f7d7a53d5eb51b8b9b508094394dc008907095))
- clean messages on 2nd pass ([8e1ab22](https://github.com/smarter-sh/smarter/commit/8e1ab22a31cd015e137437852b3b0287977ff6f3))
- developer doc paths ([b459d4d](https://github.com/smarter-sh/smarter/commit/b459d4d3ec248f300c5450f540d7947dff1f58b6))
- developer doc paths ([8793dea](https://github.com/smarter-sh/smarter/commit/8793dea455b271b0af18d7ff97b7c4e3c083da83))
- redirect to login page on 403 error ([b3f0240](https://github.com/smarter-sh/smarter/commit/b3f0240a3fa0ed4bd71cd66c8301f44b593ecd9d))
- trouble shoot smarter dict first_iteration and second_iteration dicts ([2388b86](https://github.com/smarter-sh/smarter/commit/2388b8621b11fe853b325b71f4ee6b66793f0fac))
- we only want the most recent batch of requests ([a90a4d8](https://github.com/smarter-sh/smarter/commit/a90a4d873dde0148345b54928f60db8a228e8e4d))

### Features

- add more smarter dashboard widgets ([a9d66f7](https://github.com/smarter-sh/smarter/commit/a9d66f78f2174e0a1c1c623eac1fd2cf40c1681b))
- add smarter meta prompts for function calling and token charges ([357b576](https://github.com/smarter-sh/smarter/commit/357b576152809c1f6961e41ea67fec87f7c65513))
- code dashboard widgets ([3967b7a](https://github.com/smarter-sh/smarter/commit/3967b7a15745dc9b87014ffbe7a54a4c23de1220))
- create and style smarter dashboard widgets ([9d059e7](https://github.com/smarter-sh/smarter/commit/9d059e7a9b3e811e34451a69139c098b657aa50c))
- ensure that message history is not duplicated ([7421540](https://github.com/smarter-sh/smarter/commit/74215406aa314f8843a8b8ce46456ed4eed9a092))
- finesse component state management ([b9916b3](https://github.com/smarter-sh/smarter/commit/b9916b3727c3015304806d67455e82081fae864c))
- get Console working with ChatApp config as a prop ([2c087c0](https://github.com/smarter-sh/smarter/commit/2c087c025d4a55b775f7cf1ffbb5e3c9aae176b6))

## [0.8.0](https://github.com/smarter-sh/smarter/compare/v0.7.9...v0.8.0) (2025-01-12)

### Bug Fixes

- path to developer docs ([c7b9e74](https://github.com/smarter-sh/smarter/commit/c7b9e749b49b911d56d4d177c0d71fbd7c459faf))

### Features

- add ability to create a new chat session. ([0b749cc](https://github.com/smarter-sh/smarter/commit/0b749cc7696aece16e4a31c4eb66a5947b8dd272))
- add context managed config to ChatApp ([b00845b](https://github.com/smarter-sh/smarter/commit/b00845b9b976136426ee6d2ee523b1badd9e9e50))
- add custom styling for smarter message items ([3303476](https://github.com/smarter-sh/smarter/commit/3303476c6c9d88ca53751c9367b27403f95641ef))
- add fontwesome state icons to app title ([ce1c37e](https://github.com/smarter-sh/smarter/commit/ce1c37e7c1a844eb9f29c82233bf50df8c2ae8ed))
- code menu item click handler ([2d45979](https://github.com/smarter-sh/smarter/commit/2d45979fc4e456965f1c09169cad9e73dc5e20c3))
- code state-based, formatted console output ([78a8e45](https://github.com/smarter-sh/smarter/commit/78a8e45b810a259db87d8d4571ad71652ca418d7))
- create a react context for managing config inside of state ([05db6f0](https://github.com/smarter-sh/smarter/commit/05db6f0abbedad3107231a351b932d3e9fed8ae8))
- scaffold new console output window pane ([f45e6c4](https://github.com/smarter-sh/smarter/commit/f45e6c437336891e477a74c3cffa7e148d37c522))
- scaffold new console output window pane ([9eaec6b](https://github.com/smarter-sh/smarter/commit/9eaec6b64a86ed93579076fdf2952a2e0e8a8370))
- scaffold tabbed window ([d58d25c](https://github.com/smarter-sh/smarter/commit/d58d25c7442317c1fa6f16d55f0d6210afcc65e0))
- simulate an ubuntu pod shell environment ([4496107](https://github.com/smarter-sh/smarter/commit/4496107f083a14381dbfbcf5aaa1da250b675ebe))
- style console window and make responsive ([19c1862](https://github.com/smarter-sh/smarter/commit/19c1862736e61aace68295e73e9fcd0cf568c03d))
- style the console json log data ([a837dad](https://github.com/smarter-sh/smarter/commit/a837dad29aef70925c19c77685784fb47efb056c))
- style the new log console ([98bf303](https://github.com/smarter-sh/smarter/commit/98bf303446f940667aa5ae6a09ad63ae9e940acc))
- style the smarter system chat items ([680d4bc](https://github.com/smarter-sh/smarter/commit/680d4bc90d52bb7df2f832f536f44c0dfb93c338))

## [0.7.9](https://github.com/smarter-sh/smarter/compare/v0.7.8...v0.7.9) (2025-01-09)

### Bug Fixes

- add chat_tool_call_history, chat_plugin_usage_history, chatbot_request_history ([2c07e4c](https://github.com/smarter-sh/smarter/commit/2c07e4c029402fd16bb303581d603a86231c8e31))
- add session_key to PluginSelectorHistory ([10e903a](https://github.com/smarter-sh/smarter/commit/10e903a99f04602fc51fdb9541550b1b4d779447))
- add session_key to PluginSelectorHistory ([96c2eef](https://github.com/smarter-sh/smarter/commit/96c2eef492da4f8b6732dbbd2ebcf7bd4a6e1b1a))
- ChatHelper should return the entire chat object rather than only id ([523b8fe](https://github.com/smarter-sh/smarter/commit/523b8fef55fbe52d3dd8d4b20751bb0ee1e73bef))
- finesse api error handling of ChatConfigView ([8850c4a](https://github.com/smarter-sh/smarter/commit/8850c4aab0d1f9cf5b19ae4c2d8f4318334e3467))

## [0.7.8](https://github.com/smarter-sh/smarter/compare/v0.7.7...v0.7.8) (2025-01-09)

### Bug Fixes

- add remaining history tables to chatapp config ([dadb9bd](https://github.com/smarter-sh/smarter/commit/dadb9bd94a8d8ed96181254aeaaccca146ee9f42))

## [0.7.7](https://github.com/smarter-sh/smarter/compare/v0.7.6...v0.7.7) (2025-01-08)

### Bug Fixes

- pod startup log dump ([e3d22ed](https://github.com/smarter-sh/smarter/commit/e3d22edf2f3d08b19f4e0c277dd09e1aa9714e55))

## [0.7.6](https://github.com/smarter-sh/smarter/compare/v0.7.5...v0.7.6) (2025-01-08)

### Bug Fixes

- add SMARTER_WAFFLE_SWITCH_SUPPRESS_FOR_CHATBOTS, SMARTER_WAFFLE_SWITCH_CHATAPP_VIEW_LOGGING, SMARTER_WAFFLE_MANIFEST_LOGGING ([0bebf2f](https://github.com/smarter-sh/smarter/commit/0bebf2fe7b8fa9ed8a2436fdb25f33747878c5fc))
- cleanup logger entries ([f550259](https://github.com/smarter-sh/smarter/commit/f5502598d52d193279365597e21880b4c0f56097))
- cookie expirations ([f3f59f9](https://github.com/smarter-sh/smarter/commit/f3f59f9da0b0f0a85277c3e372a06ba94387af2a))
- CSRF_COOKIE_DOMAIN ([ca7d611](https://github.com/smarter-sh/smarter/commit/ca7d611a7f7e682e523cd15912bf910d7c3fd405))
- SMARTER_WAFFLE_REACTAPP_DEBUG_MODE ([efd7402](https://github.com/smarter-sh/smarter/commit/efd7402877c798ec224a953be36a3af4f09a7156))

## [0.7.5](https://github.com/smarter-sh/smarter/compare/v0.7.4...v0.7.5) (2025-01-08)

### Bug Fixes

- use a trimmed, cleaned url for Chat() instances ([262d7fa](https://github.com/smarter-sh/smarter/commit/262d7fa3c4d9c873038b4249a305793be4aadac1))

## [0.7.4](https://github.com/smarter-sh/smarter/compare/v0.7.3...v0.7.4) (2025-01-08)

### Bug Fixes

- add session_key url param and ensure that session_key is unique to chatbot url path ([60acb6f](https://github.com/smarter-sh/smarter/commit/60acb6f50b1a8331387c85dd5dbd9470c1861093))
- make combination of session_key and url unique ([a074976](https://github.com/smarter-sh/smarter/commit/a074976846492aa332bc49135192a0c859b5fa7b))
- parameterize all cookie names and set 24 hour cookie expirations ([c652240](https://github.com/smarter-sh/smarter/commit/c6522406c45fcfef2098775a7bfe203f475ef5d9))

## [0.7.3](https://github.com/smarter-sh/smarter/compare/v0.7.2...v0.7.3) (2025-01-08)

### Bug Fixes

- add a chatbots list view page ([2675d5e](https://github.com/smarter-sh/smarter/commit/2675d5e26df17682b0e9381f3063f4a92521ab95))

## [0.7.2](https://github.com/smarter-sh/smarter/compare/v0.7.1...v0.7.2) (2025-01-07)

### Bug Fixes

- api/v1/chatbots/, api/v1/chats/ ([edfa1ed](https://github.com/smarter-sh/smarter/commit/edfa1edbe48d27a1675d489c3028a8da050b846d))
- change logo anchor to '/' for authenticated users ([6954eb5](https://github.com/smarter-sh/smarter/commit/6954eb526447c68a48eac47a9075eaf16b7143d8))
- fix all broken dashboard urls ([c85c2d3](https://github.com/smarter-sh/smarter/commit/c85c2d32aa91f735f3090f4ea4a10b787e1bdbc0))
- fixup legal links in console menu ([4da3b3e](https://github.com/smarter-sh/smarter/commit/4da3b3e668b43070999ac96e06b7980eb0123392))
- keep authenticated users on the platform ([b9dc50c](https://github.com/smarter-sh/smarter/commit/b9dc50cdb7bb44379452233e306e3bc19e94d86f))
- reorganize dashboard sidebar menu ([c0238c8](https://github.com/smarter-sh/smarter/commit/c0238c8d6c198c1b85dd3c380efbee8aa499af61))
- restructure console sidebar menu ([ebfcc38](https://github.com/smarter-sh/smarter/commit/ebfcc381fd73d8589b38a5b0a20f07184949a560))
- revert chats to chat ([1274813](https://github.com/smarter-sh/smarter/commit/12748131ffdddfc6c15ff5c410b211dfde38b582))
- sidebar menu active on clicked item ([1c543ab](https://github.com/smarter-sh/smarter/commit/1c543aba33f7e80dca2d1334c90187acc0dc479d))

## [0.7.1](https://github.com/smarter-sh/smarter/compare/v0.7.0...v0.7.1) (2025-01-06)

### Bug Fixes

- ensure that csrftoken is not included in 'Cookies' ([840fef1](https://github.com/smarter-sh/smarter/commit/840fef16b2283128a2808011b962cc12c1c00b0a))
- ensure that http response is a json object ([9338cab](https://github.com/smarter-sh/smarter/commit/9338cab989811b624be80ae348fb1ae456b7d501))
- ensure that only one csrftoken cookie exists ([c12bddb](https://github.com/smarter-sh/smarter/commit/c12bddb083e123d8a6f8404d9bbf586d38104602))
- ensure that only one csrftoken cookie exists ([affbcc8](https://github.com/smarter-sh/smarter/commit/affbcc8dd4c4864ec1642b86f04677fcf1aab57f))

# [0.7.0](https://github.com/smarter-sh/smarter/compare/v0.6.1...v0.7.0) (2025-01-03)

### Features

- add Google Gemini provider ([dcd3235](https://github.com/smarter-sh/smarter/commit/dcd3235e97bf092fe78ae854631d0dfa3a6cdae5))
- add MetaAI provider ([37f80c6](https://github.com/smarter-sh/smarter/commit/37f80c6cb9d162f4cd733b4772935d557484fa78))

### Bug Fixes

- add chat llm providers for MetaAI and GoogleAI
- refactor: create a OpenAICompatibleChatProvider abstract base class and a default…
- refactor Dockerfile and docker-compose.yml to build and run as non-root user
- refactor build/deploy workflows
- add LinkedIn oauth configuration
- monthly Dependabot version bumps

## [0.6.0](https://github.com/smarter-sh/smarter/compare/v0.5.4...v0.6.0) (2024-11-21)

### Features

- version bump all requirements and upgrade default model to gpt-4-turbo ([fa6def4](https://github.com/smarter-sh/smarter/commit/fa6def47316291d5848c11c0ecfbbb26b4effff5))

## [0.5.4](https://github.com/smarter-sh/smarter/compare/v0.5.3...v0.5.4) (2024-07-12)

### Bug Fixes

- account_for_user() should ensure that user is not AnonymousUser ([35f08f7](https://github.com/smarter-sh/smarter/commit/35f08f76816412a95c064df0554ab6f4b1b8be3d))
- add ampersands ([be04891](https://github.com/smarter-sh/smarter/commit/be04891dbe32aef604b6e07cd212d3361b1dfb62))
- add ampersands ([39a8c0c](https://github.com/smarter-sh/smarter/commit/39a8c0c8ebd8150aec32bf3add7fff851ddd7c73))
- add assistant response and tool calls to message list history ([793cb8b](https://github.com/smarter-sh/smarter/commit/793cb8be8b7451dca3a456228166d1918d193bbc))
- docker-compose-install ([2522bf8](https://github.com/smarter-sh/smarter/commit/2522bf827b5badb6af1807ce9a0c9bb2e995bcab))
- dumbass mistake ([9d3513d](https://github.com/smarter-sh/smarter/commit/9d3513dff9b2b4b14f5ab4fb42b0f2e779c58ed6))
- dumbass mistake ([9308977](https://github.com/smarter-sh/smarter/commit/93089772255bb432d37524371200a4ebbe22c62c))
- dumbass mistake ([e2c0311](https://github.com/smarter-sh/smarter/commit/e2c03113d9ac852db7861389c55e9b8b37422860))
- evaluate data type of kwargs['name'] and warn if not str ([3957fb1](https://github.com/smarter-sh/smarter/commit/3957fb1c9035f1fe48788c381979ecae0f0f19bd))
- make syntax errors ([7afa0c5](https://github.com/smarter-sh/smarter/commit/7afa0c525eb7bf75302c11640a9d5d126689cc22))
- make syntax errors ([f9432b5](https://github.com/smarter-sh/smarter/commit/f9432b5370e3ca16e4156c934b8d64f1d744abf8))
- rewrite file instead of append ([9ec807b](https://github.com/smarter-sh/smarter/commit/9ec807bb2f987324c21af36270711a4866d8eb88))
- add ChatBot.default_system_role migration ([5246cc4](https://github.com/smarter-sh/smarter/commit/5246cc446418f446ca210cb054454c58f7380ac5))
- add default_system_role to the chat and chatbot models ([266d873](https://github.com/smarter-sh/smarter/commit/266d873e583200750b38045e9f359242555f0a2b))
- add sensible defaults for all error response attributes ([ecd9d2d](https://github.com/smarter-sh/smarter/commit/ecd9d2dfb5e727674c4e442d47222e87de970b28))
- ensure internal error stack traces flow back to cli output ([dafd736](https://github.com/smarter-sh/smarter/commit/dafd7368abd8875551e03d26e9b0acff710bbb96))
- ensure that the error description at the bottom of the stack trace echos to cli console output ([c60a7ae](https://github.com/smarter-sh/smarter/commit/c60a7ae95af3927eabe1349babbd0339107f1f7f))

## [0.5.3](https://github.com/smarter-sh/smarter/compare/v0.5.2...v0.5.3) (2024-07-05)

### Bug Fixes

- assign chat.chatbot ([b6d294a](https://github.com/smarter-sh/smarter/commit/b6d294aca0b0a492a39524af289d94a908a5001b))

## [0.5.2](https://github.com/smarter-sh/smarter/compare/v0.5.1...v0.5.2) (2024-07-01)

- add authentication backend to login(). now required bc of social_core ([b8daf55](https://github.com/smarter-sh/smarter/commit/b8daf558733c743d876618f4267f8bcb45995f52))
- fix indentation of 1st line ([f4e2a73](https://github.com/smarter-sh/smarter/commit/f4e2a7397bd709e619dbc0d2f338afc3c68d1bb4))
- fix path assets/media/illustrations/sigma-1/17-dark.png ([201c72f](https://github.com/smarter-sh/smarter/commit/201c72f361925f82e795713ff245b854fd17c211))
- remove wagtail userbar tag ([1407756](https://github.com/smarter-sh/smarter/commit/14077564abe0f25a2869b5462848fe06ebc70321))

## [0.5.1](https://github.com/smarter-sh/smarter/compare/v0.5.0...v0.5.1) (2024-06-27)

### Bug Fixes

- limit openapi documentation generation to /api/ ([94d35cd](https://github.com/smarter-sh/smarter/commit/94d35cddc7ea2f1d6591dffda93b32c21b943d5f))

## [0.5.0](https://github.com/smarter-sh/smarter/compare/v0.4.1...v0.5.0) (2024-06-15)

### Features

- add sidebar to wagtail ([77cd476](https://github.com/smarter-sh/smarter/commit/77cd476d5bd7a43b1d2fb223a1eb67b55cb10217))
- add Wagtail ([8670288](https://github.com/smarter-sh/smarter/commit/8670288dc6498de4fcd1327c53b354d7696b500c))

## [0.4.1](https://github.com/smarter-sh/smarter/compare/v0.4.0...v0.4.1) (2024-06-11)

### Bug Fixes in /api/docs

- fix code element styling in docs django templates ([7d3763d](https://github.com/smarter-sh/smarter/commit/7d3763dbc39d0f83be6eaa3e97b091e6edb4b243))
- create unit tests for brokered api end point data sets: example-manifest, json-schema
- refactor urls.py to use SAMKinds to distinguish all manifest and json-schema urls endpoints
- refactor api/docs/ cli menu item

# [0.4.0](https://github.com/smarter-sh/smarter/compare/v0.3.9...v0.4.0) (2024-06-10)

### Features

- add /api/docs/
- add /api/v1/cli/schema/<str:kind>/ ([fd583b6](https://github.com/smarter-sh/smarter/commit/fd583b61c575c65402ed0ee5021f303304a07a39))

## [0.3.9](https://github.com/smarter-sh/smarter/compare/v0.3.8...v0.3.9) (2024-06-09)

### Bug Fixes

- create and assign a ChatBot to the test Chat session ([005491a](https://github.com/smarter-sh/smarter/commit/005491a45330d344ff72a16e7ea39cc825be3952))
- create and assign a ChatBot to the test Chat session ([0cddf38](https://github.com/smarter-sh/smarter/commit/0cddf38271343e7b020eecbe41b839c3b5b64b73))
- ensure that ChatBot flows to smarter handler() via the chat_helper ([85288dc](https://github.com/smarter-sh/smarter/commit/85288dc646435945d4c688f611f20b3aa1eb79b9))
- force a new release ([ab96126](https://github.com/smarter-sh/smarter/commit/ab96126cb3381c1339db03df82a977707513fa4e))
- whatchmedo directory ([df5971d](https://github.com/smarter-sh/smarter/commit/df5971df8abcfe0267a734e5f1b4596357f32d18))

## [0.3.8](https://github.com/smarter-sh/smarter/compare/v0.3.7...v0.3.8) (2024-06-05)

### Features

- added a complete suite of unit tests for /smarter/apps/api/v1/cli
- added unit tests for smarter/lib/manifest/broker/

## [0.3.7](https://github.com/smarter-sh/smarter/compare/v0.3.6...v0.3.7) (2024-06-01)

### Bug Fixes

- misc patches related to 0.3.x release
- add unit tests

## [0.3.2](https://github.com/smarter-sh/smarter/compare/v0.3.1...v0.3.2) (2024-05-31)

### Bug Fixes

- set url_chatbot() to urljoin(self.url, /api/v1/chatbots/smarter/) ([ad8036b](https://github.com/smarter-sh/smarter/commit/ad8036b1b487fc0619a5523bec52ab894c205184))
- set url_chatbot() to urljoin(self.url, /api/v1/chatbots/smarter/) ([7d2eb0c](https://github.com/smarter-sh/smarter/commit/7d2eb0c57d65e0d3d13a088490bd7ce3f6c411e4))

## [0.3.1](https://github.com/smarter-sh/smarter/compare/v0.3.0...v0.3.1) (2024-05-31)

### Bug Fixes

- url_chatbot should be urljoin(self.hostname, /api/v1/chatbots/smarter/) ([a794fdf](https://github.com/smarter-sh/smarter/commit/a794fdf7e4ea6525797247d790303e62e099bfcb))

## [0.3.6](https://github.com/smarter-sh/smarter/compare/v0.3.5...v0.3.6) (2024-06-01)

### Bug Fixes

- ensure that we fail gracefully ([3d4ab45](https://github.com/smarter-sh/smarter/commit/3d4ab4587a935575f5e32f8db66eb67e93cbcbef))
- make the error response match api/v1/cli error format ([c7f9f72](https://github.com/smarter-sh/smarter/commit/c7f9f72ec6b3ef42d115e4a4125689c6fa21ac01))

## [0.3.5](https://github.com/smarter-sh/smarter/compare/v0.3.4...v0.3.5) (2024-06-01)

### Bug Fixes

- RecursionError cause by self.user ([4362f84](https://github.com/smarter-sh/smarter/commit/4362f84068e4d828c1d8badc36424fcdb67b073a))

## [0.3.4](https://github.com/smarter-sh/smarter/compare/v0.3.3...v0.3.4) (2024-06-01)

### Bug Fixes

- add protocol to ChatBot.url_chatbot() ([4c146aa](https://github.com/smarter-sh/smarter/commit/4c146aa5f86dec432311b600015786111e4191a3))

## [0.3.3](https://github.com/smarter-sh/smarter/compare/v0.3.2...v0.3.3) (2024-06-01)

### Bug Fixes

- force a new release ([e66cbce](https://github.com/smarter-sh/smarter/commit/e66cbcef78f7af12c7d34e5ebcf9bc4d38715f9e))

## [0.3.2](https://github.com/smarter-sh/smarter/compare/v0.3.1...v0.3.2) (2024-05-31)

### Bug Fixes

- set url_chatbot() to urljoin(self.url, /api/v1/chatbots/smarter/) ([ad8036b](https://github.com/smarter-sh/smarter/commit/ad8036b1b487fc0619a5523bec52ab894c205184))
- set url_chatbot() to urljoin(self.url, /api/v1/chatbots/smarter/) ([7d2eb0c](https://github.com/smarter-sh/smarter/commit/7d2eb0c57d65e0d3d13a088490bd7ce3f6c411e4))

## [0.3.1](https://github.com/smarter-sh/smarter/compare/v0.3.0...v0.3.1) (2024-05-31)

### Bug Fixes

- url_chatbot should be urljoin(self.hostname, /api/v1/chatbots/smarter/) ([a794fdf](https://github.com/smarter-sh/smarter/commit/a794fdf7e4ea6525797247d790303e62e099bfcb))

## [0.3.0](https://github.com/smarter-sh/smarter/compare/v0.2.2...v0.3.0) (2024-05-31)

### Features

- create a universal journal to log all api request/response pairs ([2d2fbaa](https://github.com/smarter-sh/smarter/commit/2d2fbaae18fba5c56e93c7c06fe0cb4c132fc6f2))
- create SmarterJournaledJsonErrorResponse() ([bb1ab3b](https://github.com/smarter-sh/smarter/commit/bb1ab3b28c73722f33ca2cb98f82a94472e09695))
- pass prompt to broker via kwargs ([e4efb09](https://github.com/smarter-sh/smarter/commit/e4efb092ede55fe9f1a7befea9ca8d31934cee4f))
- code ApiV1CliChatApiView and refactor chatapp to make it work with journaled json responses ([8e500a7](https://github.com/smarter-sh/smarter/commit/8e500a71b348e81306bf414fb410b6004759113b))
- scaffold ApiV1CliChatApiView() ([31cfd1d](https://github.com/smarter-sh/smarter/commit/31cfd1d32a82f76646b5740436b5ef4ff4a405b1))
- scaffold ApiV1CliChatApiView() ([6f127bb](https://github.com/smarter-sh/smarter/commit/6f127bbc53ae1ad2164ad89cba3852a442011ac8))
- create SmarterTokenAuthenticationMiddleware to automate api key authentication

## [0.2.1](https://github.com/QueriumCorp/smarter/compare/v0.2.0...v0.2.1) (2024-05-19)

A refactor of the Django chatbot app.

### Feature

- add ChatBot.dns_verification_status
- add Django signals:
  - chatbot_dns_verification_initiated
  - chatbot_dns_verified
  - chatbot_dns_failed
  - chatbot_dns_verification_status_changed
- refactor aws route53 processes for asynchronous request handling
- add task to Undeploy a ChatBot
- add unit tests for tasks and manage.py commands
- refactor Dockerfile to improve layer caching
- refactor docker-compose.yaml and Helm chart to enable multiple worker threads

## [0.2.0](https://github.com/QueriumCorp/smarter/compare/v0.1.2...v0.2.0) (2024-05-16)

Introduces remote Sql server integration to the Plugin class. New Django ORMs PluginDataSql and PluginDataSqlConnection have been added for persinsting remote sql server connections, and parameterized sql queries. SAMPluginDataSqlConnectionBroker is added to fully integrate these models to /api/v1/cli.

### Features

- add SAMPluginDataSqlConnectionBroker to api/v1/cli ([f120cfd](https://github.com/QueriumCorp/smarter/commit/f120cfd3600a8e865e9dd43f9cde41a0312591df))
- add SAMPluginDataSqlConnectionBroker to api/v1/cli ([54fa4da](https://github.com/QueriumCorp/smarter/commit/54fa4da9f91d010adef4b737d0f7887e154767ac))
- add unit tests ([2c9e355](https://github.com/QueriumCorp/smarter/commit/2c9e35501d1824da521eb51cb937567627ab0dcb))
- scaffold PluginSql and Pydantic model ([e1bb076](https://github.com/QueriumCorp/smarter/commit/e1bb076ad428853c97505203cf35b476fc6dd30d))
- scaffold PluginSql models ([17daf61](https://github.com/QueriumCorp/smarter/commit/17daf615e74ed3f826fbf21db97d10d5174879bd))

## [0.1.2](https://github.com/QueriumCorp/smarter/compare/v0.1.1...v0.1.2) (2024-05-14)

Introduces a powerful new architecture for processing Kubernetes-style manifests for managing Smarter resources. The new Broker class architecture facilitates lightweight implementations of the smarter command-line implementation and the REST API that backs it.

### New features

- add /api/v1/cli rest api backing services for Go lang command-line interface
- add Pydantic to formally model cli manifests. Enforces manifest structural integrity as well as data and business rule validations.
- add SAMLoader, a generic yaml manifest loader for Pydantic
- add Broker class to abstract cli services implementations
- implement all Plugin cli services
- add a Controller class to Plugin, facilitating the future introduction of new data classes to support remote SQl databases and REST API data sources.

## [0.1.1](https://github.com/QueriumCorp/smarter/compare/v0.1.0...v0.1.1) (2024-04-02)

### New features

- add Helm charts
- add GitHub Actions CI/CD workflows
- add Makefile commands to automate local developer setup
- implement final chat REST API, referenced as http://{host}/admin/chat/chathistory/config/ which returns a context dict for a chat session. Enables a single authenticated Smarter user to manage multiple chat sessions in the sandbox.

## [0.1.0](https://github.com/QueriumCorp/smarter/compare/v0.0.1...v0.1.0) (2024-04-01)

### New features

- add FQDM's to CSRF_TRUSTED_ORIGINS ([6d6bd92](https://github.com/QueriumCorp/smarter/commit/6d6bd92dc8e9c5d162d3bd4359afbd58ef1a72ee))
- pass user to function_calling_plugin() ([0e6b1fa](https://github.com/QueriumCorp/smarter/commit/0e6b1fa94d853f1d4295ede704a3204adb53d24a))
- remove custom login.html ([b4f091f](https://github.com/QueriumCorp/smarter/commit/b4f091fd0a271cb1e12950e6ca4e5a1cdb8c038e))
- set CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS ([62a8ca3](https://github.com/QueriumCorp/smarter/commit/62a8ca38cd4d46207392c5839718abb981808da2))
- STATIC_URL = '/static/' ([277fff3](https://github.com/QueriumCorp/smarter/commit/277fff3aa2fe2aa32faf8699d3128398c36024a4))
- STATIC_URL = '/static/' ([89a2e0c](https://github.com/QueriumCorp/smarter/commit/89a2e0c5705064b878b254e83ac874d5c7fd6699))
- values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme ([dc9ca5e](https://github.com/QueriumCorp/smarter/commit/dc9ca5e09d289bd33d15723a0b4352bbc08478b2))
- add api-key authentication ([491927f](https://github.com/QueriumCorp/smarter/commit/491927fe9d51594905ad1a1542e8e9b00de22871))
- add chat history models and signals ([07e5f82](https://github.com/QueriumCorp/smarter/commit/07e5f8223f96c886a35f1344a52d3ca748231310))
- automate build/deploy by environment ([f808ed5](https://github.com/QueriumCorp/smarter/commit/f808ed50d6148d193c73088696407db219cff008))
- restore most recent chat history when app starts up ([118d884](https://github.com/QueriumCorp/smarter/commit/118d88450a63bcf0ee1649fece7db0fbbac1c50d))

## [0.0.1](https://github.com/QueriumCorp/smarter/releases/tag/v0.0.1) (2024-02-21)

Django based REST API and ReactJS web app hosting an MVP plugin platform for OpenAI API Function Calling. This release implements the following features:

### New features

- Docker-based local development environment with MySQL and Redis
- Celery worker and beat support
- an integrated ReactJS web app for interacting with LLM chatbots.
- a multi-environment conf module based on Pydantic, that resolves automated parameter initializations using any combination of command line assignments, environment variables, .env and/or terraform.tfvars files.
- Django REST Framework driven API for accounts and Plugins
- Django backed Plugin class that can be initialized from either yaml or json files
- Django Account class that facilitate a team approach to managing Plugins
- Python unit tests for all modules
- Github Action CI/CD for automated unit testing on merges to staging and main, and automated Docker build/push to AWS ECR
- Terraform based AWS cloud infrastructure management of Kubernetes resources
- Pain-free onboarding of new developers, including a complete Makefile and pre-commit code formatting, code linting and misc security validation checks.
