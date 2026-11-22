# The Smarter Project Helm Chart

A Helm chart for deploying The Smarter Project, a no-code, cloud-native
AI resource management and orchestration platform.

- **Website:** [https://smarter.sh](https://smarter.sh)
- **Docs:** [https://docs.smarter.sh/](https://docs.smarter.sh/)
- **Chart:** [https://artifacthub.io/packages/helm/project-smarter/smarter](https://artifacthub.io/packages/helm/project-smarter/smarter)
- **Dockerhub** [https://hub.docker.com/r/mcdaniel0073/smarter](https://hub.docker.com/r/mcdaniel0073/smarter)

## Quickstart

On a cluster that [smarter-infrastructure](https://github.com/smarter-sh/smarter-infrastructure)
built, install into the environment's namespace, e.g. `smarter-platform-prod`:

```bash
helm upgrade --install smarter oci://ghcr.io/smarter-sh/charts/smarter \
  --version <chart-version> \
  --timeout 900s \
  --namespace smarter-platform-prod \
  --values my-values.yaml
```

The chart reads the database, administrator, email and Django credentials from the Kubernetes Secrets
that smarter-infrastructure creates in that namespace (`infrastructureSecrets` in values.yaml), and
derives the settings module, the Celery broker, the namespace and the S3 bucket. Your values file sets
the rest: the domain, the environment, the cluster, the IAM roles and your API keys. On another
cluster, also set the database's `env.SMARTER_SUBSYSTEM_SQL_*` values and `env.DJANGO_SECRET_KEY`.

See [values.yaml](https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml)
for all available configuration options. A value left at its `SET-ME` placeholder is left out of the
pods' environment, so Smarter's own default applies.

The chart stores `env` in a [Kubernetes Secret](https://kubernetes.io/docs/concepts/configuration/secret/),
`<global.appName>-env`, and every pod reads it with `envFrom`, so passwords and API keys aren't written
into the pod specs of the Deployments, the init Job or the backup CronJob. A changed value rolls the
Deployments. Keep your values file out of source control, or supply its secrets with `--set` from your
CI's secret store.

## Prerequisites

- Kubernetes >=1.34.0
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
