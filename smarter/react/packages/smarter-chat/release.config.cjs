/**
 * semantic-release: versions, the CHANGELOG.md and the GitHub releases of @smarter.sh/ui-chat, from
 * conventional commits. The same configuration as https://github.com/smarter-sh/smarter's, run by
 * .github/workflows/pushMain.yml. alpha and beta are prerelease branches.
 *
 * @semantic-release/npm writes the new version to package.json. It does not publish to npm
 * (npmPublish: false): the GitHub release that it creates triggers .github/workflows/release.yml,
 * which builds, checks and publishes the package with npm's trusted publishing.
 */
module.exports = {
  branches: ["main", "next", { name: "beta", prerelease: true }, { name: "alpha", prerelease: true }],
  dryRun: false,
  plugins: [
    [
      "@semantic-release/commit-analyzer",
      {
        preset: "conventionalcommits",
        releaseRules: [
          { type: "docs", release: false },
          { type: "test", release: false },
          { type: "style", release: false },
          { type: "refactor", release: false },
        ],
        parserOpts: {
          noteKeywords: ["BREAKING CHANGE", "BREAKING CHANGES"],
        },
      },
    ],
    [
      "@semantic-release/release-notes-generator",
      {
        preset: "conventionalcommits",
        presetConfig: {
          types: [
            { type: "feat", section: "Features", hidden: false },
            { type: "fix", section: "Bug Fixes", hidden: false },
            { type: "refactor", section: "Refactoring", hidden: false },
            { type: "perf", section: "Performance", hidden: false },
          ],
        },
      },
    ],
    [
      "@semantic-release/changelog",
      {
        changelogFile: "CHANGELOG.md",
        changelogTitle: `# Change Log\n\nAll notable changes to this project will be documented in this file.\n\nThe format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).\n\n`,
      },
    ],
    ["@semantic-release/npm", { npmPublish: false }],
    "@semantic-release/github",
    [
      "@semantic-release/git",
      {
        assets: ["CHANGELOG.md", "package.json"],
        // No "[skip ci]": GitHub skips every push workflow when the pushed head commit's message has it,
        // so a branch fast-forwarded to a release commit, e.g. main to alpha after `git merge alpha`,
        // would never be released. Without it, the release commit's own push runs pushMain.yml again,
        // which skips its own branch's release commit: a release that failed after pushing its
        // commit would otherwise be made, and its commit pushed, again and again.
        message: "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}",
      },
    ],
  ],
};
