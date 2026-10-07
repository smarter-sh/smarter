"""
Model sources: where an LLMHost's weights come from.

A source resolves ``spec.model`` into a :class:`ResolvedModel`: how the engine refers to the
weights, and the init containers, if any, that copy them to the model volume first. Engines
then turn the resolved model into their own arguments, so that any engine can load any
source that it supports, and a new source does not change the engines.
"""

import posixpath
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from smarter.apps.llmhost.const import (
    MODELS_MOUNT_PATH,
    S3_DOWNLOAD_IMAGE,
    URL_DOWNLOAD_IMAGE,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostModelSource
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostModel

from .exceptions import LLMHostConfigurationError

MODELS_VOLUME = "models"
LOCAL_MODELS_PATH = posixpath.join(MODELS_MOUNT_PATH, "local")


@dataclass(frozen=True)
class ResolvedModel:
    """
    How an engine refers to an LLMHost's weights.

    :param source: The model source, e.g. huggingface.
    :param reference: The repository id, tag or local path that the engine loads.
    :param revision: The Hugging Face revision, if the engine downloads from Hugging Face.
    :param file: A single weights file within the repository, if any.
    :param local: Whether ``reference`` is a path on the model volume.
    :param init_containers: Containers that copy the weights to the model volume.
    """

    source: str
    reference: str
    revision: Optional[str] = None
    file: Optional[str] = None
    local: bool = False
    init_containers: list[dict[str, Any]] = field(default_factory=list)

    @property
    def path(self) -> str:
        """The local path of the weights, including the file, if any."""
        return posixpath.join(self.reference, self.file) if self.file else self.reference


class ModelSource(ABC):
    """A source of model weights."""

    name: str

    @abstractmethod
    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        """
        Resolve ``spec.model``.

        :param model: The spec's model block.
        :param slug: A DNS-safe name of the LLMHost, for local paths.
        """


class HuggingFaceSource(ModelSource):
    """A Hugging Face Hub repository, which the engine downloads itself, with HF_TOKEN for gated models."""

    name = SAMLLMHostModelSource.HUGGINGFACE.value

    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        return ResolvedModel(
            source=self.name, reference=model.repository, revision=model.revision or "main", file=model.file
        )


class OllamaSource(ModelSource):
    """An Ollama library tag, which the ollama engine pulls."""

    name = SAMLLMHostModelSource.OLLAMA.value

    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        return ResolvedModel(source=self.name, reference=model.repository)


class S3Source(ModelSource):
    """An S3 prefix, synced to the model volume by an init container.

    Credentials come from the pod's service account.
    """

    name = SAMLLMHostModelSource.S3.value

    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        target = posixpath.join(LOCAL_MODELS_PATH, slug)
        init = {
            "name": "download-model",
            "image": S3_DOWNLOAD_IMAGE,
            "command": ["aws", "s3", "sync", "--only-show-errors", model.repository, target],
            "volumeMounts": [{"name": MODELS_VOLUME, "mountPath": MODELS_MOUNT_PATH}],
        }
        return ResolvedModel(source=self.name, reference=target, file=model.file, local=True, init_containers=[init])


class UrlSource(ModelSource):
    """A single file, e.g. a GGUF file, downloaded to the model volume by an init container, unless it is there."""

    name = SAMLLMHostModelSource.URL.value

    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        target = posixpath.join(LOCAL_MODELS_PATH, slug)
        filename = model.file or posixpath.basename(urlparse(model.repository).path)
        if not filename:
            raise LLMHostConfigurationError(f"model.file: is required, because {model.repository} has no file name.")
        path = posixpath.join(target, filename)
        # the URL and path are passed as arguments, never interpolated into the script.
        script = (
            'test -s "$2" || { mkdir -p "$(dirname "$2")" && curl -fsSL -o "$2.partial" "$1" && mv "$2.partial" "$2"; }'
        )
        init = {
            "name": "download-model",
            "image": URL_DOWNLOAD_IMAGE,
            "command": ["/bin/sh", "-c", script, "download", model.repository, path],
            "volumeMounts": [{"name": MODELS_VOLUME, "mountPath": MODELS_MOUNT_PATH}],
        }
        return ResolvedModel(source=self.name, reference=target, file=filename, local=True, init_containers=[init])


class PvcSource(ModelSource):
    """Weights already on the volume of ``storage.existingClaim``, at ``repository``."""

    name = SAMLLMHostModelSource.PVC.value

    def resolve(self, model: SAMLLMHostModel, slug: str) -> ResolvedModel:
        return ResolvedModel(
            source=self.name,
            reference=posixpath.join(MODELS_MOUNT_PATH, model.repository),
            file=model.file,
            local=True,
        )


SOURCES: dict[str, ModelSource] = {
    source.name: source for source in (HuggingFaceSource(), OllamaSource(), S3Source(), UrlSource(), PvcSource())
}


def resolve_model(model: SAMLLMHostModel, slug: str) -> ResolvedModel:
    """Resolve ``spec.model`` with its source."""
    try:
        source = SOURCES[model.source]
    except KeyError as e:
        raise LLMHostConfigurationError(f"model.source: {model.source} is not supported.") from e
    return source.resolve(model, slug)


__all__ = ["ModelSource", "ResolvedModel", "SOURCES", "resolve_model", "MODELS_VOLUME"]
