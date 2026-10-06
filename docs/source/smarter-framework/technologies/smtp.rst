SMTP Email Support
======================

The Smarter framework includes built-in support for sending emails via SMTP, with the email
service of the :doc:`infrastructure services <infrastructure>`,
:class:`~smarter.apps.infrastructure.services.email.SMTPEmailService`. SMTP works with any SMTP
server, so email does not depend on the cloud provider.


Configuration
--------------

Set the following environment variables to configure SMTP email sending. These will
be consumed by :doc:`../developer-reference/smarter-settings`.

.. code-block:: bash

  SMTP_SENDER=local.platform.smarter.sh
  SMTP_PASSWORD=<YOUR_SMTP_PASSWORD (AWS_SES_SMTP_PASSWORD)>
  SMTP_USERNAME=<YOUR_SMTP_USERNAME (AWS_SES_SMTP_USERNAME)>
  SMTP_HOST=email-smtp.us-east-1.amazonaws.com
  SMTP_PORT=587
  SMTP_USE_TLS=True

Also see :doc:`Cloud infrastructure <../../smarter-platform/cloud-infrastructure>` for configuring
AWS Simple Email Service (SES) as your SMTP provider.

Basic Usage
-----------

.. code-block:: python

  from smarter.apps.infrastructure.services import infrastructure

  infrastructure.email.send_email(
      subject="Welcome!",
      body="Hello and welcome to Smarter.",
      to="user@example.com",
      html=True,
      from_email="support@smarter.com"
  )

Each email is blind copied to the platform's admin, ``SMARTER_EMAIL_ADMIN``. The copy is added
to the SMTP envelope only, so recipients never see the admin's address. Emails that carry a
secret, such as a password reset link, an account activation link, or a new user's password,
pass ``bcc_admin=False``, so that only their recipient receives them.

Delivery failures are logged, and sent as the ``email_failed`` signal, rather than raised, so
that email never breaks the request that sends it. In the unit tests, nothing is sent, so that
tests never email real people. Tests can replace the service with
:class:`~smarter.apps.infrastructure.services.email.InMemoryEmailService`, whose ``outbox``
holds what was sent.

Technical Reference
-------------------

.. autoclass:: smarter.apps.infrastructure.services.email.EmailService
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
    :no-index:

.. autoclass:: smarter.apps.infrastructure.services.email.SMTPEmailService
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
    :no-index:
