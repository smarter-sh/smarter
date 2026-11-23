Software Updates
================

A production Smarter platform is installed with the
`Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__, and it is
updated the same way: ``helm upgrade`` to a newer chart version. Each chart version installs the
Smarter release with the same number. Chart ``0.46.17`` runs the Docker image
``mcdaniel0073/smarter:v0.46.17``, so choosing a chart version is choosing a Smarter version.

There are two ways to run that upgrade. The automatic one is recommended.


Automatic updates (recommended)
-------------------------------

The smarter repository's GitHub Actions pipeline updates the platform on every release, with no
command to run:

1. **Build** runs on every push to ``main`` that calls for a release. It versions the release, builds
   its Docker image, and publishes its Helm chart.
2. **Deploy** (`deploy.yml <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/deploy.yml>`__)
   runs when Build succeeds. It connects to the cluster, writes the values file from the GitHub
   Actions secrets, and runs ``helm upgrade --install``. It skips the upgrade when Build released
   nothing.
3. **The deployment reports itself**: Deploy posts the version and the changes since the previous
   release to Slack, and the init Job emails its log to the platform's administrator.

To deploy a particular version, or to deploy again, start Deploy by hand, on the branch of the
environment (``main`` deploys ``prod``), with the tag to deploy, or with no tag for the branch's
latest one:

.. code-block:: console

   gh workflow run deploy.yml --ref main -f tag=v0.46.17

The release's image must already exist: Deploy stops before it touches the cluster if Build
hasn't built it.

Setting this up is a one-time job: the workflow's GitHub Actions secrets, which hold the same values
as ``my-values.yaml`` in :doc:`../../installation/production-deployment`, and the AWS credentials it
connects to the cluster with. Its Deploy step names each one, as ``secrets.<NAME>``. To run your own
platform this way, fork the repository, set the secrets in your fork, and change the ``env`` block
at the top of ``deploy.yml`` (``ROOT_DOMAIN``, ``PLATFORM_SUBDOMAIN``, ``NAMESPACE_BASE``,
``AWS_REGION``) to your common settings from Step 1 of the installation.

The automatic path doesn't take a backup before upgrading. The nightly backup covers it, and a
failed migration stops the upgrade before any pod is replaced (see step 4 below). Before a release
whose notes call for a change by hand, back up first as step 3 describes.


Updating by hand
----------------

These steps assume that you installed as :doc:`../../installation/production-deployment` describes, with
the release name ``smarter`` and a values file ``my-values.yaml``. Replace the namespace
``smarter-platform-prod`` with yours.

1. Find the version you run
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   helm list -n smarter-platform-prod

The ``CHART`` column shows ``smarter-<version>`` and ``APP VERSION`` the Smarter version. Note the
``NAME``, the release name: the upgrade must use it. A different name installs a second copy of
Smarter beside the first.

2. Choose the new version
~~~~~~~~~~~~~~~~~~~~~~~~~

Open the chart on `Artifact Hub <https://artifacthub.io/packages/helm/project-smarter/smarter>`__.
The version selector lists every published chart version, newest first. Only stable releases are
published there; the alpha prereleases are not.

Before upgrading, read what changed between your version and the new one:

- the chart's `Changelog <https://artifacthub.io/packages/helm/project-smarter/smarter?modal=changelog>`__
  on Artifact Hub,
- Smarter's `CHANGELOG <https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG.md>`__
  and `Releases <https://github.com/smarter-sh/smarter/releases>`__ on GitHub.

Until Smarter 1.0.0, a release that needs something from you (a renamed or new Helm value, a change
in smarter-infrastructure) says so in the description of its commit, which the release links to.
Look for these in every release between yours and the new one. You can upgrade several versions in
one step: each release's database migrations run in order.

3. Back up the database
~~~~~~~~~~~~~~~~~~~~~~~

The upgrade migrates the database, and ``helm rollback`` does not undo a migration. Run the nightly
backup once, now, and wait for its email (or Slack message) that names the file in S3:

.. code-block:: console

   kubectl create job -n smarter-platform-prod --from=cronjob/smarter-mysql-backup smarter-mysql-backup-pre-upgrade

See :doc:`backup-and-restore`.

4. Upgrade
~~~~~~~~~~

Run the command you installed with, with the new version and the same values file:

.. code-block:: console

   helm upgrade smarter oci://ghcr.io/smarter-sh/charts/smarter \
     --version <new version> \
     --namespace smarter-platform-prod \
     --values my-values.yaml \
     --timeout 900s

- **Use the same values file.** Don't add ``--reuse-values``: it keeps the previous chart's
  defaults, so a value that the new chart adds or renames is missing. Your file holds only your own
  values, so the new chart's defaults apply to everything else.
- **Artifact Hub's Install button** shows ``helm install my-smarter ...``. Don't run it as it is: it
  installs a new release named ``my-smarter``. Take only the ``oci://`` address and the version from it.
- ``oci://`` needs Helm 3.8 or later.

``helm upgrade`` then does three things, and returns when the last one has finished:

1. **Migrates the database**, before any pod is replaced, in a Job named
   ``smarter-smarter-job-migrate-<number>``, with the new release's image and settings. If the
   migration fails, ``helm upgrade`` fails, the running pods are left untouched and keep serving,
   and the failed Job is kept so that you can read its log.
2. **Rolls out the new pods**: the application server, the Celery workers and Celery Beat.
3. **Runs the init Job**, ``smarter-smarter-job-db-init-<number>``, which runs
   ``manage.py initialize_platform`` and brings the example resources and Stackademy up to date. It
   emails its log to the platform's administrator, and posts it to Slack when that is configured.

5. Check the upgrade
~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

   helm list -n smarter-platform-prod
   kubectl get pods -n smarter-platform-prod

``helm list`` should show the new version with the status ``deployed``, and every pod should be
``Running`` with few or no restarts. Then sign in to the web console and open an LLMClient's
workbench, which exercises the database, Redis, the workers and an LLM provider.

If ``helm upgrade`` failed, find the failed Job and read its log:

.. code-block:: console

   kubectl get jobs -n smarter-platform-prod
   kubectl logs -n smarter-platform-prod job/<job name>

See :doc:`../../trouble-shooting` for the common causes.


Rolling back
------------

``helm rollback`` returns the pods and the chart's settings to an earlier revision:

.. code-block:: console

   helm history smarter -n smarter-platform-prod
   helm rollback smarter <revision> -n smarter-platform-prod --timeout 900s

It does not return the database to its earlier schema. The older release usually runs on the newer
schema, because Smarter's migrations add columns and tables rather than remove them. If it doesn't,
restore the backup that you made in step 3, as :doc:`backup-and-restore` describes, after the
rollback. With automatic updates, starting Deploy by hand with the earlier tag does the same as
``helm rollback``.


Release announcements
---------------------

Release announcements are posted to `blog.smarter.sh <https://blog.smarter.sh>`__ and the Slack
workspace's ``#announcements`` channel. Each Docker image tag is also listed on
`Docker Hub <https://hub.docker.com/r/mcdaniel0073/smarter/tags>`__.
