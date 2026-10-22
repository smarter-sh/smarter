How it Works
===============

LLMTool Plugins are fundamentally more feature rich than traditional :doc:`LLM function tools <how-tools-work>`. An LLMTool Plugin manifest
defines not only what data is available to the LLM, but also the LLM prompt specification itself
(which provider, model, temperature, etc.), and most importantly, the criteria which
the tool should be presented to the LLM.

.. important::

  Imagine a use case in which you have hundreds or
  thousands of tools. It would be impractical (and exceedlingly expensive) to present all of those tools
  to the LLM for every prompt. Instead, LLMTool Plugins allow you to define:

  - **Selector**: CSS-like logic that defines when the tool should be made available to the LLM. That is, when it
    should be included in the prompt as an available tool. Remember that LLM APIs charge by token, and including
    tools in a prompt request increases the token count. Therefore, it behooves one to be judicious about which tools
    are made available to the LLM for any given prompt. A ``search_terms`` selector matches a prompt that contains every
    word of one of its search terms, in any order, ignoring case and plurals. Two waffle switches widen this:
    ``enable_plugin_fuzzy_matching``, on by default, tolerates a typo or two, and ``enable_plugin_thesaurus_matching``,
    on by default, also matches synonyms from the WordNet thesaurus, e.g. ``automobile`` for the search term ``car``.
    Each match sends the ``search_term_matched`` signal, with how it matched. See :doc:`nlp`.
  - **Prompt**: The prompt specification that defines which LLM provider, the model, temperature, and other
    parameters to use when invoking the tool. You can even modify, or completely redefine the system prompt used
    when invoking the tool.
  - **Data**: The structured data that is made available to the LLM when the tool is invoked. This
    if further defined by the Plugin type (static data, SQL, or API). In the example below of a Static Plugin, the first level
    of data keys defines the enumerations list that is presented to the tool. In the example below, the keys translate to: 'platform provider', 'about', and 'links'.

A static LLMTool Plugin manifest like this one is the simplest kind of LLMTool Plugin. We simply "load up"
the structured data defined in the Plugin manifest, and make it available to the LLM

.. literalinclude:: /_example-manifests/plugins/static/example-configuration.yaml
   :caption: Example LLMTool Plugin YAML Configuration

From `plugins/static/example-configuration.yaml <https://github.com/smarter-sh/example-manifests/blob/main/plugins/static/example-configuration.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.


**LLMTool Plugin Manifests**

An LLMClient's manifest declares the tools that it offers LLMs in two ways: by listing
:doc:`Extensions <../../smarter-framework/smarter-extensions>`, Python packages that a platform
administrator installs, in ``spec.extensions``, and by listing LLMTool Plugins, which are based on
any of a.) :doc:`static data <plugin/static>`, b.) :doc:`SQL queries <plugin/sql>`, or c.)
:doc:`external APIs <plugin/api>`, in ``spec.plugins``. See
:doc:`../../smarter-framework/extensibility` for how the two differ.

Here is an example Smarter LLMClient, configured to use both an Extension, ``weather``, and a
LLMTool Plugin, ``example_configuration``. The ``example_configuration`` Plugin is defined separately in the yaml file that follows.

.. code-block:: yaml
    :caption: Example LLMTool Plugin Configuration

    apiVersion: smarter.sh/v1
    kind: LLMClient
    metadata:
      description: "An example llmclient with tool calling and Smarter Plugins."
      name: example
      version: 0.1.0
    spec:
      config:
        prompt:
          defaultModel: gpt-6-luna
          defaultSystemRole: You are a helpful llmclient.
          provider: openai
      extensions:
      - weather
      plugins:
      - example_configuration
