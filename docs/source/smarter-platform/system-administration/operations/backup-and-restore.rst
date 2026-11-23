Backup and Restore
==================

All of Smarter's data is in its SQL database: accounts, users, every resource and its manifest,
chat history, the journal and usage. Backing up Smarter means backing up that database, and the
Helm chart does it for you, every night, to AWS S3.


The Nightly Backup
------------------

On Kubernetes, the chart runs a CronJob, ``smarter-mysql-backup``, every night at 2am UTC. It dumps
the platform's database with ``mariadb-dump``, compresses it, and uploads it to S3 as
``<database>-<timestamp>.tar.gz``. Before uploading, it checks that the dump ran to the end and that
the archive is intact, and after uploading, that the object in S3 has the archive's size.

The Job then emails its result, with the backup's log attached, to the platform's administrator, and
can also post it to a Slack channel. A successful backup's message names the file, its size and its
location in S3. A failed backup is retried in a new pod, up to twice, and each attempt sends its own
message, so a failure is never silent.

Where it goes, and with what access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Everything below is set up when you install with smarter-infrastructure and Smarter's deploy
workflow. Nothing needs to be done by hand.

- **A private bucket.** Backups go to ``s3://backups.<platform domain>/backups/sql/``, a bucket that
  smarter-infrastructure creates for each environment, apart from the platform's public bucket. Public
  access is blocked, and objects are encrypted (AES-256) and versioned. Nothing expires them, so every
  backup is kept until someone deletes it.
- **An IAM role of its own.** The Job runs as the ``smarter-backup`` ServiceAccount, with the IAM role
  ``<namespace>-smarter-backup-irsa`` (IRSA), which may only write and list objects under
  ``backups/sql/``. It can't read or delete a backup, so a compromised backup pod can't destroy the
  earlier ones.
- **A read-only database account.** The dump runs as ``smarter_backup``, which the init Job creates on
  every deployment, with ``SELECT, SHOW VIEW, TRIGGER, EVENT, SHOW CREATE ROUTINE`` on the platform's
  database (``SHOW CREATE ROUTINE`` exists in MariaDB 11.3 and later). Its password,
  ``SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD``, comes from the deploy workflow. On a platform without
  it, the backup dumps as the database's root account, and says so in its log.

The chart's ``databaseScheduledBackup`` values hold these settings: ``schedule``, ``s3Uri``,
``awsRoleArn``, ``notifyEmail`` (by default ``SMARTER_PLATFORM_EMAIL_ADMIN``),
``notifySlackChannel``, and ``enabled``.

How the Job is built
~~~~~~~~~~~~~~~~~~~~

- **The backup runs on a plain Debian image,** as an init container that installs only the MariaDB
  client and a pinned AWS CLI (``databaseScheduledBackup.awsCliVersion``), whose download it verifies
  against the AWS CLI team's PGP signature. Its script is ``backup-to-s3.sh``, from the chart's
  ``mysql-backup-script`` ConfigMap.
- **It receives only what it needs:** the database's host, port and name, the backup account, the S3
  location and the AWS credentials, and the root password only when there is no backup account. The
  password reaches ``mariadb-dump`` in a temporary option file, not on its command line, where every
  process in the pod could read it.
- **A second container, from the Smarter image, sends the result** with ``manage.py email_job_log``,
  as the init Job does. Email needs SMTP, and Slack needs ``SMARTER_SUBSYSTEM_SLACK_BOT_TOKEN``, from
  a bot with the scopes ``chat:write`` and ``files:write`` that is a member of the channel. Neither
  changes the backup's outcome.


Run a Backup Now
----------------

Before an upgrade, or any change to the database by hand, start the CronJob once. The backup runs
with its own role and account, and sends its result as the nightly one does:

.. code-block:: console

   kubectl create job -n <namespace> --from=cronjob/smarter-mysql-backup smarter-mysql-backup-manual


Restore
-------

A backup restores into the same platform, or into a new one. Restoring **replaces** the database:
the dump drops and recreates it.

1. **Get the backup onto the bastion pod.** The backup's role can't read backups, and the bastion
   pod has no AWS role, so download it with your own AWS credentials, then copy it in:

   .. code-block:: console

      aws s3 ls s3://backups.<platform domain>/backups/sql/
      aws s3 cp s3://backups.<platform domain>/backups/sql/<database>-<timestamp>.tar.gz .
      kubectl cp -n <namespace> <database>-<timestamp>.tar.gz \
        "$(kubectl get pod -n <namespace> -l app.kubernetes.io/name=smarter-bastion -o name | cut -d/ -f2)":/home/bastion/
      kubectl exec -it -n <namespace> deploy/smarter-bastion -- bash
      tar -xzf <database>-<timestamp>.tar.gz

2. **Stop the platform's writes.** Scale the app, the Celery workers and beat to zero, so that
   nothing writes to the database while it is restored:

   .. code-block:: console

      kubectl scale -n <namespace> deploy/smarter-api deploy/smarter-worker \
        deploy/smarter-worker-infrastructure deploy/smarter-beat --replicas=0

3. **Load the dump** as the root account, from the bastion pod, whose environment has the database's
   host and accounts. It asks for ``SMARTER_SUBSYSTEM_SQL_ROOT_PASSWORD``:

   .. code-block:: console

      mariadb -h "$SMARTER_SUBSYSTEM_SQL_HOST" -P "$SMARTER_SUBSYSTEM_SQL_PORT" \
        -u "$SMARTER_SUBSYSTEM_SQL_ROOT_USERNAME" -p < <database>-<timestamp>.sql

4. **Start the platform again** with ``helm upgrade``, which restores the replica counts and runs
   the init Job. The Job migrates the database, so a backup from an older release is brought up to
   date.

A restore brings back each LLMClient's ``deployed`` status, but not the Kubernetes resources or DNS
records behind it, and a restored LLMClient that is marked deployed is not redeployed automatically.
After restoring into a new cluster, undeploy and redeploy the LLMClients that must be reachable, in
batches, so that cert-manager and the certificate authority aren't flooded.


Keep the Encryption Key
-----------------------

Smarter Secrets are stored encrypted in the database, with ``SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY``
from the Helm values. The backup holds them encrypted, and a restored database can read them only
with the same key. That key is not in the backup: it is in your values file, or the deploy
workflow's secrets. A restore into a new platform needs it, or every Secret's value is lost.


Other Ways to Run Smarter
-------------------------

- **A managed database**, such as AWS RDS: its own automated backups and point-in-time recovery
  work alongside the nightly backup, or instead of it, with ``databaseScheduledBackup.enabled:
  false``.
- **Docker Compose**, for local development and evaluation, has no scheduled backup. The database's
  files are in the repository's ``mariadb-data/`` folder. Copy it while the containers are stopped,
  or dump the database with ``docker exec smarter-mariadb mariadb-dump``.
