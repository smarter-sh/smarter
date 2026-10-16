#!/usr/bin/env bash
# Call a tool of the Smarter Project MCP server (smarter.apps.mcpserver) and print its text. The
# server is read-only and needs no authentication.
#
# usage:
#   skills/smarter-project-repositories/scripts/smarter-project-mcp.sh <tool> ['<json arguments>']
#
# e.g.
#   smarter-project-mcp.sh search_code '{"query": "SmarterAuthToken", "repository": "smarter-cli"}'
#   smarter-project-mcp.sh read_file '{"repository": "smarter-python", "path": "README.md", "end_line": 40}'
#   smarter-project-mcp.sh get_repository_overview
#
# The tools are get_repository_overview, search_documentation, search_code, read_file and
# list_files. Omit "repository" to search every repository.
#
# The endpoint is SMARTER_PROJECT_MCP_URL, default the local dev server,
# http://localhost:9357/api/v1/mcp/smarter-project/. Set it to a deployed platform's
# https://<platform host>/api/v1/mcp/smarter-project/ in your own environment, not in this repository.
#
# exit status: 0 if the tool ran, 1 if the request or the tool failed.
set -euo pipefail

TOOL="${1:?usage: smarter-project-mcp.sh <tool> ['<json arguments>']}"
ARGUMENTS="${2:-{\}}"
URL="${SMARTER_PROJECT_MCP_URL:-http://localhost:9357/api/v1/mcp/smarter-project/}"

PAYLOAD="$(python3 -I -c '
import json, sys
print(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": sys.argv[1], "arguments": json.loads(sys.argv[2])}}))
' "$TOOL" "$ARGUMENTS")"

curl -sS --max-time 60 "$URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data "$PAYLOAD" |
  python3 -I -c '
import json, sys
response = json.load(sys.stdin)
if "error" in response:
    print("error:", response["error"].get("message"), file=sys.stderr)
    sys.exit(1)
result = response["result"]
print("\n".join(item.get("text", "") for item in result.get("content", [])))
sys.exit(1 if result.get("isError") else 0)
'
