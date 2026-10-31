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

The rest of data/, e.g. data/docs, stays the image's own, read from the image.
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
