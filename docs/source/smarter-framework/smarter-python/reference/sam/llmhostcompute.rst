..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMLLMHostCompute
=================

``smarter.models.sam.llmhostcompute``
-------------------------------------

.. py:module:: smarter.models.sam.llmhostcompute

SAM model of the ``LLMHostCompute`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: SAMDependency

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A resource that depends on the resource that a manifest describes.

   .. py:attribute:: kind
      :type: str

      Kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient.

      Read only.


   .. py:attribute:: name
      :type: str

      Name[String]: The name of the resource that depends on this resource.

      Read only.



.. py:class:: SAMLLMHostComputeCost

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.cost: the price of one node, from which LLMHosts' costs are reported.

   .. py:attribute:: currency
      :type: str | None

      LLMHostCompute.spec.cost.currency[str]: e.g. USD.


   .. py:attribute:: perHour
      :type: Union

      LLMHostCompute.spec.cost.perHour[decimal]: the cost per hour of one node, e.g. its on-demand price.



.. py:class:: SAMLLMHostComputeGpu

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.node.gpu: the node's GPUs.

   .. py:attribute:: count
      :type: int

      LLMHostCompute.spec.node.gpu.count[int]: the node's GPUs.


   .. py:attribute:: memoryGb
      :type: int

      LLMHostCompute.spec.node.gpu.memoryGb[int]: the memory of one GPU, in GB.


   .. py:attribute:: resource
      :type: str | None

      LLMHostCompute.spec.node.gpu.resource[str]: the Kubernetes extended resource that advertises the GPUs.


   .. py:attribute:: type
      :type: str

      LLMHostCompute.spec.node.gpu.type[str]: the GPU model, e.g. L4, A10G, H100-80GB.



.. py:class:: SAMLLMHostComputeMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHostCompute Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$', ascii_only=None)], uuid.UUID, bytes, list, dict[str, Any]]]]

      The manifest annotations.

      Used for storing arbitrary metadata as
                  key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
                  key should be a valid url-friendly string. The value accepts
                  multi-line string values (YAML block scalars) and various scalar types including
                  str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.


   .. py:attribute:: description
      :type: str | None

      The description for this resource.

      Be brief. Keep it under 255 characters.


   .. py:attribute:: name
      :type: str

      The camelCase name of the manifest resource.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMLLMHostComputeNode

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.node: the kind of node.

   .. py:attribute:: amiType
      :type: str | None

      LLMHostCompute.spec.node.amiType[str]: e.g. AL2023_x86_64_NVIDIA.

      Defaults to the NVIDIA AMI for a GPU node, else the standard AMI.


   .. py:attribute:: capacityType
      :type: Optional

      LLMHostCompute.spec.node.capacityType[str]: ON_DEMAND or SPOT.


   .. py:attribute:: cpu
      :type: int

      LLMHostCompute.spec.node.cpu[int]: the node's vCPUs.


   .. py:attribute:: diskSizeGb
      :type: Optional

      LLMHostCompute.spec.node.diskSizeGb[int]: the node's root volume, for container images.

      Model weights are on the LLMHosts' own volumes.


   .. py:attribute:: gpu
      :type: smarter.models.sam.llmhostcompute.SAMLLMHostComputeGpu | None

      LLMHostCompute.spec.node.gpu[object]: the node's GPUs.

      None for a CPU node.


   .. py:attribute:: instanceType
      :type: str

      LLMHostCompute.spec.node.instanceType[str]: e.g. g6.2xlarge.


   .. py:attribute:: memoryGb
      :type: int

      LLMHostCompute.spec.node.memoryGb[int]: the node's memory, in GiB.



.. py:class:: SAMLLMHostComputeNodeGroup

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.nodeGroup: the node group of the nodes.

   .. py:attribute:: maxNodes
      :type: Optional

      LLMHostCompute.spec.nodeGroup.maxNodes[int]: the most nodes that Smarter adds to the node group.


   .. py:attribute:: subnetIds
      :type: list[str] | None

      LLMHostCompute.spec.nodeGroup.subnetIds[list]: the node group's subnets.

      Defaults to the platform's. One subnet keeps the nodes in one availability zone, with the LLMHosts' model volumes.



.. py:class:: SAMLLMHostComputeSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHostCompute Manifest LLMHostCompute.spec.

   .. py:attribute:: cost
      :type: smarter.models.sam.llmhostcompute.SAMLLMHostComputeCost | None

      LLMHostCompute.spec.cost[object]: for reporting.


   .. py:attribute:: node
      :type: SAMLLMHostComputeNode

      LLMHostCompute.spec.node[object]: the kind of node.


   .. py:attribute:: nodeGroup
      :type: smarter.models.sam.llmhostcompute.SAMLLMHostComputeNodeGroup | None

      LLMHostCompute.spec.nodeGroup[object]: the node group of the nodes.



.. py:class:: SAMLLMHostComputeStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHostCompute Manifest - Status class.

   Read only. Besides ownership, it reports the node group, as of its most recent reconcile.

   .. py:attribute:: accountNumber
      :type: str

      LLMHostCompute.status.account_number: The account owner of this LLMHostCompute.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.llmhostcompute.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: desiredNodes
      :type: int | None

      LLMHostCompute.status.desiredNodes: the node group's desired size. Read only.


   .. py:attribute:: lastReconciledAt
      :type: datetime.datetime | None

      LLMHostCompute.status.lastReconciledAt: when it was last reconciled.

      Read only.


   .. py:attribute:: llmhosts
      :type: int | None

      LLMHostCompute.status.llmhosts: the LLMHosts that run on it.

      Read only.


   .. py:attribute:: message
      :type: str | None

      LLMHostCompute.status.message: the result of the last reconcile. Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: nodeGroupName
      :type: str | None

      LLMHostCompute.status.nodeGroupName: the cloud's name of the node group.

      Read only.


   .. py:attribute:: nodeGroupStatus
      :type: str | None

      LLMHostCompute.status.nodeGroupStatus: e.g. absent, CREATING or ACTIVE.

      Read only.


   .. py:attribute:: readyNodes
      :type: int | None

      LLMHostCompute.status.readyNodes: the nodes that have joined the cluster.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: username
      :type: str

      LLMHostCompute.status.username: The Smarter user who created this LLMHostCompute.

      Read only.



.. py:class:: SAMLLMHostCompute

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - LLMHostCompute.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMLLMHostComputeMetadata

      LLMHostCompute.metadata[obj]: Required, the LLMHostCompute metadata.


   .. py:attribute:: spec
      :type: SAMLLMHostComputeSpec

      LLMHostCompute.spec[obj]: Required, the LLMHostCompute specification.


   .. py:attribute:: status
      :type: smarter.models.sam.llmhostcompute.SAMLLMHostComputeStatus | None

      LLMHostCompute.status[obj]: Optional, Read-only.

      Stateful status information about the LLMHostCompute.
