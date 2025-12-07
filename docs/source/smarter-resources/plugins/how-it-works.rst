How it Works
===============

SAM Plugins are fundamentally more feature rich than traditional :doc:`LLM function tools <how-tools-work>`. A Smarter Plugin manifest
defines not only what data is available to the LLM, but also the LLM prompt specification itself
(which provider, model, temperature, etc.), and most importantly, the criteria which
the tool should be presented to the LLM.

.. important::

  Imagine a use case in which you have hundreds or
  thousands of tools. It would be impractical (and exceedlingly expensive) to present all of those tools
  to the LLM for every prompt. Instead, Smarter Plugins allow you to define:

  - **Selector**: CSS-like logic that defines when the tool should be made available to the LLM. That is, when it
    should be included in the prompt as an available tool. Remember that LLM APIs charge by token, and including
    tools in a prompt request increases the token count. Therefore, it behooves one to be judicious about which tools
    are made available to the LLM for any given prompt.
  - **Prompt**: The prompt specification that defines which LLM provider, the model, temperature, and other
    parameters to use when invoking the tool. You can even modify, or completely redefine the system prompt used
    when invoking the tool.
  - **Data**: The structured data that is made available to the LLM when the tool is invoked. This
    if further defined by the Plugin type (static data, SQL, or API). In the example below of a Static Plugin, the first level
    of data keys defines the enumerations list that is presented to the tool. In the example below, the keys translate to: 'platform provider', 'about', and 'links'.

A static Smarter Plugin manifest like this one is the simplest of the three kinds of Smarter Plugins. We simply "load up"
the structured data defined in the Plugin manifest, and make it available to the LLM

.. literalinclude:: ../../../../smarter/smarter/apps/plugin/data/sample-plugins/example-configuration.yaml
   :caption: Example Smarter Plugin YAML Configuration


**SAM Plugin Manifests**

Smarter Plugin technology provides two means of declaratively defining tools that can be leveraged
by LLM's for tool calling: via a defined list of built-in functions, and via SAM Plugins that
are based on any of a.) :doc:`static data <plugin/static>`, b.) :doc:`SQL queries <plugin/sql>`, or c.) :doc:`external APIs <plugin/api>`.

Here is an example Smarter Chatbot, configured to use both a function, ``get_current_weather`` and a
Smarter Plugin, ``example_configuration``. The ``example_configuration`` Plugin is defined separately in the yaml file that follows.

.. code-block:: yaml
    :caption: Example Smarter Plugin Configuration

    apiVersion: smarter.sh/v1
    kind: Chatbot
    metadata:
      description: "An example chatbot with tool calling and Smarter Plugins."
      name: example
      version: 0.1.0
    spec:
      config:
        defaultModel: gpt-4o-mini
        defaultSystemRole: You are a helpful chatbot.
        provider: openai
      functions:
      - get_current_weather
      plugins:
      - example_configuration
