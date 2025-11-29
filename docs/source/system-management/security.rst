Security
========

Security is a critical aspect of system management. This section covers best practices, tools, and techniques to ensure the security of your systems.

Firewall
---------

The Smarter project production environment is designed to be installed on an **existing** AWS Virtual Private Cloud (VPC).
AWS VPC provides robust firewall capabilities that allow you to control inbound and outbound traffic to your instances.
It is recommended to configure security groups and network ACLs to restrict access to only necessary ports and IP addresses.

Please note the following recommendations for a network design that we would consider secure:

- **Use private subnets** for instances that do not require direct internet access. Namely, database server, and compute.
- **Use public subnets** only for instances that require direct internet access, such as web servers or bastion hosts.
- **Implement AWS security groups** to control traffic at the instance level.
- **Limit inbound traffic** to only necessary ports (e.g., HTTP, HTTPS, SSH) and trusted IP addresses. SSH (port 22) access should be restricted to known IP addresses only.

Application Security
---------------------

Smarter implements the following application security measures:

Smarter Security Features
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **No DNS Wildcards**. Prevents wildcard DNS entries to avoid subdomain takeover attacks. Smarter maintains strict DNS records for each deployed ChatBot/Agent using AWS Route53 Hosted Zones. Kubernetes Ingress resources are configured to only respond to specific domain names associated with each ChatBot/Agent, and Kubernetes cert-manager manages dedicated TLS certificates for these domains. This ensures that requests to undefined subdomains are not inadvertently routed to the application, thereby mitigating the risk of subdomain takeover attacks.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/aws-route53-api-hosted-zone.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter AWS Route53 Hosted Zone for Deployed ChatBots/Agents"/>

- **Sensitive File Blocking**. Custom middleware blocks access to sensitive files access attempts such as .env, .git, and others. See `smarter/lib/django/middleware/sensitive_files.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/sensitive_files.py>`_

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-sensitive-file-blocking.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Sensitive File Blocking"/>

- **Excessive 404 Protection**. Custom middleware (above DRF's rate-limiting) to protect against blind/random file access attempts. See `smarter/lib/django/middleware/excessive_404.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/excessive_404.py>`_
- **Enhanced CSRF Protection**. Custom middleware to enhance CSRF protection for Smarter ChatBot/Agent API endpoints. See `smarter/lib/django/middleware/csrf.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/csrf.py>`_
- **Enhanced CORS Protection**. Custom middleware to enhance CORS protection for Smarter ChatBot/Agent API endpoints. See `smarter/lib/django/middleware/cors.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/cors.py>`_
- **Enhanced Json HTTP Response Protection**. Custom middleware to ensure that REST Api responses exclusively return Json in the http response body. See `smarter/lib/django/middleware/json.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/json.py>`_
- **Audit Logging**. See `Smarter Journal <smarter-journal.html>`_ for details on logging security-related events.
- **Configurable Application Logs**. See `Configuration Management <configuration.html>`_ for details on logging configuration changes.


Django Security Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Host and Domain Validation**. Smarter accepts http requests only from allowed hosts/domains. See `Host and Domain Validation <https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts>`_
- **HTTPS Enforcement** (via settings and middleware). All traffic is redirected to HTTPS. See `SECURE_SSL_REDIRECT <https://docs.djangoproject.com/en/stable/ref/settings/#secure-ssl-redirect>`_
- **HSTS (HTTP Strict Transport Security)**. Enforces secure connections to the server. See `SECURE_HSTS_SECONDS <https://docs.djangoproject.com/en/stable/ref/settings/#secure-hsts-seconds>`_
- **SSL/TLS Configuration** (via settings). Ensures secure data transmission. See `SSL/HTTPS <https://docs.djangoproject.com/en/stable/topics/security/#ssl-https>`_
- **Content Security Policy (CSP)**. Helps prevent XSS attacks by specifying allowed content sources. See `Content Security Policy <https://docs.djangoproject.com/en/stable/ref/csp/>`_
- **Cross-Origin Resource Sharing (CORS)**. Controls resource sharing between different origins. For example, cdn.smarter.sh is allowed to access resources from smarter.sh. See `CORS <https://docs.djangoproject.com/en/stable/ref/cors/>`_
- **Cross-Site Request Forgery (CSRF) Protection**. Prevents CSRF attacks using tokens that validate requests and expire after a certain period. See `CSRF Protection <https://docs.djangoproject.com/en/stable/ref/csrf/>`_
- **XSS Protection**. Mitigates Cross-Site Scripting attacks through input sanitization and output encoding. See `XSS Protection <https://docs.djangoproject.com/en/stable/topics/security/#cross-site-scripting-xss-protection>`_
- **Clickjacking Protection**. Uses X-Frame-Options header to prevent clickjacking attacks. See `Clickjacking Protection <https://docs.djangoproject.com/en/stable/ref/clickjacking/>`_
- **No DNS Prefetching**. Disabled to prevent information leakage. See `SECURE_REFERRER_POLICY <https://docs.djangoproject.com/en/stable/ref/settings/#secure-referrer-policy>`_
- **Secure Headers**. Implements various HTTP security headers to enhance security. See `Security Middleware <https://docs.djangoproject.com/en/stable/topics/security/#security-middlewares>`_
- **Secure File Uploads**. Validates and sanitizes file uploads to prevent malicious files from being uploaded. See `Managing Files <https://docs.djangoproject.com/en/stable/topics/files/>`_
- **SQL Injection Prevention**. Utilizes Django's ORM to prevent SQL injection attacks. See `SQL Injection Protection <https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection>`_
- **Security Middleware** (custom and built-in). Implements various security measures through middleware components. See `Security Middleware <https://docs.djangoproject.com/en/stable/topics/security/#security-middlewares>`_
- **Session Security**. Manages user session expiration and secure cookie settings. See `Session Security <https://docs.djangoproject.com/en/stable/topics/http/sessions/#security>`_
- **Secure Cookie Settings**. Ensures cookies are transmitted securely and are protected from cross-site scripting. See `Cookie Security <https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-SESSION_COOKIE_SECURE>`_
- **Secret Key Management**. Handles the secure generation and storage of secret keys used for cryptographic signing. See `SECRET_KEY <https://docs.djangoproject.com/en/stable/ref/settings/#secret-key>`_
- **Password Validation**. Enforces strong password policies to enhance account security. See `Password Validation <https://docs.djangoproject.com/en/stable/topics/auth/passwords/#password-validation>`_
- **Authentication Backends and Social Auth**. Supports multiple authentication methods including social authentication. See `Authentication Backends <https://docs.djangoproject.com/en/stable/topics/auth/customizing/#authentication-backends>`_
- **Middleware for Security** (custom and built-in). Applies additional security measures through middleware layers. See `Middleware <https://docs.djangoproject.com/en/stable/topics/http/middleware/>`_
- **Sensitive File Access Blocking**. Prevents unauthorized access to sensitive files. See `Serving files <https://docs.djangoproject.com/en/stable/howto/static-files/#serving-files-uploaded-by-a-user-during-development>`_
- **Logging of Security Events**. Records security-related events for monitoring and auditing. See `Logging <https://docs.djangoproject.com/en/stable/topics/logging/>`_
- **Allowed File Extensions for Uploads**. Restricts file uploads to safe and approved types. See `File Uploads <https://docs.djangoproject.com/en/stable/topics/http/file-uploads/>`_
- **SMTP Security (SSL/TLS)**. Ensures secure email transmission using SSL/TLS. See `Email Security <https://docs.djangoproject.com/en/stable/topics/email/#email-backends>`_
- **Resource Limit Logging (for container hardening)**. Monitors and logs resource usage to enhance container security. See `Logging <https://docs.djangoproject.com/en/stable/topics/logging/>`_
- **Stripe/Dj-Stripe Webhook Security**. Secures webhook endpoints to prevent unauthorized access. See `Webhooks Security <https://docs.djangoproject.com/en/stable/topics/security/#webhooks>`_
- **Wagtail Admin Security Settings**. Applies security configurations specific to the Wagtail admin interface. See `Wagtail Security <https://docs.wagtail.org/en/stable/topics/security.html>`_
- **Static and Media File Storage Security (S3, FileSystem)**. Ensures secure storage and access controls for static and media files. See `Managing Files <https://docs.djangoproject.com/en/stable/topics/files/>`_
- **JSON Error Handling (to avoid leaking sensitive info)**. Handles JSON errors securely to prevent information leakage. See `Error Reporting <https://docs.djangoproject.com/en/stable/ref/views/#django.views.defaults.server_error>`_
- **Internal IP/Host Restrictions**. Limits access based on internal IP addresses and hostnames. See `INTERNAL_IPS <https://docs.djangoproject.com/en/stable/ref/settings/#internal-ips>`_
- **Security Headers** (e.g., X-Frame-Options via middleware). See `Security Middleware <https://docs.djangoproject.com/en/stable/topics/security/#security-middlewares>`_


Secure Remote Access
---------------------

Smarter is designed as an Api-first application, even though it also includes a web-based
Prompt Engineer Workbench and Django Admin interface. This affords the Smarter platform the
luxury of minimizing its attack surface primarily to http and https traffic only, and at that,
to a limited set of URL endpoints.

Smarter Authentication
~~~~~~~~~~~~~~~~~~~~~~

Smarter implements a proprietary token-based authentication mechanism for its API endpoints
which is based on Django knox. This enables enhanced Journal support as well as log warnings
for API keys that have exceeded their maximum lifetime. See `smarter/lib/drf/middleware.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/drf/middleware.py>`_ for details.


Audit Logging
----------------

See `Smarter Journal <smarter-journal.html>`_ for details on logging security-related events.
See `Configuration Management <configuration.html>`_ for details on logging configuration changes.

Malware Protection
------------------

Smarter does not provide built-in malware protection.


User management
---------------

See `User Management <user-management.html>`_ for details on managing user access and permissions.


Data Encryption
----------------

Smarter does not provide built-in data encryption features.


Security Updates
----------------

Smarter is a Docker-based application that follows best practices for applying security updates to its
dependencies and underlying systems. It is recommended to regularly update the Docker images and dependencies used by
deploying the Smarter DockerHub 'latest' image, which includes the latest security patches and updates. The
DockerHub images are regularly maintained -- typically at least once per month -- to ensure they
include the latest security fixes.

See `Installation <installation.html>`_ for further details.
