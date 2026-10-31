The Slack Bot
=============

The Smarter Helm chart can run an optional Slack bot, which answers questions in a Slack workspace
with a deployed :doc:`LLMClient <../../smarter-resources/smarter-llmclient>`. The Smarter Project
uses it to bring ``smarter_developer``, the LLMClient that answers from the
:doc:`Smarter Project MCP Server <../../smarter-platform/smarter-project-mcp-server>`, into its own
Slack workspace, but any deployed LLMClient that doesn't require an api key works.

People talk to the bot in two ways:

- **@mention it in a channel.** It answers in the message's thread, and every later mention in that
  thread continues the same conversation.
- **Send it a direct message.** The messages outside threads are one conversation, and each thread
  is a conversation of its own.

A message that is only ``new``, ``reset``, ``start over`` or ``new conversation`` starts a new
conversation in its thread. :doc:`../../slack` is the guide for the workspace's members, to which
new members can be referred.

How It Works
------------

The bot is the chart's ``slack-bot`` subchart (``helm/charts/slack-bot``), listed in the smarter
chart's ``Chart.yaml`` with the condition ``slackBot.enabled``, which is ``false`` by default. When
it is enabled, the chart adds one Deployment, ``smarter-slack-bot``, and a ConfigMap that holds the
bot's program, ``files/bot.py``.

- **Socket Mode.** The bot opens its own connection to Slack, so nothing connects to it: there is no
  Service, Ingress, DNS record or certificate. It needs only outbound HTTPS, to Slack and to the
  LLMClient.
- **The Smarter Chat api.** For each new Slack thread, the bot starts a chat session with
  ``POST <agentUrl>/config/``, and asks each question with ``POST <agentUrl>/prompt/``, sending the
  thread's questions and answers. The platform runs the LLMClient's whole prompt, tools and
  Guardrails included, and records it in the session, so every conversation appears in the
  LLMClient's chat history and cost accounting like any other. See
  :doc:`../smarter-chat/api-contract`.
- **One replica.** The bot keeps each thread's chat session in memory, for its 500 most recently
  used threads, so a restart starts every conversation again. Two pods would each receive part of a
  thread's messages, so the Deployment runs one replica and is replaced with ``Recreate``.
- **A stock Python image.** The bot needs only the standard library and Slack Bolt, which the
  container installs when it starts (``slackBot.slackBoltVersion``). It runs as a non-root user,
  with a read-only root file system and no Kubernetes service account token, and receives only the
  two Slack tokens.

Every Slack message the bot answers is a prompt, billed by the LLMClient's provider, and anyone in the
workspace can send one. Choose an LLMClient whose model and budget suit that.

Setting It Up
-------------

1. **Create the Slack app** at `api.slack.com/apps <https://api.slack.com/apps>`__, from scratch, in
   your workspace.

   - Under **Socket Mode**, enable Socket Mode and create an app-level token with the
     ``connections:write`` scope. This is the app token, ``xapp-...``.
   - Under **OAuth & Permissions**, add the bot token scopes ``app_mentions:read``, ``chat:write`` and
     ``im:history``.
   - Under **Event Subscriptions**, subscribe to the bot events ``app_mention`` and ``message.im``.
   - Under **App Home**, enable the Messages tab, so that people can send the bot direct messages.
   - Install the app to the workspace. This gives the bot token, ``xoxb-...``.

2. **Choose the LLMClient.** Deploy it, and check that its own host answers without an api key:

   .. code-block:: console

      curl -X POST -H "Content-Type: application/json" -d '{}' \
        https://smarter-developer.<account-number>.api.<root-domain>/config/

3. **Configure the repository.** In its GitHub settings, under **Secrets and variables** then
   **Actions**, add:

   - the repository secrets ``SLACK_BOT_TOKEN`` and ``SLACK_APP_TOKEN``;
   - the repository secret ``SLACK_BOT_AGENT_URL``, the LLMClient's url.

   The deploy workflow passes them to the prod deployment only, because two bots with the same
   Slack app would each receive part of the messages. It passes the tokens to the chart as
   ``env.SMARTER_SLACK_BOT_TOKEN`` and ``env.SMARTER_SLACK_APP_TOKEN``, which are stored in the
   platform's environment Secret, and the url as ``slackBot.agentUrl``. It sets
   ``slackBot.enabled`` to ``true`` only when all three are set.

4. **Deploy**, and invite the bot to a channel (``/invite @<bot name>``).

To install the chart by hand instead, set the same values:

.. code-block:: console

   helm upgrade --install smarter ./helm/charts/smarter/ \
     --set slackBot.enabled=true \
     --set slackBot.agentUrl=https://smarter-developer.<account-number>.api.<root-domain>/ \
     --set env.SMARTER_SLACK_BOT_TOKEN=xoxb-... \
     --set env.SMARTER_SLACK_APP_TOKEN=xapp-... \
     ...

Values
------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Value
     - Meaning
   * - ``slackBot.enabled``
     - ``false`` by default. ``true`` deploys the bot.
   * - ``slackBot.agentUrl``
     - Required when enabled. The deployed LLMClient's url.
   * - ``slackBot.timeout``
     - Seconds to wait for an answer, 240 by default. An answer with several tool calls takes 10 to
       20 seconds.
   * - ``slackBot.slackBoltVersion``
     - The Slack Bolt release that the container installs.
   * - ``slackBot.image``
     - The Python image, ``python:3.12-slim`` by default.
   * - ``slackBot.resources``
     - The container's requests and limits: 50m CPU and 128Mi of memory, up to 256Mi.
   * - ``env.SMARTER_SLACK_BOT_TOKEN``, ``env.SMARTER_SLACK_APP_TOKEN``
     - The Slack app's bot and app-level tokens.

Operating It
------------

Read the bot's log, which records every question it could not answer:

.. code-block:: console

   kubectl logs -n <namespace> deploy/smarter-slack-bot

When the LLMClient doesn't answer, the bot apologizes in Slack and logs the error. When Slack's
connection drops, Slack Bolt reconnects by itself. A pod that is replaced, for example with its
node, forgets its conversations: people continue by mentioning the bot again.

The bot's tests (``helm/charts/slack-bot/tests``) need only the standard library, and run in the
Tests workflow's ``slack-bot`` job:

.. code-block:: console

   python -m unittest discover -s helm/charts/slack-bot/tests
