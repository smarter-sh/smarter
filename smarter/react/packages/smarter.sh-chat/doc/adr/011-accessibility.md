# ADR-011: Accessibility

## Status

Accepted

## Context

The chat is placed on public websites, whose owners are responsible for their accessibility, and floats over their content as a launcher. A launcher that traps the focus, or can't be closed from the keyboard, makes a site harder to use.

## Decision

- Regions and controls are labeled; icon-only buttons have an accessible name, and decorative svgs are `aria-hidden`.
- **The launcher's panel is a labeled region, not a modal dialog.** It doesn't trap the focus, and the page stays usable while it's open. Its button has `aria-expanded` and `aria-controls`, and Escape, anywhere in the panel, closes it and returns the focus to the button. Its accessible name is the `label` option.
- Resizable panels can be resized from the keyboard. Math is rendered as MathML for screen readers, as well as visually.
- ESLint's `jsx-a11y` rules lint every component, and Storybook's `addon-a11y` checks every story.
- Tests query the way users perceive the page: by role and accessible name (ADR-012).

## Alternatives Considered

- **A modal dialog for the launcher.** It would block the page that the visitor is asking about.

## Consequences

- **Positive:**
  - Accessibility regressions surface in lint, in Storybook and in tests that query by role.
- **Negative:**
  - chatscope's own markup is outside our control; fixes there are overrides.

## Related ADRs

- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-012: Testing](012-testing.md)
