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

            // Make a shallow copy (so we don't touch the frozen original)
            const cleanCommit = { ...commit };

            // Helper to normalize a date field to ISO string, only if string/number
            const normalizeDate = (d) => {
              try {
                if (!d) return new Date().toISOString();
                if (typeof d === "string" || typeof d === "number") {
                  const dateObj = new Date(d);
                  return isNaN(dateObj.getTime())
                    ? new Date().toISOString()
                    : dateObj.toISOString();
                }
                // If already a Date or Proxy, just return as is
                return d;
              } catch {
                return new Date().toISOString();
              }
            };

            if (cleanCommit.date)
              cleanCommit.date = normalizeDate(cleanCommit.date);
            if (cleanCommit.committerDate)
              cleanCommit.committerDate = normalizeDate(
                cleanCommit.committerDate,
              );
            if (cleanCommit.committer && cleanCommit.committer.date)
              cleanCommit.committer.date = normalizeDate(
                cleanCommit.committer.date,
              );

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
