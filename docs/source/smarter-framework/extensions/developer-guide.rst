Building an Extension
=====================

This guide builds the official weather Extension, step by step. Its one tool, ``get_weather``,
finds a location with the Google Maps Geocoding API, gets the forecast from the Open-Meteo API,
and returns the current weather and the next 24 hours. It's a realistic example: it has a secret
setting, an ordinary setting with a default, input that the LLM may get wrong, two third-party
services that may fail, and a result that is too big to return unstructured.

What an Extension Can Use
-------------------------

An Extension runs inside the platform, so it can import:

- the Python standard library;
- Smarter itself: ``smarter.common``, ``smarter.lib`` and ``smarter.apps``;
- every library that the platform already installs, such as Pydantic, requests, pandas, NumPy,
  Pint, ``googlemaps`` and ``openmeteo_requests``.

An Extension cannot install libraries. It declares the ones it needs in its ``pyproject.toml``'s
``dependencies``, and the platform refuses to install an Extension whose dependencies it doesn't
satisfy. To find out what a platform has, read its ``requirements`` files, or run
``pip list`` in its container.

An Extension does not define Django models, migrations, URL routes or Celery tasks. To store
data, it can create SAM resources, such as Secrets, from its lifecycle hooks: see
:doc:`lifecycle`.

.. _extension-tool-protocol:

The Tool Protocol
-----------------

Every tool, in every Extension, implements the same protocol: it is a subclass of
:class:`~smarter.apps.llmtool.extension.protocol.SmarterExtensionTool` that declares four things.

``name``
    The tool's name, unique within its Extension: letters, digits and underscores, starting with a
    letter, at most 48 characters. The LLM sees it as ``ext_<slug>_<name>``.

``arguments_model``
    A Pydantic model of the tool's arguments. Its JSON Schema is the ``parameters`` of the tool
    definition offered to the LLM, and the platform validates the LLM's arguments with it.

The class docstring
    The tool's description for the LLM. A tool can set ``description`` instead.

``call(self, arguments, context) -> JsonValue``
    Does the work. ``arguments`` is an instance of ``arguments_model``, already validated, and
    ``context`` is an :class:`~smarter.apps.llmtool.extension.protocol.ExtensionContext`: the
    Extension's settings, who called the tool, and a logger. It returns any JSON value, which is
    the result that the LLM reads, or raises
    :class:`~smarter.apps.llmtool.extension.protocol.ExtensionToolError` to tell the LLM why it
    could not do what was asked.

In return, the platform does everything else. It builds the OpenAI tool definition from the class,
validates the arguments and returns validation errors to the LLM, creates a new instance of the tool
for each call, enforces the ``timeout`` from ``pyproject.toml``, turns exceptions into
``{"error": ...}`` results that the LLM can recover from, and sends the ``llm_tool_presented``,
``llm_tool_requested`` and ``llm_tool_responded`` signals.

The platform checks the protocol when it loads an Extension. A class listed in ``tools`` that is not
a ``SmarterExtensionTool`` subclass, has an invalid name, has no ``arguments_model``, does not
implement ``call()`` or has no description makes the Extension fail to load, with a message that
names the problem. Each tool's
:meth:`~smarter.apps.llmtool.extension.protocol.SmarterExtensionTool.problems` gives the same
answer, so a unit test can assert that it's empty before the Extension is ever installed: see
:doc:`testing`.

The protocol is a base class, not a :class:`typing.Protocol`, because the base class does part of
the work. The tool definition and the validation of the LLM's arguments both come from the same
Pydantic model, so what the LLM is told the tool accepts can never disagree with what it actually
accepts. Writing a tool means filling in four declarations, not keeping a hand-written JSON
definition in step with the code. The complete API is in :doc:`reference/protocol`.

1. The Layout
-------------

Create a repository with a ``pyproject.toml`` and a Python package beside it:

.. code-block:: text

    smarter-extension-weather/
    ├── pyproject.toml
    ├── README.md
    ├── LICENSE
    └── weather/
        ├── __init__.py
        ├── models.py
        ├── services.py
        └── tools.py

The package's modules import each other with **relative imports**, ``from .models import
WeatherArguments``, never ``from weather.models import ...``. The platform imports each installed
version under a name of its own, so that two versions can run side by side during an update, and
the package's own name is not importable.

2. The pyproject.toml
---------------------

``pyproject.toml`` is a standard Python project file. Smarter reads the ``[project]`` table, which
any Python package declares, and its own ``[tool.smarter]`` table:

.. code-block:: toml

    [project]
    name = "smarter-extension-weather"
    version = "1.0.0"
    description = "Current weather and a 24-hour forecast for any location."
    authors = [{ name = "The Smarter Project" }]
    license = "AGPL-3.0"
    requires-python = ">=3.12"
    dependencies = [
        "googlemaps>=4.10",
        "openmeteo-requests>=1.5",
    ]

    [project.urls]
    Homepage = "https://github.com/smarter-sh/smarter-extension-weather"

    [tool.smarter]
    slug = "weather"
    package = "weather"
    display-name = "Weather"
    requires-smarter = ">=0.27"
    tools = ["weather.tools:GetWeather"]
    timeout = 30

    [[tool.smarter.settings]]
    name = "google_maps_api_key"
    type = "secret"
    required = true
    description = "A Google Maps Geocoding API key, which finds the latitude and longitude of a location."

    [[tool.smarter.settings]]
    name = "weather_api_url"
    type = "url"
    default = "https://api.open-meteo.com/v1/forecast"
    description = "The Open-Meteo forecast api."

- ``slug`` is the Extension's permanent identifier. LLMClients list it in ``spec.extensions``, and
  its tools are offered to LLMs as ``ext_<slug>_<tool name>``. Choose it once.
- ``version`` is the Extension's version, a `PEP 440 <https://peps.python.org/pep-0440/>`__
  version, which should follow `semantic versioning <https://semver.org/>`__. A released version
  never changes: release a new one instead.
- ``requires-smarter`` is the range of Smarter versions that the Extension works with.
- ``tools`` lists the tools' classes, as ``<module>:<class>``.
- ``settings`` are what the administrator configures. A ``secret`` setting's value is stored in a
  Smarter Secret, encrypted at rest.

Every field is described in :doc:`pyproject-reference`.

3. The Documentation
--------------------

The package's module docstring is the Extension's documentation. The web console shows it on
the Extension's page, and the registry shows it to administrators before they install it. Write
it in reStructuredText, for the administrator who decides whether to install the Extension and
then configures it:

.. code-block:: python
    :caption: weather/__init__.py

    """
    Weather
    =======

    Current weather and a 24-hour forecast for any location, from the Open-Meteo api, with
    locations found by the Google Maps Geocoding api.

    Settings
    --------

    ``google_maps_api_key``
        Required. A Google Maps API key with the Geocoding API enabled. See
        https://developers.google.com/maps/documentation/geocoding/get-api-key.

    ``weather_api_url``
        The Open-Meteo forecast api. Change it only to use a self-hosted Open-Meteo.

    Tools
    -----

    ``get_weather(location, unit)``
        The current temperature, precipitation, wind speed and cloud cover, and the forecast for each
        of the next 24 hours, starting this hour, in metric or US customary units. Times are in the
        location's own timezone, and the result names the unit of every measurement.
    """

4. The Arguments and the Result
-------------------------------

The LLM calls a tool with JSON arguments, which may be wrong: a missing location, a unit that
doesn't exist. Model them with Pydantic. The model validates the arguments, and its JSON Schema is
what the LLM is told the tool accepts, so the two can never disagree. Describe every field: the LLM
reads the descriptions.

Model the result too. The LLM can only interpret what the result says, so say everything it needs:
the weather's timezone, so that it knows what "14:00" means, and the unit of every measurement, so
that it never guesses whether the wind is in km/h or mph.

.. code-block:: python
    :caption: weather/models.py

    """The arguments and result of the get_weather tool."""

    from typing import Literal

    from pydantic import BaseModel, Field

    Unit = Literal["METRIC", "USCS"]
    """Metric, or US customary, units."""


    class WeatherArguments(BaseModel):
        """The arguments of get_weather."""

        location: str = Field(..., min_length=1, description="The city and state or country, e.g. San Francisco, CA")
        unit: Unit = Field("METRIC", description="Metric, or US customary, units.")


    class Units(BaseModel):
        """The units of the weather's measurements."""

        temperature: str = Field(..., description="e.g. °C or °F.")
        precipitation: str = Field(..., description="e.g. mm or inch.")
        wind_speed: str = Field(..., description="e.g. km/h or mph.")
        cloud_cover: str = Field("%", description="Percent of the sky.")


    class Conditions(BaseModel):
        """The weather at one time."""

        time: str = Field(..., description="The location's local time, e.g. 2026-10-15 14:00.")
        temperature: float = Field(..., description="The temperature at 2 m.")
        precipitation: float = Field(..., description="The precipitation.")
        wind_speed: float = Field(..., description="The wind speed at 10 m.")
        cloud_cover: float = Field(..., description="The cloud cover.")


    class WeatherResult(BaseModel):
        """What get_weather returns to the LLM."""

        location: str = Field(..., description="The location's address, as Google Maps found it.")
        latitude: float
        longitude: float
        timezone: str = Field(..., description="The location's timezone, e.g. Europe/Paris, in which times are given.")
        units: Units = Field(..., description="The units of every measurement.")
        current: Conditions = Field(..., description="The weather now.")
        forecast: list[Conditions] = Field(..., description="The weather in each of the next 24 hours.")

Returning a model's ``model_dump(mode="json")``, rather than a dict assembled by hand, keeps the
result's shape stable and documented.

5. The Tool
-----------

A tool subclasses :class:`~smarter.apps.llmtool.extension.protocol.SmarterExtensionTool`:

.. code-block:: python
    :caption: weather/tools.py

    """The weather extension's tools."""

    from pydantic import JsonValue
    from smarter.apps.llmtool.extension import ExtensionContext, ExtensionToolError, SmarterExtensionTool

    from .models import WeatherArguments, WeatherResult
    from .services import UNITS, ForecastError, GeocodingError, geocode, weather


    class GetWeather(SmarterExtensionTool):
        """Get the current weather, and the forecast for the next 24 hours, for a location."""

        name = "get_weather"
        arguments_model = WeatherArguments

        def call(self, arguments: WeatherArguments, context: ExtensionContext) -> JsonValue:
            settings = context.settings
            try:
                place = geocode(arguments.location, settings.google_maps_api_key.get_secret_value())
                found = weather(place, arguments.unit, settings.weather_api_url)
            except GeocodingError as e:
                raise ExtensionToolError(f"Could not find {arguments.location}: {e}") from e
            except ForecastError as e:
                raise ExtensionToolError(f"The weather service is unavailable: {e}") from e
            context.logger.info("get_weather found %s", place.address)
            return WeatherResult(
                location=place.address,
                latitude=place.latitude,
                longitude=place.longitude,
                timezone=found.timezone,
                units=UNITS[arguments.unit],
                current=found.current,
                forecast=found.forecast,
            ).model_dump(mode="json")

- ``name`` is the tool's name, unique within the Extension. The LLM sees it as
  ``ext_weather_get_weather``.
- The **class docstring** is the tool's description for the LLM. Say what it does and when to use
  it, in a sentence or two.
- ``call()`` receives the validated arguments, as an instance of ``arguments_model``, and an
  :class:`~smarter.apps.llmtool.extension.protocol.ExtensionContext`. It returns any JSON value.
- ``context.settings`` has one attribute per setting in ``pyproject.toml``. A secret setting is a
  :class:`pydantic.SecretStr`: call ``get_secret_value()`` only where you use it, and never log it.
- ``context.account``, ``context.user_profile`` and ``context.llmclient`` say who called the tool.
- ``context.logger`` logs as ``smarter_extensions.<slug>``.

Errors
~~~~~~

Raise :class:`~smarter.apps.llmtool.extension.protocol.ExtensionToolError` when the tool can't do
what was asked. Its message is returned to the LLM as ``{"error": "..."}``, so write it for the
LLM, which can then ask the user for a better location, or apologize. Any other exception is
logged with its traceback, and the LLM is told only that the tool failed. Invalid arguments never
reach ``call()``: the LLM is told what was wrong with them.

A call that runs longer than the ``timeout`` in ``pyproject.toml`` is abandoned, and the LLM is told so.

6. The Services
---------------

Keep the calls to third-party services out of the tool, so that each can be tested alone, and do
any setup when it's first needed, not when the module is imported. Importing happens when the
platform loads the Extension, in every process, and an import that fails or blocks makes the
Extension fail to load.

.. code-block:: python
    :caption: weather/services.py

    """Geocoding with Google Maps, and current conditions and forecasts from Open-Meteo."""

    from dataclasses import dataclass, field
    from datetime import datetime, timedelta, timezone

    import googlemaps
    import openmeteo_requests

    from .models import Conditions, Unit, Units

    METRICS = ["temperature_2m", "precipitation", "windspeed_10m", "cloudcover"]
    """The variables requested from Open-Meteo, in the order that they are returned."""
    HOURS = 24
    USCS_PARAMETERS = {"temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch"}
    UNITS = {
        "METRIC": Units(temperature="°C", precipitation="mm", wind_speed="km/h"),
        "USCS": Units(temperature="°F", precipitation="inch", wind_speed="mph"),
    }
    """Open-Meteo's units: its defaults, or those that USCS_PARAMETERS request."""


    class GeocodingError(Exception):
        """A location could not be found."""


    class ForecastError(Exception):
        """The forecast api failed."""


    @dataclass
    class Place:
        """A location, as Google Maps found it."""

        address: str
        latitude: float
        longitude: float


    @dataclass
    class Weather:
        """A place's current conditions and forecast, in its local time."""

        timezone: str
        current: Conditions
        forecast: list[Conditions] = field(default_factory=list)


    def geocode(location: str, api_key: str) -> Place:
        """
        Find a location's address, latitude and longitude.

        :param location: The location, e.g. ``Paris``.
        :param api_key: A Google Maps API key with the Geocoding API enabled.
        :returns: The place.
        :raises GeocodingError: If the location cannot be found, or the API key is not valid.
        """
        try:
            results = googlemaps.Client(key=api_key).geocode(location)
        except (ValueError, googlemaps.exceptions.ApiError, googlemaps.exceptions.TransportError) as e:
            raise GeocodingError(str(e)) from e
        if not results:
            raise GeocodingError("no such place")
        geometry = results[0]["geometry"]["location"]
        return Place(results[0].get("formatted_address", location), float(geometry["lat"]), float(geometry["lng"]))


    def local_time(epoch: int, utc_offset: int) -> str:
        """Return a Unix time as a local time, e.g. ``2026-10-15 14:00``."""
        return datetime.fromtimestamp(epoch + utc_offset, timezone.utc).strftime("%Y-%m-%d %H:%M")


    def conditions(time: str, values: list[float]) -> Conditions:
        """Return the conditions at a time, from the values of METRICS, in order."""
        return Conditions(
            time=time,
            temperature=round(values[0], 1),
            precipitation=round(values[1], 2),
            wind_speed=round(values[2], 1),
            cloud_cover=round(values[3], 0),
        )


    def weather(place: Place, unit: Unit, api_url: str) -> Weather:
        """
        Return a place's current conditions, and its forecast for the next 24 hours, starting this hour.

        :param place: The place.
        :param unit: ``METRIC`` or ``USCS``.
        :param api_url: The Open-Meteo forecast api.
        :returns: The weather, with times in the place's timezone.
        :raises ForecastError: If the api fails, or its response is not as expected.
        """
        params: dict = {
            "latitude": place.latitude,
            "longitude": place.longitude,
            "current": METRICS,
            "hourly": METRICS,
            "forecast_hours": HOURS,
            "timezone": "auto",
        }
        if unit == "USCS":
            params.update(USCS_PARAMETERS)
        try:
            response = openmeteo_requests.Client().weather_api(api_url, params=params)[0]
            offset = response.UtcOffsetSeconds()
            zone = (response.Timezone() or b"UTC").decode()
            current = response.Current()
            now = conditions(
                local_time(current.Time(), offset), [float(current.Variables(i).Value()) for i in range(len(METRICS))]
            )
            hourly = response.Hourly()
            values = [hourly.Variables(i).ValuesAsNumpy() for i in range(len(METRICS))]
            start, interval = hourly.Time(), hourly.Interval()
            hours = (hourly.TimeEnd() - start) // interval
            forecast = [
                conditions(local_time(start + i * interval, offset), [float(values[m][i]) for m in range(len(METRICS))])
                for i in range(min(hours, HOURS))
            ]
        # the client and the flatbuffers response raise many kinds of exceptions.
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ForecastError(str(e)) from e
        return Weather(timezone=zone, current=now, forecast=forecast)


    __all__ = ["ForecastError", "GeocodingError", "Place", "UNITS", "Weather", "geocode", "weather"]

7. Validate and Package
-----------------------

On a Smarter development platform, check the Extension as the installer and the registry will:
its ``pyproject.toml``, compatibility, that the code imports, and each tool's definition:

.. code-block:: console

    python manage.py validate_extension ../smarter-extension-weather

It prints each tool's definition, exactly as the LLM will see it. Then build the archive, which
holds the ``pyproject.toml``, the package, and the README, LICENSE and CHANGELOG, and leaves out
caches and version control:

.. code-block:: console

    python manage.py package_extension ../smarter-extension-weather --output dist
    dist/weather-1.0.0.zip
    sha256: 6f1d...

The same source always builds the same archive, with the same sha256.

8. Install and Try It
---------------------

Install it on your development platform, and configure its secret setting:

.. code-block:: console

    python manage.py install_extension dist/weather-1.0.0.zip

Then, in the web console, open **Extensions** › **Weather**, set ``google_maps_api_key`` on
the **Settings** tab, and enable it. List it in an LLMClient:

.. code-block:: yaml

    spec:
      extensions:
        - weather

and ask the LLMClient about the weather in Paris. The chat's Smarter messages show that the
Extension's tools were added, and the tool call and its result.

Next, write its tests (:doc:`testing`), and publish it (:doc:`publishing`).
