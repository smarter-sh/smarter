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
