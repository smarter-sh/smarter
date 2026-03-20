Getting Started
===============

This section helps you quickly try out the new feature and understand how it works.

Overview
--------

Briefly describe what this feature does and why it is useful.

- What problem does it solve?
- When should you use it?
- How does it fit into the Smarter platform?

Prerequisites
-------------

Before you begin, make sure you have:

- Smarter installed and running
- Access to the CLI or web dashboard
- Any required API keys or external services configured

Installation / Setup
---------------------

Explain how to enable or install the feature.

.. code-block:: console

   # Example command
   smarter enable <feature-name>

Or, if configuration is required:

.. code-block:: yaml

   # Example configuration
   feature:
     enabled: true

Quick Start Example
-------------------

Walk through a minimal working example.

**1. Create a configuration or manifest**

.. code-block:: yaml

   # Example manifest
   apiVersion: smarter.sh/v1
   kind: ExampleFeature
   metadata:
     name: my-example

**2. Apply the configuration**

.. code-block:: console

   smarter apply -f example.yaml

**3. Verify it works**

Explain what the user should see or expect.

- Expected output
- UI behavior
- Logs or status messages

How It Works
------------

Give a simple explanation of what is happening behind the scenes.

- Key components involved
- Data flow (high-level)
- Integration with other Smarter features

Next Steps
----------

Now that you’ve tried the basics, you can:

- Explore advanced configuration options
- Integrate with other resources
- Read the full reference documentation

Troubleshooting
---------------

Common issues and how to fix them:

- Problem: Something doesn’t start
  Solution: Check logs using `smarter logs`

- Problem: Configuration not applied
  Solution: Verify YAML syntax and re-apply

Reference
---------

Link to deeper documentation:

- :doc:`Full Feature Reference <path/to/feature-doc>`
- :doc:`Related Resources <smarter-resources>`

