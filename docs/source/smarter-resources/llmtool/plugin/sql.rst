SQL LLMTool Plugin
==================

The SqlPlugin lets an assistant answer from a database. A manifest declares a parameterized SQL
query and describes its parameters in plain words. The model never sees the query: it chooses
the parameter values, and Smarter runs the query with them over a Connection whose credentials
are kept as a Secret. This 60-second video shows it at work.

.. raw:: html

   <iframe width="560" height="315" src="https://www.youtube.com/embed/CmIQVkFM7OI" title="The SqlPlugin in 60 seconds" frameborder="0" allowfullscreen></iframe>

For a full example, see the ``stackademy_sql`` plugin in :doc:`the Stackademy manifests
</smarter-framework/smarter-manifests/stackademy>`.

Technical References
--------------------

- Class Reference: :py:class:`smarter.apps.llmtool.plugin.sql.SqlPlugin`
- Django ORM Model: :py:class:`smarter.apps.llmtool.models.PluginDataSql`
- :doc:`SAM Broker <../sam/brokers/sql-plugin>`
- :doc:`SAM Pydantic Class Reference <../sam/models/sql-plugin>`


.. automodule:: smarter.apps.llmtool.plugin.sql
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:
