React Integration
=================

Smarter implements a robust strategy for integrating React components into Django
template-based web pages. At a high level, the strategy involves:

1. **Vite**: Smarter uses Vite.js to build and bundle React components,
   emphasizing simplicity. That is, Smarter has a strong bias towards using Vite's
   defaults. Smarter's Vite configuration works for all of a.) React development,
   b.) Django development, and c.) production builds. No configuration changes are
   needed. Key aspects of the Vite configuration include:

    - *Single Entry Point*: Smarter has a single entry point for all React
      components.
    - *Locally-hosted Builds*: Smarter builds directly into Django's static files
      directory, resulting in fewer moving parts in the build process. Built
      assets are served from Django's static files in both development
      as well as production. Importantly, this fully eliminates any added
      complexity due to CORS, CSRF, and Django session management.
    - *manifest.json*: Vite generates a manifest.json file that provides
      a single source of truth for the names and locations of all build assets.
      Note that Vite's default build logic leads to an indetermined number of
      css output files, making the manifest.json file essential for clean and
      thorough builds.
    - *Development Server*: Smarter supports both Vite's development server for React
      development, which provides hot module replacement and other conveniences, and also
      Django's development server for Django development. Smarter's Vite configuration
      works seamlessly in both contexts without any configuration changes.
    - *Production Builds*: Smarter's Vite configuration also works seamlessly
      for production builds, because build assets are persisted to Django's static
      files directory and the manifest.json file is used to reference the correct
      asset names and locations in production as well.
    - *AWS CloudFront*: Smarter's Vite configuration also pushes built assets to
      a public read-only AWS CloudFront distribution, allowing the options of
      hosting built assets from a CDN as well as streamlining the Docker
      build process by eliminating the need to use React build tools inside
      of the Docker build process.
2. **Django Template Tags**: Smarter uses custom Django template tags to parse the
   manifest.json file and generate the appropriate HTML tags for adding the
   built React component in a Django templates.
3. **Component Props**: Smarter passes props from Django to React components via
   Django view context, mapped to data attributes on the HTML elements that
   serve as mounting points for the React components. As a matter of practice
   and consistency, the view always passes all salient cookie names for Django
   session management, CSRF protection, etcetera.
4. **Django Templates**: These are deliberately simple and typically limited to
   nothing more than the mounting points for the React components along with the
   attributes mapping the view context to individual data attributes.

   .. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/view-template-integration1.png
      :alt: View, Template, and React Component Integration
      :width: 100%

.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  react-integration/dashboard
  react-integration/prompt-list
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
