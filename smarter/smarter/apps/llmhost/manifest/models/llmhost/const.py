"""Smarter API LLMHost Manifest Constants."""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.LLMHOST.value

DEFAULT_REPLICAS = 1
DEFAULT_STORAGE_SIZE = "50Gi"
"""Default size of the model volume, which caches the weights across restarts."""
DEFAULT_SHM_SIZE = "8Gi"
"""Default size of /dev/shm, which PyTorch-based engines use for inter-process communication."""
DEFAULT_STARTUP_TIMEOUT_SECONDS = 3600
"""Default time that the inference server has to download and load the weights before it is restarted."""
DEFAULT_PERIOD_SECONDS = 10
DEFAULT_GPU_RESOURCE = "nvidia.com/gpu"

MAX_REPLICAS = 16
MAX_GPU_COUNT = 16
MAX_ARGS = 100

K8S_QUANTITY_PATTERN = r"^[0-9]+(\.[0-9]+)?(m|k|Ki|M|Mi|G|Gi|T|Ti|P|Pi|E|Ei)?$"
"""A Kubernetes resource quantity, e.g. ``500m``, ``4`` or ``24Gi``."""
K8S_LABEL_VALUE_PATTERN = r"^(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?$"
ENV_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"
HOSTNAME_PATTERN = r"^(?=.{1,253}$)([a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
