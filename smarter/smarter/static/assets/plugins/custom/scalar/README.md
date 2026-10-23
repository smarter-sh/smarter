# Scalar API Reference

Scalar renders the Smarter api's OpenAPI document at `/docs/openapi/`
(`smarter/smarter/templates/docs/openapi.html`).

- Package: [@scalar/api-reference](https://www.npmjs.com/package/@scalar/api-reference) 1.73.1
- Integrity: `sha512-YatOueurjdSAbE3K51L0NkyzdQEpksnjvzCpJTSMPaYd6VWpXMrycDfTBY0myuhszgxk+PcOehExyIXc20yXhw==`
- License: MIT ([github.com/scalar/scalar](https://github.com/scalar/scalar/blob/main/LICENSE))

Only `dist/browser/standalone.js` is vendored, as `standalone.js`. It includes its
own css. Its `sourceMappingURL` comment was removed, since the source map isn't.

The page configures Scalar to call no Scalar service: no telemetry, no default
fonts (fonts.scalar.com), no request proxy (proxy.scalar.com), no "Ask AI" agent
and no developer tools (whose Share and Deploy use Scalar's registry). "Test
Request" sends requests straight to the platform, and a platform without
internet access still renders the page.

To upgrade, `npm pack @scalar/api-reference@<version>`, check its integrity
against `npm view @scalar/api-reference@<version> dist.integrity`, copy
`dist/browser/standalone.js` here, remove its `sourceMappingURL`, update this
file, and check the page's network requests for new external hosts.
