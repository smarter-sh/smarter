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
The user's own Django settings: the Secret that templates/secret-django-settings.yaml writes from
.Values.djangoSettings, mounted read-only where smarter.settings.user reads it,
/home/smarter_user/user-settings/settings.yaml (smarter_settings.user_settings_file's default). Every pod
that loads Django's settings mounts it: the api, the workers, beat, and the init and migrate jobs.

The Secret is optional. job-migrate.yaml is a pre-upgrade hook, which runs before Helm applies the
release's Secrets: on the first upgrade to a chart that has this Secret, it doesn't exist yet, and a
required volume would hold the Job's pod in ContainerCreating, and fail the upgrade. Without it, the
directory is empty, which smarter.settings.user reads as no user settings. On later upgrades, the
migrate Job reads the previous release's Secret, as it does secret-env.yaml's.
*/}}
{{- define "smarter.userSettingsVolumes" -}}
- name: smarter-user-settings
  secret:
    secretName: "{{ .Values.global.appName }}-django-settings"
    optional: true
{{- end }}

{{- define "smarter.userSettingsVolumeMounts" -}}
- name: smarter-user-settings
  mountPath: /home/smarter_user/user-settings
  readOnly: true
{{- end }}

{{/*
The names of the api's Deployments, and of their Services, HorizontalPodAutoscalers and
PodDisruptionBudgets, comma-separated: <appName>-api, and while app.legacyName.enabled is true,
<appName> too, the name that they had before.

The api was renamed from <appName> to <appName>-api in v0.43.0. With app.legacyName.enabled, a release
runs both Deployments, whose pods share the label app.kubernetes.io/component: api, which both
Services select, so that the rename drops no request: Helm creates the new Deployment before an
upgrade with the flag off deletes the old one, and the Ingresses that still name the old Service keep
working until they are updated. It is off by default, since v0.43.0 has been deployed: an install
that upgrades from an older release turns it on for one upgrade (see values.yaml).

  {{- range $name := splitList "," (include "smarter.apiNames" .) }} ... {{- end }}
*/}}
{{- define "smarter.apiNames" -}}
{{- $names := list (printf "%s-api" .Values.global.appName) -}}
{{- if .Values.app.legacyName.enabled -}}
{{- $names = append $names .Values.global.appName -}}
{{- end -}}
{{- join "," $names -}}
{{- end }}
