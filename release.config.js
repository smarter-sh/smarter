module.exports = {
  branches: ["main", "beta", "alpha"],
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
        writerOpts: {
          transform: (commit, context) => {
            if (["docs", "test", "style"].includes(commit.type)) {
              return null;
            }

            // Deep clone commit and committer to avoid mutating frozen objects
            const cleanCommit = JSON.parse(JSON.stringify(commit));

            // Replace any broken or invalid date with a numeric timestamp
            const fixDate = (d) => {
              if (!d) return Date.now();
              if (typeof d === "number") return d;
              const n = Number(new Date(d));
              return isNaN(n) ? Date.now() : n;
            };

            cleanCommit.date = fixDate(cleanCommit.date);
            cleanCommit.committerDate = fixDate(cleanCommit.committerDate);
            if (cleanCommit.committer) {
              cleanCommit.committer.date = fixDate(cleanCommit.committer.date);
            }

            return cleanCommit;
          },
        },
      },
    ],
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
          "helm/charts/smarter/Chart.yaml",
          "smarter/smarter/__version__.py",
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
