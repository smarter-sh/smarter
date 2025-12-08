Django Signals
==============

The Smarter Framework makes extensive use of Django event-driven signals to allow for
custom behavior and extensibility. Signals are used to trigger actions in response to
certain events occurring within the application, such as user registration, data updates,
or system notifications. Django receivers can be connected to these signals to
execute custom logic when the signals are emitted.

Basic Usage
-------------

.. code-block:: python

    from django.dispatch import receiver
    from smarter.apps.plugin.signals import plugin_called

    @receiver(plugin_called, dispatch_uid="plugin_called")
    def handle_plugin_called(sender, plugin):

        logger.info("%s was called.", plugin.name)
