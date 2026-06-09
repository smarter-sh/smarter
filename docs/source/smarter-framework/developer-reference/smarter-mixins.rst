Smarter Mixins
===============

It's the simplest problems that are often the most arduous to solve. Two things in particular come
to mind: handling user accounts and working with HTTP requests. The Smarter Framework provides a
robust set of `Python Mixins <https://realpython.com/python-mixin/>`__ that mostly exist behind the scenes,
implemented throughout the framework as polymorphic class
additions to the Smarter Resources that actually take center stage for developers. What these Mixins
is comically simple:

- **Helper Mixin**: implements a short list of the most commonly used helper methods needed throughout
  the Smarter Framework.

- **Account Mixin**: provides a single source of truth for the user, account and user_profile associated
  with a request, and provides helper methods for authenticating users.

- **Request Mixin**: adds a Smarter-specific set of properties and methods for working with Django's
  HttpRequest object

- **Middleware Mixin**: works as an agent between Middleware and Smarter Resources to marshal
  information between the two. Resolves simple conundrums like determining the 'correct' internal
  IP address of a request when behind proxies, whether or not a request is secure, whether authentication
  headers are present, and more.


.. toctree::
   :maxdepth: 1

   mixins/helper
   mixins/account
   mixins/request
   mixins/middleware
