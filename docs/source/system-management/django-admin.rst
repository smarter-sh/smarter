Django Admin
==============

Smarter's admin console is customized.
See `smarter/urls/console.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/urls/console.py>`
for further details on the URL configuration.

You'll need an admin user account to log into the Django admin interface. If you don't have one yet, you can create one by running the following command
from your Smarter installation directory:

.. code-block:: bash

   python manage.py createsuperuser

Once you have an admin user account, you can log into the Django admin
interface by navigating to `/admin/` on your Smarter instance (e.g.,
`https://platform.example.com/admin/`).

.. image:: https://cdn.smarter.sh/images/smarter-admin-login.png
    :width: 75 %
    :alt: Smarter Admin Login

After logging in, you'll have access to the Django admin interface, where you
can manage CRUD operations for all Django models registered with the admin site.

.. image:: https://cdn.smarter.sh/images/smarter-django-admin.png
   :width: 75%
   :alt: Smarter Django Admin
