SMTP Email Services
====================

SMTP Email Services allow your system to send emails using an external SMTP server.
Smarter uses `AWS Simple Email Service <https://aws.amazon.com/ses/>`_ (SES) by default, but you can configure it to use any SMTP server of your choice.

.. warning::

   It is highly recommended to use AWS Simple Email Service (SES) for sending emails as this is known to be both cost effective and reliable.
   It is also recommended to use Smarter's provided Terraform scripts to set up the necessary SES resources as this is a more complex operation than might be expected, and the Terraform scripts will automate all of this for you. See `Cloud Infrastructure <cloud-infrastructure.html>`_ for more information.

Configuration
-------------

To configure SMTP Email Services, follow these steps:

1. Prepare your AWS SES account. This is taken care automatically if you use the Smarter `Terraform scripts <cloud-infrastructure.html>`_.
   This will create the necessary SES resources including verified domains and SMTP credentials, and it will also generate
   a Kubernetes Secret containing the SMTP credentials to be used by Smarter's default GitHub Actions deployment workflow.

2. Otherwise, in your Smarter settings for deployment ensure that you have included the following in your .env file:

   .. code-block:: ini

    SMTP_HOST: email-smtp.us-east-2.amazonaws.com                                                                                                                                │
    SMTP_PASSWORD: <A CREDENTIAL GENERATED IN AWS SES>                                                                                                                             │
    SMTP_PORT: "587"                                                                                                                                                             │
    SMTP_USE_SSL: "false"                                                                                                                                                        │
    SMTP_USE_TLS: "true"                                                                                                                                                         │
    SMTP_USERNAME: <A USERNAME GENERATED IN AWS SES>                                                                                                                                          │

You can test your SMTP configuration by sending a test email from the Django console:

.. code-block:: bash

   python manage.py send_welcome_email --email user@example.com
