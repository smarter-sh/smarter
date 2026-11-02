User Management
===================

**Please review** `Account Management <account-management.html>`_ **before adding users.**

Use the manage.py command to create new Accounts:

.. code-block:: bash

   python manage.py create_user \
     --account_number "####-####-####" \
     --username "newuser" \
     --email "newuser@example.com" \
     --first_name "New" \
     --last_name "User" \
     --password "securepassword" \
     --admin

If you have enabled `SMTP Email Services <smtp-email.html>`_, a `welcome email <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/account/email/welcome.html>`_
will be sent to the new user with further instructions. Add ``--language`` with another language
of the web console, ``es`` (Spanish), ``fr`` (French) or ``pt-br`` (Brazilian Portuguese), to set the
user's preferred language, which is English by default. The welcome email, and the password email
that the ``ENABLE_NEW_USER_PASSWORD_EMAIL`` switch sends, are written in it. Users who sign up in the
web console get the language of their browser, as the console itself does.
``manage.py send_welcome_email`` re-sends the welcome email, in the user's preferred language unless
you give it another ``--language``.

Two days after the welcome email, the user is sent a second email, which invites them to the Slack
workspace of ``SMARTER_BRANDING_URL_SLACK`` (by default The Smarter Project's) and introduces its
channels and its AI agent. A Celery Beat task, ``send_slack_invitation_emails``, sends it hourly to every
account contact who is due it, once per email address, when the ``ENABLE_SLACK_INVITATION_EMAIL``
waffle switch is on. The switch is off by default: turn it on in the Django admin to send the email.
Contacts who were welcomed before the platform recorded the welcome email's date are never sent it.
``manage.py send_slack_invitation_email`` sends it now, to a ``--username`` or to any ``--email``,
including someone who isn't a user. Each contact records when it was sent each email
(``AccountContact.welcomed_at`` and ``slack_invited_at``).

Both emails end with an unsubscribe link, and carry ``List-Unsubscribe`` headers, so that mail clients
show their own unsubscribe button. The link opens a page that asks the recipient to confirm, and
records the time in ``AccountContact.unsubscribed_at`` of every contact with the address, in every
account. An unsubscribed address isn't sent either email again, by the platform or by the management
commands. Notices about the account, such as password resets, are still sent.

Without ``--password``, a new user gets a random password. The command doesn't print it, because its
output usually ends up in deployment logs: the password email sends it, when that switch is on. Add
``--show_password`` to print it, or set another with ``manage.py changepassword <username>``.
