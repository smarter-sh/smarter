Troubleshooting & FAQ
=====================

.. rubric:: Frequently Asked Questions

.. dropdown:: Docker not running?

  Make sure Docker Desktop is open and running before you use any make commands.

.. dropdown:: Port already in use?

  If you get an error about port 8000, make sure nothing else is running on that port, or change the port in your .env and Docker configuration.

.. dropdown:: .env file issues?

  Double-check that your .env file exists in the project root and contains all required variables.

.. dropdown:: Still stuck?

  - Verify that `OPENAI_API_KEY` has been set in your .env file in the root of the repository.
  - Try running `docker compose ps` to see the status of your containers.
  - Check the Docker Desktop dashboard for error logs.
  - Ask for help: `Lawrence McDaniel <https://lawrencemcdaniel.com>`__
