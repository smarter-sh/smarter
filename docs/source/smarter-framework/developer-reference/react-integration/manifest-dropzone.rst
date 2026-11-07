Manifest Dropzone React Component
===================================

The Manifest Dropzone React component provides a convenient and user-friendly
interface for applying a Smarter SAM manifest. This is web-console alternative
to using the actual Smarter CLI to apply a manifest, and is especially useful
for users who are new to working with Smarter.

The drop zone is a page of the single-page console (:doc:`ADR-035 </adr/035-single-page-app>`), at
``/dashboard/dropzone/``, while ``smarter_settings.enable_dropzone_manifest_apply`` is on. ``@smarter/console``
renders ``@smarter/drop-zone``'s ``ManifestDropzone`` inside its frame, with a context whose api url is the
public api's ``/api/v1/cli/apply/``. The package has no build of its own; ``npm run dev`` in it renders the
drop zone against the Django dev server's api. Django answers the path with the console's page, and keeps
its url name. When the setting is off, the console's session says so and the console shows its Page not found.


.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/manifest-dropzone-react-component.png
   :alt: Manifest Dropzone React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%

.. toctree::
   :maxdepth: 1
   :caption: Manifest Dropzone Component Technical Reference

   manifest-dropzone/django-view
   manifest-dropzone/example-usage
   manifest-dropzone/react-component
