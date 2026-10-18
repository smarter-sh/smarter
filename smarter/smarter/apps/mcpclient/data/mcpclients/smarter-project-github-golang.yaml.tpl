---
# The Smarter Project's GitHub repository smarter-sh/smarter-golang, through the Smarter Project MCP server
# of this platform, which indexes the repository from GitHub every hour.
# Repository: https://github.com/smarter-sh/smarter-golang
# Documentation: https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html
#
# The MCP server serves one endpoint per repository, so this client reads only smarter-sh/smarter-golang.
# The smarter_sdk_guide LLMClient uses several such clients, one per repository:
# see the other smarter-project-github*.yaml.tpl manifests, and smarter-project.yaml.tpl, which
# reads all of them.
#
# This file is a string.Template: add_example_mcpclients fills in the scheme and domain of the
# platform that applies it, from smarter_settings.environment_url and
# smarter_settings.environment_platform_domain, e.g. https://alpha.platform.example.com, or
# http://localhost:9357 in local development, so that this MCPClient reads the MCP server of
# its own platform.
#
# The MCP server requires no authentication. Its tools are read-only.
apiVersion: smarter.sh/v1
kind: MCPClient
metadata:
  name: smarter_project_github_golang
  description: Searches and reads the documentation and source code of the official Go library for the Smarter platform, in The Smarter Project's GitHub repository smarter-sh/smarter-golang.
  version: 1.0.0
  tags:
    - smarter
    - documentation
    - github
    - code
  annotations:
    - smarter.sh/mcpclient/documentation: https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html
    - smarter.sh/mcpclient/repository: https://github.com/smarter-sh/smarter-golang
spec:
  config:
    transport: http
    endpointUrl: ${environment_platform_scheme}://${environment_platform_domain}/api/v1/mcp/smarter-project/smarter-golang/
    authType: none
    allowedTools:
      - get_repository_overview
      - search_documentation
      - search_code
      - read_file
      - list_files
    includeInstructions: true
    timeout: 30
    cacheTtl: 3600
    isActive: true
    priority: 100
