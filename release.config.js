module.exports = {
  branches: ["main", "beta", "alpha"],
  dryRun: false,
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/changelog",
      {
        changelogFile: "CHANGELOG.md",
      },
    ],
    "@semantic-release/github",
    [
      "@semantic-release/exec",
      {
        prepareCmd: "python scripts/bump_version.py ${nextRelease.version}",
      },
    ],
    [
      "@semantic-release/git",
      {
        assets: [
          "CHANGELOG.md",
          "smarter/smarter/apps/chatapp/reactapp/package.json",
          "smarter/smarter/apps/chatapp/reactapp/package-lock.json",
          "smarter/requirements/**/*",
          "pyproject.toml",
          "Dockerfile",
        ],
        message:
          "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
      },
    ],
  ],
};
