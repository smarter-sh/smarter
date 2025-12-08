Django Settings
===============

The Smarter platform should run out of the box on AWS infrastructure, using the
default settings provided in `smarter.settings.prod`, assuming that you
created your cloud infrastructure using Smarter's Terraform scripts. However,
you may want to customize certain settings for your deployment.
See the complete set of Django settings available to the Smarter
platform at `docs.djangoproject.com <https://docs.djangoproject.com/en/5.2/ref/settings/>`_.


.. toctree::
    :maxdepth: 1

    settings/base
    settings/smarter
