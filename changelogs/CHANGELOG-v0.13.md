# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this
project adheres to [Semantic Versioning](http://semver.org/).

## [0.13.223](https://github.com/smarter-sh/smarter/compare/v0.13.222...v0.13.223) (2026-04-19)

### Bug Fixes

- force a new release ([b9cd7d7](https://github.com/smarter-sh/smarter/commit/b9cd7d7a5e07bf6b12eda6fa24da36240b3bd6d7))

## [0.13.222](https://github.com/smarter-sh/smarter/compare/v0.13.221...v0.13.222) (2026-04-17)

### Bug Fixes

- monkey patch def secret() until v0.14 is released ([e63651a](https://github.com/smarter-sh/smarter/commit/e63651a378ec9890b9bef11199318992b5dcf943))

## [0.13.221](https://github.com/smarter-sh/smarter/compare/v0.13.220...v0.13.221) (2026-04-17)

### Bug Fixes

- temporary monkey patch until v0.14 is released ([ba51ec6](https://github.com/smarter-sh/smarter/commit/ba51ec6b234cc05c41359b1790feed0468ea63b9))

## [0.13.220](https://github.com/smarter-sh/smarter/compare/v0.13.219...v0.13.220) (2026-04-16)

### Bug Fixes

- switch to redis cache ([0261451](https://github.com/smarter-sh/smarter/commit/0261451a096b6e64208db46de99a338f109c9354))

## [0.13.219](https://github.com/smarter-sh/smarter/compare/v0.13.218...v0.13.219) (2026-04-16)

### Bug Fixes

- give the cache a filename ([b95cfdb](https://github.com/smarter-sh/smarter/commit/b95cfdb07866ac013ea80721b086106f9a5e56aa))

## [0.13.218](https://github.com/smarter-sh/smarter/compare/v0.13.217...v0.13.218) (2026-04-16)

### Bug Fixes

- AttributeError: 'NoneType' object has no attribute 'validate' ([2c1820c](https://github.com/smarter-sh/smarter/commit/2c1820c42406311ad0074d1e33044b1929be7f4a))

## [0.13.217](https://github.com/smarter-sh/smarter/compare/v0.13.216...v0.13.217) (2026-04-16)

### Bug Fixes

- requests cache path ([52e55da](https://github.com/smarter-sh/smarter/commit/52e55da18dd49db7653dc0e70c2ef1dd49c6d180))

## [0.13.216](https://github.com/smarter-sh/smarter/compare/v0.13.215...v0.13.216) (2026-04-15)

### Bug Fixes

- misc post-deployment bugs ([a7e6b52](https://github.com/smarter-sh/smarter/commit/a7e6b520f452885dcb91bd2419113dd8d53f866d))

## [0.13.215](https://github.com/smarter-sh/smarter/compare/v0.13.214...v0.13.215) (2026-04-08)

### Bug Fixes

- UserProfile.DoesNotExist exception in user receiver ([aae27ac](https://github.com/smarter-sh/smarter/commit/aae27ac4ac5c9bc3a5f9679caf20dd9be3df95e0))

## [0.13.214](https://github.com/smarter-sh/smarter/compare/v0.13.213...v0.13.214) (2026-04-07)

### Bug Fixes

- from scratch init w/o aws ([1c48204](https://github.com/smarter-sh/smarter/commit/1c48204ce7303856af6edeea483fd629abeaf89a))

## [0.13.213](https://github.com/smarter-sh/smarter/compare/v0.13.212...v0.13.213) (2026-04-06)

### Bug Fixes

- force a new release ([2b13f4b](https://github.com/smarter-sh/smarter/commit/2b13f4b41ce8c60252d3585f94b131e670cf5ec3))

## [0.13.212](https://github.com/smarter-sh/smarter/compare/v0.13.211...v0.13.212) (2026-04-04)

### Bug Fixes

- resolve Windows Git Bash path separator in ACTIVATE_VENV and replace hardcoded admin email with SMARTER_ROOT_DOMAIN ([5da6724](https://github.com/smarter-sh/smarter/commit/5da672494ac601a01cfe2a3131de9134a07ee5f6))

## [0.13.211](https://github.com/smarter-sh/smarter/compare/v0.13.210...v0.13.211) (2026-03-31)

### Bug Fixes

- lazy initialization of Plugin\* child objects from SAM to ORM ([933fe31](https://github.com/smarter-sh/smarter/commit/933fe312ffb1ef4f93965516c6eb2e75734c8250))

## [0.13.210](https://github.com/smarter-sh/smarter/compare/v0.13.209...v0.13.210) (2026-03-31)

### Bug Fixes

- add an ai doc icon to My Resources ([07dbf1a](https://github.com/smarter-sh/smarter/commit/07dbf1aada8096ca210db8e8f384f9bcd4c1fe7e))
- add branding to self-host widget ([5c74f13](https://github.com/smarter-sh/smarter/commit/5c74f13abca9e63d6bb32679a09bf8dc1b6cdf4f))
- add global recordLocator to all SAM resources ([064667f](https://github.com/smarter-sh/smarter/commit/064667f92edb6042fe19a860b45f91ba96e92053))
- add language logos to sdk widget ([eb4f940](https://github.com/smarter-sh/smarter/commit/eb4f9400d1b8fa2f4f109f7b58604bea93f61765))
- add sphinx-init ([d120f90](https://github.com/smarter-sh/smarter/commit/d120f904bc62e47048fcee343136baa2587039dc))
- always use the sandbox url for the api ([4a1ed9f](https://github.com/smarter-sh/smarter/commit/4a1ed9fc6ad5eee339ea8e00b450d945edb33652))
- cast_value() should always return the default when val is None ([0cc8a16](https://github.com/smarter-sh/smarter/commit/0cc8a16e73a1c6926772f9e30fde3c4ae31b3e8e))
- code apply drop zone page ([afc0788](https://github.com/smarter-sh/smarter/commit/afc0788ed73a766898c312f36a71d6c33c3b039d))
- do not raise error on email service failure ([ab271f6](https://github.com/smarter-sh/smarter/commit/ab271f61ae0c2ccbae53bf38cd76da6213a90adb))
- don't set name until we're certain we have a value ([fab3262](https://github.com/smarter-sh/smarter/commit/fab3262e1f6c4aa0dfa00443009b9d4bf72ca584))
- ensure that SAMStatus is included in all describe() ([a8fb48d](https://github.com/smarter-sh/smarter/commit/a8fb48d03eb10e2b9b4450ccd668c9832a0ad167))
- ensure that session_key_from_url() can process both ParseResult and str ([5fe3a9a](https://github.com/smarter-sh/smarter/commit/5fe3a9a2d881ef2d8e9de19688be31c87c320e8d))
- get_brokered_json_response() has to use post() from now on ([57fa83f](https://github.com/smarter-sh/smarter/commit/57fa83f65178894ee06960db6bb29c428a10d291))
- inherit tags TaggableManager from MetaDataWithOwnershipModel ([d66928a](https://github.com/smarter-sh/smarter/commit/d66928a1a940a705979c65ef6a26498c8850037f))
- logging should be disabled by default ([5f7da0f](https://github.com/smarter-sh/smarter/commit/5f7da0f5ff6f95188a93efa34269a445edc2cdd6))
- partial solution to csrf issues when changing manifest detail views from get() to post() ([6a0a6a9](https://github.com/smarter-sh/smarter/commit/6a0a6a9755731c4d600b5587f90475a4d8302d83))
- remap SMARTER_EMAIL_ADMIN to input ([e6ab14a](https://github.com/smarter-sh/smarter/commit/e6ab14ad40613f0b33856c396ceb19e6524d67e0))
- remove superuser restriction on menu link to Django admin ([dffdf5d](https://github.com/smarter-sh/smarter/commit/dffdf5d14e462411ef865f11eb3a7b9e630d2435))
- return waffle_orig.switch_is_active(switch_name) so that we benefit from caching ([fb9d8aa](https://github.com/smarter-sh/smarter/commit/fb9d8aa1c985539050c75f694e0dc830763a29bc))
- scaffold a file drop zone page for manifests ([092336b](https://github.com/smarter-sh/smarter/commit/092336b10370d1af45034c2856a2d46a4bcad6c2))
- test db init from scratch ([038ed17](https://github.com/smarter-sh/smarter/commit/038ed170b6e2dfa9cc45f50f31a1f788737eb002))
- test plugin caching ([26cea38](https://github.com/smarter-sh/smarter/commit/26cea38dcc9cc8dad91ae421da41e59610593913))
- type check user_profile and user_profile.account ([6b86285](https://github.com/smarter-sh/smarter/commit/6b862851bda478ed3ae7d9538513b5759454b925))
- use \_get_model_by_pk(pk, class_name=cls.**name**) ([2aa6fe2](https://github.com/smarter-sh/smarter/commit/2aa6fe2143b41153561b44158211d3c31a2c5d8d))
- work on dashboard widgets ([f26c199](https://github.com/smarter-sh/smarter/commit/f26c1993bdf6cb166e98a524d6cfd86c07cb3e80))
- wrap up new dashboard widgets ([57f7d4e](https://github.com/smarter-sh/smarter/commit/57f7d4e8f47b8644d7bd0f33f2dc99a6b2c1ab77))

### Performance Improvements

- Account, UserProfile and SmarterCachedObjects caching ([b13629d](https://github.com/smarter-sh/smarter/commit/b13629db9e945381988edefa606c8f21eee2e3eb))
- add a pk handler that prefetches tags and user_profile ([93f6cd9](https://github.com/smarter-sh/smarter/commit/93f6cd90c5ec441a464e846bc9877d52794e8492))
- add cache_invalidations() to account receivers ([b76ea71](https://github.com/smarter-sh/smarter/commit/b76ea718b587bcef18d6aa75a69f6fa8f1eb3898))
- add cached_account and cached_user ([0a54cec](https://github.com/smarter-sh/smarter/commit/0a54cec002fa38244b52778d618995d99ed93fb6))
- add class-based caching to ChatBot ([ff2e748](https://github.com/smarter-sh/smarter/commit/ff2e748307aad3ffb258b0aab81882a7069aa053))
- add fk prefetching for chatbot and provider resources ([a1551a7](https://github.com/smarter-sh/smarter/commit/a1551a754cdff3fd456d32fc02ba98bb6feb1acc))
- add invalidation for the workbench listview ([ad20390](https://github.com/smarter-sh/smarter/commit/ad20390fba733490a7fe15ee27356258036a76a5))
- add select_related() and prefetch_related() ([2b68606](https://github.com/smarter-sh/smarter/commit/2b686063aba446aae0fff10ac499946dd8a2fb50))
- add select_related() and prefetch_related() ([f1d14af](https://github.com/smarter-sh/smarter/commit/f1d14aff141e856ecbb7faa1da22eb0ff3f963db))
- cache composite QuerySet results for PromptListView, PluginsListView and ChatBots ([d7df950](https://github.com/smarter-sh/smarter/commit/d7df9503bc348069be7d4636440b3bace993ae4c))
- cache tags retrieval ([bd52320](https://github.com/smarter-sh/smarter/commit/bd52320a6df9001cb5195904ef1bde5e08eaefeb))
- ChatBot.get_cached_objects() cached prefetching ([a1920ff](https://github.com/smarter-sh/smarter/commit/a1920ffd5fcee57b951782bd8cff20c9d18687fc))
- create cls.get_cached_models_for_user_profile() ([97e15a8](https://github.com/smarter-sh/smarter/commit/97e15a87992d17f27e7090ce448a7eb3ff3db852))
- create formatted_text_blue() for cache invalidations ([fe3ac80](https://github.com/smarter-sh/smarter/commit/fe3ac805ae9a6acb7cd8d3c80cdcf66dc00c2cea))
- create TimestampedModel.get_cached_model() ([93ee7b4](https://github.com/smarter-sh/smarter/commit/93ee7b4b39ee13b9fac8256a86b8d23700ca7c34))
- enable 10-second page cache ([c10d9b1](https://github.com/smarter-sh/smarter/commit/c10d9b1dc94088b1123e501f5eb31de9f5e0f455))
- ensure all SAM querysets prefetch and select related objects ([9867ab1](https://github.com/smarter-sh/smarter/commit/9867ab1deb7837b84e28f9a74a056b006cea522b))
- expire cached smarter instances every 600 seconds ([4c52001](https://github.com/smarter-sh/smarter/commit/4c520011438320177cbb690dba6f6eef1acd1062))
- fail gracefully when we don't have a workable combination of parameters ([6dfef2d](https://github.com/smarter-sh/smarter/commit/6dfef2d257c3cbdaa14c218dda2526c75bb7b074))
- invalidate object lists for plugin and chatbot views ([809df8a](https://github.com/smarter-sh/smarter/commit/809df8ac177a6eaeead89d001d49b7c68fa369ab))
- move orm caching to the parent MetaDataModel ([df3dbdd](https://github.com/smarter-sh/smarter/commit/df3dbdd21854ad9a2f0f7f9bc0151085e61292ee))
- prefetch tags ([f14536e](https://github.com/smarter-sh/smarter/commit/f14536ef266051f78c07cdb241d1b13e105a8a1c))
- prefetch tags ([0c56095](https://github.com/smarter-sh/smarter/commit/0c5609569e126a810209719b4de6b66e38edf84e))
- read aws s3 bucket from cdn. cache chatbot.objects.filter ([ff9f1fa](https://github.com/smarter-sh/smarter/commit/ff9f1fad74b3a6d3a2b51e9fbc7f04799a75748c))
- scaffold class-based cache invalidation ([6e00acc](https://github.com/smarter-sh/smarter/commit/6e00accf4535d57e23e675173de94399712df626))
- scaffold class-based cache invalidation ([ab2b0c9](https://github.com/smarter-sh/smarter/commit/ab2b0c992c70ff8fb8f441ba67c27b3ff7d6a848))
- scaffold class-based cache invalidation ([773d5c7](https://github.com/smarter-sh/smarter/commit/773d5c710aa56998dd1ad2077c72d70a9b9fb3bc))
- scaffold class-based cache invalidation ([f665c03](https://github.com/smarter-sh/smarter/commit/f665c03371f36e56299217dad59e970391131da3))
- scaffold class-based cache invalidation ([2bc136d](https://github.com/smarter-sh/smarter/commit/2bc136d23ee6d6cb3f230b54cf11bf8a0180aef6))
- scaffold class-based cache invalidation ([e1ec35c](https://github.com/smarter-sh/smarter/commit/e1ec35c0a02114be57e49f5b13bafdb8f98c05bd))
- select related objects along with the instance itself, so that all is cached ([84f9988](https://github.com/smarter-sh/smarter/commit/84f9988c59507bf2be6dcfed5d66df1d4436b3b8))
- set default cache expiration to 600 seconds. ([31cdd53](https://github.com/smarter-sh/smarter/commit/31cdd53d5a323ff4997e7ff108506f0e7be282d3))
- switch to get_cached_account() ([a174e6e](https://github.com/smarter-sh/smarter/commit/a174e6e6fc52bff8f8e824373b5988267ca04a8f))
- work on cache invalidations for context processors ([8ce1ad1](https://github.com/smarter-sh/smarter/commit/8ce1ad18d9cb92d3feda6f2ba9eff410f9bc5bad))
- work on cache_invalidations() ([3072853](https://github.com/smarter-sh/smarter/commit/30728533626d976ff68a61c37dc6673655e7d788))
- work on class-based cache keys for SAM objects and page caching ([10c171a](https://github.com/smarter-sh/smarter/commit/10c171a7f6cfabf958e825256d722a2c6a1ce96a))
- work on get_cached_model() ([4c707ea](https://github.com/smarter-sh/smarter/commit/4c707eac873ae6b1b041481c03944dc27e768eec))
- work on get_cached_object() and get_cached_objects() ([2836992](https://github.com/smarter-sh/smarter/commit/2836992b6e083f49580549e021d813e477051cd3))
- work on invalidation() ([b5beff7](https://github.com/smarter-sh/smarter/commit/b5beff75b28ac529c3a1570664fb62975400a872))

## [0.13.209](https://github.com/smarter-sh/smarter/compare/v0.13.208...v0.13.209) (2026-03-20)

### Bug Fixes

- cache pages by user ([07c7db6](https://github.com/smarter-sh/smarter/commit/07c7db60ae85cac533fe01b889a6f38ddfacceb4))
- handle xml pages differently ([61b70cb](https://github.com/smarter-sh/smarter/commit/61b70cb9843a3912b48566ae6883921175691140))

## [0.13.208](https://github.com/smarter-sh/smarter/compare/v0.13.207...v0.13.208) (2026-03-20)

### Bug Fixes

- missing csrf js script ([c7c0e77](https://github.com/smarter-sh/smarter/commit/c7c0e773b833de9416c1eb5094e83cef109b68d9))

## [0.13.207](https://github.com/smarter-sh/smarter/compare/v0.13.206...v0.13.207) (2026-03-19)

### Bug Fixes

- add in-line documentation and re-release ([32b19c1](https://github.com/smarter-sh/smarter/commit/32b19c19f3cbdb962a984ef6f192eda715b78103))

## [0.13.206](https://github.com/smarter-sh/smarter/compare/v0.13.205...v0.13.206) (2026-03-19)

### Bug Fixes

- missing renamed imports to smarter/smarter/lib/django/models ([e1a6dfa](https://github.com/smarter-sh/smarter/commit/e1a6dfacdfaae1983c0cbf56d13b1d842be55893))

## [0.13.205](https://github.com/smarter-sh/smarter/compare/v0.13.204...v0.13.205) (2026-03-19)

### Bug Fixes

- og_url ([c754647](https://github.com/smarter-sh/smarter/commit/c75464767b2e6786fdad9cb957b7d9566457b06a))

## [0.13.204](https://github.com/smarter-sh/smarter/compare/v0.13.203...v0.13.204) (2026-03-18)

### Bug Fixes

- force a new release ([db4a1a4](https://github.com/smarter-sh/smarter/commit/db4a1a4f5bfc129ac86cdd60c1b6edcfd593c9f9))

## [0.13.203](https://github.com/smarter-sh/smarter/compare/v0.13.202...v0.13.203) (2026-03-18)

### Bug Fixes

- add yaml validation ([4eb3581](https://github.com/smarter-sh/smarter/commit/4eb35819daf38c89727d4c47b77437faa66abdaa))

### Performance Improvements

- minor startup improvements to waffle handling ([07ab3b4](https://github.com/smarter-sh/smarter/commit/07ab3b4ec10f79860a1be4af1edb3d8b413b9ef7))

## [0.13.202](https://github.com/smarter-sh/smarter/compare/v0.13.201...v0.13.202) (2026-03-18)

### Bug Fixes

- add caching to TimestampedModel ([32679c6](https://github.com/smarter-sh/smarter/commit/32679c6b93c550cc43b1b4d190c2b9d98c758076))
- add waffle switch ALLOW_API_GET ([b95b4c2](https://github.com/smarter-sh/smarter/commit/b95b4c2c1abb825a72e4f18a16f914133ce604d1))
- add waffle switch ALLOW_API_GET ([5598e4c](https://github.com/smarter-sh/smarter/commit/5598e4c63bcf335d67ad80b36bead6648691ec96))
- work on short-lived html page caching for dashboard and workbench ([2f38bc5](https://github.com/smarter-sh/smarter/commit/2f38bc5c4cb8a1e9bdd028bc94f52d18387f1544))

## [0.13.201](https://github.com/smarter-sh/smarter/compare/v0.13.200...v0.13.201) (2026-03-18)

### Bug Fixes

- revert /chat/config/ redirect ([3413e98](https://github.com/smarter-sh/smarter/commit/3413e980a8056ccc2a1514a185bd37779e265e65))

## [0.13.200](https://github.com/smarter-sh/smarter/compare/v0.13.199...v0.13.200) (2026-03-18)

### Bug Fixes

- refactor /chatbot/v1/api urls to use hashed_id slugs ([89a6885](https://github.com/smarter-sh/smarter/commit/89a68859a7cb0d55cd1b8f8378344889eb8ef91a))

## [0.13.199](https://github.com/smarter-sh/smarter/compare/v0.13.198...v0.13.199) (2026-03-17)

### Bug Fixes

- refactor all ChatBot urls to use new hashed_id slug ([94a9017](https://github.com/smarter-sh/smarter/commit/94a9017d16d10c19f34572a03dabe0cb511d91b8))
- work on middleware caching and logging ([31e58a6](https://github.com/smarter-sh/smarter/commit/31e58a6c2855460892620bc71df686ac6d412794))

## [0.13.198](https://github.com/smarter-sh/smarter/compare/v0.13.197...v0.13.198) (2026-03-17)

### Bug Fixes

- anonymize workbench urls ([350ec3a](https://github.com/smarter-sh/smarter/commit/350ec3a701f48052e854c08bc307b1947f8f1a24))

## [0.13.197](https://github.com/smarter-sh/smarter/compare/v0.13.196...v0.13.197) (2026-03-16)

### Bug Fixes

- you can only call example_chatbot.tags.names() if a pk exists ([3f20b01](https://github.com/smarter-sh/smarter/commit/3f20b010f62a12bbf7020567eef3e4636a008fe5))

## [0.13.196](https://github.com/smarter-sh/smarter/compare/v0.13.195...v0.13.196) (2026-03-16)

### Bug Fixes

- exit gracefully if we are missing name or user_profile ([5f08fa9](https://github.com/smarter-sh/smarter/commit/5f08fa9ac1949368139cf28412be313c5383ec38))
- need to consider that self.\_broker is None/Falsy if its not in a ready state ([3a61531](https://github.com/smarter-sh/smarter/commit/3a6153135b3435d79ddc524b72a60a44a46ae6b2))

## [0.13.195](https://github.com/smarter-sh/smarter/compare/v0.13.194...v0.13.195) (2026-03-16)

### Bug Fixes

- add ROOT_DOMAIN and prune env console output ([71f4e55](https://github.com/smarter-sh/smarter/commit/71f4e55e8496ba7b521a3635ce49a4327b9042d6))
- add tag data using set() ([e05f831](https://github.com/smarter-sh/smarter/commit/e05f8318cbb0d76520c04bf67c612a2216d70b74))
- revert to default Django password form ([b5e49dc](https://github.com/smarter-sh/smarter/commit/b5e49dc690d15719a807a4f474d4e9610cf1fb5e))

## [0.13.194](https://github.com/smarter-sh/smarter/compare/v0.13.193...v0.13.194) (2026-03-16)

### Bug Fixes

- orm initializations for shared ownership ([7a1b5eb](https://github.com/smarter-sh/smarter/commit/7a1b5ebc531f55df94cf2cae33aba0ec91320cda))
- remaining code for SAMApiPluginBroker().plugin_data_orm2pydantic() ([4ad4546](https://github.com/smarter-sh/smarter/commit/4ad4546194926376b5db4e3b356c369848445044))

## [0.13.193](https://github.com/smarter-sh/smarter/compare/v0.13.192...v0.13.193) (2026-03-16)

### Bug Fixes

- add AbstractBroker().orm_meta_instance ([e80d629](https://github.com/smarter-sh/smarter/commit/e80d629595f2f117d83c62a7fa71cedcdcc74ca0))

## [0.13.192](https://github.com/smarter-sh/smarter/compare/v0.13.191...v0.13.192) (2026-03-15)

### Bug Fixes

- add ORMMetaModelClass for querying ORM models by name and user_profile ([2e08b66](https://github.com/smarter-sh/smarter/commit/2e08b664dfe0441cf5f302afcdde575cf993cf97))

## [0.13.191](https://github.com/smarter-sh/smarter/compare/v0.13.190...v0.13.191) (2026-03-15)

### Bug Fixes

- try to initialize broker from the orm instance when no manifest is provided ([e9e930c](https://github.com/smarter-sh/smarter/commit/e9e930c66007420e2c9748bd9f01225623b74d40))

## [0.13.190](https://github.com/smarter-sh/smarter/compare/v0.13.189...v0.13.190) (2026-03-15)

### Bug Fixes

- re-order the chatbot listview by modification date desc ([c118cfe](https://github.com/smarter-sh/smarter/commit/c118cfe88f4e200a2ebdafd1847d788a45719a90))

## [0.13.189](https://github.com/smarter-sh/smarter/compare/v0.13.188...v0.13.189) (2026-03-15)

### Bug Fixes

- add handler for TaggedItem ([4466479](https://github.com/smarter-sh/smarter/commit/44664791a9dac8425340034bf993ae499f9671d4))

## [0.13.188](https://github.com/smarter-sh/smarter/compare/v0.13.187...v0.13.188) (2026-03-15)

### Bug Fixes

- move manifest_to_django_orm() metadata logic to AbstractBroker. add TaggableManager handling to all apply() ([2b87d2d](https://github.com/smarter-sh/smarter/commit/2b87d2d0878cabf100e82e66aed39543f962b8b4))

## [0.13.187](https://github.com/smarter-sh/smarter/compare/v0.13.186...v0.13.187) (2026-03-14)

### Bug Fixes

- add sane defaults for defaultTemperature and defaultMaxTokens ([c27546a](https://github.com/smarter-sh/smarter/commit/c27546abac75b03b6f104453bffa5dcbb876360f))
- loosen null and blank restrictions on manifest metadata ([c4224fc](https://github.com/smarter-sh/smarter/commit/c4224fc1612cb9acd0d379e170e02c8de3aeea77))

## [0.13.186](https://github.com/smarter-sh/smarter/compare/v0.13.185...v0.13.186) (2026-03-14)

### Bug Fixes

- refactor chatbot broker to use SAM model for rendering json ([1b76d68](https://github.com/smarter-sh/smarter/commit/1b76d68a1626d987ab5043c5f815b577aa207574))

## [0.13.185](https://github.com/smarter-sh/smarter/compare/v0.13.184...v0.13.185) (2026-03-13)

### Bug Fixes

- use django slugify() to ensure that name is url friendly ([f7d69c7](https://github.com/smarter-sh/smarter/commit/f7d69c7f0e32478ba0b8f0d6c7eb77c65d157560))

## [0.13.184](https://github.com/smarter-sh/smarter/compare/v0.13.183...v0.13.184) (2026-03-10)

### Bug Fixes

- django template render errors django.template.base.VariableDoesNotExist: Failed lookup for key [name] in URLResolver ([d94aa49](https://github.com/smarter-sh/smarter/commit/d94aa495dbca3eec27ab06d34cddeaf79ab28d90))

## [0.13.183](https://github.com/smarter-sh/smarter/compare/v0.13.182...v0.13.183) (2026-03-10)

### Bug Fixes

- debug_toolbar ([2d18144](https://github.com/smarter-sh/smarter/commit/2d181440902e30c280ae07b2fcdbdd56598180d9))

## [0.13.182](https://github.com/smarter-sh/smarter/compare/v0.13.181...v0.13.182) (2026-03-10)

### Bug Fixes

- debug_toolbar ([d05a131](https://github.com/smarter-sh/smarter/commit/d05a13168f16260c51b2159aa61ac3eeaf2259ec))

## [0.13.181](https://github.com/smarter-sh/smarter/compare/v0.13.180...v0.13.181) (2026-03-10)

### Bug Fixes

- debug_toolbar ([fca0aa6](https://github.com/smarter-sh/smarter/commit/fca0aa6d018c458c1cba945b16a1868bb2d78ee5))

## [0.13.180](https://github.com/smarter-sh/smarter/compare/v0.13.179...v0.13.180) (2026-03-10)

### Bug Fixes

- debug_toolbar import ([7dce20c](https://github.com/smarter-sh/smarter/commit/7dce20cf2ef379789df9e01aa640652483138c18))

## [0.13.179](https://github.com/smarter-sh/smarter/compare/v0.13.178...v0.13.179) (2026-03-10)

### Bug Fixes

- add cors waffle switch with means of enabling localhost api ([9bffacb](https://github.com/smarter-sh/smarter/commit/9bffacb0689e47c71014bc3f797606b64f1ed24c))

## [0.13.178](https://github.com/smarter-sh/smarter/compare/v0.13.177...v0.13.178) (2026-03-09)

### Bug Fixes

- add a waffle debug model toggle ([4e31931](https://github.com/smarter-sh/smarter/commit/4e31931016c3809d5b2b570ac8c568b016c65d0d))

## [0.13.177](https://github.com/smarter-sh/smarter/compare/v0.13.176...v0.13.177) (2026-03-09)

### Bug Fixes

- missing waffle switch - ENABLE_MIDDLEWARE_SECURITY ([5a606c5](https://github.com/smarter-sh/smarter/commit/5a606c56741e452a112100b000da85cc5b5da908))

## [0.13.176](https://github.com/smarter-sh/smarter/compare/v0.13.175...v0.13.176) (2026-03-09)

### Bug Fixes

- add waffle switch for SmarterSecurityMiddleware ([1d7a9c9](https://github.com/smarter-sh/smarter/commit/1d7a9c9b13304b909921b9eb4b26624c3eb14630))

## [0.13.175](https://github.com/smarter-sh/smarter/compare/v0.13.174...v0.13.175) (2026-03-09)

### Bug Fixes

- api ingress cluster issuer should be environment api domain ([7cce6d0](https://github.com/smarter-sh/smarter/commit/7cce6d08264ccd2859a1761dfb39109827fa5744))

## [0.13.174](https://github.com/smarter-sh/smarter/compare/v0.13.173...v0.13.174) (2026-03-07)

### Bug Fixes

- Settings.dump() ([c50b6e7](https://github.com/smarter-sh/smarter/commit/c50b6e79cc20bfa9fbe1169061845f5248930432))

## [0.13.173](https://github.com/smarter-sh/smarter/compare/v0.13.172...v0.13.173) (2026-03-07)

### Bug Fixes

- expand possible values of THE_EMPTY_SET ([6e31343](https://github.com/smarter-sh/smarter/commit/6e31343e59a9145a9c9ab3f0d37b326cdf6317f3))

## [0.13.172](https://github.com/smarter-sh/smarter/compare/v0.13.171...v0.13.172) (2026-03-07)

### Bug Fixes

- workflow ([3cdff3e](https://github.com/smarter-sh/smarter/commit/3cdff3e21c411f5d20aef293a7af59f4fe7260fb))

## [0.13.171](https://github.com/smarter-sh/smarter/compare/v0.13.170...v0.13.171) (2026-03-06)

### Bug Fixes

- move branding inputs to github secrets ([9662011](https://github.com/smarter-sh/smarter/commit/9662011f93dd684a6432c13872cec1fd9bba2cd7))

## [0.13.170](https://github.com/smarter-sh/smarter/compare/v0.13.169...v0.13.170) (2026-03-06)

### Bug Fixes

- create daily MariaDb backup ([33feddb](https://github.com/smarter-sh/smarter/commit/33feddb36ce832b748929a592c9d8cac3a7ef544))
- refactor account initialization and add an --all option ([bb73435](https://github.com/smarter-sh/smarter/commit/bb73435d9c9e68ca57ed64be7ec72e7fa79d9bc5))
- remove account initialization from deployment job ([b479b38](https://github.com/smarter-sh/smarter/commit/b479b38a6a592796bf38b9ac6db70ef290a04e91))
- work on account initialization ([cdc3180](https://github.com/smarter-sh/smarter/commit/cdc3180eb7171209f8929c5df9e3e39b817d3bee))

## [0.13.169](https://github.com/smarter-sh/smarter/compare/v0.13.168...v0.13.169) (2026-03-04)

### Bug Fixes

- refactor permission logic in SecretAdmin.display_value() ([61591fc](https://github.com/smarter-sh/smarter/commit/61591fcf99f3488668392ef85da13ffc72b288cd))

## [0.13.168](https://github.com/smarter-sh/smarter/compare/v0.13.167...v0.13.168) (2026-03-04)

### Bug Fixes

- model visibiity in admin console ([c9f80c5](https://github.com/smarter-sh/smarter/commit/c9f80c522d0f194a01dc930d128fa574197d4841))
- role-base access to models in admin console ([b6219b8](https://github.com/smarter-sh/smarter/commit/b6219b8c1760ddded48b65094cda2fb5de03f2f2))
- role-based access to models in admin console ([d5c8446](https://github.com/smarter-sh/smarter/commit/d5c8446bad8fb8d091ee17146ab66f2e4fc77d9c))
- setup role-based access to admin console models ([f6c7100](https://github.com/smarter-sh/smarter/commit/f6c7100fd9831f94bcc2333593c284ef6643894f))

## [0.13.167](https://github.com/smarter-sh/smarter/compare/v0.13.166...v0.13.167) (2026-03-04)

### Bug Fixes

- work on customer access to models in admin page ([5c53e0b](https://github.com/smarter-sh/smarter/commit/5c53e0bf0b9a365860cd9a213a580e1ee948d6cf))

## [0.13.166](https://github.com/smarter-sh/smarter/compare/v0.13.165...v0.13.166) (2026-03-03)

### Bug Fixes

- update permission and layout of User ([f3e781a](https://github.com/smarter-sh/smarter/commit/f3e781a5032f9960412b639ed99157230b18865b))
- update the <video> configuration ([fe1ff72](https://github.com/smarter-sh/smarter/commit/fe1ff72ffaf358d2d45c74eddbaf6aa29759b677))

## [0.13.165](https://github.com/smarter-sh/smarter/compare/v0.13.164...v0.13.165) (2026-03-03)

### Bug Fixes

- toggle welcome email if password will be sent separately. ([1d86e91](https://github.com/smarter-sh/smarter/commit/1d86e91092e669072d7121965c64b8d8ab76160e))

## [0.13.164](https://github.com/smarter-sh/smarter/compare/v0.13.163...v0.13.164) (2026-03-03)

### Bug Fixes

- add a waffle switch to toggle new user password email ([d2e1b55](https://github.com/smarter-sh/smarter/commit/d2e1b5593b27823b3bc0abf3095765dc2424ee31))

## [0.13.163](https://github.com/smarter-sh/smarter/compare/v0.13.162...v0.13.163) (2026-03-02)

### Bug Fixes

- welcome email - add deployment options bullet ([caf2958](https://github.com/smarter-sh/smarter/commit/caf295873ef78aa93168a51e208de8d269b69cf3))

## [0.13.162](https://github.com/smarter-sh/smarter/compare/v0.13.161...v0.13.162) (2026-03-02)

### Bug Fixes

- welcome email png img styling ([e95ba0f](https://github.com/smarter-sh/smarter/commit/e95ba0fe85cd23b083bbd5e3b93b7446c7a17837))

## [0.13.161](https://github.com/smarter-sh/smarter/compare/v0.13.160...v0.13.161) (2026-03-02)

### Bug Fixes

- welcome email social link styling ([3c4bc31](https://github.com/smarter-sh/smarter/commit/3c4bc313539a622e92858451e42e00cf4bf069ae))

## [0.13.160](https://github.com/smarter-sh/smarter/compare/v0.13.159...v0.13.160) (2026-03-02)

### Bug Fixes

- convert all email svg images to png ([77e627e](https://github.com/smarter-sh/smarter/commit/77e627e3c448f2a4ea077e0cbacaafcd881eca5c))

## [0.13.159](https://github.com/smarter-sh/smarter/compare/v0.13.158...v0.13.159) (2026-03-02)

### Bug Fixes

- welcome email ([6b53b86](https://github.com/smarter-sh/smarter/commit/6b53b8670b3c0bd64d49650e898bb57861b47a82))

## [0.13.158](https://github.com/smarter-sh/smarter/compare/v0.13.157...v0.13.158) (2026-03-01)

### Bug Fixes

- gpt-5-nano doesn't support tool calls. ([c8c3752](https://github.com/smarter-sh/smarter/commit/c8c3752ed623913f2ed89b55f719511a725bda80))
- LLM prompt error responses. pass these in the message list instead of raising a modal dialogue ([5952d8d](https://github.com/smarter-sh/smarter/commit/5952d8de379aeab9daad201d3b273faa189617c1))

## [0.13.157](https://github.com/smarter-sh/smarter/compare/v0.13.156...v0.13.157) (2026-02-28)

### Bug Fixes

- cleanup ChatBotHelper initialization ([24d4243](https://github.com/smarter-sh/smarter/commit/24d4243b05b92334f55c5f1c29e52f1debb9f6ca))

## [0.13.156](https://github.com/smarter-sh/smarter/compare/v0.13.155...v0.13.156) (2026-02-28)

### Bug Fixes

- cleanup AbstractBroker().**init**() ([acaa7c6](https://github.com/smarter-sh/smarter/commit/acaa7c62fa3e5ad3606f4560ea4bb0e05fa1dd8d))
- cleanup manifest().setter ([787bef8](https://github.com/smarter-sh/smarter/commit/787bef8315cad0c83a1675f0e1ae92da87a916c0))
- SAMChatbotBroker.apply() logic for pruning plugins ([57713ba](https://github.com/smarter-sh/smarter/commit/57713ba9e9f0dbb722adb668b7f056d3b581849b))

## [0.13.155](https://github.com/smarter-sh/smarter/compare/v0.13.154...v0.13.155) (2026-02-28)

### Bug Fixes

- add weather and simple chatbot examples ([b45c9d0](https://github.com/smarter-sh/smarter/commit/b45c9d0d104ac1b8e35bdcd253ab0aff4e9a5139))

## [0.13.154](https://github.com/smarter-sh/smarter/compare/v0.13.153...v0.13.154) (2026-02-27)

### Bug Fixes

- create calculator() LLM tool call function ([02b3716](https://github.com/smarter-sh/smarter/commit/02b371670f4aff85d9faef73de6c3e9424313f5c))

## [0.13.153](https://github.com/smarter-sh/smarter/compare/v0.13.152...v0.13.153) (2026-02-27)

### Bug Fixes

- add date_calculator LLM tool call function ([442b543](https://github.com/smarter-sh/smarter/commit/442b5430c74aaf897e017b28a298f83b0262bc6a))

## [0.13.152](https://github.com/smarter-sh/smarter/compare/v0.13.151...v0.13.152) (2026-02-26)

### Bug Fixes

- aws and k8s naming for local ([4f4a6ab](https://github.com/smarter-sh/smarter/commit/4f4a6ab6eb264e5573f346df389f067ae04824fb))
- refactor KubernetesHelper ([a506a50](https://github.com/smarter-sh/smarter/commit/a506a509f93caa36d48748fbd9e6c74d2db86dc7))

## [0.13.151](https://github.com/smarter-sh/smarter/compare/v0.13.150...v0.13.151) (2026-02-25)

### Bug Fixes

- welcome email context parameters ([990034d](https://github.com/smarter-sh/smarter/commit/990034dfdef4ffd1baecd06e6eb2d3107cc8e5a4))

## [0.13.150](https://github.com/smarter-sh/smarter/compare/v0.13.149...v0.13.150) (2026-02-25)

### Bug Fixes

- work on welcome email ([8400e27](https://github.com/smarter-sh/smarter/commit/8400e2721ec2702f835a26cd145419038672d51a))

## [0.13.149](https://github.com/smarter-sh/smarter/compare/v0.13.148...v0.13.149) (2026-02-25)

### Bug Fixes

- work on welcome email ([128b0dd](https://github.com/smarter-sh/smarter/commit/128b0dd2b70ceda290d847e5e4a74d7c35e1e351))

## [0.13.148](https://github.com/smarter-sh/smarter/compare/v0.13.147...v0.13.148) (2026-02-25)

### Bug Fixes

- work on password reset email ([c5d9465](https://github.com/smarter-sh/smarter/commit/c5d9465e9d6938e33db7d5bdd33732e47c8be4bd))

## [0.13.147](https://github.com/smarter-sh/smarter/compare/v0.13.146...v0.13.147) (2026-02-25)

### Bug Fixes

- work on html template parameters and defaults ([d5de3d5](https://github.com/smarter-sh/smarter/commit/d5de3d5d52cf8c753870bc912f6edea95024225b))

## [0.13.146](https://github.com/smarter-sh/smarter/compare/v0.13.145...v0.13.146) (2026-02-25)

### Bug Fixes

- parameterize product name, description ([3bb1c32](https://github.com/smarter-sh/smarter/commit/3bb1c32b715d9db60f0f1b3174f1933f173946b9))

## [0.13.145](https://github.com/smarter-sh/smarter/compare/v0.13.144...v0.13.145) (2026-02-25)

### Bug Fixes

- sign-in page ([1f04182](https://github.com/smarter-sh/smarter/commit/1f04182f4475ce1a4111ba1c8cc64c303f251ee4))

## [0.13.144](https://github.com/smarter-sh/smarter/compare/v0.13.143...v0.13.144) (2026-02-25)

### Bug Fixes

- parameterize sign-in page features with waffle switches ([3b6a2b3](https://github.com/smarter-sh/smarter/commit/3b6a2b39b13b5c41d7f08303875b3f449a1b83eb))

## [0.13.143](https://github.com/smarter-sh/smarter/compare/v0.13.142...v0.13.143) (2026-02-24)

### Bug Fixes

- add annotations to ChatConfig ([4bafaca](https://github.com/smarter-sh/smarter/commit/4bafacafd9e06d6eaa03796898531bef5880438c))
- refactor forgot password email workflow ([2738c58](https://github.com/smarter-sh/smarter/commit/2738c587f5591c21c55e7343d2eb1375d031c89a))
- refactor welcome email ([4da7001](https://github.com/smarter-sh/smarter/commit/4da7001560c51e9767725b41c738e95650f8ed87))

## [0.13.142](https://github.com/smarter-sh/smarter/compare/v0.13.141...v0.13.142) (2026-02-24)

### Bug Fixes

- repoint cdn.platform.smarter.sh to cdn.smarter.sh ([50e495f](https://github.com/smarter-sh/smarter/commit/50e495f3deabd985f8e5af803658183e1863c946))

## [0.13.141](https://github.com/smarter-sh/smarter/compare/v0.13.140...v0.13.141) (2026-02-24)

### Bug Fixes

- create security FAQ ([d49475c](https://github.com/smarter-sh/smarter/commit/d49475c8420c68531f64c8a9d7a41abc75a59d33))

## [0.13.140](https://github.com/smarter-sh/smarter/compare/v0.13.139...v0.13.140) (2026-02-21)

### Bug Fixes

- only block sensitive file if we actually have an IP address to block ([6d44b66](https://github.com/smarter-sh/smarter/commit/6d44b6690a5422863fa36a69a2be5c58aecd0d50))

## [0.13.139](https://github.com/smarter-sh/smarter/compare/v0.13.138...v0.13.139) (2026-02-21)

### Bug Fixes

- work on dns ([ac617b8](https://github.com/smarter-sh/smarter/commit/ac617b8867734c1869052461aa2654a85f5c1aaa))

## [0.13.138](https://github.com/smarter-sh/smarter/compare/v0.13.137...v0.13.138) (2026-02-21)

### Bug Fixes

- deployment workflow ([24ac124](https://github.com/smarter-sh/smarter/commit/24ac124abbc4227519ef3e48c1a0f8783c70ade0))

## [0.13.137](https://github.com/smarter-sh/smarter/compare/v0.13.136...v0.13.137) (2026-02-21)

### Bug Fixes

- deploy local to proxy api domain ([c2d248a](https://github.com/smarter-sh/smarter/commit/c2d248ac3f9738dd1f00af494d8263dcb47b19dd))

## [0.13.136](https://github.com/smarter-sh/smarter/compare/v0.13.135...v0.13.136) (2026-02-21)

### Bug Fixes

- add waffle switches to toggle middleware ([b946a78](https://github.com/smarter-sh/smarter/commit/b946a785ab5877b2a68963e3983bc35fc2716962))
- broken links ([11c5dc7](https://github.com/smarter-sh/smarter/commit/11c5dc7bd6833df706a43d87e505f1c8c4c97506))
- dns verification logic where api.platform.example.com resides inside of platform.example.com ([2208653](https://github.com/smarter-sh/smarter/commit/2208653919f3f0dc86e50127adec2c307e323a8a))
- refactor manage.py verify_dns_configuration ([09720a8](https://github.com/smarter-sh/smarter/commit/09720a81ed707a8adc7d3285399d81896c0524fd))

## [0.13.135](https://github.com/smarter-sh/smarter/compare/v0.13.134...v0.13.135) (2026-02-20)

### Bug Fixes

- convert api ingress to traefik ([58b2bb6](https://github.com/smarter-sh/smarter/commit/58b2bb6eff4099875f36cd08aac9fa0a4082b46a))

## [0.13.134](https://github.com/smarter-sh/smarter/compare/v0.13.133...v0.13.134) (2026-02-20)

### Bug Fixes

- recursion error in ChatBotHelper.is_chatbothelper_ready() ([cf3dd9d](https://github.com/smarter-sh/smarter/commit/cf3dd9d61998c63771009b23212a29462442ded1))

## [0.13.133](https://github.com/smarter-sh/smarter/compare/v0.13.132...v0.13.133) (2026-02-17)

### Bug Fixes

- sphinx linter errors ([30ca7e9](https://github.com/smarter-sh/smarter/commit/30ca7e9d47b5ead0fd48413840693709e6147722))

## [0.13.132](https://github.com/smarter-sh/smarter/compare/v0.13.131...v0.13.132) (2026-02-17)

### Bug Fixes

- sphinx doc linting ([99dbb72](https://github.com/smarter-sh/smarter/commit/99dbb72d5820c241b8e46acf9a5f3cb25d6b26f5))

## [0.13.131](https://github.com/smarter-sh/smarter/compare/v0.13.130...v0.13.131) (2026-02-17)

### Bug Fixes

- update deployment docs ([64c7300](https://github.com/smarter-sh/smarter/commit/64c73005d66d09440723458f8cf5a164b8f4fb01))

## [0.13.130](https://github.com/smarter-sh/smarter/compare/v0.13.129...v0.13.130) (2026-02-17)

### Bug Fixes

- add a deployment page. fix linter errors ([3307903](https://github.com/smarter-sh/smarter/commit/3307903a52f0786332ddd42550bd9c488f841a0c))
- root_api_domain should be of the form api.platform.example.com ([73e14b1](https://github.com/smarter-sh/smarter/commit/73e14b144c2a4100bb5a356b96bc5460c9930ed9))

## [0.13.129](https://github.com/smarter-sh/smarter/compare/v0.13.128...v0.13.129) (2026-02-17)

### Bug Fixes

- parameterize smarter_settings.platform_subdomain ([34752d5](https://github.com/smarter-sh/smarter/commit/34752d53ff92029927cb98363083140d799127d6))

## [0.13.128](https://github.com/smarter-sh/smarter/compare/v0.13.127...v0.13.128) (2026-02-16)

### Bug Fixes

- Values should be .Values ([6971e50](https://github.com/smarter-sh/smarter/commit/6971e50f404d97393a8e1d2e1bcb3703ea17df19))

## [0.13.127](https://github.com/smarter-sh/smarter/compare/v0.13.126...v0.13.127) (2026-02-16)

### Bug Fixes

- Values.env.SMARTER should be Values.env.SMARTER*MYSQL* ([d60a00c](https://github.com/smarter-sh/smarter/commit/d60a00c6240a4ae1dce1d5678a023ab560a3d3d9))

## [0.13.126](https://github.com/smarter-sh/smarter/compare/v0.13.125...v0.13.126) (2026-02-14)

### Bug Fixes

- revert/restore original Redis default values ([d36eff2](https://github.com/smarter-sh/smarter/commit/d36eff280552388b144e31a01124aba010569fa0))

## [0.13.125](https://github.com/smarter-sh/smarter/compare/v0.13.124...v0.13.125) (2026-02-08)

### Bug Fixes

- pass task_id to receivers for logging ([8c93406](https://github.com/smarter-sh/smarter/commit/8c93406fd2fa33f5da46a1159b1c25d7c0543205))

## [0.13.124](https://github.com/smarter-sh/smarter/compare/v0.13.123...v0.13.124) (2026-02-08)

### Bug Fixes

- stope endless cycle of deploy-undeploy ([a658fb1](https://github.com/smarter-sh/smarter/commit/a658fb15c38bc466198ced964f4ebe019dd748df))

## [0.13.123](https://github.com/smarter-sh/smarter/compare/v0.13.122...v0.13.123) (2026-02-08)

### Bug Fixes

- add Celery task id to all asynchronous task log entries ([65bc036](https://github.com/smarter-sh/smarter/commit/65bc0368831899c21b91b2b83ebe4a2b49d991e9))
- resolve django.template.response.ContentNotRenderedError: The response content must be rendered before it can be accessed. ([6c63699](https://github.com/smarter-sh/smarter/commit/6c636991db3e0efdd8e6826182687264d9fe0942))

## [0.13.122](https://github.com/smarter-sh/smarter/compare/v0.13.121...v0.13.122) (2026-02-08)

### Bug Fixes

- gemini flash 1.5 is deprecated ([a39911d](https://github.com/smarter-sh/smarter/commit/a39911df73e25edd8c16dbc1c651e8fe0dc7d6a3))
- swap deprecated google.generativeai for google.genai ([1745dff](https://github.com/smarter-sh/smarter/commit/1745dffa495eafb354ddf25da305ddfb4a36403b))
- update default model ([0c27533](https://github.com/smarter-sh/smarter/commit/0c275334e64630b77d8fff6a28e95586dba75122))
- update googleai model family ([2dd21a2](https://github.com/smarter-sh/smarter/commit/2dd21a2644af117ec493c5cc8772e28761b912c6))

## [0.13.121](https://github.com/smarter-sh/smarter/compare/v0.13.120...v0.13.121) (2026-02-07)

### Bug Fixes

- every main urls module needs a 'console_home' ([b2ff8f3](https://github.com/smarter-sh/smarter/commit/b2ff8f303cb22175139680555570017e50b0d2b3))

## [0.13.120](https://github.com/smarter-sh/smarter/compare/v0.13.119...v0.13.120) (2026-02-07)

### Bug Fixes

- fixup page titles ([b7bbfc1](https://github.com/smarter-sh/smarter/commit/b7bbfc1c9694caa9ff66dfa84ed02a23aee5c464))
- setup DJANGO\_ override system for defined Django settings overrides from .env ([4f2fd23](https://github.com/smarter-sh/smarter/commit/4f2fd2300d77bf827f1097659ba5d8ae1a29bbac))
- work on Django settings overrides ([da851d3](https://github.com/smarter-sh/smarter/commit/da851d377579feffc0de2fd1c998e5ba0ec29566))

## [0.13.119](https://github.com/smarter-sh/smarter/compare/v0.13.118...v0.13.119) (2026-02-06)

### Bug Fixes

- add a manifest view accessible from the workbench chatbots list view ([2ab378e](https://github.com/smarter-sh/smarter/commit/2ab378ef5b106fa64b495dd8c731ff1f0b0087ea))
- add ownership title to template. add inline documentation ([c0dc5e3](https://github.com/smarter-sh/smarter/commit/c0dc5e37bc7458fbc0cf40c869d1dc2f741d8aad))

## [0.13.118](https://github.com/smarter-sh/smarter/compare/v0.13.117...v0.13.118) (2026-02-06)

### Bug Fixes

- add a listview and toggle switch ([5cf937f](https://github.com/smarter-sh/smarter/commit/5cf937fa55530ffe119af536a35248a57dfca2e7))
- add a listview and toggle switch ([340fabe](https://github.com/smarter-sh/smarter/commit/340fabe947aaab22ccce8a7b55b45a5f9cc2514c))
- add a listview and toggle switch ([9f317a8](https://github.com/smarter-sh/smarter/commit/9f317a84d1785dbe49a920f3aa0121f8b24507ba))

## [0.13.117](https://github.com/smarter-sh/smarter/compare/v0.13.116...v0.13.117) (2026-02-06)

### Bug Fixes

- create a listview with a toggle switch ([5935dc6](https://github.com/smarter-sh/smarter/commit/5935dc69da2fd17ad5126dd9a67cfbaf34f1d730))

## [0.13.116](https://github.com/smarter-sh/smarter/compare/v0.13.115...v0.13.116) (2026-02-04)

### Bug Fixes

- ensure that smarter_reactjs_app_loader_url() doesn't break collectstatic ([95989f0](https://github.com/smarter-sh/smarter/commit/95989f05a9af47d81c9ab74a08fe2120cf14314e))

## [0.13.115](https://github.com/smarter-sh/smarter/compare/v0.13.114...v0.13.115) (2026-02-04)

### Bug Fixes

- ensure that deployment is triggered on chatbot.save() ([b87973e](https://github.com/smarter-sh/smarter/commit/b87973eb8098ead202dd439581e5de750504716d))

## [0.13.114](https://github.com/smarter-sh/smarter/compare/v0.13.113...v0.13.114) (2026-02-04)

### Bug Fixes

- roll back last commit and disable dependabot for Python dependencies ([035609d](https://github.com/smarter-sh/smarter/commit/035609de25699e4d9ba182a94175c3c5864f6f24))

## [0.13.113](https://github.com/smarter-sh/smarter/compare/v0.13.112...v0.13.113) (2026-02-04)

### Bug Fixes

- enable manifest-driven functions ([2d9c6f0](https://github.com/smarter-sh/smarter/commit/2d9c6f06f8fc6b4ff01e3134f2b49261cdaf399a))
- ensure that hyphenated chatbot name slugs work in the workbench ([36242c4](https://github.com/smarter-sh/smarter/commit/36242c4ba948d5df26351854c9b4c95e704084a1))

## [0.13.112](https://github.com/smarter-sh/smarter/compare/v0.13.111...v0.13.112) (2026-01-31)

### Bug Fixes

- add pillow to venv ([d0fcc6e](https://github.com/smarter-sh/smarter/commit/d0fcc6e5674a32258f4891cee7266468c6f64267))

## [0.13.111](https://github.com/smarter-sh/smarter/compare/v0.13.110...v0.13.111) (2026-01-31)

### Bug Fixes

- force a new release ([6500eec](https://github.com/smarter-sh/smarter/commit/6500eec54069c0223aac2c6d748b3452d8f889fa))

## [0.13.110](https://github.com/smarter-sh/smarter/compare/v0.13.109...v0.13.110) (2026-01-29)

### Bug Fixes

- history in PromptConfigView ([28bbbc2](https://github.com/smarter-sh/smarter/commit/28bbbc286e627e49c835e7f1f62a3fcc3d3900a9))

## [0.13.109](https://github.com/smarter-sh/smarter/compare/v0.13.108...v0.13.109) (2026-01-28)

### Bug Fixes

- restyle the workbench listview ([cf23fe9](https://github.com/smarter-sh/smarter/commit/cf23fe969cd641ebdefccfb1dd11fb7efb90e37a))

## [0.13.108](https://github.com/smarter-sh/smarter/compare/v0.13.107...v0.13.108) (2026-01-28)

### Bug Fixes

- place profile image if it exists ([5132af4](https://github.com/smarter-sh/smarter/commit/5132af438ce9d73b11493b33bddd8433f84d64ba))

## [0.13.107](https://github.com/smarter-sh/smarter/compare/v0.13.106...v0.13.107) (2026-01-28)

### Bug Fixes

- social auth user experience improvements ([4468213](https://github.com/smarter-sh/smarter/commit/44682132af827ae3e1689185a27b360528762f5f))

## [0.13.106](https://github.com/smarter-sh/smarter/compare/v0.13.105...v0.13.106) (2026-01-28)

### Bug Fixes

- enable waffle flags by default. re-add wagtail urls ([f202bd5](https://github.com/smarter-sh/smarter/commit/f202bd578f3f53df2fe65789fe7197bf13aa67e6))

## [0.13.105](https://github.com/smarter-sh/smarter/compare/v0.13.104...v0.13.105) (2026-01-28)

### Bug Fixes

- django-csrftoken should contain the csrf token value, not the cookie name. ([7c51ffb](https://github.com/smarter-sh/smarter/commit/7c51ffb25fd4685ca490c251655d73176e0df320))

## [0.13.104](https://github.com/smarter-sh/smarter/compare/v0.13.103...v0.13.104) (2026-01-28)

### Bug Fixes

- set ingressClassName to 'default' and remove deprecated annotation ([bfdb4a8](https://github.com/smarter-sh/smarter/commit/bfdb4a8db1c5270acccc2511d38c9c0d0b654180))

## [0.13.103](https://github.com/smarter-sh/smarter/compare/v0.13.102...v0.13.103) (2026-01-27)

### Bug Fixes

- tweaks to Smarter account ([111ce56](https://github.com/smarter-sh/smarter/commit/111ce56a6b39e9d9da3ad525edcae8fefa3668c2))

## [0.13.102](https://github.com/smarter-sh/smarter/compare/v0.13.101...v0.13.102) (2026-01-27)

### Bug Fixes

- control django debug toolbar with smarter_settings.debug_mode ([c20b944](https://github.com/smarter-sh/smarter/commit/c20b9449867442d05918e6acb6ecc3cb51609a80))

## [0.13.101](https://github.com/smarter-sh/smarter/compare/v0.13.100...v0.13.101) (2026-01-27)

### Bug Fixes

- automatically navigate to the page listview containing the resource that was applied ([d7fda39](https://github.com/smarter-sh/smarter/commit/d7fda39c5c2d18315d3296b819a5756b1c58e4b4))

## [0.13.100](https://github.com/smarter-sh/smarter/compare/v0.13.99...v0.13.100) (2026-01-27)

### Bug Fixes

- code the browser js drop-zone handler ([4b05b74](https://github.com/smarter-sh/smarter/commit/4b05b7411968b16c65423c49526f7526add927f7))
- code yaml manifest drop zone ([5847764](https://github.com/smarter-sh/smarter/commit/58477640370018ff7e18a04405f52baf1eed1fb4))
- scaffold yaml file drop zone over web console ([9681290](https://github.com/smarter-sh/smarter/commit/9681290b055e5309067cf8ea7e709bc1d1db8f6a))

## [0.13.99](https://github.com/smarter-sh/smarter/compare/v0.13.98...v0.13.99) (2026-01-26)

### Refactor

- refactor: set role authorization levels in c-ud commands [127bace](https://github.com/smarter-sh/smarter/commit/ffd04cbae1bf754aa9cd7e0afc64be74a127bace)
- refactor: resource selection criteria for user_profile instead of account
  [9e8892d](https://github.com/smarter-sh/smarter/commit/9a2407e8abee09ebd1b250e54b18261949e8892d)
- refactor: get docker init working again [99dce69](https://github.com/smarter-sh/smarter/commit/8326c4c61dc8ac2bd9bb043c6564edb2899dce69)
- refactor: swap user_profile for account in MetaDataWithOwnershipModel
  [525dc41](https://github.com/smarter-sh/smarter/commit/8b4eb956d89a549cf36c022d117366173525dc41)

### Bug Fixes

- AccountMixin initialization sequence when inherited from RequestMixin ([bb99ded](https://github.com/smarter-sh/smarter/commit/bb99ded6875e325b368757596a1fdbdb5f760600))
- flush out more orphaned references to account. replace with user_profile ([2e5e0b7](https://github.com/smarter-sh/smarter/commit/2e5e0b7951114f1053388f746ab6ca9b17cc51fc))
- squash db migrations ([7b99b5d](https://github.com/smarter-sh/smarter/commit/7b99b5d5879c90e02b61484894d48878fe7b66a8))
- test and fix up Providers ([65391f9](https://github.com/smarter-sh/smarter/commit/65391f9b93a3bf79041c06eaf98b19315f510f03))
- wagtail induced template rendering errors in workbench django template and chatbot listview ([13217f9](https://github.com/smarter-sh/smarter/commit/13217f995203440c460642ee682966e9e1e0462e))
- work on context processors and dashboard metrics ([048d970](https://github.com/smarter-sh/smarter/commit/048d970481e08796cfbb47cde77c689ed402bfc9))
- work on unit tests ([c2a2edf](https://github.com/smarter-sh/smarter/commit/c2a2edfef2f73a8003b8e142fa04940ebc69c258))

## [0.13.98](https://github.com/smarter-sh/smarter/compare/v0.13.97...v0.13.98) (2026-01-24)

### Bug Fixes

- python3.13 upgrade ([92dfc24](https://github.com/smarter-sh/smarter/commit/92dfc2496082761e0aae605ecc076e45816fe2d6))

## [0.13.97](https://github.com/smarter-sh/smarter/compare/v0.13.96...v0.13.97) (2026-01-22)

### Bug Fixes

- hide all oauth elements when oauth is not configured ([147f22e](https://github.com/smarter-sh/smarter/commit/147f22e9e6c318169fac36cd95dcefe59adb6d46))

## [0.13.96](https://github.com/smarter-sh/smarter/compare/v0.13.95...v0.13.96) (2026-01-21)

### Bug Fixes

- ensure that platform can startup (with warnings) without Google credentials ([91889f3](https://github.com/smarter-sh/smarter/commit/91889f36f21e7fa887e22802eabe9a8c20840b01))

## [0.13.95](https://github.com/smarter-sh/smarter/compare/v0.13.94...v0.13.95) (2026-01-21)

### Bug Fixes

- insert release notes after CHANGELOG.MD title ([24e97f3](https://github.com/smarter-sh/smarter/commit/24e97f3754b7327bda158bbd516fc71acf27d9ae))
- reduce disk requirements to 10Gib ([f77b715](https://github.com/smarter-sh/smarter/commit/f77b7159f2f62eb7eff5cf2e28645b697ba242d3))
- update docs urls ([03673e3](https://github.com/smarter-sh/smarter/commit/03673e37b81aae522f47dc0354aea96997f188a0))

## [0.13.94](https://github.com/smarter-sh/smarter/compare/v0.13.93...v0.13.94) (2026-01-20)

### Bug Fixes

- remaining Sphinx linter errors in docstrings ([925f440](https://github.com/smarter-sh/smarter/commit/925f440d768b295f34ff906b4b16891b8fe9ca99))

## [0.13.93](https://github.com/smarter-sh/smarter/compare/v0.13.92...v0.13.93) (2026-01-20)

### Bug Fixes

- Sphinx doc header cleanup ([02a2ec9](https://github.com/smarter-sh/smarter/commit/02a2ec91cdfdfb35cf22de702d6f8f3bdc700e11))

## [0.13.92](https://github.com/smarter-sh/smarter/compare/v0.13.91...v0.13.92) (2026-01-17)

### Bug Fixes

- refactor github loader console output. add SMARTER_AWS_EKS_CLUSTER_NAME and SMARTER_AWS_RDS_DB_INSTANCE_IDENTIFIER to ci-cd ([174ef5d](https://github.com/smarter-sh/smarter/commit/174ef5da0c5a11035d186e45d4e4aff3795635a0))

## [0.13.91](https://github.com/smarter-sh/smarter/compare/v0.13.90...v0.13.91) (2026-01-17)

### Bug Fixes

- add configuration variables to control beta and ubc accounts in ci-cd ([2160be6](https://github.com/smarter-sh/smarter/commit/2160be6148d9fbf1890e6dfe4b2ca22a3b399e87))

## [0.13.90](https://github.com/smarter-sh/smarter/compare/v0.13.89...v0.13.90) (2026-01-17)

### Bug Fixes

- force a new release ([e6080eb](https://github.com/smarter-sh/smarter/commit/e6080eb2d0ade3b62ea84cb7a63ab1ca64d3b3b0))

## [0.13.89](https://github.com/smarter-sh/smarter/compare/v0.13.88...v0.13.89) (2026-01-17)

### Bug Fixes

- bind directly to Broker with smarter.apps.plugin.util.apply_manifest() ([e49be02](https://github.com/smarter-sh/smarter/commit/e49be02e3f4aa12d42977d2304814270d51f15c3))

## [0.13.88](https://github.com/smarter-sh/smarter/compare/v0.13.87...v0.13.88) (2026-01-17)

### Bug Fixes

- refactor apply_manifest to directly instantiate the Broker ([3acd43a](https://github.com/smarter-sh/smarter/commit/3acd43a6b7ad284f01602cbd7a6069a66e784a66))

## [0.13.87](https://github.com/smarter-sh/smarter/compare/v0.13.86...v0.13.87) (2026-01-17)

### Bug Fixes

- refactor write() to logger.debug() ([bd0079f](https://github.com/smarter-sh/smarter/commit/bd0079fc77e4bfcb27bd5b24716c9d27ead131c0))

## [0.13.86](https://github.com/smarter-sh/smarter/compare/v0.13.85...v0.13.86) (2026-01-17)

### Bug Fixes

- refactor all console write() to logger.debug() ([f874ee7](https://github.com/smarter-sh/smarter/commit/f874ee7bde41501eba2a9ccd82f3eed85b7488b8))

## [0.13.85](https://github.com/smarter-sh/smarter/compare/v0.13.84...v0.13.85) (2026-01-17)

### Bug Fixes

- work on console output of manage.py apply_manifest ([a782ad7](https://github.com/smarter-sh/smarter/commit/a782ad7ebe3dd59889d9015581ced7ec52ea4c27))

## [0.13.84](https://github.com/smarter-sh/smarter/compare/v0.13.83...v0.13.84) (2026-01-17)

### Bug Fixes

- don't bother caching Secret ([2a90e4c](https://github.com/smarter-sh/smarter/commit/2a90e4c93abf4db45ce21ba2959f6f77f0b9748c))

## [0.13.83](https://github.com/smarter-sh/smarter/compare/v0.13.82...v0.13.83) (2026-01-16)

### Bug Fixes

- force a new release ([ea60774](https://github.com/smarter-sh/smarter/commit/ea607744ea317408700f906d06cc01a5120ea3cc))

## [0.13.82](https://github.com/smarter-sh/smarter/compare/v0.13.81...v0.13.82) (2026-01-16)

### Bug Fixes

- add logger.debug() to plugin broker classes ([6d553ec](https://github.com/smarter-sh/smarter/commit/6d553ecf1f3451e097893939aa269892be8bbfd2))

## [0.13.81](https://github.com/smarter-sh/smarter/compare/v0.13.80...v0.13.81) (2026-01-16)

### Bug Fixes

- skip clearing the cache ([c128328](https://github.com/smarter-sh/smarter/commit/c128328ab16638fc36706163b35a6c83b780b47a))

## [0.13.80](https://github.com/smarter-sh/smarter/compare/v0.13.79...v0.13.80) (2026-01-16)

### Bug Fixes

- pass k9s admin credentials to manage.py initialize_platform ([a21a3f6](https://github.com/smarter-sh/smarter/commit/a21a3f69ace6664542e74275375770a68ebbfa32))

## [0.13.79](https://github.com/smarter-sh/smarter/compare/v0.13.78...v0.13.79) (2026-01-16)

### Bug Fixes

- refactor new user creation ([e6a0f47](https://github.com/smarter-sh/smarter/commit/e6a0f47e6e363d89362bf956499abc8b4beec089))

## [0.13.78](https://github.com/smarter-sh/smarter/compare/v0.13.77...v0.13.78) (2026-01-16)

### Bug Fixes

- work on add_example_plugins() for new accounts ([91811cc](https://github.com/smarter-sh/smarter/commit/91811cc528822a10b07d5a68e3ae2d6c80066c7f))

## [0.13.77](https://github.com/smarter-sh/smarter/compare/v0.13.76...v0.13.77) (2026-01-16)

### Bug Fixes

- do not rely on cache when setting SecretTransformer.id ([f1a915d](https://github.com/smarter-sh/smarter/commit/f1a915d7318a137f3589f88fa2e313be583bda38))

## [0.13.76](https://github.com/smarter-sh/smarter/compare/v0.13.75...v0.13.76) (2026-01-16)

### Bug Fixes

- refactor account initialization. create manage.py initialize_account ([ea8381a](https://github.com/smarter-sh/smarter/commit/ea8381a82bafd5ddb2b4da79936c32e7f1e46c24))

## [0.13.75](https://github.com/smarter-sh/smarter/compare/v0.13.74...v0.13.75) (2026-01-16)

### Bug Fixes

- refactor manage.py commands for platform initialization ([f5f318c](https://github.com/smarter-sh/smarter/commit/f5f318c13e4c4a747547a49d663349ad8caf9a5c))

## [0.13.74](https://github.com/smarter-sh/smarter/compare/v0.13.73...v0.13.74) (2026-01-16)

### Bug Fixes

- version bump ([f9b44c4](https://github.com/smarter-sh/smarter/commit/f9b44c4664c0d985febe9bfd3241b1fc592e583a))

## [0.13.73](https://github.com/smarter-sh/smarter/compare/v0.13.72...v0.13.73) (2026-01-16)

### Bug Fixes

- calls to Django ORM objects in middleware have to be wrapped in try blocks for fresh installs ([5f05bc7](https://github.com/smarter-sh/smarter/commit/5f05bc775891f1e04ab7e91c11b575554ca603b2))

## [0.13.72](https://github.com/smarter-sh/smarter/compare/v0.13.71...v0.13.72) (2026-01-15)

### Bug Fixes

- rebrand to The Smarter Project ([9aa740f](https://github.com/smarter-sh/smarter/commit/9aa740f35e41847021103d95d341a5ed9f690b59))

## [0.13.71](https://github.com/smarter-sh/smarter/compare/v0.13.70...v0.13.71) (2026-01-15)

### Bug Fixes

- add local requirements to Dockerhub version, for smarter-deploy ([08a6363](https://github.com/smarter-sh/smarter/commit/08a63636e43e81eefea1724432d160755c48a662))

## [0.13.70](https://github.com/smarter-sh/smarter/compare/v0.13.69...v0.13.70) (2026-01-15)

### Bug Fixes

- include the prompt json of tools presented and called ([6225fd3](https://github.com/smarter-sh/smarter/commit/6225fd36d5a7b7ce42b09a4a6352751af6372544))

## [0.13.69](https://github.com/smarter-sh/smarter/compare/v0.13.68...v0.13.69) (2026-01-14)

### Bug Fixes

- ensure that csrf middleware never passes along the authenticated user ([2321f50](https://github.com/smarter-sh/smarter/commit/2321f50fe77d3a5e3a5737979bf893614a0f5cf2))

## [0.13.68](https://github.com/smarter-sh/smarter/compare/v0.13.67...v0.13.68) (2026-01-14)

### Bug Fixes

- smarter.lib.django.auth.GoogleOAuth2 should be social_core.backends.google.GoogleOAuth2 and so on. ([0210bc6](https://github.com/smarter-sh/smarter/commit/0210bc64578100934fa4c939b2c6c032e420521d))

## [0.13.67](https://github.com/smarter-sh/smarter/compare/v0.13.66...v0.13.67) (2026-01-14)

### Bug Fixes

- add waffle switch to toggle multitenant setup. parameterize whether oauth buttons appear on login page. add unit tests for authentication ([6d44177](https://github.com/smarter-sh/smarter/commit/6d441778c104d57cdcd5528beae71ec50a54412c))

## [0.13.66](https://github.com/smarter-sh/smarter/compare/v0.13.65...v0.13.66) (2026-01-14)

### Bug Fixes

- add smarter.lib.json ([cc91663](https://github.com/smarter-sh/smarter/commit/cc91663363f7005e05ba77546675d44aeb3c6617))

## [0.13.65](https://github.com/smarter-sh/smarter/compare/v0.13.64...v0.13.65) (2026-01-14)

### Bug Fixes

- aws cache location ([47f650c](https://github.com/smarter-sh/smarter/commit/47f650c7048b535601b2756f9b057ffd24928d22))

## [0.13.64](https://github.com/smarter-sh/smarter/compare/v0.13.63...v0.13.64) (2026-01-14)

### Bug Fixes

- cache hostname should be redis://:smarter@smarter-redis-master.smarter-platform-{smarter_settings.environment}.svc.cluster.local:6379/1 ([bbce5de](https://github.com/smarter-sh/smarter/commit/bbce5de2b9f6c1ddcb19e4a4b5aa7f07ed92fbee))

## [0.13.63](https://github.com/smarter-sh/smarter/compare/v0.13.62...v0.13.63) (2026-01-14)

### Bug Fixes

- force a new release ([86ad9e3](https://github.com/smarter-sh/smarter/commit/86ad9e30f1fd20ff1c053950a241f6d8733165dd))

## [0.13.62](https://github.com/smarter-sh/smarter/compare/v0.13.61...v0.13.62) (2026-01-14)

### Bug Fixes

- wrap is_database_ready() in a try block to handle k9s pod startup ([0a3a60a](https://github.com/smarter-sh/smarter/commit/0a3a60a642e58fe100086bda1503a0f882e5c1f5))

## [0.13.61](https://github.com/smarter-sh/smarter/compare/v0.13.60...v0.13.61) (2026-01-14)

### Bug Fixes

- force a new release ([fe99d9e](https://github.com/smarter-sh/smarter/commit/fe99d9ea4fa7493c65ddeac0e5b88a3be8ef35b7))

## [0.13.60](https://github.com/smarter-sh/smarter/compare/v0.13.59...v0.13.60) (2026-01-13)

### Bug Fixes

- add leading and trailing slashes if necessary in validate_connectivity_test_path() ([c32e895](https://github.com/smarter-sh/smarter/commit/c32e89569ef6fa6ea15f3ed82d470db8cd3f2dc9))

## [0.13.59](https://github.com/smarter-sh/smarter/compare/v0.13.58...v0.13.59) (2026-01-12)

### Features

- add a 'READY' / 'NOT_READY' logger.info() to top-level class instantiations: Broker, RequestMixin, AccountMixin, ChatBot, Plugin, SmarterAuthToken. This makes complex initialization sequences more auditable, and a lot easier to trouble shoot.

### Refactoring

- Add dunder methods to AbstractBroker, SAMLoader and AccountMixin.
- Standardize the behavior of to_json() throughout the AbstractBroker class hierarchy and related mixins in order to ensure consistent return objects in all V1 API responses.
- Refactor SmarterAuthToken and SAMSmarterAuthTokenBroker.
- Refactor initializations of RequestMixin and AccountMixin to more generically accept request, user, account and user_profile parameters,
  as positional parameters, args or kwargs. Extend DRF authentication into AccountMixin so that it is capable of 'pre-authentication',
  ahead of DRF's native lifecycle (something that comes up in certain edge cases).
- Refactor common conversion functions into SmarterConverterMixin.
- Standardize `__str__` and `__repr__` dunder methods across the entire class library.
- Convert nearly all logger.info() to logger.debug()
- Disable formatted log entries when not running locally.
- Standardize behavior of ready() across the class hierarchy.

### Bug Fixes

- camel_to_snake() should return None if it receives None ([61850f3](https://github.com/smarter-sh/smarter/commit/61850f39048b6619cf4d041499d2ac77524e32e7))
- misc failed tests ([6a14772](https://github.com/smarter-sh/smarter/commit/6a14772ba3387e882f971ea9c95b5ed6a44b925c))
- misc manifest and broker bug fixes. ([0b6a26b](https://github.com/smarter-sh/smarter/commit/0b6a26b764abc791fcf1b91626cc488cbe4557b1))

### Tests

- add common bank of SAM Broker unit tests to SmarterAuthToken and SAMSmarterAuthTokenBroker.

## [0.13.58](https://github.com/smarter-sh/smarter/compare/v0.13.57...v0.13.58) (2026-01-09)

### Refactor

- Test Coverage \* Added approximately 450 unit tests, focused on smarter.lib, smarter.common, smarter.apps.api.v1.cli, and the SAM broker model in general.
- Documentation \* Published a Read the Docs site: [https://docs.smarter.sh/en/latest/](https://docs.smarter.sh/en/latest/)
- Caching \* strategically implemented caching vis a vis @cache_results() on the most commonly accessed Python objects.

## [0.13.57](https://github.com/smarter-sh/smarter/compare/v0.13.56...v0.13.57) (2025-12-26)

### Bug Fixes

- add APIKeyListView ([698a07a](https://github.com/smarter-sh/smarter/commit/698a07a96c8d209c79b67aefba821d710b139b5f))
- add link to Dashboard Connection card ([178405a](https://github.com/smarter-sh/smarter/commit/178405a4baac612591220df0d18105d24d79ae95))
- add Secrets, Custom Domains, Api Keys to left side bar ([4ef17f4](https://github.com/smarter-sh/smarter/commit/4ef17f4082128ac447c9e55b4587be5122a88819))
- add waffle should_log() ([96354d7](https://github.com/smarter-sh/smarter/commit/96354d78ff1df0ff31e1decdf30411a186990648))
- exit gracefully if smarter_request_mixin.is_smarter_api == False ([6c8a5eb](https://github.com/smarter-sh/smarter/commit/6c8a5eb003a7e5fc70216b3cba15b9ca1a6a8fe7))
- implement Provider broker ([94bace6](https://github.com/smarter-sh/smarter/commit/94bace6dad2276178203febb0379a078eed35dd2))
- look for environment variable overrides ([4a00a67](https://github.com/smarter-sh/smarter/commit/4a00a67318b6e53bb6a1e7e2ecd375814dd71b3e))
- remove django login_required and staff decorators. replace with our own logic ([cc4c262](https://github.com/smarter-sh/smarter/commit/cc4c262de357fe9db6c13ccdc103f641e34a93e0))
- SmarterSecurityMiddleware should allow .well-known/acme-challenge requests ([2a97e86](https://github.com/smarter-sh/smarter/commit/2a97e862a53e49310473ac019065c1c783cf383d))

## [0.13.56](https://github.com/smarter-sh/smarter/compare/v0.13.55...v0.13.56) (2025-12-24)

### Bug Fixes

- defer initializing selector, prompt, plugin_data django ORM dicts until we know that we're going to create. ([bb5af38](https://github.com/smarter-sh/smarter/commit/bb5af38590fe1a4595448d68f836b91ea28ba5ec))

## [0.13.55](https://github.com/smarter-sh/smarter/compare/v0.13.54...v0.13.55) (2025-12-24)

### Bug Fixes

- do not reference self.request in setup() since it does not yet exist ([e065933](https://github.com/smarter-sh/smarter/commit/e065933e4ae354b2aacf54d87af6204fe5fb3a35))

## [0.13.54](https://github.com/smarter-sh/smarter/compare/v0.13.53...v0.13.54) (2025-12-23)

### Bug Fixes

- add object caching ([1787cc9](https://github.com/smarter-sh/smarter/commit/1787cc9967f797ea16d868c419c210ac56069d65))

## [0.13.53](https://github.com/smarter-sh/smarter/compare/v0.13.52...v0.13.53) (2025-12-22)

### Bug Fixes

- do not expose sensitive values when logging ([7b58495](https://github.com/smarter-sh/smarter/commit/7b5849509e0bbdd85c0a4f13e62e9aadd06e9ff7))

## [0.13.52](https://github.com/smarter-sh/smarter/compare/v0.13.51...v0.13.52) (2025-12-21)

### Bug Fixes

- define **all** in each settings module ([56dab9e](https://github.com/smarter-sh/smarter/commit/56dab9e14fced0690525de2606b915fd61e24fb3))

## [0.13.51](https://github.com/smarter-sh/smarter/compare/v0.13.50...v0.13.51) (2025-12-20)

### Bug Fixes

- work on Settings defaults ([13d02fb](https://github.com/smarter-sh/smarter/commit/13d02fb72ce17028cda6766fe5abb015e4065f66))

## [0.13.50](https://github.com/smarter-sh/smarter/compare/v0.13.49...v0.13.50) (2025-12-20)

### Bug Fixes

- ensure that all sensitive data is typed to SecretStr ([13760d4](https://github.com/smarter-sh/smarter/commit/13760d4736a7e17f26968bec36a318d11fa5c145))

## [0.13.49](https://github.com/smarter-sh/smarter/compare/v0.13.48...v0.13.49) (2025-12-19)

### Bug Fixes

- make all Django and Smarter settings overridable via .env ([923cd6f](https://github.com/smarter-sh/smarter/commit/923cd6f31d791e05cd19344114ade6b60f5b2b7e))

## [0.13.48](https://github.com/smarter-sh/smarter/compare/v0.13.47...v0.13.48) (2025-12-17)

### Bug Fixes

- install Oracle mysql client ([52083b2](https://github.com/smarter-sh/smarter/commit/52083b2577a03f37bdc156ae08a7195f3a776382))

## [0.13.47](https://github.com/smarter-sh/smarter/compare/v0.13.46...v0.13.47) (2025-12-17)

### Bug Fixes

- add custom authentication backends for hosted platforms ([dde5431](https://github.com/smarter-sh/smarter/commit/dde54314ff7abb69d0a2bfed8a193063f6d85b0c))

## [0.13.46](https://github.com/smarter-sh/smarter/compare/v0.13.45...v0.13.46) (2025-12-17)

### Bug Fixes

- add custom authentication backends for hosted platforms ([727506d](https://github.com/smarter-sh/smarter/commit/727506d45698920c475a428aa9932cbf795a6b60))

## [0.13.45](https://github.com/smarter-sh/smarter/compare/v0.13.44...v0.13.45) (2025-12-17)

### Bug Fixes

- add custom authentication backends for hosted platforms ([7a35816](https://github.com/smarter-sh/smarter/commit/7a358165c5ce3c45e43f43f5802a9a03c45f9766))

## [0.13.44](https://github.com/smarter-sh/smarter/compare/v0.13.43...v0.13.44) (2025-12-12)

### Bug Fixes

- refactor and document new caching strategy ([4272461](https://github.com/smarter-sh/smarter/commit/42724619b762347885f1f382578a0e9cef77a59c))

## [0.13.43](https://github.com/smarter-sh/smarter/compare/v0.13.42...v0.13.43) (2025-12-12)

### Bug Fixes

- re-enable waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING) ([7876844](https://github.com/smarter-sh/smarter/commit/78768443a0fb805b0002dbc4eb233f2a12380772))

## [0.13.42](https://github.com/smarter-sh/smarter/compare/v0.13.41...v0.13.42) (2025-12-12)

### Bug Fixes

- create a LazyCache class for importing from django.core.cache only after Django is fully initialized. ([c67b60e](https://github.com/smarter-sh/smarter/commit/c67b60e2528bea5e084b12aaffa5334ead3e93ea))
- remove waffle from cache.py ([49381ba](https://github.com/smarter-sh/smarter/commit/49381ba707dca4f83b2b83e2c8d2f708d736069f))

## [0.13.41](https://github.com/smarter-sh/smarter/compare/v0.13.40...v0.13.41) (2025-12-11)

### Bug Fixes

- create SmarterValidator.is_api_endpoint and use this to evaluate request path in SmarterTokenAuthenticationMiddleware ([8a157fc](https://github.com/smarter-sh/smarter/commit/8a157fc04a0deb03c2631f660a19245b11c28412))

## [0.13.40](https://github.com/smarter-sh/smarter/compare/v0.13.39...v0.13.40) (2025-12-11)

### Bug Fixes

- add link to Dashboard Connection card ([3ff65cc](https://github.com/smarter-sh/smarter/commit/3ff65cc08ac9a6ede82f66f708914f91c9bf549f))
- add waffle should_log() ([5390f33](https://github.com/smarter-sh/smarter/commit/5390f33acaea14ee0e7cca478a2f232ee4417c2c))

## [0.13.39](https://github.com/smarter-sh/smarter/compare/v0.13.38...v0.13.39) (2025-12-11)

### Bug Fixes

- add APIKeyListView ([3c74ab1](https://github.com/smarter-sh/smarter/commit/3c74ab1955d75cea5e53c580250365106454f731))
- add Secrets, Custom Domains, Api Keys to left side bar ([a055d06](https://github.com/smarter-sh/smarter/commit/a055d064508b676549084ddb39b7378eb81f0165))
- exit gracefully if smarter_request_mixin.is_smarter_api == False ([f63d01b](https://github.com/smarter-sh/smarter/commit/f63d01beee1e325e52aca98ab519a3b1706ca9e0))
- remove django login_required and staff decorators. replace with our own logic ([8ba09bb](https://github.com/smarter-sh/smarter/commit/8ba09bb52db7d7d6bc49eb319ee837d9bd56b55f))

## [0.13.38](https://github.com/smarter-sh/smarter/compare/v0.13.37...v0.13.38) (2025-12-06)

### Bug Fixes

- SmarterSecurityMiddleware should allow .well-known/acme-challenge requests ([b10f91c](https://github.com/smarter-sh/smarter/commit/b10f91c213409756d8a10402839ef5a49c57210a))

## [0.13.37](https://github.com/smarter-sh/smarter/compare/v0.13.36...v0.13.37) (2025-12-06)

### Bug Fixes

- release sphinx Read the Docs ([1ee9cb0](https://github.com/smarter-sh/smarter/commit/1ee9cb07fadd70073795464f1ddb227cd8ee7093))

## 0.13.37

- Release first version of Sphinx docs for Read the Docs.

## [0.13.36](https://github.com/smarter-sh/smarter/compare/v0.13.35...v0.13.36) (2025-11-29)

### Bug Fixes

- remove import django.core.serializers.json.DjangoJSONEncoder ([95cffb8](https://github.com/smarter-sh/smarter/commit/95cffb8b41baf7b4b9f1a0d42a3a3c0bb4422a73))

## [0.13.35](https://github.com/smarter-sh/smarter/compare/v0.13.34...v0.13.35) (2025-11-29)

### Bug Fixes

- grant amnesty to cert-manager requests to .well-known/acme-challenge/ ([ff6e1a5](https://github.com/smarter-sh/smarter/commit/ff6e1a5a99489abe3222de3ff45f0ef1736e8c59))

## [0.13.34](https://github.com/smarter-sh/smarter/compare/v0.13.35...v0.13.34) (2025-11-29)

### Bug Fixes

- add db index to created_at to resolve django.db.utils.OperationalError: (1038, 'Out of sort memory, consider increasing server sort buffer size') ([46e33f7](https://github.com/smarter-sh/smarter/commit/46e33f75047cb0d74588d355540fc4aadcc20932))

## [0.13.35](https://github.com/smarter-sh/smarter/compare/v0.13.32...v0.13.35) (2025-11-21)

### Bug Fixes

- ensure that aws deployments fail gracefully if aws is not configured ([227ef6b](https://github.com/smarter-sh/smarter/commit/227ef6ba905390e3bfba6b154f6c42a3ecd930ac))

## [0.13.32](https://github.com/smarter-sh/smarter/compare/v0.13.31...v0.13.32) (2025-11-21)

### Bug Fixes

- fail gracefully if aws is not configured ([7f63c65](https://github.com/smarter-sh/smarter/commit/7f63c6549d65e22cfd4a1ffb41a33e478f4a7211))

## [0.13.31](https://github.com/smarter-sh/smarter/compare/v0.13.30...v0.13.31) (2025-11-21)

### Bug Fixes

- only raise EmailHelperException if smarter_settings.smtp_is_configured ([9eca70c](https://github.com/smarter-sh/smarter/commit/9eca70c6ef76b06be3670824b3cadb7bf141fb1e))

## [0.13.30](https://github.com/smarter-sh/smarter/compare/v0.13.29...v0.13.30) (2025-11-20)

### Bug Fixes

- cleanup docker-init commands ([efca1d4](https://github.com/smarter-sh/smarter/commit/efca1d4f72c434a00eb9b6b4859964bade6635bd))

## [0.13.29](https://github.com/smarter-sh/smarter/compare/v0.13.28...v0.13.29) (2025-11-20)

### Bug Fixes

- set spec.ingressClassName: default ([19c745a](https://github.com/smarter-sh/smarter/commit/19c745ab59309d4563ad508f2d98a27436d0e2ec))

## [0.13.28](https://github.com/smarter-sh/smarter/compare/v0.13.27...v0.13.28) (2025-11-19)

### Bug Fixes

- cache decorator should fail gracefully if its cache is unavailable ([7438487](https://github.com/smarter-sh/smarter/commit/7438487749fcdf8dfe00eca16fe3ec6505bbcb97))

## [0.13.27](https://github.com/smarter-sh/smarter/compare/v0.13.26...v0.13.27) (2025-11-19)

### Bug Fixes

- cleanup data type linter errors ([50283b4](https://github.com/smarter-sh/smarter/commit/50283b452411cda3b6beaec58bd17847aec71ed1))
- fail gracefully if aws cli could not authenticate ([96a1f71](https://github.com/smarter-sh/smarter/commit/96a1f717c5e510491ba6d7d6075866272149344f))

## [0.13.26](https://github.com/smarter-sh/smarter/compare/v0.13.25...v0.13.26) (2025-11-19)

### Bug Fixes

- add developer_mode to fine tune behavior of local.py settings ([f925702](https://github.com/smarter-sh/smarter/commit/f925702401ad863a0e86bf2642b5885e6dc12d62))
- add the actual password to the test db ([3ebbdc8](https://github.com/smarter-sh/smarter/commit/3ebbdc88a1ecb3c304497d272fcd37e3ec507d99))
- allow overrides to DEFAULT_FILE_STORAGE in order to avoid using AWS S3 when aws is not configured ([7b3704b](https://github.com/smarter-sh/smarter/commit/7b3704b2af5e603e1b875666c2f7dc72a0eb7b13))
- ensure that we always know which settings module is being loaded ([a81ca2e](https://github.com/smarter-sh/smarter/commit/a81ca2e306c67c5356a67c3b76ed6662a62ba546))
- expose unencrypted sql connection password when in debug mode ([e873c62](https://github.com/smarter-sh/smarter/commit/e873c623261af9b2a317cb0cba145b733f38aa5e))
- setup a fixed media folder /home/smarter_user/data/media ([428402c](https://github.com/smarter-sh/smarter/commit/428402c3dcf41a7e78b2dc59cf6d08c5b2db9659))
- setup a fixed media folder /home/smarter_user/data/media ([b0463e0](https://github.com/smarter-sh/smarter/commit/b0463e05a45452938840b4a6366ef4c3beb93cd0))
- STORAGES should only use S3 if aws is configured ([031ca77](https://github.com/smarter-sh/smarter/commit/031ca77c18feacdb6df8558d7b4be318e4843406))
- STORAGES should only use S3 if aws is configured ([1ff8b8e](https://github.com/smarter-sh/smarter/commit/1ff8b8e31252ec7a8b7149dc7f27e38eca3ba5e5))
- we should only raise_error_on_disabled() if we've actually configure aws ([78b2eb5](https://github.com/smarter-sh/smarter/commit/78b2eb5b26df5decc2b0fcf2e88a1069bfe2fa41))

## [0.13.25](https://github.com/smarter-sh/smarter/compare/v0.13.24...v0.13.25) (2025-11-01)

### Bug Fixes

- remove platform argument bc specifying amd64 precludes use of aws graviton instance types ([84b2ff5](https://github.com/smarter-sh/smarter/commit/84b2ff5da7e54a6e4ea2d76bbf0d5f6ce28ad9d6))
- setup multi-architecture builds for both AMD64 and ARM64 ([8142653](https://github.com/smarter-sh/smarter/commit/8142653c480a610befa1e997b469d9d94771dd38))

## [0.13.24](https://github.com/smarter-sh/smarter/compare/v0.13.23...v0.13.24) (2025-10-14)

### Bug Fixes

- 500 error on incorrect api key ([ff6e135](https://github.com/smarter-sh/smarter/commit/ff6e13580997ed010e9f8e3110becac11757bd2c))

## [0.13.23](https://github.com/smarter-sh/smarter/compare/v0.13.22...v0.13.23) (2025-10-14)

### Bug Fixes

- incorrect http error response on incorrect or malformed api key ([83e61a5](https://github.com/smarter-sh/smarter/commit/83e61a57e60dc9f2dc6b6101e779869d3223ccf7))

## [0.13.22](https://github.com/smarter-sh/smarter/compare/v0.13.21...v0.13.22) (2025-10-14)

### Bug Fixes

- weak logic in request.user.is_authenticated evaluation ([9b7b9c8](https://github.com/smarter-sh/smarter/commit/9b7b9c84234d68274ef227a1745571b8e6ecc0ff))

## [0.13.21](https://github.com/smarter-sh/smarter/compare/v0.13.20...v0.13.21) (2025-10-14)

### Bug Fixes

- request.user Nonetype ([797fa27](https://github.com/smarter-sh/smarter/commit/797fa27b72793cecf366fb2e7a22f996e1d3514f))

## [0.13.20](https://github.com/smarter-sh/smarter/compare/v0.13.19...v0.13.20) (2025-10-14)

### Bug Fixes

- refactor project root modules \* celery, urls, hosts ([600e6ab](https://github.com/smarter-sh/smarter/commit/600e6ab99b3efdf5281b7556c52c14bd544fc536))

## [0.13.19](https://github.com/smarter-sh/smarter/compare/v0.13.18...v0.13.19) (2025-10-14)

### Bug Fixes

- base requirements version bumps ([700501f](https://github.com/smarter-sh/smarter/commit/700501f1f7de1bf9259b5e910d8717d65b9250e1))
- broken site logo link ([edf4d6a](https://github.com/smarter-sh/smarter/commit/edf4d6a4c4f12f5549b6564406bbb737f8007660))
- disallow SSO creating new accounts ([4a469b1](https://github.com/smarter-sh/smarter/commit/4a469b1fce9d78d67e1d9edcdcf11d47789a4795))
- refactor for multiple user_profile records per user ([a79c245](https://github.com/smarter-sh/smarter/commit/a79c2454f74ccfc049f962dc20f64ae06e061f7a))
- setup api domain and api receivers ([c4bb723](https://github.com/smarter-sh/smarter/commit/c4bb7232ef653d541509ee749d50fc78cd6aca2e))
- setup api domain and api receivers ([93b5b70](https://github.com/smarter-sh/smarter/commit/93b5b7093d89a27ddcd512d194b78f900f65e357))
- setup api domain and api receivers ([d49fcc3](https://github.com/smarter-sh/smarter/commit/d49fcc3531245d5b1073f41f78df11f5c94e995f))
- setup api domain and api receivers ([38e8a20](https://github.com/smarter-sh/smarter/commit/38e8a202c5a4a3311119fa29e4006c742098baff))
- setup api domain and api receivers ([66d6e4d](https://github.com/smarter-sh/smarter/commit/66d6e4d58bc83f9ef7e8b6e26e7b6ca25b6c2b81))
- we now have to consider superuser accounts that are associated with multiple accounts ([380b958](https://github.com/smarter-sh/smarter/commit/380b958ca4e6276b698ab0c7880d3691cf853c31))
- work on CORS headers ([5bdb18f](https://github.com/smarter-sh/smarter/commit/5bdb18f3f60d99c3fdfd44b08b522b994149cfee))

## [0.13.18](https://github.com/smarter-sh/smarter/compare/v0.13.17...v0.13.18) (2025-10-08)

### Bug Fixes

- add ingressClassName ([c9e6daa](https://github.com/smarter-sh/smarter/commit/c9e6daaebea8cd80bf3a10d1bfaabdc5d0802ee8))

## [0.13.17](https://github.com/smarter-sh/smarter/compare/v0.13.16...v0.13.17) (2025-10-08)

### Bug Fixes

- ensure that plugin and chatbot urls are always rfc1034 compliant ([71eb6a1](https://github.com/smarter-sh/smarter/commit/71eb6a1352d2c0ffe570f0ce8a3d189ff55144fb))

## [0.13.16](https://github.com/smarter-sh/smarter/compare/v0.13.15...v0.13.16) (2025-10-08)

### Bug Fixes

- evaluate the http request IP address rather than the internal ip of the pod ([8a68e05](https://github.com/smarter-sh/smarter/commit/8a68e05ffb147d6a15f264402181403199857799))

## [0.13.15](https://github.com/smarter-sh/smarter/compare/v0.13.14...v0.13.15) (2025-10-08)

### Bug Fixes

- ignore http protocol when determining mode() ([28b2b50](https://github.com/smarter-sh/smarter/commit/28b2b5073247075d569d34912f01e8e1d57d7ba5))

## [0.13.14](https://github.com/smarter-sh/smarter/compare/v0.13.13...v0.13.14) (2025-10-07)

### Bug Fixes

- favicon url ([6947591](https://github.com/smarter-sh/smarter/commit/6947591fa0414e147d76067ba1e6298269bc8ff0))

## [0.13.13](https://github.com/smarter-sh/smarter/compare/v0.13.12...v0.13.13) (2025-09-28)

### Bug Fixes

- wrap google authentication in try block ([6c07f63](https://github.com/smarter-sh/smarter/commit/6c07f6350e28be3d06c450d713a35cc2c650c60d))

## [0.13.12](https://github.com/smarter-sh/smarter/compare/v0.13.11...v0.13.12) (2025-09-28)

### Bug Fixes

- collect assets after permissions to improve caching ([ce932c8](https://github.com/smarter-sh/smarter/commit/ce932c87f7be9a71b156397db9cf961f8532c5f6))

## [0.13.11](https://github.com/smarter-sh/smarter/compare/v0.13.10...v0.13.11) (2025-09-28)

### Bug Fixes

- AbstractBroker must be able to initialize from a manifest passed as a dict ([b3532a6](https://github.com/smarter-sh/smarter/commit/b3532a6adde3c0743dfba8f32f9ab1481f9210a2))
- add DjangoJSONEncoder to every json.dumps() ([9306237](https://github.com/smarter-sh/smarter/commit/9306237cdcc0445afc77ea8b17a7df85eb97767f))
- get_cached_user_for_user_id() needs to consider that User might not exist ([3152910](https://github.com/smarter-sh/smarter/commit/3152910c8e3e8849d252a226e2b53ff5c1955bad))
- initialization error in TestSqlPlugin.sql_plugin_model() ([1ad9cbf](https://github.com/smarter-sh/smarter/commit/1ad9cbf8687d6fdd6e66ba4949c5563c5f6a7850))
- key error in StaticPlugin.tool_call_fetch_plugin_response() ([681f8f8](https://github.com/smarter-sh/smarter/commit/681f8f8a0eed43f3d6050779026dfe0b61caa0e0))
- leave the logger level bc WaffleSwitchedLoggerWrapper() manages this now ([66b6d57](https://github.com/smarter-sh/smarter/commit/66b6d57622e8720b688dd35e580a919b2b4123af))
- new docs path inside Docker file system ([cb0bac9](https://github.com/smarter-sh/smarter/commit/cb0bac9a0dc0c39634fd9cc211190717c8242847))
- reverts to using a data/docs/ folder ([770fb61](https://github.com/smarter-sh/smarter/commit/770fb6176cafccaf2d890249fa2e9f945cbeaca5))
- temp patch of PluginPrompt.max_completion_tokens until gpt 4 models are deprecated ([51a5e14](https://github.com/smarter-sh/smarter/commit/51a5e14f46edae83a5a0403e55fe2a779269636f))
- test_camel_to_snake() ([f5d9101](https://github.com/smarter-sh/smarter/commit/f5d9101befbe14379911ba9b44b43e4e4144d3c0))
- tool_call is required ([b4b1fd4](https://github.com/smarter-sh/smarter/commit/b4b1fd495f8aabcb336f5a1403fe3d468bd086a4))

## [0.13.10](https://github.com/smarter-sh/smarter/compare/v0.13.9...v0.13.10) (2025-09-27)

### Bug Fixes

- realign receiver params ([f4e0331](https://github.com/smarter-sh/smarter/commit/f4e03312a367894a1ebb44c34732cb85cab27a50))

## [0.13.9](https://github.com/smarter-sh/smarter/compare/v0.13.8...v0.13.9) (2025-09-27)

### Bug Fixes

- we have to allow 'tool' role messages to pass to openai on thread history. otherwise we get a 400 response ([2ee2444](https://github.com/smarter-sh/smarter/commit/2ee24448aea1727ece585fadb57b40e5e1baff72))

## [0.13.8](https://github.com/smarter-sh/smarter/compare/v0.13.7...v0.13.8) (2025-09-26)

### Bug Fixes

- should be cloning https://github.com/QueriumCorp/smarter-demo ([d9bd0a9](https://github.com/smarter-sh/smarter/commit/d9bd0a9805f1f7700b87a10cf6e73de9b19f6f74))
- should be cloning https://github.com/QueriumCorp/smarter-demo ([2944098](https://github.com/smarter-sh/smarter/commit/29440980ed7e21d0b991cedbbdae1caef4b0f8e1))
- sql syntax error ([c4b6dfe](https://github.com/smarter-sh/smarter/commit/c4b6dfe0e72fe224b897224b756f8a289cce761d))

## [0.13.7](https://github.com/smarter-sh/smarter/compare/v0.13.6...v0.13.7) (2025-09-26)

### Bug Fixes

- ensure that chatbot name is rfc1034_compliant_str ([a1f486a](https://github.com/smarter-sh/smarter/commit/a1f486a84f2ebd27109ab1c63ccdc295475ba923))

## [0.13.6](https://github.com/smarter-sh/smarter/compare/v0.13.5...v0.13.6) (2025-09-26)

### Bug Fixes

- logo and favicon ([8a5194b](https://github.com/smarter-sh/smarter/commit/8a5194b5f335f106bd37bc119c9943e67544aa93))

## [0.13.5](https://github.com/smarter-sh/smarter/compare/v0.13.4...v0.13.5) (2025-09-26)

### Bug Fixes

- release.config.js @semantic-release/git assets list needs **version**.py and helm/charts/smarter/Chart.yaml ([cee493a](https://github.com/smarter-sh/smarter/commit/cee493ae6f408ed510cbec94663846226c847de0))

## [0.13.4](https://github.com/smarter-sh/smarter/compare/v0.13.3...v0.13.4) (2025-09-26)

### Bug Fixes

- return_data_keys() should only return staticData key value. Providers should send signals for the complete tool_call lifecycle ([7611f35](https://github.com/smarter-sh/smarter/commit/7611f356edd362d9614ae270527a4e9b84d5c738))

## [0.13.3](https://github.com/smarter-sh/smarter/compare/v0.13.2...v0.13.3) (2025-09-20)

### Bug Fixes

- prepare to open source ([2f814f6](https://github.com/smarter-sh/smarter/commit/2f814f626974723fde916792a9ce778bbefcbc16))

## [0.13.2](https://github.com/smarter-sh/smarter/compare/v0.13.1...v0.13.2) (2025-09-19)

### Bug Fixes

- do not raise exception on missing UserProfile since this happens during bootstrap on fresh installs ([d5946ee](https://github.com/smarter-sh/smarter/commit/d5946eed7b3a484a51820b29d3d28525fff67bc3))
- downgrade default model to gpt-4-turbo ([e7c0a0c](https://github.com/smarter-sh/smarter/commit/e7c0a0c7d462f7990ddfa745e539c56cb49cb568))
- downgrade to gpt-4-turbo ([29f5483](https://github.com/smarter-sh/smarter/commit/29f5483d746cc22cb3f3f86009270038d7fe20fe))
- ensure that db is initialized and that waffle table exists ([c71dddc](https://github.com/smarter-sh/smarter/commit/c71dddccfeefce2fa5d4e1cbd275746af5b1cd5c))
- ensure that name is snake_case ([8a43478](https://github.com/smarter-sh/smarter/commit/8a4347842f2fb900cf197925597495df5b09dd63))
- ensure that only smarter_user has permissions ([b2c612d](https://github.com/smarter-sh/smarter/commit/b2c612d0b2fcbfc073fb326d1f5d6d6825cdf0bf))
- further restrict permissions, and ignore any non-build files ([c0356cc](https://github.com/smarter-sh/smarter/commit/c0356ccadbe1eca7e56dcd96e47849104544a7a7))
- ignore anything that is not explicitly needed inside the container. ([38c5818](https://github.com/smarter-sh/smarter/commit/38c5818fda7872dde91d33929a189ff71b3868db))
- IndexError: list index out of range error ([f309963](https://github.com/smarter-sh/smarter/commit/f309963cc1a7c1e2bc32ac551b11615e8a3e2cbb))
- setup GOOGLE_SERVICE_ACCOUNT_B64 in .env ([d43f149](https://github.com/smarter-sh/smarter/commit/d43f149270d793de73bee6f050950672334d8578))
- switch to importlib.metadata import distributions() ([4c68753](https://github.com/smarter-sh/smarter/commit/4c68753d306c3adac5ef77f9baa75153c8cc9c29))
- syntax error in docker-init ([ca7060d](https://github.com/smarter-sh/smarter/commit/ca7060d6b68f69fb331f7a96a0c4cbd3c8bdab5f))
- tool_call_fetch_plugin_response() needs to fetch from staticData key ([0b8f90e](https://github.com/smarter-sh/smarter/commit/0b8f90e2a9d9351427157d6c07055b8955db3aea))
- uniformly update all occurrences of version ([a60fa43](https://github.com/smarter-sh/smarter/commit/a60fa431108984d705d8c19d957c2747904453d2))

## [0.13.1](https://github.com/smarter-sh/smarter/compare/v0.13.0...v0.13.1) (2025-08-26)

### Bug Fixes

- broken yaml manifest style on drill-down pages ([364238e](https://github.com/smarter-sh/smarter/commit/364238e08be7beba010a7208828ae890b2900d87))
- log apply ([f7c8355](https://github.com/smarter-sh/smarter/commit/f7c8355496ff4be2f0641681320d42c18910b550))
- logging switch logic ([6fd93ab](https://github.com/smarter-sh/smarter/commit/6fd93abb1e5963ebb0eb24369008b83f5733c5c7))
- plugin apply update manifest initialization bug ([86c5061](https://github.com/smarter-sh/smarter/commit/86c5061c08306212108dc533e39e4d430cf234b0))

## [0.13.0](https://github.com/smarter-sh/smarter/compare/v0.12.0...v0.13.0) (2025-08-25)

### Bug Fixes

- authenticate if not already done, and we find an Authentication token in the header ([a84f0f5](https://github.com/smarter-sh/smarter/commit/a84f0f50e20ce1a885b35b74a77725473ce517b8))
- cache authenticate_credentials() ([f1a2eb4](https://github.com/smarter-sh/smarter/commit/f1a2eb4c4df06ef5fc61e2bb2d78058c6dbccb93))
- cannot assume that request objects always have a META attribute ([452ebab](https://github.com/smarter-sh/smarter/commit/452ebaba2f5fad9f4545a21b2b6f66bcb027c6ae))
- cannot include tool responses in 1st iteration ([9c5b828](https://github.com/smarter-sh/smarter/commit/9c5b828e662ec1345deb914a84e8b0d1e1e1c603))
- container resource memory settings ([f7d300a](https://github.com/smarter-sh/smarter/commit/f7d300a35932c586b55c0b583c9534ff77cc7531))
- dns verification should be based on cascading hosted zones ([0de5ddf](https://github.com/smarter-sh/smarter/commit/0de5ddfad7d4a7bd326f85b3e65d00fb6444542b))
- environment NS records belong in platform.domain.com and api.domain.com ([f26977c](https://github.com/smarter-sh/smarter/commit/f26977c0c3da881e8f2cdedb32b05b0064be2e7f))
- is Kind is missing then say so ([8d38a78](https://github.com/smarter-sh/smarter/commit/8d38a78ad710af1a33e9327856617f133695db61))
- recast DRF Request as HttpRequest ([a3f39ac](https://github.com/smarter-sh/smarter/commit/a3f39ac5f922d97129f073b9d29f11cc0f111b0e))
- setup cache invalidations and implement for Account, User, UserProfile and related SAM objects ([3fb8de7](https://github.com/smarter-sh/smarter/commit/3fb8de7f2a19a275e8b615e861b1463a33d62fb7))
- should_log() should ensure that log level is >= logging.INFO ([fdda0fc](https://github.com/smarter-sh/smarter/commit/fdda0fc334cfcaa28981aed4f261a69dc7c574ec))
- trouble shoot PromptConfigView initialization ([71c2b37](https://github.com/smarter-sh/smarter/commit/71c2b37af7fadda8a32835ecfce56cfefda25697))
- trouble shoot PromptConfigView initialization ([46104b8](https://github.com/smarter-sh/smarter/commit/46104b8ed3faefc47d990be088a8e666c25f4aff))

### Features

- add /api/v1/providers/ end points ([dba2ad9](https://github.com/smarter-sh/smarter/commit/dba2ad9692eab4c50f09a738389a68ac37261cef))
- add serializers ([60201f7](https://github.com/smarter-sh/smarter/commit/60201f70488827864f0a80afbeb92062617770c1))
- code get_model_for_provider() ([15df290](https://github.com/smarter-sh/smarter/commit/15df2907e5d21ca28125bdf396dd30abf03665db))
- code provider verification ([e2cdb18](https://github.com/smarter-sh/smarter/commit/e2cdb18c7468f90c5ebd2b697ee2b672b0268492))
- code provider verification ([0c3161b](https://github.com/smarter-sh/smarter/commit/0c3161ba1ed82a37d039f82b853c9bc97c345d08))
- create manage.py create_sqldb_connection ([0369ebd](https://github.com/smarter-sh/smarter/commit/0369ebd96f0d7e0acec77e267e849d7c578ff249))
- create manage.py initialize_providers ([110edf3](https://github.com/smarter-sh/smarter/commit/110edf31c8518df2a008d95358d450a5b0b843cc))
- create ProviderModelTypedDict ([1ff8992](https://github.com/smarter-sh/smarter/commit/1ff8992656e0272f1009afb03a0fb90bf04f1ba7))
- create ProviderVerification model and ProviderVerificationTypes ([b52fa08](https://github.com/smarter-sh/smarter/commit/b52fa08fe54015a8e80fc5404b6e2209f0cef9f3))
- create Pydantic model ([308560a](https://github.com/smarter-sh/smarter/commit/308560a53f8b5ac342968e86a8f2fef4eb73520d))
- generalize instantiation of Plugin classes based on manifest type ([3a77e2b](https://github.com/smarter-sh/smarter/commit/3a77e2bd25e24010e70d67706ac61970ba82e155))
- register admin models ([77ef5d3](https://github.com/smarter-sh/smarter/commit/77ef5d3504be2bb582b8605417f3d56824c0c3c9))
- scaffold provider app ([cb8975b](https://github.com/smarter-sh/smarter/commit/cb8975b53f7e1008cc516467d4f40d4d8929de15))
- scaffold provider verifications ([036da3d](https://github.com/smarter-sh/smarter/commit/036da3dd56e57aada21972920804153f78e835ff))
- setup Broker base classes for Connection and Plugin ([601bc99](https://github.com/smarter-sh/smarter/commit/601bc99b046072d4e3b4616c8c9e29032c28b5b9))
