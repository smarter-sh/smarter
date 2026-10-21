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

Each Django app that implements SAM resources has an ``add_example_<kinds>`` command that creates
the example resources of its kinds, from the manifests in its ``data/`` folder, for example
``add_example_guardrails``, ``add_example_tools`` and ``add_example_llmclients``.
``manage.py initialize_platform`` runs them in the order of their dependencies. The
:doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>` is not in the
platform's ``data/`` folders: ``manage.py load_from_github`` applies it from its own GitHub repository. SmarterExamplesCommand is the base class of the newest of them: it resolves the
owner, ``--username``, applies each manifest in a transaction, fills in manifest templates, and
reports the manifests that failed without stopping the others.

.. autoclass:: smarter.lib.django.management.examples.SmarterExamplesCommand
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
