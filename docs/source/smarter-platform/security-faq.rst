Security FAQ
============

Following are commonly asked questions about Smarter security.

.. note::

  Many of these questions are in response to preliminary security due
  diligence projects performed with the assistance of coding LLMs such as
  Claude Code as opposed to more purpose designed tools like for example,
  `Agentic QE <https://agentic-qe.dev/>`__. Take note that, while these
  LLMs are capable of doing some
  pretty impressive things, they are not effective tools for analyzing large
  code bases like Smarter's, and they are prone to generating false positives.
  The following answers are based on multiple careful manual reviews of
  the code base in response to LLM-generated security concerns.


* **SQL Injection, XSS**: Smarter is not vulnerable to SQL injection attacks because
  automated botnets cannot register for accounts. Without access to authenticated
  pages, botnets have no opportunity to exploit SQL injection vulnerabilities.

* **Terraform State Encryption**: LLMs occasionally recommend encrypting the
  AWS S3 bucket remote state contents in addition to using a private S3 bucket.
  Note that Smarter uses Terraform's automatic remote state setup functionality, which
  Terraform provide as a convenience to users. This sets up a private S3 bucket
  (with no public access) for storing remote Terraform state. This is a standard, secure
  configuration that is widely used and recommended by Terraform. It works well,
  it’s 1-click, and the safety of the state data has never been questioned
  (other than occasionally by LLMs like Claude Code).

  See `smarter-sh/smarter-infrastructure/aws/terragrunt.hcl <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terragrunt.hcl>`__.


* **DB Credentials**: LLMs sometimes raise false-positive concerns about
  hard-coded credentials in Smarter source code. Note that the following
  `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml#L20>`__
  file is provided in the root of the main repo for standing up Smarter in a
  local development environment. This seems to be the source of some confusion
  for LLMs.

  On the contrary, Smarter credentials (THERE ARE MANY) are maintained by a
  combination of GitHub Secrets and Kubernetes Secrets (`kubernetes-secrets.tf <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/smarter/kubernetes-secrets.tf>`__)
  and accessed with GitHub Actions workflows like this (`k8s-get-secret/action.yml <https://github.com/smarter-sh/smarter/blob/main/.github/actions/k8s-get-secret/action.yml>`__).
  NONE OF THESE CREDENTIALS ARE HARD-CODED NOR EXPOSED IN ANY WAY.

  In fact, Smarter credentials aren’t even exposed internally, within running
  Python code, let alone in the public domain. See `conf.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf.py#L407>`__.

* **SECRET_KEY logging**. Per the preceding bullets above, and
  consistent with all four dozen or so pieces of sensitive data in Smarter,
  the SECRET_KEY is not exposed anywhere, at any point. Not the logs, not
  Terraform, not Terraform’s state, not S3, not Kubernetes, not the deployment
  workflow, not the running Kubernetes pods, not in some accidentally
  exposed .env file. Nowhere, no exceptions.

* **API Key logging**: Smarter API Keys as well as any other credential or
  sensitive data are stored using Pydantic's SecretStr data type, which
  prevents the data from leaking into logs or other kinds of standard output.
  See: `https://docs.pydantic.dev/2.7/examples/secrets/ <https://docs.pydantic.dev/2.7/examples/secrets/>`__

  Smarter logs API keys and other sensitive variables for many reasons, but,
  it does so in a secure way that prevents the actual values from being exposed.
  A sample of Smarter logs with API keys redacted looks like this:

  .. code-block:: bash

    Environment variable ENV_LOADED found: ENV_LOADED=False
    Environment variable ENVIRONMENT found: ENVIRONMENT='prod'
    Environment variable ROOT_DOMAIN found: ROOT_DOMAIN='smarter.sh'
    Environment variable ALLOWED_HOSTS value 'None' cannot be converted to list. Using default ['localhost'].
    Environment variable ANTHROPIC_API_KEY found: ANTHROPIC_API_KEY='****'
    Environment variable API_SCHEMA found: API_SCHEMA='http'
    Environment variable AWS_PROFILE found: AWS_PROFILE=None
    Environment variable AWS_ACCESS_KEY_ID found: AWS_ACCESS_KEY_ID='****'
    Environment variable AWS_SECRET_ACCESS_KEY found: AWS_SECRET_ACCESS_KEY='****'
    Environment variable AWS_REGION found: AWS_REGION='ca-central-1'
    Environment variable ENVIRONMENT found: ENVIRONMENT='prod'
    Environment variable FERNET_ENCRYPTION_KEY found: FERNET_ENCRYPTION_KEY='****'
    Environment variable GOOGLE_MAPS_API_KEY found: GOOGLE_MAPS_API_KEY='****'
    Environment variable GOOGLE_SERVICE_ACCOUNT_B64 found: GOOGLE_SERVICE_ACCOUNT_B64='****'
    Environment variable GEMINI_API_KEY found: GEMINI_API_KEY='****'
    Environment variable INTERNAL_IP_PREFIXES found: INTERNAL_IP_PREFIXES=['192.168.']
    Environment variable LANGCHAIN_MEMORY_KEY found: LANGCHAIN_MEMORY_KEY='chat_history'
    Environment variable LLAMA_API_KEY found: LLAMA_API_KEY='****'
    Environment variable DEBUG_MODE found: DEBUG_MODE=False
    Environment variable MAILCHIMP_API_KEY found: MAILCHIMP_API_KEY='****'
    Environment variable MARKETING_SITE_URL found: MARKETING_SITE_URL='https://smarter.sh'
    Environment variable MYSQL_TEST_DATABASE_SECRET_NAME found: MYSQL_TEST_DATABASE_SECRET_NAME='smarter_test_db'
    Environment variable MYSQL_TEST_DATABASE_PASSWORD found: MYSQL_TEST_DATABASE_PASSWORD='****'
    Environment variable OPENAI_API_KEY found: OPENAI_API_KEY='****'
    Environment variable PINECONE_API_KEY found: PINECONE_API_KEY='****'
    Environment variable SECRET_KEY found: SECRET_KEY='****'


* **Rate Limiting**: Smarter posts the active settings for API rate limits at
  the top of every app log, for convenience, because its of interest to admins

  .. code-block:: bash

    [2026-02-22 17:39:45 +0000] * INFO * API queries_quota: 60

* **CSRF Bypasses**. LLMs sometimes raise concerns about CSRF bypasses.
  This is presumably because of Smarter's selective use of a
  Python-Django decorator, “@csrf_exempt”, which is (correctly) placed on
  public-facing views as well as the prompt engineer workbench (which
  runs in React and so CSRF is a moot point).
  See: `smarter-sh/smarter/smarter/smarter/apps/prompt/views.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/prompt/views.py#L173>`__

* **Expired tokens not rejected**. LLMs sometimes raise concerns about expired
  tokens not being rejected. This is not technically possible in Django.

* **Public EKS end point**: Smarter does use a public EKS end point.
  LLMs sometimes raise concerns about this, but it is a common configuration
  for EKS clusters.

  See: `smarter-sh/smarter-infrastructure/aws/terraform/kubernetes/main.tf <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/main.tf#L39>`__.

  This is a commonly used configuration option, not a security vulnerability. The Terraform
  module maintainers (ie AWS EKS Engineers) find it an important enough feature
  to to include on their QuickStart in their README. It’s anecdotally equivalent
  to a public IP address for a ssh private-key authenticated Linux server.

* **Permissive Security Groups**. LLMs might raise concerns about “permissive” security groups
  in Smarter's Kubernetes ingresses, but this seems to be incorrect, or at least unclear.

* **Cookie Security**. LLMs are prone to raising concerns about cookie security
  because of Smarter's use of the Django setting

  .. code-block:: python

    CSRF_COOKIE_SAMESITE = “Lax”

  Note that Smarter uses this cookie to locally persist the chat session_id on the device.
  This is not sensitive data in that using it requires login authentication by
  the same user, or else it self-corrupts and gets deleted/replaced.
  See: `smarter-sh/smarter//smarter/smarter/settings/base.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/settings/base.py#L196>`__

* **Auth Token Exposure**: LLMs have sometimes raised concerns about auth token exposure.
  However, this is not technically possible in Smarter. Smarter is https-only.
  There’s not a way for the token to be exposed.

* **CORS Misconfiguring**: LLMs sometimes raise concerns about CORS misconfigurations.
  However, Smarter uses CORS only as part of serving the React App from
  a CDN which is not the same host as that of the web console. It’s a GET-only
  http request that serves transpiled js and css files. There’s nothing to
  misconfigure.

  See: `smarter-sh/smarter-infrastructure/aws/terraform/smarter/cloudfront.tf <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/smarter/cloudfront.tf>`__

* **Missing TLS enforcement**: TLS resolution is managed by Kubernetes cert-manager
  along with AWS Certificate Manager. Feel free to weigh in with your thoughts
  on either. See: `smarter-sh/smarter-infrastructure/aws/terraform/kubernetes_cert_manager/main.tf <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes_cert_manager/main.tf>`__

* **Webhook secrets**: SMARTER HAS NO WEBHOOKS.

* **Container hardening**: LLMs have raised concerns about needing to harden the
  Smarter container. However, Smarter containers exceed what is considered best
  practice in terms of minimizing file permissions within the container file
  system. See: `smarter-sh/smarter/Dockerfile#L200 <https://github.com/smarter-sh/smarter/blob/main/Dockerfile#L200>`__.
  These are as close to "no-trust" as a file system can technically achieve
  without actually breaking the code due to permissions problems. Moreover, the
  containers themselves run as pods inside of Kubernetes following all security
  best practices (as implemented by AWS’s own EKS engineers’ Terraform module),
  on a private network inside of a VPC with no public access. Generally, this is
  what you’ll find inside of a running Smarter container:

  .. code-block:: bash

    dr-x------. 1 smarter_user smarter_user   93 Feb 21 22:33 .
    dr-x------. 1 smarter_user smarter_user   40 Feb 21 22:33 ..
    -r--------. 1 smarter_user smarter_user  647 Feb 21 22:32 __init__.py
    -r--------. 1 smarter_user smarter_user  143 Feb 21 22:32 __version__.py
    dr-x------. 1 smarter_user smarter_user  139 Feb 21 22:33 apps
    -r--------. 1 smarter_user smarter_user  338 Feb 21 22:32 asgi.py
    dr-x------. 1 smarter_user smarter_user   40 Feb 21 22:33 common
    -r--------. 1 smarter_user smarter_user 6.7K Feb 21 22:32 hosts.py
    dr-x------. 1 smarter_user smarter_user  129 Feb 21 22:33 lib
    dr-x------. 1 smarter_user smarter_user   25 Feb 21 22:33 settings
    dr-x------. 1 smarter_user smarter_user  131 Feb 21 22:32 static
    dr-x------. 1 smarter_user smarter_user  16K Feb 21 22:32 templates
    dr-x------. 1 smarter_user smarter_user  157 Feb 21 22:32 tests
    dr-x------. 1 smarter_user smarter_user   76 Feb 21 22:32 urls
    dr-x------. 1 smarter_user smarter_user   25 Feb 21 22:33 workers
    -r--------. 1 smarter_user smarter_user  781 Feb 21 22:32 wsgi.py
    smarter_user@smarter-6789cccff6-db529:~/smarter/smarter$


* **Log rotation**: LLMs have sometimes criticized Smarter for lacking a formal
  log rotation mechanism. Note that pods, logs, and for that matter the EC2
  instances themselves are all ephemeral. Smarter's Kubernetes cluster is
  configured to use EC2 spot-priced instances, which as a practical matter tend
  to be replaced in not more than 5 to 7 calendar days, simply due to normal
  market forces which lead to the instances being simultaneously taken away and
  replaced by AWS. This has the effect of compulsorily "rotating" the logs every
  few days, without any need for a formal log rotation mechanism.
  In other words, the logs are automatically rotated by the nature of the infrastructure itself.

  See `smarter-sh/smarter-infrastructure/aws/terraform/kubernetes/main.tf#L148 <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/main.tf#L148>`__.
