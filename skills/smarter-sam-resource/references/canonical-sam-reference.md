# Canonical SAM Reference: every file a new kind touches

The **CustomDomain** kind (llmclient app, release 0.18) was the most recent kind
added end to end. Use its file for each step as the model. **Guardrail** is the
model for a kind that has its own app. Paths are relative to `smarter/smarter/`
unless they start with `docs/`.

## 1. Kind registration

| Step              | File                                                    | CustomDomain example                                                                      |
| ----------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Journal thing     | `lib/journal/enum.py`                                   | `SmarterJournalThings.CUSTOM_DOMAIN = "CustomDomain"` and its `choices()` tuple           |
| Journal migration | `lib/journal/migrations/`                               | `0007_alter_samjournal_thing_custom_domain.py`                                            |
| SAM kind          | `apps/api/v1/manifests/enum.py`                         | `SAMKinds.CUSTOM_DOMAIN = CUSTOM_DOMAIN_MANIFEST_KIND`, documented in the class docstring |
| Kind constant     | `apps/llmclient/manifest/models/custom_domain/const.py` | `MANIFEST_KIND = "CustomDomain"`                                                          |

## 2. Manifest (Pydantic)

`apps/llmclient/manifest/models/custom_domain/`:

- `metadata.py`: `SAMCustomDomainMetadata`, the common metadata (name,
  description, version, tags, annotations).
- `spec.py`: `SAMCustomDomainSpec` with a nested `SAMCustomDomainSpecConfig`.
  Field validators reject bad input, such as an invalid domain name.
- `status.py`: `SAMCustomDomainStatus`, read-only, used by `describe`.
- `model.py`: `SAMCustomDomain(AbstractSAMBase)`, which ties them together.

## 3. Broker

| Step              | File                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------- |
| Broker            | `apps/llmclient/manifest/brokers/custom_domain.py`: `SAMCustomDomainBroker(AbstractBroker)` |
| CLI registration  | `apps/api/v1/cli/brokers.py`: `SAMKinds.CUSTOM_DOMAIN.value: SAMCustomDomainBroker`         |
| User dependencies | `apps/account/manifest/brokers/user.py`: `(SAMKinds.CUSTOM_DOMAIN, LLMClientCustomDomain)`  |

## 4. Django model and serializer

| Step          | File                                                                                                                                                                  |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Model         | `apps/llmclient/models/llmclient_custom_domain.py`: `LLMClientCustomDomain(MetaDataWithOwnershipModel)`, with `unique_together` on `user_profile` and `name`          |
| Status fields | `verification_status` (`VerificationStatusChoices`: not verified, verifying, verified, failed), the verification date, and `set_verification_status()`                |
| Migration     | `apps/llmclient/migrations/0006_llmclientcustomdomain_ownership.py`: added ownership to a released app, so it's a new migration with a data migration for legacy rows |
| Serializer    | `apps/llmclient/serializers.py`: `LLMClientCustomDomainListSerializer`, a `MetaDataWithOwnershipModelSerializer` with `Meta.kind`                                     |

## 5. Web console

| Step                               | File                                                                                                             |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Detail view (manifest editor page) | `apps/llmclient/views/detailview.py`                                                                             |
| List page view                     | `apps/llmclient/views/listview/view.py`                                                                          |
| List, clone, rename, delete api    | `apps/llmclient/views/listview/api.py`                                                                           |
| URL names                          | `apps/llmclient/urls.py`: `LLMClientReverseNames.custom_domain_*`                                                |
| Template tag                       | `apps/llmclient/templatetags/react_custom_domain_list.py`                                                        |
| Template                           | `templates/react/custom-domain-list.html`                                                                        |
| React package                      | `smarter/react/packages/smarter-custom-domain-list/`                                                             |
| Sidebar                            | `apps/dashboard/context_processors.py` (`"custom_domains": reverse(...)`) and `templates/dashboard/sidebar.html` |
| Dashboard count                    | `apps/dashboard/views/views/api/my_resources.py`: `get_custom_domains()`                                         |

## 6. Docs app (JSON schema and example manifest served by Django)

| Step                  | File                                                                                           |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| JSON schema view      | `apps/docs/views/json_schema.py`: `DocsJsonSchemaCustomDomainView`                             |
| Example manifest view | `apps/docs/views/manifest.py`: `DocsExampleManifestCustomDomainView`                           |
| Routes                | `apps/docs/urls.py`: `json_schema_path(SAMKinds.CUSTOM_DOMAIN.value)` and `manifest_path(...)` |

## 7. Built-in data

| Step           | File                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| Manifest       | `apps/llmclient/data/custom-domains/example-com.yaml`                                                   |
| Loader command | `apps/llmclient/management/commands/add_builtin_custom_domains.py`                                      |
| Platform setup | `apps/account/management/commands/initialize_platform.py`: `call_command("add_builtin_custom_domains")` |

## 8. Sphinx

| Step                       | File                                                      |
| -------------------------- | --------------------------------------------------------- |
| Resource page              | `docs/source/smarter-resources/smarter-custom-domain.rst` |
| Toctree and overview prose | `docs/source/smarter-resources.rst`                       |

## 9. Tests

| Step              | File                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------- |
| Broker            | `apps/llmclient/manifest/brokers/tests/test_custom_domain_broker.py` plus `data/custom_domain.yaml` |
| Views             | `apps/llmclient/tests/test_custom_domain_views.py`                                                  |
| Verification task | `apps/llmclient/tests/test_verify_custom_domain.py`                                                 |
| Built-in loader   | `apps/llmclient/tests/test_add_builtin_custom_domains.py`                                           |
| React             | `smarter/react/packages/smarter-custom-domain-list/src/**/*.test.tsx` and stories                   |
