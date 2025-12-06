User Management
===================

**Please review** `Account Management <account-management.html>`_ **before adding users.**

Use the manage.py command to create new Accounts:

.. code-block:: bash

   python manage.py create_user \
     --account-number "####-####-####" \
     --username "newuser" \
     --email "newuser@example.com" \
     --first_name "New" \
     --last_name "User" \
     --password "securepassword" \
     --admin

If you have enabled `SMTP Email Services <smtp-email.html>`_, a `welcom email <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/templates/account/welcome.html>`_
will be sent to the new user with further instructions.
