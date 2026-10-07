# Canonical Sphinx References

| Page type                           | Reference                                                     | Notes                                                                                             |
| ----------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Resource page, complete             | `docs/source/smarter-resources/smarter-guardrail.rst`         | Overview, How It Works, The Manifest, topic sections, Security Notes, Technical Reference toctree |
| Resource page, compact              | `docs/source/smarter-resources/smarter-custom-domain.rst`     | The minimum for a new kind                                                                        |
| Section index with overview prose   | `docs/source/smarter-resources.rst`                           | New kinds go in its toctree and are woven into its overview paragraphs with `:doc:` links         |
| Autodoc page                        | `docs/source/smarter-resources/guardrail/models.rst`          | Title, then `.. automodule::` with `:members:`, `:undoc-members:`, and `:show-inheritance:`       |
| Autodoc of Pydantic manifest models | `docs/source/smarter-resources/guardrail/manifest/models.rst` | One `automodule` per `const`, `metadata`, `spec`, `status`, and `model`                           |
| Nested autodoc index                | `docs/source/smarter-resources/guardrail/manifest.rst`        | A titled toctree of sub-pages                                                                     |

## Verification

From the repository root. It doesn't build the docs:

```console
skills/smarter-sphinx-docs/scripts/check-docs.sh docs/source/smarter-resources/smarter-custom-domain.rst
skills/smarter-sphinx-docs/scripts/check-docs.sh            # every page
```
