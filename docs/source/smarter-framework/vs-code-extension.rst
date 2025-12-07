VS Code Extension
===================

Smarter's `Visual Studio Code Extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`__ provides enhanced
support for working with Smarter YAML manifest files, similar to Kubernetes manifests. It includes syntax validation,
semantic checking, and auto-completion for reserved keywords. A Smarter manifest will include the following two keys at the top of the document:

.. code-block:: yaml

  apiVersion: smarter.sh/v1
  kind: Chatbot

Valid manifest 'kind' values: Chatbot, Plugin, Account, SmarterAuthToken, User, Chat, ChatConfig, ChatHistory, ChatPluginUsage, ChatToolCall, SqlConnection, ApiConnection

Features
----------

- **Syntax Validation**: Ensures your YAML files are properly formatted.
- **Semantic Checking**: Validates the content of your YAML manifests against predefined schemas.
- **Auto-Completion**: Provides intelligent suggestions for reserved keywords and properties.
- **Error Highlighting**: Highlights syntax and semantic errors in real-time.
- **Schema Support**: Supports custom schemas for Smarter YAML manifests.

Getting Started
----------------

1. Install the extension from the VS Code Marketplace (or manually if in development).
2. Open a YAML manifest file in VS Code.
3. The extension will automatically validate and provide suggestions.


Configuration
----------------

You can configure the extension by adding the following settings to your settings.json:

.. code-block:: json

  {
    "yaml.schemas": {
      "path/to/your/schema.json": "*.yaml"
    },
    "smarterYaml.rootUrl": "https://platform.smarter.sh"
  }

JSON Schemas
--------------

- https://platform.smarter.sh/api/v1/cli/schema/Chatbot/
- https://platform.smarter.sh/api/v1/cli/schema/Plugin/
- https://platform.smarter.sh/api/v1/cli/schema/Account/
- https://platform.smarter.sh/api/v1/cli/schema/SmarterAuthToken/
- https://platform.smarter.sh/api/v1/cli/schema/User/
- https://platform.smarter.sh/api/v1/cli/schema/Chat/
- https://platform.smarter.sh/api/v1/cli/schema/ChatConfig/
- https://platform.smarter.sh/api/v1/cli/schema/ChatHistory/
- https://platform.smarter.sh/api/v1/cli/schema/ChatPluginUsage/
- https://platform.smarter.sh/api/v1/cli/schema/ChatToolCall/
- https://platform.smarter.sh/api/v1/cli/schema/SqlConnection/
- https://platform.smarter.sh/api/v1/cli/schema/ApiConnection/
