#!/usr/bin/env bash
# Estimate a Markdown blog post's reading time: prose words outside fenced code
# blocks, at 230 words a minute. Tables and lists count as prose.
#
# usage:
#   skills/blog.smarter.sh-blog-post/scripts/reading-time.sh ~/desktop/blog-<slug>.md
set -euo pipefail

POST="${1:-}"
if [ -z "$POST" ] || [ ! -f "$POST" ]; then
  echo "usage: $0 <post.md>" >&2
  exit 1
fi

awk '
  /^[[:space:]]*```/ { fence = !fence; next }
  fence { code += NF; next }
  {
    line = $0
    gsub(/\]\([^)]*\)/, "]", line)   # link targets are not read
    gsub(/[|#*`>-]/, " ", line)       # Markdown punctuation
    prose += split(line, words, /[[:space:]]+/) - (line ~ /^[[:space:]]/ ? 1 : 0)
  }
  END {
    printf "prose words: %d\ncode words:  %d\nreading time: about %.1f minutes\n", prose, code, prose / 230
  }
' "$POST"
