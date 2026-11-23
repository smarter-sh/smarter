Trouble Shooting & FAQ
=======================

.. rubric:: Frequently Asked Questions

.. dropdown:: Docker not running?

  Make sure Docker Desktop is open and running before you use any make commands.

.. dropdown:: Port already in use?

  If you get an error about port 9357, make sure nothing else is running on that port, or change the port in your .env and Docker configuration.

.. dropdown:: .env file issues?

  Double-check that your .env file exists in the project root, and that it contains
  ``SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY``, which ``make`` adds when it creates the file. No other
  variable is required to run the platform locally: a feature whose setting is missing logs a
  console error, framed by lines of ``=``, that says what to set.

.. dropdown:: Still stuck?

  - Verify that `SMARTER_APP_PROVIDER_OPENAI_API_KEY` has been set in your .env file in the root of the repository.
    Without it, the built-in LLMClients answer with an error that names it. After you set it, restart the
    platform and run `docker exec smarter-api python manage.py initialize_providers`.
  - Try running `docker compose ps` to see the status of your containers.
  - Check the Docker Desktop dashboard for error logs.
  - Ask for help, in one of the places below.


Where to go for Help
--------------------

1. **Documentation**: Refer to the official Smarter documentation at `docs.smarter.sh <https://docs.smarter.sh/>`_ for guides, tutorials, and reference materials.
2. **Smarter Community Forum**: For general questions, discussions, and community support, visit the Smarter Community Forum at GitHub at `github.com/smarter-sh/smarter/discussions/ <https://github.com/smarter-sh/smarter/discussions/>`_.
3. **Slack**: For real-time questions and discussion with other Smarter users and contributors, join The Smarter Project's Slack workspace with this `invite link <https://join.slack.com/t/thesmarterproject/shared_invite/zt-4f0t6v46q-e2c5Of4hS4fBr_XwfQARCw>`_. Its bot, @Smarter Developer, answers questions about Smarter at any hour: see :doc:`../slack`.
4. **GitHub Issues**: If you encounter a bug or need to report an issue, please use the GitHub Issues page at `github.com/smarter-sh/smarter/issues/ <https://github.com/smarter-sh/smarter/issues/>`_.
5. **Contact The Author**: For direct support or inquiries, you can reach out to the project author, Lawrence McDaniel via email at `lpm0073@gmail.com <mailto:lpm0073@gmail.com>`_.

Questions about security are answered in the :doc:`system-administration/security/security-faq`.
