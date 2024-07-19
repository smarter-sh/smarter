"""Multi-vendor support for LLM backing services."""

from .vendors import LLMVendors


# singleton instance
llm_vendors = LLMVendors()
