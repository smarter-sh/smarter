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

            // Helper to normalize a date field to ISO string
            const normalizeDate = (d) => {
              if (!d) return new Date().toISOString();
              if (typeof d === "string" || typeof d === "number") {
                const dateObj = new Date(d);
                return isNaN(dateObj.getTime())
                  ? new Date().toISOString()
                  : dateObj.toISOString();
              }
              // If already a Date, Proxy, or object, just return a new ISO string now
              return new Date().toISOString();
            };

            cleanCommit.date = normalizeDate(cleanCommit.date);
            cleanCommit.committerDate = normalizeDate(
              cleanCommit.committerDate,
            );
            if (cleanCommit.committer) {
              cleanCommit.committer.date = normalizeDate(
                cleanCommit.committer.date,
              );
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
