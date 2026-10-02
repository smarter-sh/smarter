# Built-in LLMHosts and LLMHostCompute

`llmhost/` contains example LLMHost manifests for the most popular open-weight models on
Hugging Face and in the Ollama library. Together they demonstrate every inference engine
(vLLM, SGLang, TGI, llama.cpp, Ollama and Text Embeddings Inference) and the huggingface,
ollama and url model sources, on GPU and CPU nodes.

They are also the `builtin` model catalog of `LLMHostService.search_models(catalog="builtin")`.

`compute/` contains the built-in LLMHostCompute manifests: the kinds of node that LLMHosts run
on, from a small CPU node to eight NVIDIA H100s. Each LLMHostCompute is one EKS managed node
group, which Smarter creates when an LLMHost first needs one of its nodes, and whose nodes it adds
and removes as LLMHosts are launched and destroyed. An LLMHost names its compute in
`spec.compute`, and its `spec.resources` must fit that node.

`manage.py initialize_platform` applies both, for the Smarter admin, so that every account may use
them: `add_builtin_llmhost_compute`, then `add_builtin_llmhost`.

Apply one with the Smarter CLI, then launch it:

```console
smarter apply -f llama-3.1-8b-instruct.yaml
smarter deploy llmhost llama_3_1_8b_instruct
smarter describe llmhost llama_3_1_8b_instruct
smarter describe llmhostcompute gpu_a10g_1x
```

Gated models (Llama, Gemma, Mistral) need a Hugging Face access token in a Smarter Secret
named `huggingface_token`, and their license accepted on huggingface.co.

## Node groups

Smarter's IAM identity needs `eks:CreateNodegroup`, `eks:DescribeNodegroup`,
`eks:ListNodegroups`, `eks:UpdateNodegroupConfig`, `eks:DeleteNodegroup`, `eks:TagResource`,
`autoscaling:TerminateInstanceInAutoScalingGroup`, and `iam:PassRole` on the node role.

A node group's IAM role and subnets are `SMARTER_LLMHOST_NODE_ROLE_ARN` and
`SMARTER_LLMHOST_NODE_SUBNET_IDS`, if they are set, else those of the cluster's own node group. A
model volume is an EBS volume in one availability zone, so one subnet per node group keeps an
LLMHost's node in the same zone as its retained volume. GPU nodes need the NVIDIA device plugin,
which advertises their GPUs to Kubernetes.

You'll find these in /home/smarter_user/data/manifests/ inside the Docker container.
