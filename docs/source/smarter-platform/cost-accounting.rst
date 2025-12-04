Cost Accounting
===============

Smarter's asynchronous workers persist detailed cost accounting information for all external service requests and responses.
This information can be used for billing, cost analysis, and budgeting purposes. Specifically, Smarter
tracks the following cost metrics:

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-account-charges.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Account Charges"/>


.. list-table:: Example Record
   :header-rows: 1

   * - Field
     - Value
   * - ID
     - Smarter record identifier. ex 1658
   * - Created at
     - Smarter record create data. eg Nov. 27, 2025, 1:46 a.m.
   * - Updated at
     - Smarter record update date. eg Nov. 27, 2025, 1:46 a.m.
   * - Account
     - The Smarter account number. eg 3141-5926-5359 - Smarter
   * - User
     - The Smarter user identifier. eg mcdaniel
   * - Session key
     - The Smarter session key for the chat session. Use this to aggregate charges for a single chat session (conversation) eg 224a6a9fdc383a48c9e28357dad55c97defcaa2468ba4fb9abfd58d6b775bb16
   * - Provider
     - The LLM Provider. eg OpenAI
   * - Charge type
     - Smarter internal charge category. Values: Prompt Completion, Plugin, Tool
   * - Prompt tokens
     - The number of tokens in the prompt, for external billing purposes. eg 455
   * - Completion tokens
     - The number of tokens in the completion, for external billing purposes. eg 154
   * - Total tokens
     - The total number of tokens, for external billing purposes. eg 609
   * - Model
     - The Provider LLM model used for the request. eg gpt-4o-mini
   * - Reference
     - External provider billing reference. eg fp_b547601dbd

An example of a custom SQL query to aggregate token usage by session for a given month is shown below. Other
Django models associated with cost accounting include: `ChatBotRequests`, `PluginSelectorHistory`, and `Chat`.

.. code-block:: sql

    USE smarter_platform_prod;

    SELECT  session_key,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(total_tokens) as total_tokens
    FROM    account_charge
    WHERE   MONTH(created_at) = 11 AND
            YEAR(created_at) = 2025
    GROUP BY session_key
