SMTP Email Support
======================

The Smarter framework includes built-in support for sending emails via SMTP.
This is facilitated through the `EmailHelper` class located in the `smarter.common.helpers.email_helpers` module.


Configuration
--------------

Set the following environment variables to configure SMTP email sending. These will
be consumed by :doc:`smarter-settings`.

.. code-block:: bash

  SMTP_SENDER=local.platform.smarter.sh
  SMTP_PASSWORD=<YOUR_SMTP_PASSWORD (AWS_SES_SMTP_PASSWORD)>
  SMTP_USERNAME=<YOUR_SMTP_USERNAME (AWS_SES_SMTP_USERNAME)>
  SMTP_HOST=email-smtp.us-east-1.amazonaws.com
  SMTP_PORT=587
  SMTP_USE_TLS=True

Also see :doc:`Cloud infrastructure <../smarter-platform/cloud-infrastructure>` for configuring
AWS Simple Email Service (SES) as your SMTP provider.

Basic Usage
-----------

.. code-block:: python

  from smarter.common.helpers.email_helpers import email_helper

  email_helper.send_email(
      subject="Welcome!",
      body="Hello and welcome to Smarter.",
      html=True,
      from_email="support@smarter.com"
  )

Technical Reference
-------------------

.. autoclass:: smarter.common.helpers.email_helpers.EmailHelper
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
