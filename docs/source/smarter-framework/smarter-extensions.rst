Smarter Extensions
==================

A Smarter Extension is a Python package that adds tools to the LLMs of a Smarter platform. It
has its own tools, settings, documentation, assets and lifecycle, and a platform administrator
installs it at run time, from the web console's Extensions page, by uploading it or from the Smarter Extension registry. See
:doc:`extensibility` for how Extensions differ from Plugins, and
:doc:`../smarter-platform/extensions` for how administrators manage them.

These pages are for the developers who build Extensions. They follow one example from start to
finish: the official weather Extension, whose ``get_weather`` tool is the tool that the
`OpenAI function calling guide <https://platform.openai.com/docs/guides/function-calling>`__
describes, implemented for real. Its source is
`smarter-sh/smarter-extension-weather <https://github.com/smarter-sh/smarter-extension-weather>`__.

An Extension in Brief
---------------------

.. code-block:: text

    smarter-extension-weather/
    ├── pyproject.toml          # name, version, tools, settings, compatibility
    ├── README.md
    ├── LICENSE
    └── weather/                # the Python package
        ├── __init__.py         # its module docstring is the Extension's documentation
        ├── models.py           # the Pydantic models of the tool's arguments and result
        ├── services.py         # geocoding and the weather api
        └── tools.py            # the GetWeather tool

A tool is a class. Its docstring is the description that the LLM reads, its Pydantic arguments
model is the JSON Schema of its parameters, and its ``call()`` method does the work:

.. code-block:: python

    class GetWeather(SmarterExtensionTool):
        """Get the current weather, and the forecast for the next 24 hours, for a location."""

        name = "get_weather"
        arguments_model = WeatherArguments

        def call(self, arguments: WeatherArguments, context: ExtensionContext) -> JsonValue:
            place = geocode(arguments.location, context.settings.google_maps_api_key.get_secret_value())
            found = weather(place, arguments.unit, context.settings.weather_api_url)
            return WeatherResult(location=place.address, current=found.current, ...).model_dump(mode="json")

Smarter does the rest: it offers the tool to the LLM as ``ext_weather_get_weather``, validates
the LLM's arguments, runs the tool with the administrator's settings and a timeout, returns the
result, or an error that the LLM can recover from, and sends the signals that Smarter's logs,
progress messages and history record.

.. toctree::
   :maxdepth: 1
   :caption: Developer Guide

   extensions/developer-guide
   extensions/pyproject-reference
   extensions/lifecycle
   extensions/testing
   extensions/publishing
   extensions/technical-reference
