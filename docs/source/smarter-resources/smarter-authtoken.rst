Smarter Authtoken
==================

Overview
--------

Overview
--------

Smarter Authtoken is a Django REST Framework API authentication token that can be
associated with any Smarter resource, rather than being limited to a user account.
This allows access to be scoped precisely: individual users and services can each
be issued a token limited to a specific resource, rather than sharing one broad
credential across an entire integration.

This gives the engineer or product manager building an AI solution direct control
over who, and what, can reach a given resource. A single automated service or
team member can be issued a token restricted to exactly the resource it needs,
with no broader access implied.

Technical Reference
-------------------

See: :doc:`Smarter Django REST Framework <smarter-framework/developer-reference/lib/drf>`
