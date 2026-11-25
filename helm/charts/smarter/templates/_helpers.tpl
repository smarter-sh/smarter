{{/*
The directories that the processes of the Smarter image write at runtime. Every other path
in the image is read-only: the Dockerfile's permissions stage makes root the owner of the
code and the virtualenv, and global.containerSecurityContext.readOnlyRootFilesystem makes
the whole root filesystem read-only. Each of these is an emptyDir, which, like the
container's own filesystem, lasts as long as the pod.

- /tmp: temporary files, e.g. load_from_github's clones, extension staging, the init job's log
- .cache: python packages' caches, e.g. tldextract's public suffix list
- data/.kube: the kubeconfig that aws eks update-kubeconfig writes
- data/celery: celery beat's schedule file
- data/media: Django's media storage, when the platform is not configured for S3
- data/manifests/example_manifests: the output of manage.py generate_example_manifests

The rest of data/ stays the image's own, read from the image.
*/}}
{{- define "smarter.writableVolumes" -}}
- name: smarter-tmp
  emptyDir: {}
- name: smarter-cache
  emptyDir: {}
- name: smarter-data-kube
  emptyDir: {}
- name: smarter-data-celery
  emptyDir: {}
- name: smarter-data-media
  emptyDir: {}
- name: smarter-data-example-manifests
  emptyDir: {}
{{- end }}

{{- define "smarter.writableVolumeMounts" -}}
- name: smarter-tmp
  mountPath: /tmp
- name: smarter-cache
  mountPath: /home/smarter_user/.cache
- name: smarter-data-kube
  mountPath: /home/smarter_user/data/.kube
- name: smarter-data-celery
  mountPath: /home/smarter_user/data/celery
- name: smarter-data-media
  mountPath: /home/smarter_user/data/media
- name: smarter-data-example-manifests
  mountPath: /home/smarter_user/data/manifests/example_manifests
{{- end }}

{{/*
The platform's environment: the settings that every pod reads, from the Secret in secret-env.yaml.

  {{- $env := include "smarter.env" . | fromYaml }}

It starts from .Values.env, then:

- leaves out every null value, e.g. the AWS keys when the pods have an IAM role, and every
  SET-ME placeholder, so that a setting nobody set gets Smarter's own default rather than the
  placeholder's text;
- derives what follows from the other values, unless .Values.env sets it:
  DJANGO_SETTINGS_MODULE from SMARTER_ENVIRONMENT, DJANGO_CELERY_BROKER_URL from the chart's Redis
  and the release's namespace, SMARTER_SUBSYSTEM_K8S_NAMESPACE (the release's namespace), and
  SMARTER_PLATFORM_S3_BUCKET, which smarter-infrastructure names after the environment's platform
  domain: <subdomain>.<root domain> in prod, <environment>.<subdomain>.<root domain> elsewhere;
- reads the Kubernetes Secrets that smarter-infrastructure creates in the release's namespace
  (infrastructureSecrets in values.yaml): the database, administrator, email and Django
  credentials. A value read from one of them supersedes .Values.env, because the infrastructure
  created the credential it describes. A Secret that doesn't exist, as in `helm template`, which
  can't read the cluster, is skipped.
*/}}
{{- define "smarter.env" -}}
{{- $env := dict -}}
{{- range $key, $value := .Values.env -}}
{{- $isNull := kindIs "invalid" $value -}}
{{- $isPlaceholder := and (kindIs "string" $value) (hasPrefix "SET-ME" $value) -}}
{{- if not (or $isNull $isPlaceholder) -}}
{{- $_ := set $env $key $value -}}
{{- end -}}
{{- end -}}
{{- $environment := get $env "SMARTER_ENVIRONMENT" | default "prod" -}}
{{- $subdomain := get $env "SMARTER_PLATFORM_SUBDOMAIN" | default "platform" -}}
{{- $rootDomain := get $env "SMARTER_PLATFORM_ROOT_DOMAIN" | default "example.com" -}}
{{- $prefix := ternary "" (printf "%s." $environment) (eq $environment "prod") -}}
{{- $redis := printf "%s-master.%s.svc.cluster.local:6379" .Values.redis.fullnameOverride .Release.Namespace -}}
{{- $_ := set $env "DJANGO_SETTINGS_MODULE" (get $env "DJANGO_SETTINGS_MODULE" | default (printf "smarter.settings.%s" $environment)) -}}
{{- $_ := set $env "DJANGO_CELERY_BROKER_URL" (get $env "DJANGO_CELERY_BROKER_URL" | default (printf "redis://:%s@%s/0" .Values.redis.auth.password $redis)) -}}
{{- $_ := set $env "SMARTER_SUBSYSTEM_K8S_NAMESPACE" (get $env "SMARTER_SUBSYSTEM_K8S_NAMESPACE" | default .Release.Namespace) -}}
{{- $_ := set $env "SMARTER_PLATFORM_S3_BUCKET" (get $env "SMARTER_PLATFORM_S3_BUCKET" | default (printf "%s%s.%s" $prefix $subdomain $rootDomain)) -}}
{{- if .Values.infrastructureSecrets.enabled -}}
{{- range $secretName, $keys := .Values.infrastructureSecrets.secrets -}}
{{- $secret := lookup "v1" "Secret" $.Release.Namespace $secretName -}}
{{- $data := get $secret "data" | default dict -}}
{{- range $secretKey, $envName := $keys -}}
{{- if hasKey $data $secretKey -}}
{{- $_ := set $env $envName (get $data $secretKey | b64dec) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- toYaml $env -}}
{{- end }}

{{/*
The init container that holds a pod of a fresh install until its database is migrated.

On an install, Helm starts the Deployments' pods as soon as it creates them, but the database, its
user and its schema are created later, by the post-install init Job (job-init.yaml). Without this,
the api answers 500 and the Celery workers and beat crash and restart until the Job has migrated.
This container runs `manage.py migrate --check`, which fails while the database is missing,
unreachable or has unapplied migrations, every 10 seconds until it passes, so that the pod's own
containers start on a migrated database.

Only on an install: on an upgrade, the pre-upgrade Job (job-migrate.yaml) has already migrated
before the rollout, so new pods don't wait, and don't pay for a Django start of their own. The next
upgrade's pods have no init container.

  {{- include "smarter.waitForDatabase" . | nindent 6 }}   (in a pod's spec, at its initContainers' level)
*/}}
{{- define "smarter.waitForDatabase" -}}
{{- if .Release.IsInstall -}}
initContainers:
  - name: "{{ .Values.global.appName }}-wait-for-database"
    image: '{{ .Values.env.SMARTER_DOCKER_IMAGE | default (printf "%s:%s" .Values.global.image.repository .Values.global.image.tag) }}'
    imagePullPolicy: {{ .Values.global.image.pullPolicy | default "Always" }}
    command:
      - /bin/sh
      - -c
      - |
        until python manage.py migrate --check > /dev/null 2>&1; do
          echo "Waiting for the init job to create and migrate the database..."
          sleep 10
        done
        echo "The database is migrated."
    resources:
      requests:
        memory: "256Mi"
        cpu: "50m"
      limits:
        memory: "1Gi"
        cpu: "1"
    # the platform's environment, from the Secret in secret-env.yaml, for the database's credentials.
    envFrom:
      - secretRef:
          name: "{{ .Values.global.appName }}-env"
    env:
      - name: PYTHONUNBUFFERED
        value: "1"
    securityContext:
      {{- toYaml .Values.global.containerSecurityContext | nindent 6 }}
    volumeMounts:
      {{- include "smarter.writableVolumeMounts" . | nindent 6 }}
{{- end }}
{{- end }}

{{/*
The names of the api's Deployments, and of their Services, HorizontalPodAutoscalers and
PodDisruptionBudgets, comma-separated: <appName>-api, and while api.legacyName.enabled is true,
<appName> too, the name that they had before.

The api was renamed from <appName> to <appName>-api in v0.43.0. With api.legacyName.enabled, a release
runs both Deployments, whose pods share the label app.kubernetes.io/component: api, which both
Services select, so that the rename drops no request: Helm creates the new Deployment before an
upgrade with the flag off deletes the old one, and the Ingresses that still name the old Service keep
working until they are updated. It is off by default, since v0.43.0 has been deployed: an install
that upgrades from an older release turns it on for one upgrade (see values.yaml).

  {{- range $name := splitList "," (include "smarter.apiNames" .) }} ... {{- end }}
*/}}
{{- define "smarter.apiNames" -}}
{{- $names := list (printf "%s-api" .Values.global.appName) -}}
{{- if .Values.api.legacyName.enabled -}}
{{- $names = append $names .Values.global.appName -}}
{{- end -}}
{{- join "," $names -}}
{{- end }}
