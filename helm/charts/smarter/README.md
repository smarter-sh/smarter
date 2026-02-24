# The Smarter Project Helm Chart

A Helm chart for deploying The Smarter Project, a no-code, cloud-native
AI resource management and orchestration platform.

- **Website:** [https://smarter.sh](https://smarter.sh)
- **Docs:** [https://docs.smarter.sh/](https://docs.smarter.sh/)
- **Chart:** [https://artifacthub.io/packages/helm/project-smarter/smarter](https://artifacthub.io/packages/helm/project-smarter/smarter)
- **Dockerhub** [https://hub.docker.com/r/mcdaniel0073/smarter](https://hub.docker.com/r/mcdaniel0073/smarter)

## Quickstart

```bash
helm upgrade --install --force smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version 0.13.142 \
  --timeout 900s \
  --namespace smarter-prod \
  --create-namespace \
  --set env.MYSQL_HOST=your-mysql-host \
  --set env.MYSQL_PASSWORD=your-password \
  --set env.OPENAI_API_KEY=your-key \
  --set env.SECRET_KEY=your-django-secret \
  --set env.FERNET_ENCRYPTION_KEY=your-fernet-key \
  --values values.yaml
```

See [values.yaml](https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml)
for all available configuration options.

**Note:** For production, use [Kubernetes secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
to manage sensitive values like passwords and API keys.

## Prerequisites

- Kubernetes >=1.28.0
- Helm 3.8+

## Installation

First, ensure you are using Helm 3.8.0 or later, as OCI support is required.

Then install the chart directly from the OCI registry:

```bash
helm install smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version <chart-version> \
  --namespace your-namespace \
  --create-namespace \
  --values values.yaml
```

Replace `<chart-version>` with the desired chart version (see [Artifact Hub: project-smarter/smarter](https://artifacthub.io/packages/helm/project-smarter/smarter)
for available versions).

## Upgrading

```bash
helm upgrade smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version <new-chart-version> \
  --namespace your-namespace \
  --values values.yaml
```

## Uninstalling

```bash
helm uninstall smarter --namespace your-namespace
```

## Configuration

This chart is designed to support automated CI-CD through the use of environment
variables for all application configuration options. See the top of [values.yaml](./values.yaml)
for all configuration options that are available as environment variables.
Any of these that are are set in the environment session will be
consumed automatically during helm deployment. All other defined Helm chart
options are set normally, via helm.
