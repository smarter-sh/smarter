URL Patterns
================

Smarter installations host multiple URL patterns to serve different parts of the application. The Smarter
platform consists of:

+----------------------+-----------------------------------------------------------------------------------------------------------------------------------+
| Host                 | Description                                                                                                                       |
+======================+===================================================================================================================================+
| Web Application      | A web application for Prompt Engineers and system administrators.                                                                 |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------+
| REST API             | A REST Api that supports client software including the command-line interface (CLI), the Smarter Chat React UI component, and     |
|                      | third-party integrations.                                                                                                         |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------+
| Sandbox Endpoints    | REST Api endpoints for sandbox (undeployed) ChatBots/Agents                                                                       |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------+
| Deployed Endpoints   | REST Api endpoints for deployed ChatBot/Agents                                                                                    |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------+

the URL patterns are implements using Django's URL routing system. For more information on the URL configuration, see
`smarter/hosts.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/hosts.py>`.

Example URL Patterns
--------------------

Here are some example URL patterns for a Smarter installation hosted at `platform.example.com`:

+----------------------------------------------------------+--------------------------------------------------+
| URL Pattern                                              | Description                                      |
+==========================================================+==================================================+
| `https://platform.example.com/`                          | Web application                                  |
+----------------------------------------------------------+--------------------------------------------------+
| `https://alpha.platform.example.com/`                    | Web application (cloud development)              |
+----------------------------------------------------------+--------------------------------------------------+
| `https://beta.platform.example.com/`                     | Web application (cloud test)                     |
+----------------------------------------------------------+--------------------------------------------------+
| `https://next.platform.example.com/`                     | Web application (cloud pre-production)           |
+----------------------------------------------------------+--------------------------------------------------+
| `https://platform.example.com/api/v1/`                   | The REST API for client software.                |
+----------------------------------------------------------+--------------------------------------------------+
| `https://platform.example.com/api/v1/chatbots/1/chat/`   | REST API endpoints for sandbox ChatBots/Agents.  |
+----------------------------------------------------------+--------------------------------------------------+
| `https://stackademy-api.3141-5926-5359.api.example.com/` | REST API endpoints for deployed ChatBots/Agents. |
+----------------------------------------------------------+--------------------------------------------------+

ChatBot/Agents are served by the same Django view logic, regardless of whether they are sandbox or deployed. The difference
between the two is as follows:

- **SSL/TLS certificates management**. certificates are independently managed for deployed resources whereas sandbox resources are part of the web platform. Part of the deployment process involves creating a Kubernetes Ingress resource that provisions a TLS certificate for the deployed endpoint. See `smarter/apps/chatbot/k8s/ingress.yaml.tpl <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/chatbot/k8s/ingress.yaml.tpl>` for implementation details.

- **Authentication**. Deployed resources authenticate via API keys, whereas sandbox resources authenticate via the Django session cookie.
