---
name: smarter-extension-registry
description: Use when a Smarter Extension (a smarter-extension-<slug> repository such as smarter-extension-weather, calculator or date-calculator) has a new release that must be published to smarter-sh/extensions-registry, e.g. "I just pushed a fix to smarter-extension-weather, update the registry", or when adding an extension or publisher to the registry. Covers how semantic-release cuts the extension's GitHub release, the registry entry file extensions/<slug>/<version>.yaml, the script that writes and validates it, and what happens after the merge. Not for changing the platform's registry client (smarter.apps.llmtool.extension.registry).
---

# Publishing a Smarter Extension release to the registry

Platforms find extensions, and updates to the ones they have installed, through the signed index
that `smarter-sh/extensions-registry` publishes. Releasing an extension doesn't change the index.
A release reaches platforms only when its **registry entry** is merged to the registry's `main`.

The local checkouts are siblings of this repository: `../extensions-registry` and
`../smarter-extension-<slug>`.

## 1. The extension's release (already automatic)

Each extension repository runs semantic-release on every push to `main`
(`release.config.js`, `.github/workflows/release.yml`):

- `fix:` releases a patch, `feat:` a minor version, `BREAKING CHANGE` a major one. `docs`, `test`,
  `style`, `refactor` and `ci` release nothing.
- It sets the version in `pyproject.toml`, updates `CHANGELOG.md`, commits them as
  `chore(release): <version> [skip ci]`, tags `v<version>`, and creates the GitHub release with
  `<slug>-<version>.zip` and `<slug>-<version>.zip.sha256` attached.

So after the user pushes a fix, check that the release exists before writing anything. If no
`v<version>` tag appeared, the commit type released nothing, or the workflow failed. Say which,
and don't write an entry. The user's local checkout will be one commit behind (the release
commit). Tell them to pull.

## 2. Write the entry

```bash
# from this repository's root
skills/smarter-extension-registry/scripts/registry-entry.sh ../smarter-extension-weather          # latest v* tag
skills/smarter-extension-registry/scripts/registry-entry.sh ../smarter-extension-weather 0.2.1    # a given version
```

The script reads the slug from `[tool.smarter]` in the extension's `pyproject.toml` and the
repository URL from its `origin`. It downloads the release's archive, checks it against the
attached `.sha256`, and writes `../extensions-registry/extensions/<slug>/<version>.yaml`:

```yaml
slug: weather
version: 0.2.1
publisher: smarter-sh
archive_url: https://github.com/smarter-sh/smarter-extension-weather/releases/download/v0.2.1/weather-0.2.1.zip
sha256: <the archive's hex sha256>
```

Then it runs the registry's `scripts/validate.py --all`. That's the check CI runs on a pull
request, plus every older entry. It needs PyYAML (`../extensions-registry/requirements.txt`).
It refuses to overwrite an existing entry. **A released version is never changed.** To fix one,
release another.

`gh` may not be authenticated. The script uses only public download URLs, so it doesn't need it.

## 3. Hand over the git commands

Never run them (see `smarter-git-commits`). Print the commands for the user, in
`../extensions-registry`:

```bash
git add extensions/<slug>/<version>.yaml
git commit -m "feat: publish <slug> <version>" -m "<one line on what the release changes>"
git push
```

The registry README asks for a pull request, which runs `validate.yml`. The Smarter team's own
entries have gone straight to `main`. Mention both, and let the user choose. Several extensions
released together go in one commit (`feat: publish weather and calculator 0.2.0`).

## 4. After the merge

`publish.yml` validates every entry, builds `index.json`, signs it with the
`REGISTRY_SIGNING_KEY` secret, and deploys it to GitHub Pages. Platforms cache the index for an
hour (`smarter.apps.llmtool.extension.registry`), and a daily Celery beat task,
`smarter.apps.llmtool.tasks.check_extension_updates`, records which installed extensions have
updates. Administrators are offered the update
within a day. Nothing in this repository changes.

## Other registry changes

- **A new extension** needs only its first entry. Its slug then belongs to that publisher.
- **A new publisher** adds itself to `publishers.yaml` with `badge: community`. Only the Smarter
  team changes badges, keys, `scripts/`, `schema/` and workflows (`.github/CODEOWNERS`).
- **A new official extension** that platforms install by default also goes in the official slugs
  in `smarter/smarter/apps/llmtool/const.py`.
