Management Commands
=====================

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

Example resources
-----------------

The platform's example resources are not in its source tree. Their manifests live in GitHub
repositories of their own, the :doc:`example manifests repository
</smarter-framework/smarter-manifests/example-manifests>` and the :doc:`Stackademy example project
</smarter-framework/smarter-manifests/stackademy>`, and ``manage.py load_from_github`` applies them:
it resolves the owner, applies each manifest in a transaction, in the order of their kinds'
dependencies, fills in manifest templates, and reports the manifests that failed without stopping
the others. ``manage.py initialize_platform`` runs it for both repositories. See
:doc:`/smarter-resources/account/commands/load_from_github`.
