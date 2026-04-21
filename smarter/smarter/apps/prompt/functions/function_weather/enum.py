"""
Enums for the weather function parameters, units, and metrics.
"""

from smarter.common.enum import SmarterEnum


class WeatherParameters(SmarterEnum):
    """
    Enum for weather function parameters.
    """

    LOCATION = "location"
    UNIT = "unit"


class WeatherUnits(SmarterEnum):
    """
    Enum for supported weather units.
    """

    METRIC = "METRIC"
    USCS = "USCS"


class WeatherMetrics(SmarterEnum):
    """
    Enum for weather metrics to retrieve from the API.
    """

    TEMPERATURE_2M = "temperature_2m"
    PRECIPITATION = "precipitation"
    SNOWFALL = "snowfall"
    WEATHERCODE = "weathercode"
    WINDSPEED_10M = "windspeed_10m"
    WINDDIRECTION_10M = "winddirection_10m"
    WINDGUSTS_10M = "windgusts_10m"
    CLOUDCOVER = "cloudcover"


__all__ = [
    "WeatherParameters",
    "WeatherUnits",
    "WeatherMetrics",
]
