"""
Smarter API Manifest - LLMHostCompute.spec.

An LLMHostCompute is a kind of node that LLMHosts run on, and the node group of those nodes:
on AWS, one EKS managed node group of one instance type. Applying the manifest stores it; Smarter
creates the node group when an LLMHost first needs one of its nodes, adds and removes nodes as
LLMHosts are launched and destroyed, and deletes the node group when the LLMHostCompute is deleted.

An LLMHost chooses an LLMHostCompute with ``spec.compute``, and its pods run only on that node
group's nodes. Its ``spec.resources`` must fit the node.

.. code-block:: yaml

    spec:
      node:
        instanceType: g6.2xlarge                # the cloud's instance type
        cpu: 8                                  # vCPUs
        memoryGb: 32                            # GiB
        gpu:
          type: L4
          count: 1
          memoryGb: 24                          # per GPU
        diskSizeGb: 100                         # container images; weights are on their own volumes
      nodeGroup:
        maxNodes: 4                             # the most nodes that Smarter adds
      cost:
        perHour: 0.9776                         # of one node, e.g. its on-demand price
"""

import os
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from smarter.lib.manifest.models import AbstractSAMSpecBase

from .const import (
    DEFAULT_CURRENCY,
    DEFAULT_DISK_SIZE_GB,
    DEFAULT_MAX_NODES,
    MANIFEST_KIND,
    MAX_NODES,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class LLMHostComputeBaseModel(AbstractSAMSpecBase):
    """Base class of the LLMHostCompute spec's blocks.

    Unknown fields are rejected, to catch typos.
    """

    model_config = ConfigDict(extra="forbid")


class SAMLLMHostComputeGpu(LLMHostComputeBaseModel):
    """Spec.node.gpu: the node's GPUs."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".node.gpu"

    type: str = Field(..., description=f"{class_identifier}.type[str]: the GPU model, e.g. L4, A10G, H100-80GB.")
    count: int = Field(..., ge=1, le=16, description=f"{class_identifier}.count[int]: the node's GPUs.")
    memoryGb: int = Field(..., ge=1, description=f"{class_identifier}.memoryGb[int]: the memory of one GPU, in GB.")
    resource: str = Field(
        default="nvidia.com/gpu",
        description=f"{class_identifier}.resource[str]: the Kubernetes extended resource that advertises the GPUs.",
    )


class SAMLLMHostComputeNode(LLMHostComputeBaseModel):
    """Spec.node: the kind of node."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".node"

    instanceType: str = Field(..., description=f"{class_identifier}.instanceType[str]: e.g. g6.2xlarge.")
    cpu: int = Field(..., ge=1, description=f"{class_identifier}.cpu[int]: the node's vCPUs.")
    memoryGb: int = Field(..., ge=1, description=f"{class_identifier}.memoryGb[int]: the node's memory, in GiB.")
    gpu: Optional[SAMLLMHostComputeGpu] = Field(
        default=None, description=f"{class_identifier}.gpu[object]: the node's GPUs. None for a CPU node."
    )
    diskSizeGb: int = Field(
        default=DEFAULT_DISK_SIZE_GB,
        ge=20,
        description=(
            f"{class_identifier}.diskSizeGb[int]: the node's root volume, for container images. Model weights "
            "are on the LLMHosts' own volumes."
        ),
    )
    capacityType: str = Field(
        default="ON_DEMAND",
        pattern=r"^(ON_DEMAND|SPOT)$",
        description=f"{class_identifier}.capacityType[str]: ON_DEMAND or SPOT.",
    )
    amiType: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.amiType[str]: e.g. AL2023_x86_64_NVIDIA. Defaults to the NVIDIA AMI for a GPU "
            "node, else the standard AMI."
        ),
    )


class SAMLLMHostComputeNodeGroup(LLMHostComputeBaseModel):
    """Spec.nodeGroup: the node group of the nodes."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".nodeGroup"

    maxNodes: int = Field(
        default=DEFAULT_MAX_NODES,
        ge=1,
        le=MAX_NODES,
        description=f"{class_identifier}.maxNodes[int]: the most nodes that Smarter adds to the node group.",
    )
    subnetIds: list[str] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.subnetIds[list]: the node group's subnets. Defaults to the platform's. One "
            "subnet keeps the nodes in one availability zone, with the LLMHosts' model volumes."
        ),
    )


class SAMLLMHostComputeCost(LLMHostComputeBaseModel):
    """Spec.cost: the price of one node, from which LLMHosts' costs are reported."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".cost"

    perHour: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description=f"{class_identifier}.perHour[decimal]: the cost per hour of one node, e.g. its on-demand price.",
    )
    currency: str = Field(default=DEFAULT_CURRENCY, description=f"{class_identifier}.currency[str]: e.g. USD.")


class SAMLLMHostComputeSpec(LLMHostComputeBaseModel):
    """Smarter API LLMHostCompute Manifest LLMHostCompute.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    node: SAMLLMHostComputeNode = Field(..., description=f"{class_identifier}.node[object]: the kind of node.")
    nodeGroup: SAMLLMHostComputeNodeGroup = Field(
        default_factory=SAMLLMHostComputeNodeGroup,
        description=f"{class_identifier}.nodeGroup[object]: the node group of the nodes.",
    )
    cost: SAMLLMHostComputeCost = Field(
        default_factory=SAMLLMHostComputeCost, description=f"{class_identifier}.cost[object]: for reporting."
    )


__all__ = [
    "SAMLLMHostComputeCost",
    "SAMLLMHostComputeGpu",
    "SAMLLMHostComputeNode",
    "SAMLLMHostComputeNodeGroup",
    "SAMLLMHostComputeSpec",
]
