# pylint: disable=W0718
"""Smarter API Manifest handler"""

from smarter.lib.manifest.broker import SAMBrokerError


class SAMConnectionBrokerError(SAMBrokerError):
    """Base exception for Smarter API Connection Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Connection Manifest Broker Error"
