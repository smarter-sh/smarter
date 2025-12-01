manage.py
=========

Smarter subclasses Django's management command framework in order to
provide more consistent console output and app logging. SmarterCommand
is the base class for all management commands in Smarter, and serves
as a drop-in replacement for Django's base command class.

For more details on the original Django management command interface, see the
:class:`django.core.management.base.BaseCommand` documentation.

Example
-------

.. code-block:: python

    from smarter.lib.django.management.base import SmarterCommand

    class Command(SmarterCommand):
        help = "My custom management command."

        def handle(self, *args, **options):
            self.stdout.write(self.style.SUCCESS("Hello from SmarterCommand!"))

.. autoclass:: smarter.lib.django.management.base.SmarterCommand
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
