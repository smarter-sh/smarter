# Smarter Helm Chart

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/project-smarter)](https://artifacthub.io/packages/search?repo=project-smarter)

A Helm chart for deploying Smarter API and web console to Kubernetes.

## Description

**Smarter** is a platform for managing and orchestrating AI resources. This Helm chart deploys the REST API and web console components.

## Prerequisites

- Kubernetes >=1.28.0
- Helm 3.x
- MySQL database
- Redis cache

## Installation

### Install from OCI registry

```bash
helm upgrade --install smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --namespace your-namespace \
  --create-namespace \
  --timeout 900s \
  --values values.yaml
```

### Install from GitHub Container Registry

```bash
docker pull ghcr.io/smarter-sh/charts/smarter:0.7.6
```

## Configuration

See [values.yaml](./values.yaml) for all available configuration options.

### Required Configuration

Create a `values.yaml` file with your configuration:

```yaml
env:
  # Django settings
  DJANGO_SETTINGS_MODULE: "smarter.settings.prod"
  ENVIRONMENT: "production"

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

## Parameters

### Common Parameters

| Name | Description | Default |
|------|-------------|---------|
| `env.DJANGO_SETTINGS_MODULE` | Django settings module | `smarter.settings.prod` |
| `env.ENVIRONMENT` | Deployment environment | `prod` |
| `env.DEBUG_MODE` | Enable debug mode | `false` |
| `env.ROOT_DOMAIN` | Root domain | `example.com` |

### Database Configuration

| Name | Description | Default |
|------|-------------|---------|
| `env.MYSQL_HOST` | MySQL hostname | Required |
| `env.MYSQL_PORT` | MySQL port | `3306` |
| `env.MYSQL_DATABASE` | Database name | Required |
| `env.MYSQL_USER` | Database user | Required |
| `env.MYSQL_PASSWORD` | Database password | Required |

### AI Service API Keys

| Name | Description | Default |
|------|-------------|---------|
| `env.OPENAI_API_KEY` | OpenAI API key | Required |
| `env.GEMINI_API_KEY` | Google Gemini API key | Optional |
| `env.LLAMA_API_KEY` | Meta Llama API key | Optional |

## Support

- [GitHub Issues](https://github.com/smarter-sh/smarter/issues)
- [Documentation](https://platform.smarter.sh/docs/)

## License

AGPL-3.0
