Front End Development with React, Vite.js and Bootstrap
=======================================================

**Why Smarter.** Each page of the web console is a small, separate React app in an npm workspace,
built with Vite and styled with Bootstrap, so a student can work on one page without having to
understand all of them. The workspace has Storybook stories, Vitest tests, Mock Service Worker
mocks, ESLint and Prettier already set up.

**Look at.** ``smarter/react/packages/``: the ``smarter-*-list`` apps are near-identical list
pages, ``smarter-common`` holds the shared code, and ``smarter-chat`` is the chat interface.

**Read.** :doc:`/smarter-framework/smarter-chat/development`,
:doc:`/smarter-framework/smarter-chat/embedding`.

**Exercises.**

- Run ``make react-storybook`` and study a list page's components in isolation, then write a
  new story for a state that has none, such as an empty list or an error.
- Add a column, a filter or a sort to a list page, with a Vitest test.
- Embed a deployed LLMClient in a page of their own with the
  `@smarter.sh/ui-chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__ npm package.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
