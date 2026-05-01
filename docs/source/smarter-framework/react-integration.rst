React Integration
=================

Smarter implements a robust strategy for integrating React components into Django
template-based web pages. At a high level, the strategy involves:

1. **Vite**: Smarter uses Vite.js to build and bundle our React components,
   emphasizing simplicity. That is, we have a strong bias towards using Vite's
   defaults. Smarter's Vite configuration works for all of a.) React development,
   b.) Django development, and c.) production builds. No configuration changes are
   needed. Key aspects of our Vite configuration include:

    - **Single Entry Point**: Smarter has a single entry point for all React
      components.
    - **Build Destination**: Smarter builds directly into Django's static files
      directory, resulting in fewer moving parts in the build process.
    - **manifest.json**: Vite generates a manifest.json file that provides
      a single source of truth for the names and locations of all build assets.
      Note that Vite's default build logic leads to an indetermined number of
      css output files, making the manifest.json file essential for clean and
      thorough builds.
2. **Django Template Tags**: Smarter uses custom Django template tags to parse the
   manifest.json file and generate the appropriate HTML tags for including the
   built React components in our Django templates.
3. **Component Props**: Smarter passes props from Django to React components via
   Django view context, mapped to data attributes on the HTML elements that
   serve as mounting points for the React components. As a matter of practice
   and consistency, the view always passes all salient cookie names for Django
   session management, CSRF protection, etcetera. See this example Django template
   ``smarter/templates/react/terminal-emulator.html``.
4. **Django Templates**: These are deliberately simple and typically limited to
   nothing more than the mounting points for the React components along with the
   attributes mapping the view context to individual data attributes.



.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  react-integration/terminal-application
  react-integration/prompt-passthrough
  react-integration/smarter-chat

.. toctree::
  :maxdepth: 1
  :caption: Code Samples

  react-integration/example-vite
  react-integration/example-template-tag
  react-integration/example-template
  react-integration/example-view
  react-integration/example-react-mount
