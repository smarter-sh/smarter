..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMLLMHost
==========

``smarter.models.sam.llmhost``
------------------------------

.. py:module:: smarter.models.sam.llmhost

SAM model of the ``LLMHost`` kind, generated from the Smarter platform's JSON Schema.

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



.. py:class:: ApiFormat

   Bases: :class:`enum.Enum`

   LLMHost.spec.engine.apiFormat[str]: the wire protocol.

   One of: ['openai_compatible', 'huggingface', 'ollama_native', 'custom'].


.. py:class:: Name

   Bases: :class:`enum.Enum`

   LLMHost.spec.engine.name[str]: the inference server.

   One of: ['vllm', 'tgi', 'sglang', 'llama_cpp', 'ollama', 'tei', 'custom'].


.. py:class:: SAMLLMHostEngineConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.engine: the inference server.

   The common settings, e.g. ``contextLength``, are translated into each engine's own
   arguments, e.g. vLLM's ``--max-model-len`` and llama.cpp's ``--ctx-size``. ``args`` and
   ``env`` are passed to the engine as they are, for everything else.

   .. py:attribute:: apiFormat
      :type: smarter.models.sam.llmhost.ApiFormat | None

      LLMHost.spec.engine.apiFormat[str]: the wire protocol.

      One of: ['openai_compatible', 'huggingface', 'ollama_native', 'custom'].


   .. py:attribute:: args
      :type: list[str] | None

      LLMHost.spec.engine.args[list]: additional arguments, passed to the engine as they are.


   .. py:attribute:: command
      :type: list[str] | None

      LLMHost.spec.engine.command[list]: overrides the image's entrypoint.

      For custom engines.


   .. py:attribute:: contextLength
      :type: Optional

      LLMHost.spec.engine.contextLength[int]: the maximum context the server allocates, in tokens.


   .. py:attribute:: dtype
      :type: str | None

      LLMHost.spec.engine.dtype[str]: e.g. auto, bfloat16, float16.


   .. py:attribute:: env
      :type: dict[str, str] | None

      LLMHost.spec.engine.env[dict]: additional environment variables.


   .. py:attribute:: gpuMemoryUtilization
      :type: Optional

      LLMHost.spec.engine.gpuMemoryUtilization[float]: the fraction of GPU memory the server may use.


   .. py:attribute:: image
      :type: str | None

      LLMHost.spec.engine.image[str]: the container image.

      Defaults to the engine's official image. Pin a version in production. Required for custom.


   .. py:attribute:: maxConcurrentRequests
      :type: Optional

      LLMHost.spec.engine.maxConcurrentRequests[int]: the requests that one replica serves at once.


   .. py:attribute:: name
      :type: Name

      LLMHost.spec.engine.name[str]: the inference server.

      One of: ['vllm', 'tgi', 'sglang', 'llama_cpp', 'ollama', 'tei', 'custom'].


   .. py:attribute:: port
      :type: Optional

      LLMHost.spec.engine.port[int]: the container port.

      Defaults to the engine's port. Required for custom.


   .. py:attribute:: tensorParallelSize
      :type: Optional

      LLMHost.spec.engine.tensorParallelSize[int]: the GPUs that one replica shards the model across.


   .. py:attribute:: trustRemoteCode
      :type: bool | None

      LLMHost.spec.engine.trustRemoteCode[bool]: run Python code from the model repository.

      Only for repositories that you trust.



.. py:class:: SAMLLMHostHealthCheck

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.healthCheck: the probes that decide when a replica is ready.

   .. py:attribute:: path
      :type: str | None

      LLMHost.spec.healthCheck.path[str]: the HTTP health path.

      Defaults to the engine's, e.g. /health.


   .. py:attribute:: periodSeconds
      :type: Optional

      LLMHost.spec.healthCheck.periodSeconds[int]: how often the probes run.


   .. py:attribute:: startupTimeoutSeconds
      :type: Optional

      LLMHost.spec.healthCheck.startupTimeoutSeconds[int]: the time the server has to download and load the weights before it is restarted.

      Large models need more.



.. py:class:: SAMLLMHostMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHost Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, str | int | float | bool | datetime.date | datetime.datetime | uuid.UUID | bytes | list | dict[str, Any]]]

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



.. py:class:: Quantization

   Bases: :class:`enum.Enum`

   LLMHost.spec.model.quantization[str]: the weights' precision.

   One of: ['none', 'fp32', 'fp16', 'bf16', 'fp8', 'mxfp4', 'int8', 'int4', 'gguf', 'awq', 'gptq'].


.. py:class:: Source

   Bases: :class:`enum.Enum`

   LLMHost.spec.model.source[str]: where the weights come from.

   One of: ['huggingface', 'ollama', 's3', 'url', 'pvc'].


.. py:class:: Task

   Bases: :class:`enum.Enum`

   LLMHost.spec.model.task[str]: what the model does.

   One of: ['text-generation', 'embedding'].


.. py:class:: SAMLLMHostModelCapabilities

   Bases: :class:`smarter.models.sam.base.SAMModel`

   What the model can do.

   Informational, for discovery and for the LLMClients that use it.

   .. py:attribute:: functionCalling
      :type: bool | None

      LLMHost.spec.model.capabilities.functionCalling[bool]: supports tool calls.

      Some engines also require args, e.g. vLLM's --enable-auto-tool-choice and --tool-call-parser.


   .. py:attribute:: reasoning
      :type: bool | None

      LLMHost.spec.model.capabilities.reasoning[bool]: a reasoning model.


   .. py:attribute:: streaming
      :type: bool | None

      LLMHost.spec.model.capabilities.streaming[bool]: streams responses.


   .. py:attribute:: vision
      :type: bool | None

      LLMHost.spec.model.capabilities.vision[bool]: accepts images.



.. py:class:: SAMLLMHostNetwork

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.network: how the LLMHost is reached.

   It is always reachable inside the cluster, at its Service. With ``ingress``, it is also
   reachable at ``https://<hostname>``, with a TLS certificate from cert-manager. A public
   endpoint requires an API key, unless ``allowUnauthenticated``.

   .. py:attribute:: allowUnauthenticated
      :type: bool | None

      LLMHost.spec.network.allowUnauthenticated[bool]: permit an Ingress for an engine that does not authenticate requests, e.g. tgi and ollama.

      Anyone who knows the hostname can use the model.


   .. py:attribute:: apiKeySecret
      :type: str | None

      LLMHost.spec.network.apiKeySecret[str]: the name of a Smarter Secret with the API key that clients must send as a Bearer token.

      If omitted, Smarter generates one when the LLMHost is launched, and stores it in the Secret llmhost\_<name>_api_key.


   .. py:attribute:: hostname
      :type: str | None

      LLMHost.spec.network.hostname[str]: the Ingress hostname.

      Defaults to <name>.llmhost.<account number>.<environment API domain>.


   .. py:attribute:: ingress
      :type: bool | None

      LLMHost.spec.network.ingress[bool]: create an Ingress.



.. py:class:: SAMLLMHostResources

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.resources: the compute that each replica, one pod, requests.

   These are the pod's resource requests, not a node's capacity. They must fit a node of the
   LLMHost's compute, which also determines the GPU model.

   .. py:attribute:: cpu
      :type: str | None

      LLMHost.spec.resources.cpu[str]: the pod's CPU request, e.g. 4 or 3500m.


   .. py:attribute:: gpuCount
      :type: Optional

      LLMHost.spec.resources.gpuCount[int]: the GPUs per replica.

      0 runs on CPU.


   .. py:attribute:: gpuResource
      :type: str | None

      LLMHost.spec.resources.gpuResource[str]: the Kubernetes extended resource, e.g. nvidia.com/gpu.


   .. py:attribute:: memory
      :type: str | None

      LLMHost.spec.resources.memory[str]: the pod's memory request and limit, e.g. 24Gi.


   .. py:attribute:: nodeSelector
      :type: dict[str, str] | None

      LLMHost.spec.resources.nodeSelector[dict]: additional node labels.


   .. py:attribute:: serviceAccountName
      :type: str | None

      LLMHost.spec.resources.serviceAccountName[str]: e.g. for IRSA access to an S3 model source.


   .. py:attribute:: shmSize
      :type: str | None

      LLMHost.spec.resources.shmSize[str]: the size of /dev/shm.


   .. py:attribute:: tolerations
      :type: list[dict[str, Any]] | None

      LLMHost.spec.resources.tolerations[list]: Kubernetes tolerations.

      When gpuCount > 0, a toleration of the gpuResource taint is added.


   .. py:attribute:: vramRequiredGb
      :type: Optional

      LLMHost.spec.resources.vramRequiredGb[int]: the GPU memory the model requires.

      Informational.



.. py:class:: SAMLLMHostScaling

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.scaling: the replicas.

   .. py:attribute:: replicas
      :type: Optional

      LLMHost.spec.scaling.replicas[int]: the replicas.

      More than one requires storage.accessMode ReadWriteMany or ReadOnlyMany.



.. py:class:: SAMLLMHostStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHost Manifest - Status class.

   Read only. Besides ownership, it reports the LLMHost's lifecycle state, where it can be
   reached, and its accumulated cost, as of its most recent status check.

   .. py:attribute:: accountNumber
      :type: str

      LLMHost.status.account_number: The account owner of this LLMHost.

      Read only.


   .. py:attribute:: apiKeySecret
      :type: str | None

      LLMHost.status.apiKeySecret: the Smarter Secret with the API key, if any.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.llmhost.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: deployedAt
      :type: datetime.datetime | None

      LLMHost.status.deployedAt: when it was last launched.

      Read only.


   .. py:attribute:: endpoint
      :type: str | None

      LLMHost.status.endpoint: the base URL inside the cluster, e.g. for LLMClients.

      Read only.


   .. py:attribute:: estimatedCost
      :type: float | str | None

      LLMHost.status.estimatedCost: uptimeHours times replicas times each replica's share of its compute's node price. Read only.


   .. py:attribute:: healthy
      :type: bool | None

      LLMHost.status.healthy: the result of the last health check.

      Read only.


   .. py:attribute:: hostStatus
      :type: str | None

      LLMHost.status.hostStatus: the lifecycle state, e.g. pending, active or error.

      Read only.


   .. py:attribute:: lastCheckedAt
      :type: datetime.datetime | None

      LLMHost.status.lastCheckedAt: when its status was last checked.

      Read only.


   .. py:attribute:: message
      :type: str | None

      LLMHost.status.message: why the LLMHost is in its state, e.g. a container error.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: publicUrl
      :type: str | None

      LLMHost.status.publicUrl: the base URL of the Ingress, if any.

      Read only.


   .. py:attribute:: readyReplicas
      :type: int | None

      LLMHost.status.readyReplicas: ready.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: replicas
      :type: int | None

      LLMHost.status.replicas: desired.

      Read only.


   .. py:attribute:: uptimeHours
      :type: float | None

      LLMHost.status.uptimeHours: hours since deployedAt.

      Read only.


   .. py:attribute:: username
      :type: str

      LLMHost.status.username: The Smarter user who created this LLMHost.

      Read only.



.. py:class:: AccessMode

   Bases: :class:`enum.Enum`

   LLMHost.spec.storage.accessMode[str]: One of: ['ReadWriteOnce', 'ReadWriteMany', 'ReadOnlyMany'].


.. py:class:: SAMLLMHostStorage

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.storage: the model volume, a PersistentVolumeClaim mounted at /models.

   It caches the weights, so that a restarted server does not download them again. The
   cluster's storage class provisions its PersistentVolume.

   .. py:attribute:: accessMode
      :type: smarter.models.sam.llmhost.AccessMode | None

      LLMHost.spec.storage.accessMode[str]: One of: ['ReadWriteOnce', 'ReadWriteMany', 'ReadOnlyMany'].


   .. py:attribute:: existingClaim
      :type: str | None

      LLMHost.spec.storage.existingClaim[str]: an existing PersistentVolumeClaim to mount, instead of creating one.

      Required when model.source is pvc.


   .. py:attribute:: retain
      :type: bool | None

      LLMHost.spec.storage.retain[bool]: keep the volume, and its downloaded weights, on undeploy.

      It is always deleted when the LLMHost is deleted.


   .. py:attribute:: size
      :type: str | None

      LLMHost.spec.storage.size[str]: e.g. 50Gi.


   .. py:attribute:: storageClass
      :type: str | None

      LLMHost.spec.storage.storageClass[str]: defaults to the cluster's default class.



.. py:class:: SAMLLMHostModel

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Spec.model: what is served, and where its weights come from.

   .. py:attribute:: architecture
      :type: str | None

      LLMHost.spec.model.architecture[str]: e.g. llama, qwen3, gemma3.


   .. py:attribute:: capabilities
      :type: smarter.models.sam.llmhost.SAMLLMHostModelCapabilities | None

      LLMHost.spec.model.capabilities[object]: what the model can do.


   .. py:attribute:: contextWindow
      :type: Optional

      LLMHost.spec.model.contextWindow[int]: the model's maximum context, in tokens.


   .. py:attribute:: embeddingDimensions
      :type: Optional

      LLMHost.spec.model.embeddingDimensions[int]: for embedding models.


   .. py:attribute:: file
      :type: str | None

      LLMHost.spec.model.file[str]: a single weights file within the repository, e.g. a GGUF file for llama_cpp.

      For ollama with a Hugging Face source, the quantization tag, e.g. Q4_K_M.


   .. py:attribute:: license
      :type: str | None

      LLMHost.spec.model.license[str]: e.g. apache-2.0.


   .. py:attribute:: parameterCount
      :type: Optional

      LLMHost.spec.model.parameterCount[int]: the number of parameters.


   .. py:attribute:: quantization
      :type: smarter.models.sam.llmhost.Quantization | None

      LLMHost.spec.model.quantization[str]: the weights' precision.

      One of: ['none', 'fp32', 'fp16', 'bf16', 'fp8', 'mxfp4', 'int8', 'int4', 'gguf', 'awq', 'gptq'].


   .. py:attribute:: repository
      :type: str

      LLMHost.spec.model.repository[str]: the model, in the source's terms: a Hugging Face repository id, e.g. Qwen/Qwen3-8B; an Ollama tag, e.g. llama3.1:8b; an S3 prefix, e.g. s3://bucket/models/qwen3; a URL; or, for pvc, a path within the volume.


   .. py:attribute:: revision
      :type: str | None

      LLMHost.spec.model.revision[str]: a Hugging Face branch, tag or commit SHA.

      Pin a commit SHA for reproducible deployments. Defaults to main.


   .. py:attribute:: servedName
      :type: str | None

      LLMHost.spec.model.servedName[str]: the model name that clients send in their requests.

      Defaults to the LLMHost's name. Ollama always uses repository.


   .. py:attribute:: source
      :type: smarter.models.sam.llmhost.Source | None

      LLMHost.spec.model.source[str]: where the weights come from.

      One of: ['huggingface', 'ollama', 's3', 'url', 'pvc'].


   .. py:attribute:: task
      :type: smarter.models.sam.llmhost.Task | None

      LLMHost.spec.model.task[str]: what the model does.

      One of: ['text-generation', 'embedding'].


   .. py:attribute:: tokenSecret
      :type: str | None

      LLMHost.spec.model.tokenSecret[str]: the name of a Smarter Secret with a Hugging Face access token, for gated models, e.g. Llama and Gemma.

      You must also accept the model's license on huggingface.co.



.. py:class:: SAMLLMHostSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMHost Manifest LLMHost.spec.

   .. py:attribute:: compute
      :type: str | None

      LLMHost.spec.compute[str]: the LLMHostCompute that the LLMHost runs on, e.g. gpu_l4_1x.

      Defaults to the cheapest one that its resources fit.


   .. py:attribute:: engine
      :type: SAMLLMHostEngineConfig

      LLMHost.spec.engine[object]: the inference server.


   .. py:attribute:: healthCheck
      :type: smarter.models.sam.llmhost.SAMLLMHostHealthCheck | None

      LLMHost.spec.healthCheck[object]: probes.


   .. py:attribute:: model
      :type: SAMLLMHostModel

      LLMHost.spec.model[object]: what is served.


   .. py:attribute:: network
      :type: smarter.models.sam.llmhost.SAMLLMHostNetwork | None

      LLMHost.spec.network[object]: reachability.


   .. py:attribute:: resources
      :type: smarter.models.sam.llmhost.SAMLLMHostResources | None

      LLMHost.spec.resources[object]: compute.


   .. py:attribute:: scaling
      :type: smarter.models.sam.llmhost.SAMLLMHostScaling | None

      LLMHost.spec.scaling[object]: replicas.


   .. py:attribute:: storage
      :type: smarter.models.sam.llmhost.SAMLLMHostStorage | None

      LLMHost.spec.storage[object]: the model volume.



.. py:class:: SAMLLMHost

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - LLMHost.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMLLMHostMetadata

      LLMHost.metadata[obj]: Required, the LLMHost metadata.


   .. py:attribute:: spec
      :type: SAMLLMHostSpec

      LLMHost.spec[obj]: Required, the LLMHost specification.


   .. py:attribute:: status
      :type: smarter.models.sam.llmhost.SAMLLMHostStatus | None

      LLMHost.status[obj]: Optional, Read-only.

      Stateful status information about the LLMHost.
