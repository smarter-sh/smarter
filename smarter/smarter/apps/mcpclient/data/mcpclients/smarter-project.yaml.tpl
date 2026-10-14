---
# Every GitHub repository of The Smarter Project, through the Smarter Project MCP server of this
# platform, which indexes the repositories from GitHub every hour: the platform and its
# documentation, https://docs.smarter.sh, the command-line interface, the Python, Node.js and Go
# SDKs, the VS Code extension, the SmarterChat component, the quick start, and the cloud
# infrastructure.
# Documentation: https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html
#
# Its tools take a repository argument, and the search tools search every repository when it is
# omitted. To read one repository only, use one of the smarter-project-github*.yaml.tpl manifests.
#
# This file is a string.Template: add_builtin_mcpclients fills in the scheme and domain of the
# platform that applies it, from smarter_settings.environment_url and
# smarter_settings.environment_platform_domain, e.g. https://alpha.platform.example.com, or
# http://localhost:9357 in local development, so that this MCPClient reads the MCP server of
# its own platform.
#
# The MCP server requires no authentication. Its tools are read-only.
apiVersion: smarter.sh/v1
kind: MCPClient
metadata:
  name: smarter_project
  description: Searches and reads the documentation, https://docs.smarter.sh, and the source code of every GitHub repository of The Smarter Project.
  version: 1.0.0
  tags:
    - smarter
    - documentation
    - github
    - code
  annotations:
    - smarter.sh/mcpclient/documentation: https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html
    - smarter.sh/mcpclient/repository: https://github.com/smarter-sh
spec:
  config:
    transport: http
    endpointUrl: ${environment_platform_scheme}://${environment_platform_domain}/api/v1/mcp/smarter-project/
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
