"""
The Smarter Chat api contract.

It is the versioned requests and responses of the configuration and prompt apis, which Smarter Chat
(``smarter/react/packages/smarter.sh-chat``) and the ``smarter`` cli call.

See :doc:`The Chat API Contract </smarter-framework/smarter-chat/api-contract>`.
"""

from .const import (
    CHAT_CONTRACT_V1,
    CHAT_CONTRACT_V2,
    CHAT_CONTRACT_V2_CAPABILITY,
)

__all__ = ["CHAT_CONTRACT_V1", "CHAT_CONTRACT_V2", "CHAT_CONTRACT_V2_CAPABILITY"]
