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
  DJANGO_SETTINGS_MODULE from SMARTER_ENVIRONMENT, DJANGO_CELERY_BROKER_URL from the chart's Redis,
  the release's namespace and Redis's password (SMARTER_SUBSYSTEM_REDIS_PASSWORD, read from a Secret below), SMARTER_SUBSYSTEM_K8S_NAMESPACE (the release's namespace), and
  SMARTER_PLATFORM_S3_BUCKET, which smarter-infrastructure names after the environment's platform
  domain: <subdomain>.<root domain> in prod, <environment>.<subdomain>.<root domain> elsewhere;
  and, with workerTools.enabled, SMARTER_APP_LLMTOOL_TOOL_RUNNER=remote, which sends the app's tool
  calls to the tool worker;
- reads the Kubernetes Secrets that smarter-infrastructure creates in the release's namespace
  (infrastructureSecrets in values.yaml): the database, administrator, email, Django and Redis
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
{{- $_ := set $env "SMARTER_SUBSYSTEM_K8S_NAMESPACE" (get $env "SMARTER_SUBSYSTEM_K8S_NAMESPACE" | default .Release.Namespace) -}}
{{- $_ := set $env "SMARTER_PLATFORM_S3_BUCKET" (get $env "SMARTER_PLATFORM_S3_BUCKET" | default (printf "%s%s.%s" $prefix $subdomain $rootDomain)) -}}
{{- if (.Values.workerTools | default dict).enabled -}}
{{- $_ := set $env "SMARTER_APP_LLMTOOL_TOOL_RUNNER" (get $env "SMARTER_APP_LLMTOOL_TOOL_RUNNER" | default "remote") -}}
{{- end -}}
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
{{- /* after the Secrets, which hold Redis's password. Without it, the broker's url is left out, and
       smarter.settings.base_aws refuses to start with a message that names the missing setting. */ -}}
{{- $redisPassword := get $env "SMARTER_SUBSYSTEM_REDIS_PASSWORD" | default "" -}}
{{- if and (not (hasKey $env "DJANGO_CELERY_BROKER_URL")) $redisPassword -}}
{{- $_ := set $env "DJANGO_CELERY_BROKER_URL" (printf "redis://:%s@%s/0" (urlquery $redisPassword) $redis) -}}
{{- end -}}
{{- toYaml $env -}}
{{- end }}

{{/*
The tool worker's environment, from its own Secret in secret-env-tools.yaml (ADR-038).

  {{- $env := include "smarter.toolsEnv" . | fromYaml }}

Only what it needs to start, take its tasks from the broker and read extension archives from the
cache, from smarter.env: settings that aren't secret. Never DJANGO_CACHES or smarter.env's broker url,
which carry Redis's default user's password. Never the database's, the Django secret key, the
Fernet key, the LLM providers' keys or the AWS keys: each tool call brings the credentials that it
needs. Then:

- SMARTER_DATABASE_UNAVAILABLE=true: the worker never opens a database connection, and reads every
  waffle switch as off;
- Redis's credentials are its own ACL user's, tools, not the default user's (ADR-030, rule 8):
  SMARTER_SUBSYSTEM_REDIS_USERNAME, SMARTER_SUBSYSTEM_REDIS_PASSWORD from the Secret smarter-redis-users,
  which smarter-infrastructure generates, and the broker's url built from them. Without that Secret, the
  password and the url are left out, and the worker refuses to start rather than run as the default user;
- AWS_EC2_METADATA_DISABLED=true: boto3, which settings start, doesn't ask the node's instance
  metadata for its IAM role. The network policy blocks it too.
*/}}
{{- define "smarter.toolsEnv" -}}
{{- $all := include "smarter.env" . | fromYaml -}}
{{- $env := dict -}}
{{- $keys := list
  "AWS_REGION"
  "DJANGO_SETTINGS_MODULE"
  "SMARTER_APP_LLMTOOL_PLUGIN_MAX_DATA_RESULTS"
  "SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE"
  "SMARTER_DEBUG_MODE"
  "SMARTER_ENVIRONMENT"
  "SMARTER_LOG_LEVEL"
  "SMARTER_PLATFORM_CLOUD_PROVIDER"
  "SMARTER_PLATFORM_INTERNAL_IP_PREFIXES"
  "SMARTER_PLATFORM_ROOT_DOMAIN"
  "SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER"
  "SMARTER_PLATFORM_SUBDOMAIN"
  "SMARTER_SUBSYSTEM_K8S_NAMESPACE"
-}}
{{- range $key := $keys -}}
{{- if hasKey $all $key -}}
{{- $_ := set $env $key (get $all $key) -}}
{{- end -}}
{{- end -}}
{{- $_ := set $env "SMARTER_DATABASE_UNAVAILABLE" "true" -}}
{{- $_ := set $env "AWS_EC2_METADATA_DISABLED" "true" -}}
{{- $toolsUser := "tools" -}}
{{- $_ := set $env "SMARTER_SUBSYSTEM_REDIS_USERNAME" $toolsUser -}}
{{- $users := lookup "v1" "Secret" .Release.Namespace "smarter-redis-users" -}}
{{- $usersData := get $users "data" | default dict -}}
{{- if hasKey $usersData $toolsUser -}}
{{- $toolsPassword := get $usersData $toolsUser | b64dec -}}
{{- $redis := printf "%s-master.%s.svc.cluster.local:6379" .Values.redis.fullnameOverride .Release.Namespace -}}
{{- $_ := set $env "SMARTER_SUBSYSTEM_REDIS_PASSWORD" $toolsPassword -}}
{{- $_ := set $env "DJANGO_CELERY_BROKER_URL" (printf "redis://%s:%s@%s/0" $toolsUser (urlquery $toolsPassword) $redis) -}}
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
