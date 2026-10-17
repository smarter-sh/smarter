"""
The messages of the web console terminal's WebSocket, and of its ticket api.

The browser sends :class:`TerminalInputMessage` and :class:`TerminalResizeMessage` as JSON text
messages. The server sends the shell's output as binary messages, the raw bytes that the shell
wrote to its terminal, and :class:`TerminalSessionMessage` and :class:`TerminalExitMessage` as JSON
text messages. See :mod:`.consumers`.
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

TERMINAL_MAX_INPUT = 64 * 1024
"""The most characters of input in one message, e.g. a paste."""

TERMINAL_MAX_SIZE = 1000
"""The most columns or rows of a terminal."""


class TerminalInputMessage(BaseModel):
    """Keystrokes, or pasted text, for the shell."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["input"]
    data: str = Field(max_length=TERMINAL_MAX_INPUT, description="What the user typed or pasted.")


class TerminalResizeMessage(BaseModel):
    """The browser's terminal changed size, so the shell's terminal does too."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["resize"]
    cols: int = Field(ge=1, le=TERMINAL_MAX_SIZE, description="The terminal's width, in characters.")
    rows: int = Field(ge=1, le=TERMINAL_MAX_SIZE, description="The terminal's height, in lines.")


TerminalClientMessage = Annotated[Union[TerminalInputMessage, TerminalResizeMessage], Field(discriminator="type")]
"""A message from the browser."""

terminal_client_message = TypeAdapter(TerminalClientMessage)
"""Validates a message from the browser: ``terminal_client_message.validate_json(text)``."""


class TerminalSessionMessage(BaseModel):
    """
    The shell started.

    The first message of every session.

    The browser shows where the shell runs, and how long the session can last, in the banner that
    it prints above the shell's prompt.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["session"] = "session"
    hostname: str = Field(description="The host name of the pod, or container, that runs the shell.")
    user: str = Field(description="The operating system user that runs the shell.")
    command: str = Field(description="The shell's command line.")
    pid: int = Field(description="The shell's process id.")
    idle_timeout: int = Field(description="Seconds without input after which the session ends.")
    max_duration: int = Field(description="Seconds after which the session ends, with or without input.")


class TerminalExitMessage(BaseModel):
    """The session ended.

    The last message of every session that started.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["exit"] = "exit"
    reason: Literal["exited", "idle", "expired", "failed"] = Field(
        description=(
            "exited: the shell exited, e.g. after `exit`. idle: no input for idle_timeout seconds. "
            "expired: the session lasted max_duration seconds. failed: the shell could not be started."
        )
    )
    code: Optional[int] = Field(default=None, description="The shell's exit status, when it exited.")


class TerminalTicket(BaseModel):
    """The ticket api's response: a single use ticket, and the WebSocket to redeem it at."""

    model_config = ConfigDict(extra="forbid")

    ticket: str = Field(description="A random, single use token, valid for a minute.")
    url: str = Field(description="The WebSocket's path, e.g. /ws/terminal/. The ticket is its ticket query parameter.")
