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
The platform's environment: every setting, which smarter.podEnv filters into each kind of pod's own Secret.

  {{- $env := include "smarter.env" . | fromYaml }}

It starts from .Values.env, then:

- leaves out the values that only the chart reads, when it renders, and no pod: DOCKERHUB_PAT and
  DOCKERHUB_USERNAME, which only the image-pull Secret, secret-docker.yaml, needs (#1103);
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
{{- /* values of env that only the chart reads, when it renders, and no pod: the image-pull Secret's
       Docker Hub credentials (secret-docker.yaml). They never reach a pod's Secret, or its environment (#1103). */ -}}
{{- $chartOnly := list "DOCKERHUB_PAT" "DOCKERHUB_USERNAME" -}}
{{- range $key, $value := .Values.env -}}
{{- $isNull := kindIs "invalid" $value -}}
{{- $isPlaceholder := and (kindIs "string" $value) (hasPrefix "SET-ME" $value) -}}
{{- if and (not (or $isNull $isPlaceholder)) (not (has $key $chartOnly)) -}}
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
The environment of one kind of pod, from its own Secret, <appName>-env-<pod> in secret-env.yaml (ADR-038,
phase 3, issue #1084): smarter.env without the credentials that the kind doesn't hold.

  {{- $env := include "smarter.podEnv" (dict "root" . "pod" "worker") | fromYaml }}

"pod" is a kind of pod, as SERVICE_TYPE names it (smarter.common.const.SmarterKubernetesPodKinds). Each
credential setting says which kinds hold it (HeldBy, in smarter.common.conf.credentials), and
files/credentials.json, which make chart-credentials copies from the settings, maps each of its environment
variables to them. A variable in the map is left out unless it names "pod"; a credential that no pod holds,
e.g. the Slack bot's app token, is left out of every one. A variable that isn't in the map isn't a credential,
and every kind receives it.

The derived broker url carries Redis's password, which every kind holds.

A kind whose pods read only a few named keys, with secretKeyRef, has an allowlist in smarter.podKeys, and its
Secret holds those keys alone (#1103).
*/}}
{{- define "smarter.podEnv" -}}
{{- $all := include "smarter.env" .root | fromYaml -}}
{{- $holders := .root.Files.Get "files/credentials.json" | fromJson -}}
{{- $pod := .pod -}}
{{- $allowed := get (include "smarter.podKeys" . | fromYaml) $pod -}}
{{- $env := dict -}}
{{- range $key, $value := $all -}}
{{- $listed := or (has $key ($allowed | default list)) (and (has "DJANGO_*" ($allowed | default list)) (hasPrefix "DJANGO_" $key)) -}}
{{- if and $allowed (not $listed) -}}
{{- /* not one of the few keys that this kind's pods read */ -}}
{{- else if not (hasKey $holders $key) -}}
{{- $_ := set $env $key $value -}}
{{- else if has $pod (get $holders $key) -}}
{{- $_ := set $env $key $value -}}
{{- end -}}
{{- end -}}
{{- toYaml $env -}}
{{- end }}

{{/*
The keys that the pods of a kind read from its Secret, for each kind that reads few of the platform's
settings: smarter.podEnv gives its Secret those keys alone (#1103). A kind not listed here gets every setting
but the credentials it doesn't hold. Each list is what the kind was found to read, by running it with
nothing else; a key that a kind reads and that is missing here is a pod that can't start or do its job.

- bastion: the database's administrator and backup accounts' passwords, and AWS's key pair, for its shell's
  mariadb and backup-to-s3.sh, with secretKeyRef. The rest of what it reads, the database's host, port and
  name, the bucket and the region, is written into its pod spec as plain values (deployment-bastion.yaml).
- job-backup: the dump container's keys (the database's administrator and backup accounts' passwords,
  AWS's key pair), and what its email container's manage.py email_job_log reads: the bucket and the region,
  where a log too large to email is saved; SMTP; the Slack bot token; and the admin's address. Not the
  database's own password, nor branding: nothing there reads them.
- job-migrate: the database's host, port, name, user and password, for manage.py migrate.
- beat: the database, which its pod's wait-for-database init container checks, and the queues of its
  schedule (smarter.workers.celerybeat).

Every kind that runs Django (job-backup's email container, job-migrate, beat) also gets what Django's prod
settings need to start: Redis's password; the environment, the root domain, the subdomain and the shared
resource identifier, which name Redis's host, <identifier>-redis-master.<namespace>, and the platform's
domains; logging; and every DJANGO_* key, each of which overrides the Django setting it names, the broker's
url and the caches' among them (smarter.settings.overrides). "DJANGO_*" in a list stands for them.

  {{- $keys := get (include "smarter.podKeys" . | fromYaml) "bastion" }}
*/}}
{{- define "smarter.podKeys" -}}
bastion:
  - SMARTER_SUBSYSTEM_SQL_ROOT_PASSWORD
  - SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
job-backup:
  - SMARTER_SUBSYSTEM_SQL_ROOT_PASSWORD
  - SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_REGION
  - SMARTER_PLATFORM_S3_BUCKET
  - SMARTER_SUBSYSTEM_SMTP_HOST
  - SMARTER_SUBSYSTEM_SMTP_PORT
  - SMARTER_SUBSYSTEM_SMTP_USE_SSL
  - SMARTER_SUBSYSTEM_SMTP_USE_TLS
  - SMARTER_SUBSYSTEM_SMTP_USERNAME
  - SMARTER_SUBSYSTEM_SMTP_PASSWORD
  - SMARTER_SUBSYSTEM_SMTP_FROM_EMAIL
  - SMARTER_SUBSYSTEM_SMTP_SENDER
  - SMARTER_SUBSYSTEM_SLACK_BOT_TOKEN
  - SMARTER_PLATFORM_EMAIL_ADMIN
  - SMARTER_SUBSYSTEM_REDIS_PASSWORD
  - SMARTER_ENVIRONMENT
  - SMARTER_PLATFORM_ROOT_DOMAIN
  - SMARTER_PLATFORM_SUBDOMAIN
  - SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER
  - SMARTER_LOG_LEVEL
  - SMARTER_DEBUG_MODE
  - SMARTER_SUBSYSTEM_LOGGING_LOKI_URL
  - DJANGO_*
job-migrate:
  - SMARTER_SUBSYSTEM_SQL_HOST
  - SMARTER_SUBSYSTEM_SQL_PORT
  - SMARTER_SUBSYSTEM_SQL_DATABASE
  - SMARTER_SUBSYSTEM_SQL_USER
  - SMARTER_SUBSYSTEM_SQL_PASSWORD
  - SMARTER_SUBSYSTEM_REDIS_PASSWORD
  - SMARTER_ENVIRONMENT
  - SMARTER_PLATFORM_ROOT_DOMAIN
  - SMARTER_PLATFORM_SUBDOMAIN
  - SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER
  - SMARTER_LOG_LEVEL
  - SMARTER_DEBUG_MODE
  - SMARTER_SUBSYSTEM_LOGGING_LOKI_URL
  - DJANGO_*
beat:
  - SMARTER_SUBSYSTEM_SQL_HOST
  - SMARTER_SUBSYSTEM_SQL_PORT
  - SMARTER_SUBSYSTEM_SQL_DATABASE
  - SMARTER_SUBSYSTEM_SQL_USER
  - SMARTER_SUBSYSTEM_SQL_PASSWORD
  - SMARTER_APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE
  - SMARTER_APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE
  - SMARTER_SUBSYSTEM_REDIS_PASSWORD
  - SMARTER_ENVIRONMENT
  - SMARTER_PLATFORM_ROOT_DOMAIN
  - SMARTER_PLATFORM_SUBDOMAIN
  - SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER
  - SMARTER_LOG_LEVEL
  - SMARTER_DEBUG_MODE
  - SMARTER_SUBSYSTEM_LOGGING_LOKI_URL
  - DJANGO_*
{{- end }}

{{/*
The name of one kind of pod's environment Secret, which smarter.podEnv fills: <appName>-env-<pod>.

  name: "{{ include "smarter.podEnvName" (dict "root" . "pod" "worker") }}"
*/}}
{{- define "smarter.podEnvName" -}}
{{- printf "%s-env-%s" .root.Values.global.appName .pod -}}
{{- end }}

{{/*
The environment of a worker without a database: the tool worker or the Extension worker, each from its own
Secret, secret-env-tools.yaml or secret-env-extensions.yaml (ADR-038, issue #1077).

  {{- $env := include "smarter.toolWorkerEnv" (dict "root" . "user" "tools" "queue" "") | fromYaml }}

Only what it needs to start, take its tasks from the broker and read extension archives from the
cache, from smarter.env: settings that aren't secret. Not DJANGO_SETTINGS_MODULE, which the Celery app derives
from SMARTER_ENVIRONMENT (smarter.workers.celery), nor the AWS region, the cloud provider or the Kubernetes
namespace, which it never reads: it calls neither AWS nor Kubernetes. Both queues' names, because it declares
both, and the Extension worker's startup check proves that it can't read the tool worker's queue, by name. Never DJANGO_CACHES or smarter.env's broker url,
which carry Redis's default user's password. Never the database's, the Django secret key, the
Fernet key, the LLM providers' keys or the AWS keys: each tool call brings the credentials that it
needs. Then:

- SMARTER_DATABASE_UNAVAILABLE=true: the worker never opens a database connection, and reads every
  waffle switch as off;
- Redis's credentials are its own ACL user's, "user" (tools or extensions), not the default user's (ADR-030,
  rule 8): SMARTER_SUBSYSTEM_REDIS_USERNAME, SMARTER_SUBSYSTEM_REDIS_PASSWORD from the Secret
  smarter-redis-users, which smarter-infrastructure generates, and the broker's url built from them. Without
  that Secret's key, the password and the url are left out, and the worker refuses to start rather than run
  as the default user;
- CACHE_RESULTS_CACHE, @cache_results' own cache (the cache-results package reads it): the cache's
  database, as the same user, under the key prefix <user>_cache, which that user's ACL rule allows. Every
  other pod leaves it unset, and caches results in the platform's cache;
- SMARTER_APP_TOOLS_WORKER_QUEUE, "queue", when it is given: the Extension worker's queue. The tool worker
  leaves it out, and its queue is the tools queue;
- AWS_EC2_METADATA_DISABLED=true: boto3, which settings start, doesn't ask the node's instance
  metadata for its IAM role. The network policy blocks it too.
*/}}
{{- define "smarter.toolWorkerEnv" -}}
{{- $root := .root -}}
{{- $all := include "smarter.env" $root | fromYaml -}}
{{- $env := dict -}}
{{- $keys := list
  "SMARTER_APP_LLMTOOL_PLUGIN_MAX_DATA_RESULTS"
  "SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE"
  "SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE"
  "SMARTER_DEBUG_MODE"
  "SMARTER_ENVIRONMENT"
  "SMARTER_LOG_LEVEL"
  "SMARTER_PLATFORM_INTERNAL_IP_PREFIXES"
  "SMARTER_PLATFORM_ROOT_DOMAIN"
  "SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER"
  "SMARTER_PLATFORM_SUBDOMAIN"
-}}
{{- range $key := $keys -}}
{{- if hasKey $all $key -}}
{{- $_ := set $env $key (get $all $key) -}}
{{- end -}}
{{- end -}}
{{- $_ := set $env "SMARTER_DATABASE_UNAVAILABLE" "true" -}}
{{- $_ := set $env "AWS_EC2_METADATA_DISABLED" "true" -}}
{{- /* the kind of pod, which smarter_settings names, and checks, when it starts. */ -}}
{{- $_ := set $env "SERVICE_TYPE" (ternary "worker-extensions" "worker-tools" (eq .user "extensions")) -}}
{{- if .queue -}}
{{- $_ := set $env "SMARTER_APP_TOOLS_WORKER_QUEUE" .queue -}}
{{- end -}}
{{- $user := .user -}}
{{- $_ := set $env "SMARTER_SUBSYSTEM_REDIS_USERNAME" $user -}}
{{- $users := lookup "v1" "Secret" $root.Release.Namespace "smarter-redis-users" -}}
{{- $usersData := get $users "data" | default dict -}}
{{- if hasKey $usersData $user -}}
{{- $password := get $usersData $user | b64dec -}}
{{- $redis := printf "%s-master.%s.svc.cluster.local:6379" $root.Values.redis.fullnameOverride $root.Release.Namespace -}}
{{- $_ := set $env "SMARTER_SUBSYSTEM_REDIS_PASSWORD" $password -}}
{{- $_ := set $env "DJANGO_CELERY_BROKER_URL" (printf "redis://%s:%s@%s/0" $user (urlquery $password) $redis) -}}
{{- /* @cache_results' own cache (cache-results' CACHE_RESULTS_CACHE): the cache's database, as the same
user, under keys that only this user's ACL rule, ~<user>_cache:*, allows. The timeouts are settings/base.py's
CACHE_SOCKET_CONNECT_TIMEOUT and CACHE_SOCKET_TIMEOUT. */ -}}
{{- $cacheOptions := dict "SOCKET_CONNECT_TIMEOUT" 2 "SOCKET_TIMEOUT" 5 -}}
{{- $cacheLocation := printf "redis://%s:%s@%s/1" $user (urlquery $password) $redis -}}
{{- $cache := dict "BACKEND" "django_redis.cache.RedisCache" "LOCATION" $cacheLocation "KEY_PREFIX" (printf "%s_cache" $user) "OPTIONS" $cacheOptions -}}
{{- $_ := set $env "CACHE_RESULTS_CACHE" (toJson $cache) -}}
{{- end -}}
{{- toYaml $env -}}
{{- end }}

{{/*
The tool worker's environment, from its own Secret in secret-env-tools.yaml: smarter.toolWorkerEnv, as the
Redis user tools, on the tools queue.
*/}}
{{- define "smarter.toolsEnv" -}}
{{- include "smarter.toolWorkerEnv" (dict "root" . "user" "tools" "queue" "") -}}
{{- end }}

{{/*
The Extension worker's environment, from its own Secret in secret-env-extensions.yaml: smarter.toolWorkerEnv,
as the Redis user extensions, on the Extensions queue (issue #1077).
*/}}
{{- define "smarter.extensionsEnv" -}}
{{- $queue := .Values.env.SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE | default "extensions_celery_task_queue" -}}
{{- include "smarter.toolWorkerEnv" (dict "root" . "user" "extensions" "queue" $queue) -}}
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

  {{- include "smarter.waitForDatabase" (dict "root" . "pod" "api") | nindent 6 }}   (in a pod's spec, at its initContainers' level)

"pod" is the pod's kind, whose environment Secret, smarter.podEnvName, the container reads, as the pod's own
containers do.
*/}}
{{- define "smarter.waitForDatabase" -}}
{{- $root := .root -}}
{{- if $root.Release.IsInstall -}}
initContainers:
  - name: "{{ $root.Values.global.appName }}-wait-for-database"
    image: '{{ $root.Values.env.SMARTER_DOCKER_IMAGE | default (printf "%s:%s" $root.Values.global.image.repository $root.Values.global.image.tag) }}'
    imagePullPolicy: {{ $root.Values.global.image.pullPolicy | default "Always" }}
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
    # the pod's own environment, from its Secret in secret-env.yaml, for the database's credentials.
    envFrom:
      - secretRef:
          name: "{{ include "smarter.podEnvName" . }}"
    env:
      - name: PYTHONUNBUFFERED
        value: "1"
    securityContext:
      {{- toYaml $root.Values.global.containerSecurityContext | nindent 6 }}
    volumeMounts:
      {{- include "smarter.writableVolumeMounts" $root | nindent 6 }}
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

{{/*
The egress proxy's url (ADR-038, phase 4): its Service, egressProxy in values.yaml.
*/}}
{{- define "smarter.egressProxyUrl" -}}
{{- printf "http://%s-egress-proxy.%s.svc.cluster.local:%v" .Values.global.appName .Release.Namespace (.Values.egressProxy.port | default 4750) -}}
{{- end }}

{{/*
The hosts that the platform's pods reach without the egress proxy, comma-separated, for NO_PROXY.

Smokescreen refuses private, link-local and metadata addresses, whatever its action, so everything in
the cluster and the VPC goes around it:

- localhost, and the in-cluster names: .svc and .cluster.local, which the LLMHosts' and the self-hosted
  vectorstores' endpoints use, and the short names that the settings use: Loki's (from
  SMARTER_SUBSYSTEM_LOGGING_LOKI_URL), the database's (SMARTER_SUBSYSTEM_SQL_HOST) and the app's Services;
- .eks.amazonaws.com, the cluster's api, which kubectl reaches at its private endpoint from inside the VPC;
- the instance metadata service and the EKS pod identity agent;
- the private ranges, for the clients that read CIDRs in NO_PROXY (requests, and Go's: kubectl). httpx,
  urllib and botocore don't, so an address in them must be reached by a name listed here.

egressProxy.noProxy adds to it.
*/}}
{{- define "smarter.egressProxyNoProxy" -}}
{{- $hosts := list "localhost" "127.0.0.1" "::1" ".svc" ".cluster.local" ".eks.amazonaws.com" "169.254.169.254" "169.254.170.2" "10.0.0.0/8" "172.16.0.0/12" "192.168.0.0/16" -}}
{{- $loki := .Values.env.SMARTER_SUBSYSTEM_LOGGING_LOKI_URL | default "" -}}
{{- if $loki -}}
{{- $hosts = append $hosts (first (splitList ":" (urlParse $loki).host)) -}}
{{- end -}}
{{- with .Values.env.SMARTER_SUBSYSTEM_SQL_HOST -}}
{{- $hosts = append $hosts . -}}
{{- end -}}
{{- range $name := splitList "," (include "smarter.apiNames" .) -}}
{{- $hosts = append $hosts $name -}}
{{- end -}}
{{- $hosts = concat $hosts (.Values.egressProxy.noProxy | default list) -}}
{{- join "," (uniq $hosts) -}}
{{- end }}

{{/*
The environment that sends a container's HTTP and HTTPS requests through the egress proxy, with
egressProxy.enabled, or nothing: entries of a container's env list.

Both cases of each name: Python and Go read either, but curl and apt, which the backup's container runs,
read only the lower case ones.

  env:
    - name: SERVICE_TYPE
      value: "api"
    {{- include "smarter.egressProxyEnv" $ | nindent 12 }}
*/}}
{{- define "smarter.egressProxyEnv" -}}
{{- if .Values.egressProxy.enabled -}}
{{- $url := include "smarter.egressProxyUrl" . -}}
{{- $noProxy := include "smarter.egressProxyNoProxy" . -}}
# the egress proxy (ADR-038, phase 4): egressProxy in values.yaml
{{- range $name := list "HTTPS_PROXY" "https_proxy" "HTTP_PROXY" "http_proxy" }}
- name: {{ $name }}
  value: {{ $url | quote }}
{{- end }}
{{- range $name := list "NO_PROXY" "no_proxy" }}
- name: {{ $name }}
  value: {{ $noProxy | quote }}
{{- end }}
{{- end -}}
{{- end }}
