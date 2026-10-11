#!/usr/bin/env bash
# Download a published blog.smarter.sh post and save its article body as
# Markdown-like text, so the post can be read in full. WebFetch returns only a
# summary of a page, which loses the voice that the post is a guide to.
#
# Only https://blog.smarter.sh/ urls are accepted.
#
# usage, from the repository root:
#   skills/blog.smarter.sh-blog-post/scripts/fetch-post.sh <post url> <output .md>
set -euo pipefail

URL="${1:-}"
OUT="${2:-}"
if [ -z "$URL" ] || [ -z "$OUT" ]; then
  echo "usage: $0 https://blog.smarter.sh/<yyyy>/<mm>/<dd>/<slug>/ <output.md>" >&2
  exit 1
fi
case "$URL" in
  https://blog.smarter.sh/*) ;;
  *)
    echo "only https://blog.smarter.sh/ urls are accepted" >&2
    exit 1
    ;;
esac

HTML="$(mktemp)"
trap 'rm -f "$HTML"' EXIT
curl -fsSL "$URL" -o "$HTML"

python3 -I - "$HTML" "$OUT" <<'PY'
import html
import re
import sys

source, target = sys.argv[1], sys.argv[2]
with open(source, encoding="utf-8") as f:
    page = f.read()

match = re.search(r"<article.*?</article>", page, re.S)
body = match.group(0) if match else page
body = re.sub(r"<(script|style)\b.*?</\1>", "", body, flags=re.S)
body = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: "\n```\n" + re.sub(r"<[^>]+>", "", m.group(1)) + "\n```\n", body, flags=re.S)
body = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", body)
body = re.sub(r"<li[^>]*>", "\n- ", body)
body = re.sub(r"</t[dh]>", " | ", body)
body = re.sub(r"<tr[^>]*>", "\n| ", body)
body = re.sub(r"<(p|br|table|blockquote)[^>]*>", "\n\n", body)
body = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", body, flags=re.S)
body = re.sub(r"<[^>]+>", "", body)
body = html.unescape(body)
body = re.sub(r"[ \t]+\n", "\n", body)
body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"

with open(target, "w", encoding="utf-8") as f:
    f.write(body)
print(f"{target}: {len(body.split())} words")
PY
