"""Constants of Smarter annotations, which follow Kubernetes annotations."""

namespace = "annotation"

ANNOTATION_KEY_PREFIX_MAX_LENGTH = 253
"""The longest key prefix, a DNS subdomain such as ``acme.com``, as in Kubernetes."""

ANNOTATION_KEY_SEGMENT_MAX_LENGTH = 63
"""The longest segment of a key's name, the parts between slashes, as in Kubernetes."""

ANNOTATION_KEY_MAX_LENGTH = ANNOTATION_KEY_PREFIX_MAX_LENGTH + 1 + ANNOTATION_KEY_SEGMENT_MAX_LENGTH
"""The longest key, 317 characters: the longest key that Kubernetes accepts."""

ANNOTATIONS_TOTAL_MAX_BYTES = 256 * 1024
"""The most that one resource's annotations, keys and values together, may hold: 256 KiB, as in Kubernetes."""

RESERVED_ANNOTATION_PREFIXES = ("smarter.sh",)
"""
Key prefixes that belong to the Smarter platform, as ``kubernetes.io`` belongs to Kubernetes.

A prefix's subdomains are reserved too, e.g. ``llmclient.smarter.sh``. Manifests may carry
these keys, but only Smarter's own code registers handlers for them.
"""

ANNOTATION_SELECTOR_PARAM = "annotation"
"""The query parameter of the cli ``get`` api that holds an annotation selector, e.g. ``?annotation=acme.com/crm-id=42``."""
