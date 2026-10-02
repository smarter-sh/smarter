"""
The LLMHost service layer: discover, launch, observe and destroy the models that Smarter.

hosts on Kubernetes.

- :mod:`.service`: :class:`LLMHostService`, the API of the service layer.
- :mod:`.discovery`: model catalogs, e.g. Hugging Face, sizing, and manifest drafts.
- :mod:`.sources` and :mod:`.engines`: where weights come from, and the servers that serve them.
- :mod:`.renderer`: an LLMHost's Kubernetes resources.
- :mod:`.cluster`: the Kubernetes cluster, behind a backend that tests replace.
- :mod:`.observability`: status, health and cost reporting.
"""

from .cluster import (
    ClusterBackend,
    InMemoryClusterBackend,
    KubectlClusterBackend,
    configure_cluster,
    get_cluster,
)
from .discovery import ModelInfo, draft_manifest, estimate_vram_gb, get_catalog
from .exceptions import (
    LLMHostBudgetExceeded,
    LLMHostClusterError,
    LLMHostConfigurationError,
    LLMHostDiscoveryError,
    LLMHostServiceError,
)
from .observability import HealthProber, LLMHostObservation
from .service import LLMHostService

__all__ = [
    "ClusterBackend",
    "HealthProber",
    "InMemoryClusterBackend",
    "KubectlClusterBackend",
    "LLMHostClusterError",
    "LLMHostConfigurationError",
    "LLMHostBudgetExceeded",
    "LLMHostDiscoveryError",
    "LLMHostObservation",
    "LLMHostService",
    "LLMHostServiceError",
    "ModelInfo",
    "configure_cluster",
    "draft_manifest",
    "estimate_vram_gb",
    "get_catalog",
    "get_cluster",
]
