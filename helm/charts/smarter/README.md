# Smarter Helm Chart

A Helm chart for deploying Smarter, a no-code, cloud-native AI orchestration platform, to Kubernetes.

- **Website:** [https://smarter.sh](https://smarter.sh)
- **Docs:** [https://platform.smarter.sh/docs/](https://platform.smarter.sh/docs/)
- **Chart:** [https://artifacthub.io/packages/helm/project-smarter/smarter](https://artifacthub.io/packages/helm/project-smarter/smarter)

## Quickstart

```bash
helm upgrade --install --force smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version 0.8.8 \
  --timeout 900s \
  --namespace smarter-prod \
  --create-namespace \
  --set env.MYSQL_HOST=your-mysql-host \
  --set env.MYSQL_PASSWORD=your-password \
  --set env.OPENAI_API_KEY=your-key \
  --set env.SECRET_KEY=your-django-secret \
  --set env.FERNET_ENCRYPTION_KEY=your-fernet-key
```

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

Replace `<chart-version>` with the desired chart version (see [Artifact Hub: project-smarter/smarter](https://artifacthub.io/packages/helm/project-smarter/smarter) for available versions).

## Upgrading

```bash
helm upgrade smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version <new-chart-version> \
  --namespace your-namespace \
  --values values.yaml
```

See [values.yaml](https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml) for all available configuration options.

**Note:** For production, use [Kubernetes secrets](https://kubernetes.io/docs/concepts/configuration/secret/) to manage sensitive values like passwords and API keys.

## Uninstalling

```bash
helm uninstall smarter --namespace your-namespace
```

## Configuration

See [values.yaml](./values.yaml) for all available configuration options.

### Required Configuration

```yaml
env:
  # Django settings
  DJANGO_SETTINGS_MODULE: "smarter.settings.prod"
  ENVIRONMENT: "prod"

  # Database (required)
  MYSQL_HOST: "your-mysql-host"
  MYSQL_DATABASE: "smarter"
  MYSQL_USER: "smarter"
  MYSQL_PASSWORD: "your-password"

  # Redis (required)
  CACHES_LOCATION: "redis://your-redis:6379/0"
  CELERY_BROKER_URL: "redis://your-redis:6379/0"

  # API Keys (required)
  OPENAI_API_KEY: "your-key"
  SECRET_KEY: "your-django-secret"
  FERNET_ENCRYPTION_KEY: "your-fernet-key"
```
