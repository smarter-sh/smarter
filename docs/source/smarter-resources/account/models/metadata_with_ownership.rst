MetaDataWithOwnership Model
=============================

Adds the concept of ownership to the base :class:`smarter.lib.django.models.MetaDataModel`
model, which is used as a base for all AI resource models in the Smarter
platform. Ownership is defined in terms of a UserProfile (User + Account)
and is used to determine permissions for reading and editing resources.

Role Based Access Control (RBAC)
--------------------------------

This model extends the base :class:`smarter.lib.django.models.MetaDataModel` model to include ownership based on a UserProfile.
MetaDataWithOwnership inherits from from MetaDataModel and
then it additionally extends the base Django ORM model manager to include
readership and ownership based on a few simple concepts:

1. A UserProfile can be an owner of a MetaDataWithOwnership object, which grants them full permissions to that object.
2. A UserProfile can be a reader of any MetaDataWithOwnership object that is owns, or that is owned by a staff user of
   the same :class:`smarter.apps.account.models.Account`, or that is owned by the Smarter admin user.
3. A UserProfile with staff privileges can act as an owner of any resource owned by a user of the same :class:`smarter.apps.account.models.Account`.
4. The Smarter admin user can act as an owner of any resource in the system.


Example Usage
-----------------

.. code-block:: python

   llm_clients_i_can_see = LLMClient.objects.with_read_permission_for(user=request.user)
   llm_clients_i_can_edit = LLMClient.objects.with_ownership_permission_for(user=request.user)
   llm_clients_shared_with_me = LLMClient.objects.shared_with(user=request.user)
   llm_clients_i_own = LLMClient.objects.owned_by(user=request.user)


.. automodule:: smarter.apps.account.models.metadata_with_ownership
   :members:
   :undoc-members:
   :show-inheritance:
