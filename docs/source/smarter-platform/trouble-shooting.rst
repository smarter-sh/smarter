Trouble Shooting & FAQ
=======================

.. rubric:: Frequently Asked Questions

.. dropdown:: Docker not running?

  Make sure Docker Desktop is open and running before you use any make commands.

.. dropdown:: Port already in use?

  If you get an error about port 8000, make sure nothing else is running on that port, or change the port in your .env and Docker configuration.

.. dropdown:: .env file issues?

  Double-check that your .env file exists in the project root, and that it contains
  ``SMARTER_FERNET_ENCRYPTION_KEY``, which ``make`` adds when it creates the file. No other
  variable is required to run the platform locally: a feature whose setting is missing logs a
  console error, framed by lines of ``=``, that says what to set.

.. dropdown:: Still stuck?

  - Verify that `SMARTER_OPENAI_API_KEY` has been set in your .env file in the root of the repository.
    Without it, the built-in LLMClients answer with an error that names it. After you set it, restart the
    platform and run `docker exec smarter-app python manage.py initialize_providers`.
  - Try running `docker compose ps` to see the status of your containers.
  - Check the Docker Desktop dashboard for error logs.
  - Ask for help: `Lawrence McDaniel <https://lawrencemcdaniel.com>`__
