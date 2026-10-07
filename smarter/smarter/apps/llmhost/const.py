"""Constants for the llmhost app."""

import os

namespace = "llmhost"
presentation_app_name = "LLMHost"

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
BUILTIN_MANIFESTS_PATH = os.path.join(DATA_PATH, "llmhost")
"""The example LLMHost manifests of the most popular open-weight models."""

# --- Kubernetes ---------------------------------------------------------------

RESOURCE_PREFIX = "llmhost"
"""The prefix of the names of an LLMHost's Kubernetes resources: llmhost-<id>-<name>."""
MAX_RESOURCE_NAME_LENGTH = 50
"""Leaves room for the suffixes that Kubernetes adds to pod names, within 63 characters."""
LABEL_LLMHOST = "smarter.sh/llmhost"
LABEL_ACCOUNT = "smarter.sh/account-number"
LABEL_COMPUTE = "smarter.sh/compute"
"""The node label of an LLMHostCompute's node group, and its LLMHosts' pod label and node selector."""
TAINT_COMPUTE = LABEL_COMPUTE
"""The taint of a CPU node group's nodes, so that only LLMHosts are scheduled on them."""
TAINT_GPU = "nvidia.com/gpu"
"""
The taint of a GPU node group's nodes.

The NVIDIA device plugin, which a GPU node needs to
advertise its GPUs, tolerates it, and pods that do not request GPUs do not.
"""
MODELS_MOUNT_PATH = "/models"
"""Where the model volume is mounted.

Engines cache downloaded weights here.
"""
# a memory-backed emptyDir volume's mount path, not a temp file.
SHM_MOUNT_PATH = "/dev/shm"  # nosec B108
"""Where the shared-memory volume, a memory-backed emptyDir, is mounted.

PyTorch-based engines exchange tensors between processes through /dev/shm, and a container's
default 64 MB is too small.
"""
# the server must listen on the pod's interfaces, so that its Service can reach it.
CONTAINER_BIND_ADDRESS = "0.0.0.0"  # nosec B104
"""The address that inference servers listen on, inside their container.

Every interface of the pod, so that its Service can reach it. What can reach the pod is decided
by the Service, which is inside the cluster, and the optional Ingress, not by this address.
"""
SERVICE_PORT = 80
MANAGED_KINDS = ["deployment", "service", "ingress", "secret"]
"""The kinds of an LLMHost's Kubernetes resources that undeploy deletes.

The model volume is kept, unless purged.
"""
VOLUME_KIND = "persistentvolumeclaim"

DEFAULT_CPU = "2"
DEFAULT_MEMORY = "8Gi"

# The engines' official images. They float with their projects' releases: pin a version,
# with spec.engine.image, for reproducible production deployments.
DEFAULT_IMAGES = {
    "vllm": "vllm/vllm-openai:latest",
    "tgi": "ghcr.io/huggingface/text-generation-inference:latest",
    "sglang": "lmsysorg/sglang:latest",
    "llama_cpp": "ghcr.io/ggml-org/llama.cpp:server-cuda",
    "ollama": "ollama/ollama:latest",
    "tei": "ghcr.io/huggingface/text-embeddings-inference:latest",
}
DEFAULT_CPU_IMAGES = {
    "llama_cpp": "ghcr.io/ggml-org/llama.cpp:server",
    "tei": "ghcr.io/huggingface/text-embeddings-inference:cpu-latest",
}
"""The images of engines that have a separate build for CPU-only nodes."""
S3_DOWNLOAD_IMAGE = "amazon/aws-cli:latest"
URL_DOWNLOAD_IMAGE = "curlimages/curl:latest"

# --- Secrets ------------------------------------------------------------------

API_KEY_SECRET_NAME = "llmhost_{name}_api_key"
"""The name of the Smarter Secret in which Smarter stores a generated API key."""
API_KEY_BYTES = 32

# --- Observability ------------------------------------------------------------

HEALTH_CHECK_TIMEOUT_SECONDS = 5
DEFAULT_LOG_LINES = 200
MAX_LOG_LINES = 5000
STATUS_REFRESH_MINUTES = 5
"""How often Celery Beat refreshes the status of deployed LLMHosts, and reconciles every compute."""

# --- Compute ------------------------------------------------------------------

BUILTIN_COMPUTE_PATH = os.path.join(DATA_PATH, "compute")
"""The built-in LLMHostCompute: the kinds of node that the built-in LLMHosts fit."""
RECONCILE_INTERVAL_SECONDS = 30
"""How often a compute is reconciled while its node group is adding or removing nodes."""
RECONCILE_MAX_ATTEMPTS = 60
"""How many times a compute is reconciled before Celery Beat's reconcile takes over: 30 minutes."""
