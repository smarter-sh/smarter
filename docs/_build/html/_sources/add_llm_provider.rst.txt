.. _add_llm_provider:

=========================================
How-To: Adding Anthropic as an LLM Provider
=========================================

This guide outlines the steps required to register Anthropic as a custom LLM provider within the Smarter platform to support **Claude Code**. 

Prerequisites
=============

* Administrative or configuration access to the Smarter platform codebase.
* Anthropic API credentials or internal on-premise gateway routing details provided by the NAPL infrastructure team.

Configuration Steps
===================

To integrate Anthropic into Smarter, you must define the provider configuration schema, supply the necessary endpoint data points, and register the model identifier.

1. Locate the Provider Registry
-------------------------------
Navigate to the provider configuration module in your Smarter codebase where supported LLM vendors are registered (typically under the platform's core configuration or providers package).

2. Define Provider Parameters
-----------------------------
Add Anthropic to the supported provider dictionary using the following required data points:

* **Provider Name:** `anthropic`
* **Base API Endpoint:** The URL pointing to your on-premise Smarter LLM gateway or Anthropic's API endpoint (e.g., ``https://api.anthropic.com/v1`` or your internal proxy URL).
* **Authentication Header:** Configure the system to pass the API key using the standard Anthropic header format:
  * Header Name: ``x-api-key``
  * Header Version: ``anthropic-version: 2023-06-01``
* **Supported Model Identifiers:** Register the target model string for Claude Code:
  * Model ID: ``claude-3-7-sonnet-latest`` (or your organization's deployed Claude variant).

3. Register Provider Schema
---------------------------
Ensure the provider mapping is exposed to the platform authoring interface so developers can select Claude Code when configuring their coding assistant environments.

Verification
============

Once the provider is added and the platform service is restarted, verify the registration by querying the Smarter provider list endpoint or checking the authoring UI dashboard to confirm that Anthropic and Claude Code appear as selectable options.
