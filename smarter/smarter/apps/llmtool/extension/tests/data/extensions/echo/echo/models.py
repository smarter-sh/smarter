"""The arguments of the echo extension's tools."""

from pydantic import BaseModel, Field


class EchoArguments(BaseModel):
    """The arguments of the echo tool."""

    text: str = Field(..., min_length=1, description="The text to echo.")


class NoArguments(BaseModel):
    """A tool that takes no arguments."""
